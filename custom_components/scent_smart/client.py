"""Pure, strictly validated GAS-501F framing and state decoding."""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

from .const import FRAME_HEAD, FRAME_TAIL


def checksum(data: bytes) -> int:
    return -sum(data) & 0xff


def build_frame(cmd: int, payload: bytes) -> bytes:
    if not 0 <= cmd <= 255 or len(payload) > 254:
        raise ValueError('frame too long or command invalid')
    body = FRAME_HEAD + bytes((len(payload) + 1, cmd)) + payload
    return body + bytes((checksum(body), FRAME_TAIL))


def op_frame(func: int, value: int) -> bytes:
    if func == 1:
        raise ValueError('operation 0x01 resets the program and is forbidden')
    if value not in (0, 1):
        raise ValueError('invalid switch value')
    return build_frame(7, bytes((func, value, 0)))


@dataclass
class TimerState:
    enable: bool | None
    serial: int
    mode: int
    start: int
    stop: int
    run: int
    suspend: int
    tail: int

    def to_payload(self) -> bytes:
        if self.enable is None:
            raise ValueError('status timer has no enable flag')
        return struct.pack('<BBHHHHHI', int(self.enable), self.serial, self.mode,
                           self.start, self.stop, self.run, self.suspend, self.tail)

    @classmethod
    def from_payload(cls, data: bytes) -> TimerState:
        if len(data) != 16 or data[0] not in (0, 1):
            raise ValueError('invalid timer record')
        enable, serial, mode, start, stop, run, suspend, tail = struct.unpack('<BBHHHHHI', data)
        return cls(bool(enable), serial, mode, start, stop, run, suspend, tail)


def timer_frame(timer: TimerState) -> bytes:
    return build_frame(0x14, timer.to_payload())


def validate_frame(frame: bytes) -> tuple[int, bytes]:
    if (len(frame) < 6 or frame[:2] != FRAME_HEAD or frame[2] < 1
            or len(frame) != frame[2] + 5 or frame[-1] != FRAME_TAIL
            or checksum(frame[:-2]) != frame[-2]):
        raise ValueError('invalid, incomplete or corrupt frame')
    return frame[3], frame[4:-2]


def parse_timer_list(frame: bytes) -> dict[int, TimerState]:
    cmd, payload = validate_frame(frame)
    if cmd != 0x88 or len(payload) < 2:
        raise ValueError('not a timer-list response')
    count = int.from_bytes(payload[:2], 'little')
    if count != 5 or len(payload) != 2 + count * 16:
        raise ValueError('incomplete or unexpected timer list')
    timers = {}
    for offset in range(2, len(payload), 16):
        timer = TimerState.from_payload(payload[offset:offset + 16])
        if timer.serial not in range(1, 6) or timer.serial in timers:
            raise ValueError('invalid or duplicate timer serial')
        timers[timer.serial] = timer
    return timers


@dataclass
class DeviceState:
    running: bool | None = None
    fan: bool | None = None
    child_lock: bool | None = None
    ambient_light: int | None = None
    active_serial: int | None = None
    active_timer: TimerState | None = None
    programs: dict[int, TimerState] = field(default_factory=dict)
    unknown: dict[str, Any] = field(default_factory=dict)
    raw_hex: str = ''

    def as_dict(self) -> dict[str, Any]:
        timer = self.active_timer
        return {'running': self.running, 'fan': self.fan, 'child_lock': self.child_lock,
                'ambient_light': self.ambient_light, 'active_program': self.active_serial,
                'run_time': timer.run if timer else None, 'pause_time': timer.suspend if timer else None,
                'window_start': timer.start if timer else None, 'window_stop': timer.stop if timer else None,
                'window_enabled': timer.enable if timer else None, 'raw_dump': self.raw_hex,
                'unknown_fields': self.unknown}


def parse_state(frame: bytes) -> DeviceState:
    cmd, payload = validate_frame(frame)
    if cmd != 0x21 or len(payload) < 4:
        raise ValueError('not a status dump')
    count = int.from_bytes(payload[2:4], 'little')
    offset = 4 + count * 2
    if count < 1 or offset + 2 + 15 > len(payload):
        raise ValueError('truncated status dump')
    work = int.from_bytes(payload[4:6], 'little')
    record = payload[offset + 2:offset + 17]
    serial, mode, start, stop, run, pause, timer_id = struct.unpack('<BHHHHHI', record)
    timer = TimerState(None, serial, mode, start, stop, run, pause, timer_id)
    return DeviceState(running=bool(work & 1), active_serial=serial, active_timer=timer,
                       unknown={'state_code': work}, raw_hex=frame.hex())


def split_notify(data: bytes) -> list[bytes]:
    return FrameStream().feed(data)


class FrameStream:
    """Reassemble notifications; a corrupt frame is discarded, never delivered."""
    def __init__(self) -> None:
        self.buffer = bytearray()

    def feed(self, data: bytes) -> list[bytes]:
        self.buffer.extend(data)
        result = []
        while True:
            start = self.buffer.find(FRAME_HEAD)
            if start < 0:
                self.buffer[:] = self.buffer[-1:] if self.buffer[-1:] == b'\x55' else b''
                break
            del self.buffer[:start]
            if len(self.buffer) < 3:
                break
            if self.buffer[2] == 0:
                del self.buffer[0]
                continue
            size = self.buffer[2] + 5
            if len(self.buffer) < size:
                break
            frame = bytes(self.buffer[:size])
            try:
                validate_frame(frame)
            except ValueError:
                del self.buffer[0]
                continue
            del self.buffer[:size]
            result.append(frame)
        return result
