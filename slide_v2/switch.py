"""Support for Slide slides TouchAndGo."""
from datetime import timedelta

import async_timeout

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import _LOGGER, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up entry."""
    api = hass.data[DOMAIN][entry.entry_id]
    coordinator = MyCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        (TouchAndGo(coordinator, api, idx) for idx, ent in enumerate(coordinator.data)),
        True,
    )


class MyCoordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(self, hass, api):
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name="TouchAndGo",
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=60),
        )
        self.api = api

    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """

        # Note: asyncio.TimeoutError and aiohttp.ClientError are already
        # handled by the data update coordinator.
        async with async_timeout.timeout(10):
            return await self.api.slides_overview()


class TouchAndGo(SwitchEntity):
    """Representation of a Slide cover Touch and Go setting."""

    # Implement one of these methods.

    def __init__(self, coordinator, api, idx):
        self._attr_unique_id = (
            coordinator.data[idx]["device_id"].replace("slide_", "") + "_touch_and_go"
        )

        self._switch = {}
        self._switch["state"] = coordinator.data[idx]["touch_go"]
        self.coordinator = coordinator
        self.idx = idx
        self._attr_name = "Touch and Go"
        self._attr_entity_category = EntityCategory.CONFIG

    @property
    def is_on(self) -> bool:
        """Return true if entity is on."""
        return self._switch["state"] is True

    @property
    def is_off(self) -> bool:
        """Return true if the entity is off."""
        return self._switch["state"] is False

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""
        return None

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""
        return None
