"""Config flow for Ollama Vision integration."""
import logging
import aiohttp
import voluptuous as vol
from urllib.parse import urlparse

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


def _parse_url_or_host_port(url_or_host, port=None):
    """
    Parse either a full URL (e.g., http://server.example.com/subpath), hostname:port, or hostname.
    
    Returns a tuple of (protocol, host, port, path) where:
    - protocol: 'http' or 'https'
    - host: hostname or IP
    - port: port number (int)
    - path: path component (e.g., '/subpath') or empty string
    
    Supported formats:
    - Full URL: http://server.example.com/subpath
    - Hostname with port: 192.168.1.1:11434
    - Hostname only: 192.168.1.1 (defaults to port 11434)
    
    If url_or_host is a full URL, port parameter is ignored.
    If url_or_host contains hostname:port, port parameter is ignored.
    """
    url_or_host_str = str(url_or_host).strip()
    
    # Check if it looks like a full URL
    if url_or_host_str.startswith("http://") or url_or_host_str.startswith("https://"):
        try:
            parsed = urlparse(url_or_host_str)
            protocol = parsed.scheme
            host = parsed.hostname
            parsed_port = parsed.port
            
            # Default ports based on protocol
            if parsed_port is None:
                if protocol == "https":
                    parsed_port = 443
                else:
                    parsed_port = 80
            
            path = parsed.path.rstrip('/')  # Remove trailing slash if present
            
            return protocol, host, parsed_port, path
        except Exception as e:
            _LOGGER.warning(f"Failed to parse URL '{url_or_host_str}': {e}. Treating as hostname.")
            # Fall through to hostname handling
    
    # Check if it's in hostname:port format
    if ':' in url_or_host_str and not url_or_host_str.startswith('http'):
        try:
            # Split on the last colon to handle IPv6 addresses
            parts = url_or_host_str.rsplit(':', 1)
            if len(parts) == 2:
                host_part = parts[0]
                port_part = parts[1]
                # Try to parse port
                try:
                    parsed_port = int(port_part)
                    return "http", host_part, parsed_port, ""
                except ValueError:
                    # Not a valid port, treat as hostname with colons (IPv6)
                    pass
        except Exception:
            pass
    
    # Treat as hostname only (backward compatibility)
    # Use provided port or default to 11434 (Ollama default)
    parsed_port = port if port is not None else 11434
    
    return "http", url_or_host_str, int(parsed_port), ""


def _build_api_url(host, port=None, endpoint="version"):
    """
    Build API URL from host and optional port, handling both full URLs and hostname:port.
    
    Args:
        host: Either a full URL (http://server.example.com/subpath) or hostname
        port: Port number (optional, ignored if host is a full URL, defaults to 11434)
        endpoint: API endpoint (default: 'version')
    
    Returns:
        Full API URL string
    """
    protocol, parsed_host, parsed_port, path = _parse_url_or_host_port(host, port)
    base_path = path if path else ""
    return f"{protocol}://{parsed_host}:{parsed_port}{base_path}/api/{endpoint}"


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
                api_url = _build_api_url(user_input[CONF_HOST], None, "version")
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
                api_url = _build_api_url(user_input[CONF_TEXT_HOST], None, "version")
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
                vol.Required(CONF_TEXT_MODEL, default=DEFAULT_TEXT_MODEL): str,
                vol.Required(CONF_TEXT_KEEPALIVE, default=DEFAULT_KEEPALIVE): int,
            }),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OllamaVisionOptionsFlow()


class OllamaVisionOptionsFlow(config_entries.OptionsFlow):
    """Handle an options flow for Ollama Vision using multiple steps."""

    def __init__(self):
        """Initialize options flow."""
        super().__init__()
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
        
        # Migrate old config: combine host:port if port exists separately
        existing_host = options.get(CONF_HOST, data.get(CONF_HOST, ""))
        existing_port = options.get(CONF_PORT, data.get(CONF_PORT))
        # If port exists and host doesn't already contain :port, combine them
        if existing_port and existing_host and ':' not in existing_host and not existing_host.startswith('http'):
            existing_host = f"{existing_host}:{existing_port}"
        
        schema = vol.Schema({
            vol.Required(
                CONF_HOST,
                default=existing_host,
            ): str,
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
        
        # Migrate old config: combine host:port if port exists separately
        existing_text_host = options.get(CONF_TEXT_HOST, data.get(CONF_TEXT_HOST, ""))
        existing_text_port = options.get(CONF_TEXT_PORT, data.get(CONF_TEXT_PORT))
        # If port exists and host doesn't already contain :port, combine them
        if existing_text_port and existing_text_host and ':' not in existing_text_host and not existing_text_host.startswith('http'):
            existing_text_host = f"{existing_text_host}:{existing_text_port}"
        
        schema = vol.Schema({
            vol.Required(
                CONF_TEXT_HOST,
                default=existing_text_host,
            ): str,
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
