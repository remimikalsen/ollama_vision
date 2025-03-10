"""Constants for the Ollama Vision integration."""
__version__ = "1.0.2"
DOMAIN = "ollama_vision"
INTEGRATION_NAME = "Ollama Vision"
MANUFACTURER = "@remimikalsen (https://github.com/remimikalsen)"

CONF_HOST = "host"
CONF_PORT = "port"
CONF_MODEL = "model"
DEFAULT_KEEPALIVE = -1

# Default values
DEFAULT_PORT = 11434
DEFAULT_MODEL = "moondream"
CONF_VISION_KEEPALIVE = "vision_keepalive"
DEFAULT_PROMPT = "This image is from a security camera above my front door. If there are people in the image, describe thir genders, estimated ages, facial expressions (moods), hairstyles, notable facial features, and clothing styles clearly and concisely. If no people are present, describe what is on my porch clearly and concisely."

# Service call constants
SERVICE_ANALYZE_IMAGE = "analyze_image"
ATTR_IMAGE_URL = "image_url"
ATTR_PROMPT = "prompt"
ATTR_IMAGE_NAME = "image_name"
ATTR_DEVICE_ID = "device_id"

# Event constants
EVENT_IMAGE_ANALYZED = "ollama_vision_image_analyzed"

# Textual model (optional)
CONF_TEXT_MODEL_ENABLED = "text_model_enabled"
CONF_TEXT_HOST = "text_host"
CONF_TEXT_PORT = "text_port"
CONF_TEXT_MODEL = "text_model"
DEFAULT_TEXT_PORT = 11434
DEFAULT_TEXT_MODEL = "llama3.1"
CONF_TEXT_KEEPALIVE = "text_keepalive"
DEFAULT_TEXT_PROMPT = "You are an AI that introduces people who come to visit me. You are cheeky and love a roast. Based on the following description: <description>{description}</description> – introduce this guest to me. Keep it short and concise, in English."

# Textual model service call constants
ATTR_USE_TEXT_MODEL = "use_text_model"
ATTR_TEXT_PROMPT = "text_prompt"
