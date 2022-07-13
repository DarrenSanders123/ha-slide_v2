"""Support for Slide slides."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

import async_timeout

from homeassistant.components.cover import ATTR_POSITION, CoverDeviceClass, CoverEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_CLOSED, STATE_CLOSING, STATE_OPEN, STATE_OPENING
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import DEFAULT_OFFSET, DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=20)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up entry."""
    api = hass.data[DOMAIN][entry.entry_id]
    coordinator = MyCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    async_add_entities(
        (SlideCover(coordinator, api, idx) for idx, ent in enumerate(coordinator.data)),
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
            name="Curtains",
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


class SlideCover(CoordinatorEntity, CoverEntity):
    """Representation of a Slide cover."""

    _attr_assumed_state = True
    _attr_device_class = CoverDeviceClass.CURTAIN

    def __init__(self, coordinator, api, idx):
        """Initialize the cover."""
        super().__init__(coordinator)
        self.idx = idx
        self.api = api
        self._slide = {}
        self._attr_name = self.coordinator.data[self.idx]["device_name"]
        self._slide["slide_setup"] = self.coordinator.data[self.idx]["slide_setup"]
        self._slide["curtain_type"] = self.coordinator.data[self.idx]["curtain_type"]
        self._slide["zone_id"] = self.coordinator.data[self.idx]["zone_id"]

        self.handle_slides_update()

    def handle_slides_update(self):
        """Handle slides update."""
        self._slide["id"] = self.coordinator.data[self.idx]["id"]
        self._slide["online"] = True
        self._attr_unique_id = self.coordinator.data[self.idx]["device_id"].replace(
            "slide_", ""
        )

        self._attr_name = self.coordinator.data[self.idx]["device_name"]

    def get_state(self):
        """Return the state of the cover."""
        if self._slide["position"] <= (0 + DEFAULT_OFFSET):
            return STATE_OPEN
        elif self._slide["position"] >= (1 - DEFAULT_OFFSET):
            return STATE_CLOSED

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state."""
        return True

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._slide["slide_setup"] = self.coordinator.data[self.idx]["slide_setup"]
        self._slide["curtain_type"] = self.coordinator.data[self.idx]["curtain_type"]
        self._slide["zone_id"] = self.coordinator.data[self.idx]["zone_id"]

    async def async_update(self) -> None:
        """Update the state of the cover."""
        # print("Updating (by poll)")
        current_slide = await self.api.slide_info(self._slide["id"])

        if current_slide is None:
            _LOGGER.error("Slide API does not work or returned an error")
            return

        self._slide["online"] = True
        self._slide["position"] = current_slide["pos"]
        self._slide["calib_time"] = current_slide["calib_time"]
        self._slide["state"] = self.get_state()
        self._slide["board_rev"] = current_slide["board_rev"]

    @property
    def device_info(self) -> (DeviceInfo | None):
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._attr_unique_id)
            },
            "name": self._attr_name,
            "manufacturer": "Innovation in Motion B.V.",
            "model": "Slide",
            "sw_version": "1.0",
            "hw_version": self._slide["board_rev"],
            "device_name": self._attr_name,
            "zone_id": self._slide["zone_id"],
            "config_entries": [self._attr_unique_id + "_touch_and_go",]

        }

    @property
    def is_opening(self) -> bool:
        """Return if the cover is opening or not."""
        return self._slide["state"] == STATE_OPENING

    @property
    def is_closing(self) -> bool:
        """Return if the cover is closing or not."""
        return self._slide["state"] == STATE_CLOSING

    @property
    def is_closed(self) -> bool | None:
        """Return None if status is unknown, True if closed, else False."""
        if self._slide["state"] is None:
            return None
        return self._slide["state"] == STATE_CLOSED

    @property
    def is_open(self) -> bool | None:
        """Return None if status is unknown, True if open, else False."""
        if self._slide["state"] is None:
            return None
        return self._slide["state"] == STATE_OPEN

    @property
    def available(self) -> bool:
        """Return False if state is not available."""
        return self._slide["online"]

    @property
    def current_cover_position(self) -> int | None:
        """Return the current position of cover shutter."""
        if (pos := self._slide["position"]) is not None:
            if (1 - pos) <= DEFAULT_OFFSET or pos <= DEFAULT_OFFSET:
                pos = round(pos)
            pos = int(pos * 100)
        return pos

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        self._slide["state"] = STATE_OPENING

        # set state to opening
        self.async_write_ha_state()

        # open the cover
        await self.api.slide_set_position(self._slide["id"], 0)

        # wait for the slide to open then update the state
        await asyncio.sleep((self._slide["calib_time"] + 2000) / 1000)

        # run the command again to make sure the slide is opend (workaround for a bug that displays the wrong state)
        if not self._slide["stopped"]:
            await self.api.slide_set_position(self._slide["id"], 0)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        self._slide["state"] = STATE_CLOSING

        # set state to closing
        self.async_write_ha_state()

        # close the cover
        await self.api.slide_set_position(self._slide["id"], 1)

        # wait for the slide to close then update the state
        await asyncio.sleep((self._slide["calib_time"] + 2000) / 1000)

        # run the command again to make sure the slide is closed (workaround for a bug that displays the wrong state)
        if not self._slide["stopped"]:
            await self.api.slide_set_position(self._slide["id"], 1)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        # set stopped to true
        self._slide["stopped"] = True
        # stop slide movement
        await self.api.slide_stop(self._slide["id"])


    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        position = kwargs[ATTR_POSITION] / 100
        # if target position is bigger then the current position, set the state to closing
        if self._slide["position"] is not None:
            if position > self._slide["position"]:
                self._slide["state"] = STATE_CLOSING

            else:
                self._slide["state"] = STATE_OPENING

        await self.api.slide_set_position(self._slide["id"], position)
