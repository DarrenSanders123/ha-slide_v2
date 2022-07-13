"""The slideV2 integration."""
from __future__ import annotations
from datetime import timedelta
import logging
from telnetlib import DO

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_CLOSED, STATE_OPEN, Platform
from homeassistant.core import HomeAssistant

from goslideapi import GoSlideCloud
from homeassistant.helpers.discovery import async_load_platform

from homeassistant.helpers.event import async_track_time_interval

from .const import API_CLOUD, DEFAULT_OFFSET, DOMAIN, SLIDES

# For your initial PR, limit it to 1 platform.
PLATFORMS: list[Platform] = [Platform.COVER, Platform.SWITCH]

_LOGGER = logging.getLogger(__name__)

DEFAULT_SCAN_INTERVAL = timedelta(seconds=1)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up slideV2 from a config entry."""
    # TODO Store an API object for your platforms to access
    # hass.data[DOMAIN][entry.entry_id] = MyApi(...)
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][SLIDES] = {}

    hass.data[DOMAIN].setdefault(entry.entry_id, {})

    username = entry.data["username"]
    password = entry.data["password"]

    hass.data[DOMAIN][entry.entry_id] = GoSlideCloud(username, password)

    # await async_update_slides(hass, entry)

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


# async def async_update_slides(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Update slides."""
    result = await hass.data[DOMAIN][entry.entry_id].slides_overview()

    _LOGGER.error(result)
    if result is None:
        _LOGGER.error("Slide API does not work or returned an error")
        return

    for slide in result:
        uid = slide["device_id"].replace("slide_", "")
        slide_entity = hass.data[DOMAIN][SLIDES].setdefault(uid, {})
        slide_entity["mac_address"] = uid
        slide_entity["id"] = slide["id"]
        slide_entity["name"] = slide["device_name"]
        slide_entity["state"] = None
        slide_entity["pos"] = None
        slide_entity["online"] = False
        last_position = slide_entity.get("pos")

        if "device_info" not in slide:
            _LOGGER.error(
                "Slide %s (%s) has no device_info Entry=%s",
                slide["id"],
                slide_entity["mac_address"],
                slide,
            )
            continue

        if await hass.data[DOMAIN][entry.entry_id].slide_get_position(slide["id"]):
            slide_entity["online"] = True
            slide_entity["pos"] = await hass.data[DOMAIN][
                entry.entry_id
            ].slide_get_position(slide["id"])
            slide_entity["pos"] = max(0, min(1, slide_entity["pos"]))



            if last_position is None or last_position == slide_entity["pos"]:
                slide_entity["state"] = (
                    STATE_CLOSED
                    if slide_entity["pos"] > (1 - DEFAULT_OFFSET)
                    else STATE_OPEN
                )
            elif last_position < slide_entity["pos"]:
                slide_entity["state"] = (
                    STATE_CLOSED
                    if slide_entity["pos"] > (1 - DEFAULT_OFFSET)
                    else STATE_OPEN
                )
            elif last_position > slide_entity["pos"]:
                slide_entity["state"] = (
                    STATE_CLOSED
                    if slide_entity["pos"] > (1 - DEFAULT_OFFSET)
                    else STATE_OPEN
                )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
