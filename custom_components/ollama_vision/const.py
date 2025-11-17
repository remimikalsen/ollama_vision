"""Constants for the Ollama Vision integration."""
__version__ = "1.0.7"
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
DEFAULT_PROMPT = "Describe the image. How many people are there? What is their gender, hair style, age, mood, facial features and clothes?"

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
DEFAULT_TEXT_PROMPT = "You are an AI that describes people outside of my home. Give me a short brief based on the following description: <description>{description}</description>. Do it in English, and only give me a short brief, nothing else."

# Textual model service call constants
ATTR_USE_TEXT_MODEL = "use_text_model"
ATTR_TEXT_PROMPT = "text_prompt"

# Model parameter constants (user-friendly names)
# Vision model parameters
CONF_VISION_TEMPERATURE = "vision_temperature"
CONF_VISION_TOP_P = "vision_top_p"
CONF_VISION_TOP_K = "vision_top_k"
CONF_VISION_REPEAT_PENALTY = "vision_repeat_penalty"
CONF_VISION_SEED = "vision_seed"
CONF_VISION_NUM_PREDICT = "vision_num_predict"

# Text model parameters
CONF_TEXT_TEMPERATURE = "text_temperature"
CONF_TEXT_TOP_P = "text_top_p"
CONF_TEXT_TOP_K = "text_top_k"
CONF_TEXT_REPEAT_PENALTY = "text_repeat_penalty"
CONF_TEXT_SEED = "text_seed"
CONF_TEXT_NUM_PREDICT = "text_num_predict"

# Default values for model parameters (Ollama defaults)
DEFAULT_TEMPERATURE = 0.8
DEFAULT_TOP_P = 0.9
DEFAULT_TOP_K = 40
DEFAULT_REPEAT_PENALTY = 1.1
DEFAULT_SEED = 0  # 0 means random
DEFAULT_NUM_PREDICT = 128  # -1 means infinite, 128 is a reasonable default

# Service call attribute names for parameter overrides
ATTR_VISION_TEMPERATURE = "vision_temperature"
ATTR_VISION_TOP_P = "vision_top_p"
ATTR_VISION_TOP_K = "vision_top_k"
ATTR_VISION_REPEAT_PENALTY = "vision_repeat_penalty"
ATTR_VISION_SEED = "vision_seed"
ATTR_VISION_NUM_PREDICT = "vision_num_predict"
ATTR_TEXT_TEMPERATURE = "text_temperature"
ATTR_TEXT_TOP_P = "text_top_p"
ATTR_TEXT_TOP_K = "text_top_k"
ATTR_TEXT_REPEAT_PENALTY = "text_repeat_penalty"
ATTR_TEXT_SEED = "text_seed"
ATTR_TEXT_NUM_PREDICT = "text_num_predict"
