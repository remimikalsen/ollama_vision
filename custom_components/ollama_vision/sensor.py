"""Sensor platform for Ollama Vision."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.util import slugify
import logging

_LOGGER = logging.getLogger(__name__)

from .const import (
    DOMAIN,
    CONF_TEXT_MODEL_ENABLED,
    CONF_TEXT_HOST,
    CONF_TEXT_MODEL,
    CONF_MODEL,
    CONF_HOST,
    INTEGRATION_NAME,
)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Ollama Vision sensors."""
    hass.data[DOMAIN][entry.entry_id]["async_add_entities"] = async_add_entities
    
    # Create the info sensors
    entities = [OllamaVisionInfoSensor(hass, entry)]
    text_model_enabled = entry.options.get(
        CONF_TEXT_MODEL_ENABLED, 
        entry.data.get(CONF_TEXT_MODEL_ENABLED, False)
    )
    if text_model_enabled:
        entities.append(OllamaTextModelInfoSensor(hass, entry))
    
    # Initialize the created_sensors dict if it doesn't exist
    hass.data[DOMAIN].setdefault("created_sensors", {})
    
    # Re-create previously created image sensors after a restart
    entity_registry = async_get_entity_registry(hass)
    existing_entities = entity_registry.entities
    
    # Look for our image sensors in the entity registry
    for entity_id, entry_data in existing_entities.items():
        if entry_data.platform != DOMAIN or not entry_data.unique_id.startswith(f"{entry.entry_id}_"):
            continue
            
        # This is one of our image sensors
        if entry_data.unique_id == f"{DOMAIN}_{entry.entry_id}_vision_info" or entry_data.unique_id == f"{DOMAIN}_{entry.entry_id}_text_info":
            # Skip the info sensors
            continue
            
        # Extract image name from the unique_id
        unique_id_parts = entry_data.unique_id.split('_', 1)
        if len(unique_id_parts) == 2:
            # Create a sensor for this existing entity
            image_name = entity_id.split('.', 1)[1]  # Remove the domain prefix
            sensor = OllamaVisionImageSensor(hass, entry, image_name)
            
            # Store in our tracking dict
            if sensor.unique_id not in hass.data[DOMAIN]["created_sensors"]:
                entities.append(sensor)
                hass.data[DOMAIN]["created_sensors"][sensor.unique_id] = sensor
                hass.data[DOMAIN][entry.entry_id].setdefault("sensors", {})[image_name] = sensor
    
    async_add_entities(entities, True)
    
    @callback
    async def async_create_sensor_from_event(event):
        """Create a new sensor or update an existing one when an image is analyzed."""
        entry_id = event.data["entry_id"]
        image_name = event.data["image_name"]
        
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None:
            _LOGGER.error(f"No config entry found for {entry_id}")
            return
        
        # Generate a proper unique_id
        sensor_unique_id = f"{entry_id}_{slugify(image_name)}"
        
        # Check if sensor already exists
        created_sensors = hass.data[DOMAIN]["created_sensors"]
        if sensor_unique_id in created_sensors:
            # Sensor exists, update it
            _LOGGER.debug(f"Updating existing sensor {sensor_unique_id}")
            created_sensors[sensor_unique_id].async_update_from_pending()
        else:
            # Create new sensor
            _LOGGER.debug(f"Creating new sensor for {image_name}")
            sensor = OllamaVisionImageSensor(hass, entry, image_name)
            
            # Store in our tracking dicts
            created_sensors[sensor_unique_id] = sensor
            hass.data[DOMAIN][entry_id].setdefault("sensors", {})[image_name] = sensor
            
            # Add the entity
            async_add_entities = hass.data[DOMAIN][entry_id]["async_add_entities"]
            async_add_entities([sensor], True)
    
    # Register event listener
    hass.bus.async_listen(f"{DOMAIN}_create_sensor", async_create_sensor_from_event)


class OllamaVisionInfoSensor(SensorEntity):
    """Information sensor for the Ollama Vision model."""
    
    def __init__(self, hass, entry):
        """Initialize the sensor."""
        self.hass = hass
        self.entry = entry
        config = hass.data[DOMAIN][entry.entry_id]["config"]
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_vision_info"
        self._attr_name = f"Vision model {config['name']}"
        self._attr_icon = "mdi:information-outline"
        self._attr_native_value = f"{config[CONF_MODEL]} @ {config[CONF_HOST]}"
    
    @property
    def device_info(self):
        """Return the device info."""
        return self.hass.data[DOMAIN][self.entry.entry_id]["device_info"]


class OllamaTextModelInfoSensor(SensorEntity):
    """Information sensor for the Ollama Text model."""
    
    def __init__(self, hass, entry):
        """Initialize the sensor."""
        self.hass = hass
        self.entry = entry
        config = hass.data[DOMAIN][entry.entry_id]["config"]
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_text_info"
        self._attr_name = f"Text model {config['name']}"
        self._attr_icon = "mdi:information-outline"
        self._attr_native_value = f"{config[CONF_TEXT_MODEL]} @ {config[CONF_TEXT_HOST]}"
    
    @property
    def device_info(self):
        """Return the device info."""
        return self.hass.data[DOMAIN][self.entry.entry_id]["device_info"]


class OllamaVisionImageSensor(SensorEntity):
    """Sensor representing an image analyzed by Ollama Vision."""
    
    def __init__(self, hass, entry, image_name):
        """Initialize the sensor."""
        self.hass = hass
        self.entry = entry
        self.entry_id = entry.entry_id
        self.image_name = image_name
        
        # Ensure we have a properly slugified name
        slugified_image_name = slugify(image_name)
        
        # Generate config name
        config_name = hass.data[DOMAIN][self.entry_id]["config"]["name"]
        
        # Set entity attributes
        self._attr_name = f"{config_name} {slugified_image_name}"
        self._attr_unique_id = f"{self.entry_id}_{slugified_image_name}"
        self._attr_icon = "mdi:image-text"
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}
        
        # Register in the created_sensors dict
        hass.data[DOMAIN].setdefault("created_sensors", {})[self._attr_unique_id] = self
    
    @callback
    def async_update_from_pending(self):
        """Fetch the latest data from pending_sensors."""
        pending_sensors = self.hass.data[DOMAIN].get("pending_sensors", {})
        entry_sensors = pending_sensors.get(self.entry_id, {})
        
        # Try to find the sensor data using both the original name and the slugified name
        sensor_data = entry_sensors.get(self.image_name)
        if not sensor_data:
            # Try with the unslugified version from the name attribute
            for key, data in entry_sensors.items():
                if slugify(key) == slugify(self.image_name):
                    sensor_data = data
                    break
        
        if sensor_data:
            description = sensor_data.get("description")
            self._attr_native_value = description[:255] if description else None
            
            # Update attributes
            attributes = {
                "integration_id": self.entry_id,
                "image_url": sensor_data.get("image_url"),
                "prompt": sensor_data.get("prompt"),
                "full_description": description,  # Store the full description
            }
            
            if sensor_data.get("used_text_model"):
                attributes.update({
                    "used_text_model": True,
                    "text_prompt": sensor_data.get("text_prompt"),
                    "final_description": sensor_data.get("final_description")
                })
            
            self._attr_extra_state_attributes = attributes
            self.async_write_ha_state()
            
            _LOGGER.debug(f"Updated sensor {self._attr_unique_id} with new data")
    
    async def async_update(self):
        """Update the sensor."""
        # This is intentionally empty as updates come through events
        pass
    
    async def async_added_to_hass(self):
        """When entity is added to hass."""
        # Fetch initial data after entity registration
        self.async_update_from_pending()
    
    @property
    def device_info(self):
        """Return the device info."""
        return self.hass.data[DOMAIN][self.entry_id]["device_info"]