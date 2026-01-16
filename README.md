![Build Status](https://img.shields.io/github/actions/workflow/status/remimikalsen/ollama_vision/publish.yaml)
![HACS Test](https://img.shields.io/github/actions/workflow/status/remimikalsen/ollama_vision/hacs.yaml?label=HACS)
![Hassfest Test](https://img.shields.io/github/actions/workflow/status/remimikalsen/ollama_vision/hassfest.yaml?label=Hassfest)
![License](https://img.shields.io/github/license/remimikalsen/ollama_vision)


# Ollama Vision ~2

This is a copy of the origional [Ollama Vision](https://github.com/remimikalsen/ollama_vision) with the intent at this time to allow for multiple image files being sent to the LLM. I have specifically renamed it to ollama vision 2, as to not interfere with the version of ollama vision that is already installed.

# Changes

Image_url: now accepts multiple "path"s

Default LLM: [antony66/gemma3-tools:27b](https://ollama.com/antony66/gemma3-tools:27b)

DEFAULT_MODEL = "antony66/gemma3-tools:27b"

DEFAULT_TEXT_MODEL = "antony66/gemma3-tools:27b"

Added the option to define a context size to the model for calls.


## Usage

You can queue images for analysis via the `ollama_vision.analyze_image` service. When called, it generates or updates a dynamic sensor holding the description of the analyzed image. 

Note! The sensors will appear as **unavailable** after rebooting Home Assistant or reloading the integration. This is due to the fact that these sensors are dynamically created. You can create thousands of sensors if you wish, and I don't think persisting them is a good idea, because it would also require a bulletproof way of cleaning them up when needed.

### Frigate example
The following automation describes a person detected by Frigate:

```
action: ollama_vision2.analyze_image
data:
  prompt: >-
    Image 1 is a reference with no people in it. Can you compare these 2 images? Is there now a person?
  image_url: 
    - www/camera_snapshots/Front_default.jpg
    - https://myipcamera.local/live.jpg
  device_id: b9d50fa9859ada72422dd2691febcd88
  image_name: Front_Status
  device_id: <YOUR OLLAMA VISION DEVICE ID>    
```

# Installation and Troubleshooting

Remimikalsen has done a great job of the origional
[Ollama Vision](https://github.com/remimikalsen/ollama_vision)