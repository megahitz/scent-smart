"""Pure-protocol client for the Scent GAS-501F diffuser (YooAI ScentLife app).

No Home Assistant imports here: frame building, checksum, timer packing and
state parsing are pure functions so they can be tested without a device.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any

from .const import (
    CMD_OPERATION,
    CMD_SET_TIME,
    CMD_TIMER,
    FRAME_HEAD,
    FRAME_TAIL,
    TIMER_MODE_EVERY_DAY,
    TIMER_PAYLOAD_LEN,
    TIMER_TAIL,
)


def checksum(frame: bytes) -> int:
    """CK = 256 - (sum of bytes from 0x55 through end of payload) % 256; 0 if mod==0."""
    total = sum(frame) % 256
    return (256 - total) % 256 if total else 0


def build_frame(cmd: int, payload: bytes) -> bytes:
    """Build 55 AA | LEN | CMD | payload | CK | 5A."""
    body = FRAME_HEAD + bytes((len(payload) + 1, cmd)) + payload
    return body + bytes((checksum(body), FRAME_TAIL))


def op_frame(func: int, value: int) -> bytes:
    """CMD 0x07 operation: [func, val, 0x00]."""
    return build_frame(CMD_OPERATION, bytes((func, value & 0xFF, 0x00)))


def numeric_frame(func: int, value: int) -> bytes:
    """CMD 0x07 numeric: [func, val_lo, val_hi] (u16 LE)."""
    return build_frame(CMD_OPERATION, bytes((func,)) + struct.pack("<H", value & 0xFFFF))


def time_sync_frame(unixtime: int) -> bytes:
    """CMD 0x06: u32 LE unixtime."""
    return build_frame(CMD_SET_TIME, struct.pack("<I", unixtime & 0xFFFFFFFF))


@dataclass
class TimerState:
    """One timer/period group (TimerVo)."""

    enable: bool = True
    serial: int = 1  # 1..5
    mode: int = TIMER_MODE_EVERY_DAY  # weekday bitmask, 0x00FF = every day
    start: int = 480  # minute-of-day
    stop: int = 1320  # minute-of-day
    run: int = 60  # seconds, 5..200 step 5
    suspend: int = 200  # seconds, 20..300 step 5
    tail: int = TIMER_TAIL  # u32 LE constant 0x00000001

    def clamp(self) -> "TimerState":
        from .const import RUN_MAX, RUN_MIN, SUSPEND_MAX, SUSPEND_MIN

        self.run = max(RUN_MIN, min(RUN_MAX, self.run))
        self.suspend = max(SUSPEND_MIN, min(SUSPEND_MAX, self.suspend))
        self.start = max(0, min(1439, self.start))
        self.stop = max(0, min(1439, self.stop))
        self.serial = max(1, min(5, self.serial))
        return self

    def to_payload(self) -> bytes:
        """Pack to the validated 16-byte TimerVo layout."""
        self.clamp()
        return bytes((1 if self.enable else 0, self.serial)) + struct.pack(
            "<HHHHHI", self.mode, self.start, self.stop, self.run, self.suspend, self.tail
        )

    @classmethod
    def from_payload(cls, data: bytes) -> "TimerState | None":
        if len(data) != TIMER_PAYLOAD_LEN:
            return None
        enable, serial = data[0], data[1]
        mode, start, stop, run, suspend, tail = struct.unpack("<HHHHHI", data[2:16])
        return cls(
            enable=bool(enable), serial=serial, mode=mode, start=start,
            stop=stop, run=run, suspend=suspend, tail=tail,
        )


def timer_frame(timer: TimerState) -> bytes:
    """CMD 0x14 frame for one timer group."""
    return build_frame(CMD_TIMER, timer.to_payload())


# 16-byte timer tail pattern used to locate timers inside 0x21 state dumps:
# ... [10:12] suspend LE | tail 01 00 00 00
TIMER_TAIL_BYTES = struct.pack("<I", TIMER_TAIL)


@dataclass
class DeviceState:
    """Parsed 0x21 state dump (defensive: unknown bytes kept raw)."""

    running: bool | None = None
    fan: bool | None = None
    child_lock: bool | None = None
    ambient_light: int | None = None
    active_serial: int | None = None
    active_timer: TimerState | None = None
    programs: dict[int, TimerState] = field(default_factory=dict)
    unknown: dict[str, Any] = field(default_factory=dict)
    raw_hex: str = ""

    def as_dict(self) -> dict[str, Any]:
        t = self.active_timer
        return {
            "running": self.running,
            "fan": self.fan,
            "child_lock": self.child_lock,
            "ambient_light": self.ambient_light,
            "active_program": self.active_serial,
            "run_time": t.run if t else None,
            "pause_time": t.suspend if t else None,
            "window_start": t.start if t else None,
            "window_stop": t.stop if t else None,
            "window_enabled": t.enable if t else None,
            "raw_dump": self.raw_hex,
            "unknown_fields": self.unknown,
        }


def _looks_like_timer(data: bytes, idx: int) -> TimerState | None:
    """Check for a TimerVo at idx: enable 0/1, serial 1..5 or 0xFF (active marker), tail 01 00 00 00."""
    if idx + TIMER_PAYLOAD_LEN > len(data):
        return None
    chunk = data[idx : idx + TIMER_PAYLOAD_LEN]
    if chunk[0] not in (0, 1) or not (chunk[1] in (1, 2, 3, 4, 5) or chunk[1] == 0xFF):
        return None
    if chunk[12:16] != TIMER_TAIL_BYTES:
        return None
    return TimerState.from_payload(chunk)


def parse_state(frame: bytes) -> DeviceState:
    """Parse a NOTIFY frame; cmd 0x21 dumps include timers and flags.

    The full layout beyond the validated timer block and short ACKs is not
    documented, so anything unrecognised is stored as raw hex in
    DeviceState.unknown rather than guessed.
    """
    st = DeviceState(raw_hex=frame.hex())
    if len(frame) < 4 or frame[0:2] != FRAME_HEAD:
        return st
    length, cmd = frame[2], frame[3]
    payload = frame[4 : 4 + max(0, length - 1)]
    if len(payload) + 1 != length or (len(frame) >= 4 + length + 2 and frame[4 + length] != checksum(frame[: 4 + length])):
        st.unknown["frame"] = "malformed length or checksum"
    if cmd == 0x87:  # ACK to CMD 0x07
        st.unknown["ack_07"] = payload.hex()
        return st
    if cmd == 0x94:  # ACK to CMD 0x14
        st.unknown["ack_14"] = payload.hex()
        return st
    if cmd != 0x21:
        st.unknown[f"cmd_{cmd:02x}"] = payload.hex()
        return st

    # Locate timers: scan for the 16-byte TimerVo pattern.
    idx = 0
    active_marker = None
    while idx <= len(payload) - TIMER_PAYLOAD_LEN:
        t = _looks_like_timer(payload, idx)
        if t:
            if t.serial == 0xFF:
                # 0xFF = "timer ativo" — normaliza pro programa 1 e lembra.
                active_marker = t
                st.unknown["active_serial_marker"] = "0xFF"
                t.serial = 1
            st.programs[t.serial] = t
            idx += TIMER_PAYLOAD_LEN
        else:
            idx += 1

    if st.programs:
        # Active program = the one present (device echoes current group);
        # prefer the 0xFF marker, then serial 1.
        serials = sorted(st.programs)
        if active_marker is not None:
            st.active_serial = 1
        else:
            st.active_serial = serials[0] if 1 in serials else serials[-1]
        st.active_timer = st.programs[st.active_serial]

    # Unmapped leading bytes (device flags: pump state, oil level etc.).
    if st.programs and idx is not None:
        first_timer_at = payload.find(st.programs[st.active_serial].to_payload())
        if first_timer_at > 0:
            prefix = payload[:first_timer_at]
            st.unknown["prefix"] = prefix.hex()
            # Estado do ciclo (confirmado empíricamente): u16 LE no prefix[4:6].
            # 0x000B = ciclo ativo rodando; 0x0002/0x0003 = parado/idle.
            if len(prefix) >= 6:
                code = int.from_bytes(prefix[4:6], "little")
                st.unknown["state_code"] = code
                st.running = (code == 0x0B)

    # Trailing bytes after the last timer block.
    if st.programs:
        last = max(payload.rfind(t.to_payload()) for t in st.programs.values())
        end = last + TIMER_PAYLOAD_LEN
        if end < len(payload):
            st.unknown["suffix"] = payload[end:].hex()

    return st


def split_notify(data: bytes) -> list[bytes]:
    """Split a notification buffer into complete frames (55 AA ... 5A)."""
    frames: list[bytes] = []
    pos = 0
    while True:
        start = data.find(FRAME_HEAD, pos)
        if start < 0:
            break
        if len(data) < start + 4:
            break
        length = data[start + 2]
        end = start + 4 + length + 1  # head(2)+len+cmd+payload+ck+tail(1)
        if len(data) >= end and data[end - 1] == FRAME_TAIL:
            frames.append(data[start:end])
            pos = end
        else:
            break
    return frames
