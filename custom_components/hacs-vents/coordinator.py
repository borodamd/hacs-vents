"""VentoUpdateCoordinator class."""

from datetime import timedelta
import logging

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
    CoordinatorEntity,
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
        self._init_fan()

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),
        )

    def _init_fan(self) -> None:
        """Initialize or reinitialize the fan connection."""
        self._fan = Fan(
            self.config.data[CONF_IP_ADDRESS],
            self.config.data[CONF_PASSWORD],
            self.config.data[CONF_DEVICE_ID],
            self.config.data[CONF_NAME],
            self.config.data[CONF_PORT],
        )
        self._fan.init_device()

    async def async_update_config(self, config: ConfigEntry) -> None:
        """Update the coordinator with a new config entry."""
        self.config = config
        self._init_fan()
        await self.async_refresh()

    async def _async_update_data(self) -> None:
        """Fetch data from API endpoint."""
        try:
            # Выполняем обновление в executor, так как это может быть блокирующая операция
            return await self.hass.async_add_executor_job(self._fan.update)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with device: {err}") from err
