"""VentoUpdateCoordinator class."""

from datetime import timedelta
import logging
from typing import Any

from vents_breezy import Fan

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_IP_ADDRESS,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class VentoFanDataUpdateCoordinator(DataUpdateCoordinator):
    """Class for Vento Fan Update Coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
    ) -> None:
        """Initialize global Vento data updater."""
        self.config = config
        self._fan = None
        self._data = {}
        self._init_fan()

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )

    def _init_fan(self) -> None:
        """Initialize or reinitialize the fan connection."""
        try:
            self._fan = Fan(
                self.config.data[CONF_IP_ADDRESS],
                self.config.data[CONF_PASSWORD],
                self.config.data[CONF_DEVICE_ID],
                self.config.data[CONF_NAME],
                self.config.data[CONF_PORT],
            )
            self._fan.init_device()
            _LOGGER.debug(
                "Fan initialized with IP: %s, ID: %s",
                self.config.data[CONF_IP_ADDRESS],
                self._fan.id
            )
        except Exception as err:
            _LOGGER.error("Failed to initialize fan: %s", err)
            raise

    async def async_update_config(self, config: ConfigEntry) -> None:
        """Update the coordinator with a new config entry."""
        _LOGGER.debug("Updating coordinator config for entry: %s", config.entry_id)
        self.config = config
        
        # Пересоздаём подключение
        try:
            await self.hass.async_add_executor_job(self._init_fan)
            await self.async_refresh()
            _LOGGER.debug("Coordinator updated successfully")
        except Exception as err:
            _LOGGER.error("Failed to update coordinator: %s", err)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API endpoint."""
        try:
            # Выполняем обновление в executor
            result = await self.hass.async_add_executor_job(self._fan.update)
            
            # Если update возвращает словарь с данными, сохраняем его
            if result is not None:
                self._data = result
                _LOGGER.debug("Fan data updated successfully: %s", result)
            else:
                _LOGGER.debug("Fan update completed, no data returned")
                
            return self._data
            
        except Exception as err:
            _LOGGER.error("Error updating fan data: %s", err)
            raise UpdateFailed(f"Error communicating with device: {err}") from err

    def get_data(self) -> dict[str, Any]:
        """Get the latest data."""
        return self._data
