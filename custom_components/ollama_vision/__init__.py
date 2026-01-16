"""The Ollama Vision 2 integration."""
import logging
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import config_validation as cv
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import CONF_NAME, Platform
import homeassistant.helpers.entity_registry as er
from homeassistant.helpers.device_registry import async_get as async_get_device_registry
from homeassistant.helpers.config_validation import config_entry_only_config_schema
from homeassistant.util import slugify
from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_PORT,
    CONF_MODEL,
    ATTR_IMAGE_URL,
    ATTR_PROMPT,
    ATTR_IMAGE_NAME,
    ATTR_DEVICE_ID,
    SERVICE_ANALYZE_IMAGE,
    EVENT_IMAGE_ANALYZED,
    ATTR_USE_TEXT_MODEL,
    ATTR_TEXT_PROMPT,
    CONF_TEXT_MODEL_ENABLED,
    CONF_TEXT_HOST,
    CONF_TEXT_PORT,
    CONF_TEXT_MODEL,
    DEFAULT_TEXT_PORT,
    DEFAULT_TEXT_MODEL,
    CONF_TEXT_KEEPALIVE,
    DEFAULT_KEEPALIVE,
    CONF_VISION_KEEPALIVE,
    CONF_TEXT_CONTEXTSIZE,
    DEFAULT_CONTEXTSIZE,
    CONF_VISION_CONTEXTSIZE,
    DEFAULT_PROMPT,
    DEFAULT_TEXT_PROMPT,
    __version__,
    INTEGRATION_NAME,
    MANUFACTURER,
)
from .api import OllamaClient

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = config_entry_only_config_schema(DOMAIN)

# Service schema
ANALYZE_IMAGE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_IMAGE_URL):  vol.Any(cv.string, [cv.string]),
        vol.Optional(ATTR_PROMPT, default=DEFAULT_PROMPT): cv.string,
        vol.Required(ATTR_IMAGE_NAME): cv.string,
        vol.Optional(ATTR_DEVICE_ID): cv.string,
        vol.Optional(ATTR_USE_TEXT_MODEL, default=False): cv.boolean,
        vol.Optional(ATTR_TEXT_PROMPT, default=DEFAULT_TEXT_PROMPT): cv.string,
    }
)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Ollama Vision 2 component."""
    hass.data[DOMAIN] = {}
    hass.data[DOMAIN]["pending_sensors"] = {}
    hass.data[DOMAIN]["created_sensors"] = {}
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Ollama Vision 2 from a config entry."""
    host = entry.data.get(CONF_HOST) or entry.options.get(CONF_HOST)
    port = entry.data.get(CONF_PORT) or entry.options.get(CONF_PORT)
    
    # Migrate old config: combine host:port if port exists separately
    if port and host and ':' not in host and not host.startswith('http'):
        host = f"{host}:{port}"
        port = None
    
    model = entry.data.get(CONF_MODEL) or entry.options.get(CONF_MODEL)
    name = entry.data.get(CONF_NAME)
    vision_keepalive = entry.data.get(CONF_VISION_KEEPALIVE) or entry.options.get(CONF_VISION_KEEPALIVE, DEFAULT_KEEPALIVE)
    vision_contextsize = entry.data.get(CONF_VISION_CONTEXTSIZE) or entry.options.get(CONF_VISION_CONTEXTSIZE, DEFAULT_CONTEXTSIZE)
    
    # Get text model settings
    text_model_enabled = entry.options.get(
        CONF_TEXT_MODEL_ENABLED, 
        entry.data.get(CONF_TEXT_MODEL_ENABLED, False)
    )
    text_host = None
    text_port = None
    text_model = None
    text_keepalive = DEFAULT_KEEPALIVE
    text_contextsize = DEFAULT_CONTEXTSIZE
    
    if text_model_enabled:
        text_host = entry.data.get(CONF_TEXT_HOST) or entry.options.get(CONF_TEXT_HOST)
        text_port = entry.data.get(CONF_TEXT_PORT) or entry.options.get(CONF_TEXT_PORT)
        
        # Migrate old text config: combine host:port if port exists separately
        if text_port and text_host and ':' not in text_host and not text_host.startswith('http'):
            text_host = f"{text_host}:{text_port}"
            text_port = None
        
        text_model = entry.data.get(CONF_TEXT_MODEL) or entry.options.get(CONF_TEXT_MODEL, DEFAULT_TEXT_MODEL)
        text_keepalive = entry.data.get(CONF_TEXT_KEEPALIVE) or entry.options.get(CONF_TEXT_KEEPALIVE, DEFAULT_KEEPALIVE)
        text_contextsize = entry.data.get(CONF_TEXT_CONTEXTSIZE) or entry.options.get(CONF_TEXT_CONTEXTSIZE, DEFAULT_CONTEXTSIZE)
    
    client = OllamaClient(hass, host, port, model, text_host, text_port, text_model, vision_keepalive, vision_contextsize, text_keepalive, text_contextsize) ##follow vision_keepalive for vision_contextsize
    
    # Store the client in hass.data
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "sensors": {},
        "config": {
            CONF_HOST: host,  # host may contain hostname:port or full URL
            CONF_MODEL: model,
            CONF_NAME: name,
            CONF_TEXT_MODEL_ENABLED: text_model_enabled,
            CONF_TEXT_HOST: text_host,  # host may contain hostname:port or full URL
            CONF_TEXT_MODEL: text_model,
            CONF_TEXT_KEEPALIVE: text_keepalive,
            CONF_TEXT_CONTEXTSIZE: text_contextsize
        },
        "device_info": {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"{INTEGRATION_NAME} {name}",
            "manufacturer": MANUFACTURER,
            "model": f"{INTEGRATION_NAME}: {model} + {text_model}" if text_model else f"{INTEGRATION_NAME}: {model}",
            "sw_version": __version__
        }
    }
    
    # Create service handler wrapper
    @callback
    def async_handle_service(call):
        """Handle the service call."""
        hass.async_create_task(handle_analyze_image(hass, call))
    
    # Register service with the wrapper
    hass.services.async_register(
        DOMAIN,
        SERVICE_ANALYZE_IMAGE,
        async_handle_service,
        schema=ANALYZE_IMAGE_SCHEMA,
    )
    
    # Check if the text model is enabled and remove the sensor if it exists and the model is disabled
    if not text_model_enabled:
        ent_registry = er.async_get(hass)
        text_sensor_entity_id = ent_registry.async_get_entity_id(
            domain="sensor",
            platform=DOMAIN, 
            unique_id=f"{DOMAIN}_{entry.entry_id}_text_info",
        )
        if text_sensor_entity_id:
            # Remove it, so it disappears from Home Assistant entirely
            ent_registry.async_remove(text_sensor_entity_id)
    
    # Create update listener
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    
    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    return True

async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)

# Define the analyze_image service outside of async_setup_entry
async def handle_analyze_image(hass, call):
    """Handle the analyze_image service call."""
    image_url = call.data.get(ATTR_IMAGE_URL)
    vision_prompt = call.data.get(ATTR_PROMPT, DEFAULT_PROMPT)
    image_name = call.data.get(ATTR_IMAGE_NAME)
    device_id = call.data.get(ATTR_DEVICE_ID)
    use_text_model = call.data.get(ATTR_USE_TEXT_MODEL, False)
    text_prompt = call.data.get(ATTR_TEXT_PROMPT, DEFAULT_TEXT_PROMPT)
    
    # Properly slugify the image name to ensure consistent IDs
    slugified_image_name = slugify(image_name)
    
    # Determine which integration to use based on device_id
    entry_id_to_use = None
    
    if device_id:
        # Use device registry to find the config entry
        device_registry = async_get_device_registry(hass)
        device = device_registry.async_get(device_id)
        
        if device and device.config_entries:
            # Get the first config entry associated with this device
            # that belongs to our domain
            for entry_id in device.config_entries:
                if entry_id in hass.data[DOMAIN]:
                    entry_id_to_use = entry_id
                    break
    
    if not entry_id_to_use:
        # Filter out non-integration keys like "pending_sensors" or "created_sensors"
        valid_entry_ids = [
            k for k, v in hass.data[DOMAIN].items()
            if isinstance(v, dict) and "client" in v
        ]
        if not valid_entry_ids:
            # Means there are no configured integrations at all
            raise HomeAssistantError("No configured Ollama Vision 2 entries found. "
                                    "Please add at least one config entry or specify device_id.")
        if len(valid_entry_ids) > 1 and not device_id:
            _LOGGER.warning(
                "Multiple Ollama Vision 2 instances found but no device_id specified. "
                "Using first available. Specify device_id parameter to target a specific instance."
            )
        # Pick the first valid entry
        entry_id_to_use = valid_entry_ids[0]
    
    client_to_use = hass.data[DOMAIN][entry_id_to_use]["client"]
    
    # Analyze the image using the selected client
    vision_description = await client_to_use.analyze_image(image_url, vision_prompt)
    
    if vision_description is None:
        raise HomeAssistantError("Failed to analyze image")
    
    # Determine if we should use the text model for elaboration
    config = hass.data[DOMAIN][entry_id_to_use]["config"]
    text_model_enabled = config.get(CONF_TEXT_MODEL_ENABLED, False)
    
    # Only elaborate if both the service call requests it and the config has it enabled
    final_description = vision_description
    text_prompt_formatted = None
    if use_text_model and text_model_enabled:
        text_prompt_formatted = text_prompt.format(description=vision_description)
        final_description = await client_to_use.elaborate_text(vision_description, text_prompt_formatted)
    
    
    # Replace 'www/' with 'local/' if applicable
    # If the image is within /config/www, it will actually 
    # be displayed in companion app notifications
    # Normalize image_url to a list
    if isinstance(image_url, str):
        image_urls = [image_url]
    else:
        image_urls = list(image_url)

    #validate for strings
    for url in image_urls:
        if not isinstance(url, str):
            raise ValueError("image_url entries must be strings")

    # Normalize each path
    normalized_urls = []
    for url in image_urls:
        if url.startswith("www/"):
            url = url.replace("www/", "local/", 1)
        normalized_urls.append(url)

    image_url = normalized_urls
    
    # Store data so the sensor can display it
    pending_sensors = hass.data[DOMAIN].setdefault("pending_sensors", {}).setdefault(entry_id_to_use, {})
    pending_sensors[image_name] = {
        "description": vision_description,
        "image_url": image_url,
        "prompt": vision_prompt,
        "unique_id": f"{entry_id_to_use}_{slugified_image_name}",
        "final_description": final_description if (use_text_model and text_model_enabled) else None,
        "text_prompt": text_prompt_formatted,
        "used_text_model": use_text_model and text_model_enabled
    }
    
    # Fire event for sensor creation/update
    hass.bus.async_fire(f"{DOMAIN}_create_sensor", {
        "entry_id": entry_id_to_use,
        "image_name": image_name
    })
    
    # Try to update existing sensor if it exists
    created_sensors = hass.data[DOMAIN].setdefault("created_sensors", {})
    sensor_unique_id = f"{entry_id_to_use}_{slugified_image_name}"
    if sensor_unique_id in created_sensors:
        created_sensors[sensor_unique_id].async_update_from_pending()
    
    # Fire user-facing event with all relevant fields
    event_data = {
        "integration_id": entry_id_to_use,
        "image_name": image_name,
        "image_url": image_url,
        "prompt": vision_prompt,
        "description": vision_description,
        "used_text_model": use_text_model and text_model_enabled,
        "text_prompt": text_prompt_formatted,
        "final_description": final_description,
    }
    hass.bus.async_fire(EVENT_IMAGE_ANALYZED, event_data)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload sensor platform
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        # Check if this is the last instance of the integration
        valid_entries = [k for k, v in hass.data[DOMAIN].items() 
                         if isinstance(v, dict) and "client" in v]
        
        if len(valid_entries) <= 1:
            # Unregister service if this is the last instance
            hass.services.async_remove(DOMAIN, SERVICE_ANALYZE_IMAGE)
        
        # Remove data for this entry
        if entry.entry_id in hass.data[DOMAIN]:
            hass.data[DOMAIN].pop(entry.entry_id)
        
        if entry.entry_id in hass.data[DOMAIN].get("pending_sensors", {}):
            hass.data[DOMAIN]["pending_sensors"].pop(entry.entry_id)
        
        # Clean up created_sensors that belong to this entry
        created_sensors = hass.data[DOMAIN].get("created_sensors", {})
        sensors_to_remove = [uid for uid in list(created_sensors.keys()) 
                            if uid.startswith(f"{entry.entry_id}_")]
        
        for uid in sensors_to_remove:
            created_sensors.pop(uid, None)
    
    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)