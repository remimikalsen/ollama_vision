"""API client for Ollama Vision (collecting NDJSON lines)."""
import logging
import aiohttp
import base64
import json

_LOGGER = logging.getLogger(__name__)


class OllamaClient:
    """Ollama API client that parses NDJSON lines when stream=true."""

    def __init__(
        self,
        host,
        port,
        model,
        text_host=None,
        text_port=None,
        text_model=None,
        vision_keepalive=-1,
        text_keepalive=-1,
    ):
        self.host = host
        self.port = port
        self.model = model
        self.vision_keepalive = vision_keepalive
        self.api_base_url = f"http://{host}:{port}/api"

        self.text_enabled = text_host is not None
        self.text_host = text_host
        self.text_port = text_port
        self.text_model = text_model
        self.text_keepalive = text_keepalive
        self.text_api_base_url = (
            f"http://{text_host}:{text_port}/api" if self.text_enabled else None
        )

    async def analyze_image(self, image_url: str, prompt: str) -> str:
        """
        Send an image analysis request to Ollama in streaming (NDJSON) mode.
        Concatenate the .response fields into one final string, or return None on error.
        """
        try:
            # 1) Download the image
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status != 200:
                        _LOGGER.error("Failed to fetch image from URL: %s", image_url)
                        return None
                    image_data = await resp.read()

            # 2) Convert to Base64
            image_base64 = base64.b64encode(image_data).decode("utf-8")

            # 3) Build request payload with stream=true
            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": [image_base64],
                "stream": True,
                "keep_alive": self.vision_keepalive
            }

            _LOGGER.debug("Vision model: %s", self.model)
            _LOGGER.debug("Vision API: %s", self.api_base_url)
            _LOGGER.debug("Vision prompt: %s", prompt)

            # 4) Make the POST request and parse NDJSON lines
            async with aiohttp.ClientSession() as session:
                url = f"{self.api_base_url}/generate"
                async with session.post(url, json=payload) as gen_response:
                    if gen_response.status != 200:
                        text = await gen_response.text()
                        _LOGGER.error("Failed response from Ollama: %s", text)
                        return None

                    final_text = await self._collect_ndjson(gen_response)
                    return final_text

        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error("Error analyzing image: %s", exc)
            return None

    async def elaborate_text(self, text: str, prompt_template: str) -> str:
        """
        Same NDJSON approach for text elaboration, if the user has a text model.
        Concatenate partial tokens from .response
        """
        if not self.text_enabled:
            # fallback
            return text

        try:
            # 1) Substitute the user’s text into the prompt template
            prompt = prompt_template.replace("{description}", text)

            payload = {
                "model": self.text_model,
                "prompt": prompt,
                "stream": True,
                "keep_alive": self.text_keepalive
            }

            _LOGGER.debug("Text model: %s", self.text_model)
            _LOGGER.debug("Text API: %s", self.text_api_base_url)
            _LOGGER.debug("Text prompt: %s", prompt)

            async with aiohttp.ClientSession() as session:
                url = f"{self.text_api_base_url}/generate"
                async with session.post(url, json=payload) as gen_response:
                    if gen_response.status != 200:
                        err = await gen_response.text()
                        _LOGGER.error("Failed response from text Ollama: %s", err)
                        return text

                    final_text = await self._collect_ndjson(gen_response)
                    return final_text or text

        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error("Error elaborating text: %s", exc)
            return text

    async def _collect_ndjson(self, response: aiohttp.ClientResponse) -> str:
        """
        Collect NDJSON lines of the form:
            {"response":" The", "done":false}
        and keep appending .response to a list.
        Stop if 'done': true or if no more lines.
        Return the concatenated text.
        """
        collected_parts = []
        async for raw_line in response.content:
            line = raw_line.decode("utf-8").rstrip("\n")
            if not line.strip():
                continue  # skip empty lines

            # Each line is a full JSON object
            try:
                data_obj = json.loads(line)
            except json.JSONDecodeError:
                _LOGGER.warning("NDJSON parse error on line: %r", line)
                continue

            # Extract the partial text
            partial = data_obj.get("response", "")
            collected_parts.append(partial)

            # If done == true, we can break
            if data_obj.get("done") is True:
                break

        return "".join(collected_parts)
