"""Entity calls remain passive except for explicit, supported actions."""
import importlib
import types
import unittest
from test_actions import module, updates

registry = module('homeassistant.helpers.device_registry')
registry.DeviceInfo = lambda **kw: kw
class CoordinatorEntity:
    def __class_getitem__(cls, item): return cls
    def __init__(self, coordinator):
        self.coordinator = coordinator
        self.hass = types.SimpleNamespace()
    def async_write_ha_state(self): pass
updates.CoordinatorEntity = CoordinatorEntity
for platform, cls in [('number', 'NumberEntity'), ('switch', 'SwitchEntity'), ('button', 'ButtonEntity')]:
    setattr(module('homeassistant.components.' + platform), cls, type(cls, (), {}))
sensor_mod = module('homeassistant.components.sensor')
sensor_mod.SensorEntity = type('SensorEntity', (), {})
number = importlib.import_module('scent_smart_fixed.number')
sensor = importlib.import_module('scent_smart_fixed.sensor')
switch = importlib.import_module('scent_smart_fixed.switch')
button = importlib.import_module('scent_smart_fixed.button')

class DummyCoordinator:
    address = 'test'
    data = None
    last_update_success = True
    def __init__(self): self.calls = []
    async def async_change_timer(self, field, value): self.calls.append((field, value))
    async def async_send_operation(self, func, value): self.calls.append((func, value))
    async def async_spray_now(self): self.calls.append(('spray',))

class Entities(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.c = DummyCoordinator()
        self.entry = types.SimpleNamespace(entry_id='1', options={}, data={})

    async def test_numbers_delegate_without_defaults_or_options(self):
        await number.SprayDurationNumber(self.c, self.entry).async_set_native_value(15)
        await number.PauseTimeNumber(self.c, self.entry).async_set_native_value(300)
        self.assertEqual(self.c.calls, [('run', 15), ('suspend', 300)])

    async def test_button_delegates_to_safe_spray_transaction(self):
        obj = button.ScentSmartSprayNow(self.c, self.entry)
        self.assertTrue(obj.available)
        await obj.async_press()
        self.assertEqual(self.c.calls, [('spray',)])

    async def test_program_switch_unavailable_and_no_writes(self):
        obj = switch.ScentSmartProgramSwitch(self.c, self.entry, 1)
        self.assertFalse(obj.available)
        with self.assertRaises(Exception): await obj.async_turn_on()
        self.assertEqual(self.c.calls, [])

    async def test_sensor_does_not_invent_off_state(self):
        from test_protocol import client
        self.c.data = client.DeviceState()
        obj = sensor.ScentSmartStateSensor(self.c, self.entry, 'state')
        self.assertIsNone(obj.native_value)

    def test_no_window_editor_or_defaults_options(self):
        from pathlib import Path
        text = (Path(number.__file__).parent / 'config_flow.py').read_text()
        self.assertNotIn('default_window_start', text)
        self.assertNotIn('async_get_options_flow', text)

    async def test_switch_does_not_optimistically_claim_success(self):
        obj = switch.ScentSmartToggle(self.c, self.entry, 'working_mode', 0x12)
        await obj.async_turn_on()
        self.assertEqual(self.c.calls, [(0x12, 1)])
        self.assertIsNone(obj.is_on)
