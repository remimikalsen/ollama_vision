"""Config flow for Ollama Vision integration."""
import logging
import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_NAME

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_MODEL,
    DEFAULT_PORT,
    DEFAULT_MODEL,
    CONF_TEXT_MODEL_ENABLED,
    CONF_TEXT_HOST,
    CONF_TEXT_PORT,
    CONF_TEXT_MODEL,
    DEFAULT_TEXT_PORT,
    DEFAULT_TEXT_MODEL,
    CONF_VISION_KEEPALIVE,
    DEFAULT_KEEPALIVE,
    CONF_TEXT_KEEPALIVE,
)

_LOGGER = logging.getLogger(__name__)


class OllamaVisionConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ollama Vision."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize the config flow."""
        self.vision_config = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step for vision model configuration."""
        errors = {}

        if user_input is not None:
            # Test connection to Ollama vision server
            try:
                session = aiohttp.ClientSession()
                api_url = f"http://{user_input[CONF_HOST]}:{user_input[CONF_PORT]}/api/version"
                async with session.get(api_url) as response:
                    if response.status == 200:
                        await session.close()
                        # Store vision config and proceed
                        self.vision_config = user_input
                        # If text model is enabled, go to text model config step
                        if user_input.get(CONF_TEXT_MODEL_ENABLED):
                            return await self.async_step_text_model()
                        # Otherwise create entry with just vision config
                        return self.async_create_entry(
                            title=user_input[CONF_NAME],
                            data=user_input,
                        )
                    errors["base"] = "cannot_connect"
                await session.close()
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Show form for vision model input
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Required(CONF_MODEL, default=DEFAULT_MODEL): str,
                vol.Required(CONF_VISION_KEEPALIVE, default=DEFAULT_KEEPALIVE): int,
                vol.Optional(CONF_TEXT_MODEL_ENABLED, default=False): bool,
            }),
            errors=errors,
        )

    async def async_step_text_model(self, user_input=None):
        """Handle the text model configuration step during initial setup."""
        errors = {}

        if user_input is not None:
            # Test connection to text model Ollama server
            try:
                session = aiohttp.ClientSession()
                api_url = f"http://{user_input[CONF_TEXT_HOST]}:{user_input[CONF_TEXT_PORT]}/api/version"
                async with session.get(api_url) as response:
                    if response.status == 200:
                        await session.close()
                        # Merge vision and text configs
                        combined_config = {**self.vision_config, **user_input}
                        return self.async_create_entry(
                            title=self.vision_config[CONF_NAME],
                            data=combined_config,
                        )
                    errors["base"] = "cannot_connect"
                await session.close()
            except aiohttp.ClientError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # Show form for text model input
        return self.async_show_form(
            step_id="text_model",
            data_schema=vol.Schema({
                vol.Required(CONF_TEXT_HOST): str,
                vol.Required(CONF_TEXT_PORT, default=DEFAULT_TEXT_PORT): int,
                vol.Required(CONF_TEXT_MODEL, default=DEFAULT_TEXT_MODEL): str,
                vol.Required(CONF_TEXT_KEEPALIVE, default=DEFAULT_KEEPALIVE): int,
            }),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OllamaVisionOptionsFlow(config_entry)


class OllamaVisionOptionsFlow(config_entries.OptionsFlow):
    """Handle an options flow for Ollama Vision using multiple steps."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry
        # This will hold the vision configuration options from the first step
        self.vision_options = {}

    async def async_step_init(self, user_input=None):
        """Handle the first step: vision options and text model toggle."""
        if user_input is not None:
            self.vision_options = user_input
            if user_input.get(CONF_TEXT_MODEL_ENABLED):
                # If text model is enabled, proceed to second step.
                return await self.async_step_text_model_options()
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        data = self.config_entry.data
        schema = vol.Schema({
            vol.Required(
                CONF_HOST,
                default=options.get(CONF_HOST, data.get(CONF_HOST)),
            ): str,
            vol.Required(
                CONF_PORT,
                default=options.get(CONF_PORT, data.get(CONF_PORT, DEFAULT_PORT)),
            ): int,
            vol.Required(
                CONF_MODEL,
                default=options.get(CONF_MODEL, data.get(CONF_MODEL, DEFAULT_MODEL)),
            ): str,
            vol.Required(
                CONF_VISION_KEEPALIVE,
                default=options.get(CONF_VISION_KEEPALIVE, data.get(CONF_VISION_KEEPALIVE, DEFAULT_KEEPALIVE)),
            ): int,
            vol.Optional(
                CONF_TEXT_MODEL_ENABLED,
                default=options.get(CONF_TEXT_MODEL_ENABLED, data.get(CONF_TEXT_MODEL_ENABLED, False)),
            ): bool,
        })
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )

    async def async_step_text_model_options(self, user_input=None):
        """Handle the second step: text model configuration options."""
        if user_input is not None:
            # Merge the vision options and the text model options into one entry.
            combined_options = {**self.vision_options, **user_input}
            return self.async_create_entry(title="", data=combined_options)

        options = self.config_entry.options
        data = self.config_entry.data
        schema = vol.Schema({
            vol.Required(
                CONF_TEXT_HOST,
                default=options.get(CONF_TEXT_HOST, data.get(CONF_TEXT_HOST, "")),
            ): str,
            vol.Required(
                CONF_TEXT_PORT,
                default=options.get(CONF_TEXT_PORT, data.get(CONF_TEXT_PORT, DEFAULT_TEXT_PORT)),
            ): int,
            vol.Required(
                CONF_TEXT_MODEL,
                default=options.get(CONF_TEXT_MODEL, data.get(CONF_TEXT_MODEL, DEFAULT_TEXT_MODEL)),
            ): str,
            vol.Required(
                CONF_TEXT_KEEPALIVE,
                default=options.get(CONF_TEXT_KEEPALIVE, data.get(CONF_TEXT_KEEPALIVE, DEFAULT_KEEPALIVE)),
            ): int,
        })
        return self.async_show_form(
            step_id="text_model_options",
            data_schema=schema,
        )
