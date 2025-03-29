![Build Status](https://img.shields.io/github/actions/workflow/status/remimikalsen/ollama_vision/publish.yaml)
![HACS Test](https://img.shields.io/github/actions/workflow/status/remimikalsen/ollama_vision/hacs.yaml?label=HACS)
![Hassfest Test](https://img.shields.io/github/actions/workflow/status/remimikalsen/ollama_vision/hassfest.yaml?label=Hassfest)
![License](https://img.shields.io/github/license/remimikalsen/ollama_vision)
![Version](https://img.shields.io/github/tag/remimikalsen/ollama_vision)


# Ollama Vision

This integration enables you to analyze images using a local Ollama server running a vision-enabled LLM. Optionally, it can also use a specialized text model to generate more elaborate text. For example, you could add a cheeky or “roast-style” introduction for people captured on a security camera. 

You can for example use external images reachable over http/https, Frigate, Google Nest cameras or even local files as the image source for analysis. Have your local LLM describe images and send those descriptions to your phone, or use them in automations however you like.

I wrote a step-by-step guide for Ollama Vision on my technology blog, [The Awesome Garage](https://theawesomegarage.com/blog/ollama-vision-local-ai-image-processing-in-home-assistant).

## Requirements

 - Images must be accessible via either:
    - HTTP/HTTPS to your Home Assistant server.
    - Located within the config-directory of your Home Assistant installation.
    - An internal API that is accessible through a hass client session.
    - The Google Nest doorbell needs a little extra config to work.
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

Note! The sensors will appear as **unavailable** after rebooting Home Assistant or reloading the integration. This is due to the fact that these sensors are dynamically created. You can create thousands of sensors if you wish, and I don't think persisting them is a good idea, because it would also require a bulletproof way of cleaning them up when needed.

### Frigate example
The following automation describes a person detected by Frigate:

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

### Google Nest doorbell example
The following automation describes a person detected by a Google Nest doorbell. Before you begin, set up your [Google Nest integration](https://www.home-assistant.io/integrations/nest/). And make sure to go to your Google Home app and enable person and chime notifications on your mobile phone. This won't work if you don't enable the notifications in the Google Home app.

When you've set up the integration successfully, you will get a device from your doorbell that you can use to trigger automations like this:

```
alias: Describe the person in front of my doorbell
description: ""
triggers:
  - device_id: <YOUR GOOGLE NEST DOORBELL DEVICE ID>
    domain: nest
    type: doorbell_chime
    trigger: device
  - device_id: <YOUR GOOGLE NEST DOORBELL DEVICE ID>
    domain: nest
    type: camera_person
    trigger: device
conditions:
  - condition: template
    value_template: >-
      {% set last =
      state_attr('automation.describe_the_person_in_front_of_my_doorbell','last_triggered')
      %} {{ last is none or (now() - last).total_seconds() > 60 }}
actions:
  - action: shell_command.download_nest_image
    data:
      url: http://<HOME-ASSISTANT-IP>:8123{{ trigger.event.data.attachment.image }}
      token: >-
        <ADD-A-LONG-LIVED-ACCESS-TOKEN-HERE>
      filename: doorbell
  - action: ollama_vision.analyze_image
    data:
      image_url: www/my_nest_images/doorbell.jpg
      image_name: doorbell
      device_id: <YOUR OLLAMA VISION DEVICE ID>
mode: single
```

For this to work, you must do a few more things.

1) Add a script to your config directory (alongside your main configuration.yaml-file). Call it `download_nest_image.sh`, and make it have the following contents:

```
#!/bin/bash
mkdir -p /config/www/my_nest_images
curl -s -X GET "$1" -H "Authorization: Bearer $2" --output "/config/www/my_nest_images/$3.jpg"
```

It's imperative the script is executable. Make it so from the terminal:

```
chmod +x download_nest_image.sh
```

2) Now, create a download action in your `configuration.yaml` file:

```
shell_command:
  download_nest_image: bash /config/download_nest_image.sh "{{ url }}" "{{ token }}" "{{ filename }}"
```

Needless to say, after you've changed `configuration.yaml`, you need to restart for the actions to take effect.

3) Finally, create a long lived access token to use in the automation. Go to the bottom of your Home Assistant profile page and generate a new token.

Now, update the relevant parts of the automation above and try it out.


The above examples either creates or updates a sensor named something like `sensor.<integration_name>_person_outside` or `sensor.<integration_name>_doorbell` containing your model’s description. You may also provide the `prompt` parameter if you want to change the default parameter used for the vision model; for example if you want to try and make it read license plates or give it other more specific tasks.

**NOTE!** The first time you call the analyze_image action after starting or restarting Ollama it will be slow. This is because Ollama needs to load its models into memory.

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
 - "image_url": The `image_url` a best effort companion app compatible link to the analyzed image.
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
      message: Image notification
      data:
        ttl: 0
        priority: high
        sticky: true
        image: |
          {{ trigger.event.data.image_url }}
  - action: notify.mobile_app_myphone
    continue_on_error: true
    data:
      message: |
        {{ trigger.event.data.final_description }}
      data:
        ttl: 0
        priority: high
        sticky: true
```

This automation listens for the `ollama_vision_image_analyzed` event and sends a notification to your mobile device with the final text from the LLM.

Note! You can opt for sending the image and the text in one notification, but on Android, your message will be cut short. That's why I opt for sending the notification in two messages.


## Troubleshooting

### Failed response from text Ollama: {"error":"llama runner process has terminated: error loading model: check_tensor_dims: tensor 'output.weight' not found"}

These kinds of errors can typically mean you either run an unsupported model, or that you have installed a supported model, but you must update your Ollama server. To update on Linux, simply run:

```
curl -fsSL https://ollama.com/install.sh | sh
```


### Ollama stopped working from Home Assistant after upgrade

Check your ollama service file. Maybe Ollama reverted to only answer on localhost, not on your network. Override the Ollama default service file through an override-file that will survive upgrades.

```
sudo systemctl edit ollama

# This will open a blank or a templated editor
# Add the following text where the template tells  you to, or if it's a blank file, just paste the text to the file:
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_KEEP_ALIVE=-1"
```

Now save and exit, and run:   

```
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

You should be good again!