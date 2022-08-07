from typing import Optional, cast

from homeassistant.components.sensor import (RestoreSensor, SensorDeviceClass,
                                             SensorStateClass)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (ATTR_UNIT_OF_MEASUREMENT, CONF_DEVICE,
                                 ENERGY_KILO_WATT_HOUR, ENERGY_MEGA_WATT_HOUR,
                                 ENERGY_WATT_HOUR)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (Event, State,
                                         async_track_state_change_event)

from . import CONF_INPUTS, CONF_OUTPUTS


class DeltaHistory:
    buffer = 0

    def __init__(self, keys: list[str], commited: int = 0):
        self.commited = commited
        self.keys = keys
        self.pendings = list[tuple[int, set[str]]]()

    def append(self, value: int):
        if not value:
            return
        self.pendings.append((value, set(self.keys)))

    def revert(self, key: str, value: int):
        i = 0
        while i < len(self.pendings):
            d, s = self.pendings[i]
            if key not in s:
                i += 1
                continue
            s.remove(key)
            if value > d:
                value -= d
                d = 0
            else:
                d -= value
                value = 0
            self.pendings[i] = (d, s)
            i += 1

        for d, s in self.pendings:
            if not s:
                if self.buffer == 0 and d >= 1:
                    self.buffer = 1
                    d -= 1
                self.commited += d

        self.pendings = [x for x in self.pendings if x[0] != 0 and x[1]]

        if value and self.buffer == 1:
            value -= 1
            self.buffer = 0

        return value

    @property
    def total(self):
        return self.commited + self.buffer + sum(d for d, s in self.pendings)


class BaseEntity(RestoreSensor):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = ENERGY_WATT_HOUR
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, device: Optional[DeviceInfo], mode: str, name: str):
        self._entry = entry
        self._mode = mode
        self._attr_name = name
        self._attr_device_info = device
        self._attr_unique_id = entry.entry_id + "-" + mode

    @property
    def device_info(self):
        dr = device_registry.async_get(self.hass)
        if devid := self._entry.options.get(CONF_DEVICE, None):
            if device := dr.async_get(devid):
                return DeviceInfo(identifiers=device.identifiers)
        return None


class TotalEntity(BaseEntity):
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, entry: ConfigEntry, device: Optional[DeviceInfo], history: DeltaHistory, mode: str, name: str):
        super().__init__(entry, device, mode, name)
        self._history = history

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if data := await self.async_get_last_sensor_data():
            self._history.commited = data.native_value

    @property
    def native_value(self):
        return self._history.total


class ThroughEntity(BaseEntity):
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_value = 0

    def __init__(self, entry: ConfigEntry, device: Optional[DeviceInfo]):
        super().__init__(entry, device, "through", "Energy pass-through")

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if data := await self.async_get_last_sensor_data():
            self._attr_native_value = data.native_value


def _update(event: Event, input: TotalEntity, output: TotalEntity, through: ThroughEntity):
    old_state: State = event.data.get("old_state")
    new_state: State = event.data.get("new_state")
    eid: str = event.data["entity_id"]

    if not new_state or not old_state:
        return

    for x in [input, output]:
        x._attr_native_unit_of_measurement = new_state.attributes.get(
            ATTR_UNIT_OF_MEASUREMENT, None)

    if eid in input._history.keys:  # is output
        history = (output._history, input._history)
    else:
        history = (input._history, output._history)

    try:
        delta = int(float(new_state.state)) - int(float(old_state.state))
    except ValueError:
        return

    if delta < 0:
        return

    unit = new_state.attributes[ATTR_UNIT_OF_MEASUREMENT]
    if unit == ENERGY_WATT_HOUR:
        pass
    elif unit == ENERGY_KILO_WATT_HOUR:
        delta *= 1000
    elif unit == ENERGY_MEGA_WATT_HOUR:
        delta *= 1000000
    else:
        raise ValueError("Invalid unit: " + unit)

    d1 = history[1].revert(eid, delta)
    through._attr_native_value += delta - d1
    history[0].append(d1)

    for x in cast(list[BaseEntity], [input, output, through]):
        if not x.hass or not x.entity_id:
            continue
        x.async_write_ha_state()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    data = entry.options
    dr = device_registry.async_get(hass)
    device_info = None
    if devid := data.get(CONF_DEVICE, None):
        if device := dr.async_get(devid):
            device_info = DeviceInfo(identifiers=device.identifiers)

    input = TotalEntity(entry, device_info, DeltaHistory(
        data[CONF_OUTPUTS]), "in", "Energy charged")
    output = TotalEntity(entry, device_info, DeltaHistory(
        data[CONF_OUTPUTS]), "out", "Energy discharged")
    through = ThroughEntity(entry, device_info)

    async_add_entities([input, output, through])

    ids = set[str](data[CONF_INPUTS] + data[CONF_OUTPUTS])
    entry.async_on_unload(async_track_state_change_event(
        hass, ids, lambda event: _update(event, input, output, through)))
