![Build Status](https://img.shields.io/github/actions/workflow/status/remimikalsen/ollama_vision/publish.yaml)
![License](https://img.shields.io/github/license/remimikalsen/ollama_vision)
![Version](https://img.shields.io/github/tag/remimikalsen/ollama_vision)


# Ollama Vision

This integration enables you to analyze images using a local Ollama server running a vision-enabled LLM. Optionally, it can also use a specialized text model to generate more elaborate text. For example, you could add a cheeky or “roast-style” introduction for people captured on a security camera. 

This integration is perfect if you use Frigate for local object detection—now you can have a fully local LLM describe images from Frigate and send those descriptions to your phone, or use them in automations however you like.

I wrote a step-by-step guide for Ollama Vision on my technology blog, [The Awesome Garage](https://theawesomegarage.com/blog/ollama-vision-local-ai-image-processing-in-home-assistant).

## Requirements

 - Images must be accessible via HTTP/HTTPS to your Home Assistant server.
 - You must have access to a vision-enabled model running on an Ollama server.
 - (Optional) You must have access to a general-purpose LLM (on an Ollama server) if you want to enhance/embellish the vision model’s descriptions.

## Features

 - Connect to one or more Ollama servers with vision-capable models
 - Analyze images with customizable prompts
 - Optionally enhance descriptions using a specialized text model
 - Dynamically create/update sensors with the latest image descriptions
 - Fire an event when each image is analyzed, for downstream automations

## Installation

To install the "Ollama Vision" integration in Home Assistant, follow these steps:

 1. Ensure you have [HACS](https://hacs.xyz/) (Home Assistant Community Store) installed.
 2. Add the repository to HACS:

    - Go to HACS in Home Assistant
    - Click the three dots in the upper right corner
    - Select "Custom repositories"
    - Paste the repository link: https://github.com/remimikalsen/ollama_vision
    - Select type: Integration
    - Click "Add"

 3. Close the modal, search for "Ollama Vision" in HACS and select it.
 4. Download the integration.
 5. Restart Home Assistant for the integration to become available.

## Configuration

After restarting Home Assistant, go to Settings → Devices & Services.

 1. Click + Add Integration.
 2. Search for “Ollama Vision” and select it.
 3. You’ll be prompted to configure:

 - **Name**: A name for this Ollama Vision instance
 - **Vision Host**: Hostname/IP for your Ollama server running the vision-enabled model
 - **Vision Port**: Port for the vision server (default: 11434)
 - **Vision Model**: The vision-capable model name (default: moondream)
 - **Vision Model Keep-Alive**: Keep this model loaded in memory (-1 for indefinite)
 - **Enable Text Model**: Toggle a separate text model for enhanced descriptions
 - **Text Model Host**: Hostname/IP for the optional text-model server
 - **Text Model Port**: Port for the text-model server (default: 11434)
 - **Text Model**: The text model name (default: llama3.1)
 - **Text Model Keep-Alive**: Keep the text model loaded in memory (-1 for indefinite)

Click Submit to save. You can add multiple Ollama Vision configurations (each with a different name or model) if you wish; each configuration will appear as a device with its own sensors.

## Usage

You can queue images for analysis via the `ollama_vision.analyze_image` service. When called, it generates or updates a dynamic sensor holding the description of the analyzed image. 

Note! The sensors will appear as **unavailable** after rebooting Home Assistant or reloading the integration. This is due to the fact that these sensors are dynamically created. You can create thousands of sensors if you wish, and I don't think persisting them is a good idea, because it would also require a bullet proof way of cleaning them up when needed.

Below is an example automation that describes a person detected by Frigate:

```
alias: Describe the person outside
description: ""
triggers:
  - topic: frigate/events
    trigger: mqtt
conditions:
  - condition: template
    value_template: "{{ trigger.payload_json['after']['label'] == 'person' }}"
  - condition: template
    value_template: |-
      {{ 'front' in trigger.payload_json['after']['entered_zones'] or
         'back' in trigger.payload_json['after']['entered_zones'] }}
  - condition: template
    value_template: >-
      {% set last =
      state_attr('automation.describe_the_person_outside','last_triggered') %} {{
      last is none or (now() - last).total_seconds() > 60 }}
actions:
  - action: ollama_vision.analyze_image
    data:
      image_url: >-
        http://<HOME-ASSISTANT-IP>:8123/api/frigate/notifications/{{trigger.payload_json['after']['id']}}/thumbnail.jpg
      image_name: person_outside
      use_text_model: true
      text_prompt: >-
        You are an AI that introduces people that come visit me. You are
        cheeky and love a good roast. based on the following description:
        <description>{description}</description> - introduce this guest for
        me. Make it short and concise.
      device_id: <YOUR OLLAMA VISION DEVICE ID>    
```

This either creates or updates a sensor named something like `sensor.<integration_name>_person_outside` containing your model’s description. You may also provide the `prompt` parameter if you want to change the default parameter used for the vision model; for example if you want to try and make it read license plates or give it other more specific tasks.

### Service Parameters

| Parameter      | Required | Description                                                                                                           |
|----------------|----------|-----------------------------------------------------------------------------------------------------------------------|
| image_url      | Yes      | URL of the image to analyze. Must be accessible to Home Assistant.                                                    |
| image_name     | Yes      | Unique identifier for the image (also used in naming the sensor).                                                     |
| prompt         | No       | Prompt sent to the vision model (default: a prompt asking for a clear description of any people, ages, expressions, and what’s on your porch). |
| device_id      | No       | If you have multiple Ollama Vision devices configured, specify which device ID to use. If omitted, the service uses the first available Ollama Vision device. |
| use_text_model | No       | Whether to use a second, specialized text model for elaboration (default: false).                                      |
| text_prompt    | No       | Prompt for the text model, referencing {description} which is the output from the vision model (default: a short, cheeky introduction). |

### Events

When an image is analyzed, the integration fires an event named ollama_vision_image_analyzed. Its data fields include:

 - "integration_id": The device/config entry used.
 - "image_name": The `image_name` provided.
 - "image_url": The `image_url` provided.
 - "prompt": The prompt given to the vision model.
 - "description": The vision model’s raw output.
 - "used_text_model": Whether a specialized text model was used.
 - "text_prompt": The text prompt passed to the second model (if any).
 - "final_description": The final output from the integration.

You can use this event to trigger other automations. For example, sending the result to your phone:

```
alias: Send analysis results to my phone
triggers:
  - event_type: ollama_vision_image_analyzed
    trigger: event
conditions: []
actions:
  - action: notify.mobile_app_myphone
    continue_on_error: true
    data:
      message: |
        {{ trigger.event.data.final_description }}
      data:
        ttl: 0
        priority: high    
```

This automation listens for the `ollama_vision_image_analyzed` event and sends a notification to your mobile device with the final text from the LLM.
