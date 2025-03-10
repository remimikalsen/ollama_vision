"""Sensor platform for Ollama Vision."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
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

    entities = [OllamaVisionInfoSensor(hass, entry)]

    text_model_enabled = entry.options.get(
        CONF_TEXT_MODEL_ENABLED, 
        entry.data.get(CONF_TEXT_MODEL_ENABLED, False)
    )
    if text_model_enabled:
        entities.append(OllamaTextModelInfoSensor(hass, entry))

    async_add_entities(entities, True)

    @callback
    async def async_create_sensor_from_event(event):
        entry_id = event.data["entry_id"]
        image_name = event.data["image_name"]

        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None:
            _LOGGER.error(f"No config entry found for {entry_id}")
            return

        sensor_unique_id = f"{entry_id}_{slugify(image_name)}"
        created_sensors = hass.data[DOMAIN].setdefault("created_sensors", {})

        if sensor_unique_id in created_sensors: 
            sensor = created_sensors[sensor_unique_id]
            sensor.async_update_from_pending()
        else:
            sensor = OllamaVisionImageSensor(hass, entry, image_name)
            hass.data[DOMAIN][entry.entry_id]["sensors"][image_name] = sensor
            async_add_entities = hass.data[DOMAIN][entry.entry_id]["async_add_entities"]
            async_add_entities([sensor], True)

    hass.bus.async_listen(f"{DOMAIN}_create_sensor", async_create_sensor_from_event)


class OllamaVisionInfoSensor(SensorEntity):
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        config = hass.data[DOMAIN][entry.entry_id]["config"]

        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_vision_info"
        self._attr_name = f"Vision model {config['name']}"
        self._attr_icon = "mdi:information-outline"
        self._attr_native_value = f"{config[CONF_MODEL]} @ {config[CONF_HOST]}"

    @property
    def device_info(self):
        return self.hass.data[DOMAIN][self.entry.entry_id]["device_info"]


class OllamaTextModelInfoSensor(SensorEntity):
    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        config = hass.data[DOMAIN][entry.entry_id]["config"]

        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_text_info"
        self._attr_name = f"Text model {config['name']}"
        self._attr_icon = "mdi:information-outline"
        self._attr_native_value = f"{config[CONF_TEXT_MODEL]} @ {config[CONF_TEXT_HOST]}"

    @property
    def device_info(self):
        return self.hass.data[DOMAIN][self.entry.entry_id]["device_info"]


class OllamaVisionImageSensor(SensorEntity):
    def __init__(self, hass, entry, image_name):
        self.hass = hass
        self.entry = entry
        self.entry_id = entry.entry_id
        self.image_name = image_name

        config_name = hass.data[DOMAIN][self.entry_id]["config"]["name"]
        config_name_slug = slugify(config_name)

        self._attr_name = f"{config_name_slug} {image_name}"
        self._attr_unique_id = f"{self.entry_id}_{slugify(image_name)}"

        self._attr_native_value = None
        self._attr_extra_state_attributes = {}
    
    @callback
    def async_schedule_update(self):
        """Update the entity when new data is received."""
        sensor_data = self.hass.data[DOMAIN]["pending_sensors"].get(self.entry_id, {}).get(self.image_name, {})
        if sensor_data:
            description = sensor_data.get("description")
            self._attr_native_value = description[:255] if description else None
            attributes = {
                "integration_id": self.entry_id,
                "image_url": sensor_data.get("image_url"),
                "prompt": sensor_data.get("prompt"),                
            }
            if sensor_data.get("used_text_model"):
                attributes.update({
                    "used_text_model": True,
                    "text_prompt": sensor_data.get("text_prompt"),
                    "final_description": sensor_data.get("final_description")
                })
            self._attr_extra_state_attributes = attributes
            self.async_write_ha_state()

    @callback
    def async_update_from_pending(self):
        """Fetch the latest data from pending_sensors."""
        sensor_data = self.hass.data[DOMAIN]["pending_sensors"].get(self.entry.entry_id, {}).get(self.image_name)
        if sensor_data:
            description = sensor_data.get("description")
            self._attr_native_value = description[:255] if description else None
            self._attr_extra_state_attributes = {
                "integration_id": self.entry.entry_id,
                "image_url": sensor_data.get("image_url"),
                "prompt": sensor_data.get("prompt"),
                "final_description": sensor_data.get("final_description"),
                "text_prompt": sensor_data.get("text_prompt"),
                "used_text_model": sensor_data.get("used_text_model"),
            }
            self.async_write_ha_state()

    async def async_update(self):
        """Update is intentionally blank; updates happen via events."""
        pass      


    async def async_added_to_hass(self):
        """Fetch initial data after entity registration."""
        self.async_update_from_pending()          

    @property
    def device_info(self):
        return self.hass.data[DOMAIN][self.entry.entry_id]["device_info"]