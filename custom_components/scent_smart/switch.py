"""Master switch; legacy switches remain present but unavailable."""
from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN, FUNC_CHILD_LOCK, FUNC_FAN, FUNC_RUNNING_STATUS, NUM_PROGRAMS
from .entity import ScentSmartEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    funcs = {'working_mode': FUNC_RUNNING_STATUS, 'fan': FUNC_FAN, 'child_lock': FUNC_CHILD_LOCK}
    entities = [ScentSmartToggle(coordinator, entry, key, func) for key, func in funcs.items()]
    entities += [ScentSmartProgramSwitch(coordinator, entry, i) for i in range(1, NUM_PROGRAMS + 1)]
    async_add_entities(entities)


class ScentSmartToggle(ScentSmartEntity, SwitchEntity):
    def __init__(self, coordinator, entry, key, func):
        super().__init__(coordinator, entry, key)
        self._func = func
        self._attr_translation_key = key

    @property
    def available(self):
        return self._func == FUNC_RUNNING_STATUS and super().available

    @property
    def is_on(self):
        return self.state_obj.running if self.state_obj and self._func == FUNC_RUNNING_STATUS else None

    async def async_turn_on(self, **kwargs):
        await self.coordinator.async_send_operation(self._func, 1)

    async def async_turn_off(self, **kwargs):
        await self.coordinator.async_send_operation(self._func, 0)


class ScentSmartProgramSwitch(ScentSmartEntity, SwitchEntity):
    def __init__(self, coordinator, entry, serial):
        super().__init__(coordinator, entry, f'program_{serial}_enabled')
        self._serial = serial
        self._attr_name = f'Programa {serial}'

    @property
    def available(self):
        return False

    @property
    def is_on(self):
        return None

    async def async_turn_on(self, **kwargs):
        raise RuntimeError('Alteração de programa não está disponível')

    async def async_turn_off(self, **kwargs):
        raise RuntimeError('Alteração de programa não está disponível')
