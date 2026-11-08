"""Cover entity for A-OK RS485 curtains over a transparent TCP-to-RS485 gateway."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from homeassistant.components.cover import ATTR_POSITION, CoverEntity, CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    CONF_CHANNEL, CONF_DEVICE_ID, CONF_TIMEOUT, CONF_POLL_INTERVAL,
    DEFAULT_TIMEOUT, DEFAULT_POLL_INTERVAL,
)
from .protocol import (
    RESPONSE_LENGTH, close_frame, open_frame, parse_status, position_frame,
    query_frame, stop_frame,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    """Add motor configured via the UI."""
    config = {**entry.data, **entry.options}
    async_add_entities([AokCover(entry, config)])


class AokCover(CoverEntity):
    """Represent one motor ID/channel; poll motor for current position."""

    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )
    _attr_should_poll = False
    _attr_has_entity_name = False

    def __init__(self, entry: ConfigEntry, config: dict) -> None:
        self._host = config[CONF_HOST]
        self._port = config[CONF_PORT]
        self._device_id = config[CONF_DEVICE_ID]
        self._channel = config[CONF_CHANNEL]
        self._timeout = config.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
        self._poll_interval = config.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
        self._attr_name = config[CONF_NAME]
        self._attr_unique_id = f"{entry.entry_id}_cover"
        self._attr_available = False
        self._attr_current_cover_position = None
        self._attr_is_opening = False
        self._attr_is_closing = False
        self._lock = asyncio.Lock()
        self._last_direction: str | None = None

    async def async_added_to_hass(self) -> None:
        """Start periodic motor queries after the entity is registered."""
        await super().async_added_to_hass()

        async def poll(_now) -> None:
            await self.async_update_ha_state(force_refresh=True)

        self.async_on_remove(
            async_track_time_interval(
                self.hass, poll, timedelta(seconds=self._poll_interval)
            )
        )
        await self.async_update_ha_state(force_refresh=True)

    async def _tcp_exchange(self, request: bytes, expect_reply: bool = False) -> bytes | None:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(self._host, self._port), timeout=self._timeout
        )
        try:
            writer.write(request)
            await asyncio.wait_for(writer.drain(), timeout=self._timeout)
            if not expect_reply:
                return None

            async def receive_frame() -> bytes:
                # Ignore leading noise, require the 0xD8 frame header.
                for _ in range(64):
                    lead = await reader.readexactly(1)
                    if lead == b"\xd8":
                        return lead + await reader.readexactly(RESPONSE_LENGTH - 1)
                raise ValueError("No status frame header (0xD8) detected")

            return await asyncio.wait_for(receive_frame(), timeout=self._timeout)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass

    async def _send(self, payload: bytes, direction: str | None) -> None:
        async with self._lock:
            try:
                await self._tcp_exchange(payload)
            except (OSError, ValueError, asyncio.TimeoutError) as err:
                self._attr_available = False
                self.async_write_ha_state()
                raise HomeAssistantError(f"A-OK RS485 command failed: {err}") from err
            # TCP write is not an acknowledgement from the motor.
            self._last_direction = direction
            self._attr_is_opening = direction == "opening"
            self._attr_is_closing = direction == "closing"
            self.async_write_ha_state()

    async def async_update(self) -> None:
        async with self._lock:
            try:
                reply = await self._tcp_exchange(
                    query_frame(self._device_id, self._channel), expect_reply=True
                )
                status = parse_status(reply, self._device_id, self._channel)
            except (OSError, ValueError, asyncio.TimeoutError, asyncio.IncompleteReadError) as err:
                self._attr_available = False
                _LOGGER.debug("A-OK RS485 motor status query failed: %s", err)
                return
            previous = self._attr_current_cover_position
            self._attr_current_cover_position = status.ha_position
            self._attr_available = True
            if status.moving:
                if previous is not None and status.ha_position != previous:
                    self._last_direction = (
                        "opening" if status.ha_position > previous else "closing"
                    )
                self._attr_is_opening = self._last_direction == "opening"
                self._attr_is_closing = self._last_direction == "closing"
            else:
                self._last_direction = None
                self._attr_is_opening = False
                self._attr_is_closing = False

    @property
    def extra_state_attributes(self) -> dict:
        return {"rs485_device_id": self._device_id, "rs485_channel": self._channel}

    async def async_open_cover(self, **kwargs) -> None:
        await self._send(open_frame(self._device_id, self._channel), "opening")

    async def async_close_cover(self, **kwargs) -> None:
        await self._send(close_frame(self._device_id, self._channel), "closing")

    async def async_stop_cover(self, **kwargs) -> None:
        await self._send(stop_frame(self._device_id, self._channel), None)

    async def async_set_cover_position(self, **kwargs) -> None:
        position = int(kwargs[ATTR_POSITION])
        old = self._attr_current_cover_position
        direction = ("opening" if old is not None and position > old
                     else "closing" if old is not None and position < old else None)
        await self._send(position_frame(self._device_id, self._channel, position), direction)
