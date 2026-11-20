"""Action-level tests against a simulated BLE transport, not hardware."""
import asyncio
import importlib
import pathlib
import sys
import types
import unittest
from unittest.mock import patch
from test_protocol import client, REAL


def module(name):
    obj = types.ModuleType(name)
    sys.modules[name] = obj
    return obj

bleak = module('bleak')
bleak.BleakClient = type('BleakClient', (), {})
bleak.BleakError = type('BleakError', (Exception,), {})
connector = module('bleak_retry_connector')
connector.establish_connection = None
ha = module('homeassistant')
components = module('homeassistant.components')
bluetooth = module('homeassistant.components.bluetooth')
bluetooth.async_ble_device_from_address = lambda *a, **k: object()
components.bluetooth = bluetooth
entries = module('homeassistant.config_entries')
entries.ConfigEntry = type('ConfigEntry', (), {})
core = module('homeassistant.core')
core.HomeAssistant = type('HomeAssistant', (), {})
helpers = module('homeassistant.helpers')
updates = module('homeassistant.helpers.update_coordinator')
class DataUpdateCoordinator:
    def __class_getitem__(cls, item): return cls
    def __init__(self, hass, *args, **kwargs):
        self.hass, self.data, self.last_update_success = hass, None, True
    def async_set_updated_data(self, data): self.data = data
updates.DataUpdateCoordinator = DataUpdateCoordinator
updates.UpdateFailed = type('UpdateFailed', (Exception,), {})
coordinator = importlib.import_module('scent_smart_fixed.coordinator')

class Transport:
    def __init__(self):
        self.writes = []
        self.records = bytearray(REAL[4:-2])
        self.callback = None
        self.is_connected = True
        self.query_count = 0
        self.fail_query = False
        self.fail_second_query = False
        self.corrupt_second = False
        self.reject_write = False
        self.status_word = None
        self.dynamic_status = False
    async def start_notify(self, uuid, callback): self.callback = callback
    async def disconnect(self): self.is_connected = False
    async def write_gatt_char(self, uuid, frame, response=False):
        self.writes.append(frame)
        cmd, payload = client.validate_frame(frame)
        if cmd == 8:
            self.query_count += 1
            if not self.fail_query and not (self.fail_second_query and self.query_count == 2):
                records = bytearray(self.records)
                if self.corrupt_second and self.query_count == 2:
                    records[14] ^= 1  # valid frame but wrong timer ID
                reply = client.build_frame(0x88, bytes(records))
                for i in range(0, len(reply), 7): self.callback(None, reply[i:i+7])
        elif cmd == 0x14:
            if not self.reject_write:
                self.records[2:18] = payload
            self.callback(None, client.build_frame(0x94, b'\0'))
        elif cmd == 7 and (self.status_word is not None or self.dynamic_status):
            record15 = bytes(self.records[3:18])
            work = (0x0b if payload[1] else 0x02) if self.dynamic_status else self.status_word
            p = b'\0\0\1\0' + work.to_bytes(2, 'little') + b'\x64\0' + record15
            self.callback(None, client.build_frame(0x21, p))

class Actions(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.transport = Transport()
        async def connect(*args, **kwargs): return self.transport
        self.patcher = patch.object(coordinator, 'establish_connection', connect)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.c = coordinator.ScentSmartCoordinator(object(), object(), 'test')
        coordinator.ACK_WAIT_S = 0.01

    async def test_spray_reapplies_the_identical_program_when_mode_known_on(self):
        self.c._latest = client.DeviceState(running=True)
        await self.c.async_spray_now()
        self.assertEqual([f[3] for f in self.transport.writes], [8, 0x14, 8])
        self.assertEqual(self.transport.writes[1][4:-2], REAL[6:22])
        self.assertTrue(self.c.data.running)
        self.assertEqual(self.c.data.active_timer.run, 15)
        self.assertEqual(self.c.data.active_timer.suspend, 300)

    async def test_spray_checks_running_after_acquiring_lock(self):
        self.c._latest = client.DeviceState(running=True)
        self.transport.dynamic_status = True
        await self.c._lock.acquire()
        real_sleep = asyncio.sleep
        try:
            with patch.object(coordinator.asyncio, 'sleep', new=unittest.mock.AsyncMock()):
                task = asyncio.create_task(self.c.async_spray_now())
                await real_sleep(0)
                self.c._latest = client.DeviceState(running=False)
                self.c._lock.release()
                await task
        finally:
            if self.c._lock.locked():
                self.c._lock.release()
        self.assertEqual([f[3] for f in self.transport.writes], [8, 7, 7, 8])

    async def test_spray_never_connects_if_mode_unknown(self):
        self.c._latest = client.DeviceState(running=None)
        with self.assertRaises(coordinator.UpdateFailed):
            await self.c.async_spray_now()
        self.assertEqual(self.transport.writes, [])

    async def test_spray_when_off_restores_off_without_rewriting_program(self):
        self.c._latest = client.DeviceState(running=False)
        self.transport.dynamic_status = True
        with patch.object(coordinator.asyncio, 'sleep', new=unittest.mock.AsyncMock()) as sleep:
            await self.c.async_spray_now()
        self.assertEqual([f[3] for f in self.transport.writes], [8, 7, 7, 8])
        self.assertEqual(self.transport.writes[1], client.op_frame(0x12, 1))
        self.assertEqual(self.transport.writes[2], client.op_frame(0x12, 0))
        sleep.assert_awaited_once_with(15)
        self.assertFalse(self.c.data.running)
        self.assertEqual(self.c.data.active_timer.run, 15)
        self.assertEqual(self.c.data.active_timer.suspend, 300)

    async def test_cancelled_spray_attempts_to_restore_off(self):
        self.c._latest = client.DeviceState(running=False)
        self.transport.dynamic_status = True
        with patch.object(coordinator.asyncio, 'sleep', new=unittest.mock.AsyncMock(side_effect=asyncio.CancelledError)):
            with self.assertRaises(asyncio.CancelledError):
                await self.c.async_spray_now()
        self.assertEqual([f[3] for f in self.transport.writes], [8, 7, 7])
        self.assertEqual(self.transport.writes[-1], client.op_frame(0x12, 0))

    async def test_spray_does_not_enable_disabled_program(self):
        self.c._latest = client.DeviceState(running=True)
        self.transport.records[2] = 0
        with self.assertRaises(coordinator.UpdateFailed):
            await self.c.async_spray_now()
        self.assertEqual([f[3] for f in self.transport.writes], [8])

    async def test_run_update_query_write_readback_preserves_fields(self):
        self.assertTrue(hasattr(self.c, 'async_change_timer'), 'transaction missing')
        await self.c.async_change_timer('run', 20)
        self.assertEqual([f[3] for f in self.transport.writes], [8, 0x14, 8])
        before = REAL[6:22]
        after = self.transport.writes[1][4:-2]
        self.assertEqual(after[:8], before[:8])
        self.assertEqual(after[8:10], b'\x14\0')
        self.assertEqual(after[10:], before[10:])
        self.assertEqual(self.c.data.active_timer.run, 20)
        self.assertEqual(self.c.data.active_timer.suspend, 300)

    async def test_ack_is_not_confirmation(self):
        self.transport.reject_write = True
        with self.assertRaises(coordinator.UpdateFailed):
            await self.c.async_change_timer('run', 20)
        self.assertIsNone(self.c.data)

    async def test_failed_query_causes_no_write(self):
        self.transport.fail_query = True
        with self.assertRaises(coordinator.UpdateFailed):
            await self.c.async_change_timer('run', 20)
        self.assertEqual([x[3] for x in self.transport.writes], [8])
        self.assertIsNone(self.c.data)

    async def test_switch_requires_post_write_dump(self):
        self.transport.status_word = 0x0b
        await self.c.async_send_operation(0x12, 1)
        self.assertTrue(self.c.data.running)
        self.assertEqual([x[3] for x in self.transport.writes], [7])

    async def test_switch_failure_is_not_success(self):
        with self.assertRaises(coordinator.UpdateFailed): await self.c.async_send_operation(0x12, 1)
        self.assertIsNone(self.c.data)

    async def test_forbidden_reset(self):
        with self.assertRaises(coordinator.UpdateFailed): await self.c.async_send_operation(1, 0)
        self.assertEqual(self.transport.writes, [])

    async def test_timeout_after_write_retains_prior_state(self):
        old = client.DeviceState(running=False)
        self.c._latest = old
        self.c.data = old
        self.transport.fail_second_query = True
        with self.assertRaises(coordinator.UpdateFailed):
            await self.c.async_change_timer('run', 20)
        self.assertIs(self.c.data, old)
        self.assertEqual([f[3] for f in self.transport.writes], [8, 0x14, 8])

    async def test_matching_intervals_with_wrong_id_fails(self):
        self.transport.corrupt_second = True
        with self.assertRaises(coordinator.UpdateFailed):
            await self.c.async_change_timer('run', 20)
        self.assertIsNone(self.c.data)

    async def test_switch_off_uses_work_state_lsb(self):
        self.transport.status_word = 2
        await self.c.async_send_operation(0x12, 0)
        self.assertIs(self.c.data.running, False)

    async def test_switch_mismatch_does_not_update(self):
        self.transport.status_word = 2
        with self.assertRaises(coordinator.UpdateFailed):
            await self.c.async_send_operation(0x12, 1)
        self.assertIsNone(self.c.data)

    async def test_pause_update_preserves_disabled_program_and_custom_id(self):
        self.transport.records[2] = 0
        self.transport.records[14:18] = bytes.fromhex('78563412')
        await self.c.async_change_timer('suspend', 295)
        written = self.transport.writes[1][4:-2]
        self.assertEqual(written[0], 0)
        self.assertEqual(written[8:12], bytes.fromhex('0f002701'))
        self.assertEqual(written[12:16], bytes.fromhex('78563412'))

    async def test_invalid_interval_never_connects(self):
        for field, value in [('run', 201), ('run', 16), ('suspend', 15), ('suspend', 300.5)]:
            with self.assertRaises(ValueError): await self.c.async_change_timer(field, value)
        self.assertEqual(self.transport.writes, [])
        self.assertIsNone(self.c._client)

    async def test_15_300_confirmed_as_a_pair(self):
        await self.c.async_change_timer('run', 15)
        self.assertEqual(self.c.data.active_timer.run, 15)
        self.assertEqual(self.c.data.active_timer.suspend, 300)
        self.assertEqual([f[3] for f in self.transport.writes], [8, 0x14, 8])

    def test_setup_does_not_start_boot_session(self):
        source = (pathlib.Path(coordinator.__file__).parent / '__init__.py').read_text()
        self.assertNotIn('async_boot_connect', source)

if __name__ == '__main__': unittest.main()
