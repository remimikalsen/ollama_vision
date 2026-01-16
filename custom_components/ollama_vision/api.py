"""API client for Ollama Vision 2 (collecting NDJSON lines)."""
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import os
import logging
import aiohttp
import base64
import json
from urllib.parse import urlparse
from typing import Sequence, Union

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


class OllamaClient:
    """Ollama API client that parses NDJSON lines when stream=true."""

    def __init__(
        self,
        hass,
        host,
        port,
        model,
        text_host=None,
        text_port=None,
        text_model=None,
        vision_keepalive=-1,
        text_keepalive=-1,
    ):
        self.hass = hass
        self.model = model
        self.vision_keepalive = vision_keepalive
        
        # Parse vision host/URL
        vision_protocol, vision_host, vision_port, vision_path = _parse_url_or_host_port(host, port)
        self.host = vision_host
        self.port = vision_port
        # Build API base URL with path support
        base_path = vision_path if vision_path else ""
        self.api_base_url = f"{vision_protocol}://{vision_host}:{vision_port}{base_path}/api"

        # Parse text model host/URL
        self.text_enabled = text_host is not None
        self.text_host = text_host
        self.text_port = text_port
        self.text_model = text_model
        self.text_keepalive = text_keepalive
        
        if self.text_enabled:
            text_protocol, parsed_text_host, parsed_text_port, text_path = _parse_url_or_host_port(text_host, text_port)
            self.text_host = parsed_text_host
            self.text_port = parsed_text_port
            # Build text API base URL with path support
            text_base_path = text_path if text_path else ""
            self.text_api_base_url = f"{text_protocol}://{parsed_text_host}:{parsed_text_port}{text_base_path}/api"
        else:
            self.text_api_base_url = None

    async def analyze_image(self, image_url: Union[str, Sequence[str]], prompt: str) -> str:
        """
        Send an image analysis request to Ollama in streaming (NDJSON) mode.
        Concatenate the .response fields into one final string, or return None on error.
        """
        if isinstance(image_url, str):
            image_urls = [image_url]
        else:
            image_urls = list(image_url)

        images_b64 = []

        try:
            # Loop through all images
            for image_url in image_urls:

                # 1) Get image data
                # a) Directly from an internal API
                if image_url.startswith("/api"):
                    full_url = f"{self.hass.config.internal_url.rstrip('/')}{image_url}"
                    session = async_get_clientsession(self.hass)

                    async with session.get(full_url) as resp:
                        if resp.status != 200:
                            _LOGGER.error("Failed to fetch image from URL: %s", full_url)
                            return None
                        image_data = await resp.read()

                # b) External URL
                elif image_url.startswith("http://") or image_url.startswith("https://"):
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(image_url) as resp:
                                if resp.status != 200:
                                    _LOGGER.error(
                                        "Failed to fetch external image (Status: %s, URL: %s)", 
                                        resp.status, 
                                        image_url
                                    )
                                    return None
                                
                                try:
                                    image_data = await resp.read()
                                except Exception as read_exc:
                                    _LOGGER.error(
                                        "Error reading image data from external URL (URL: %s): %s", 
                                        image_url, 
                                        str(read_exc)
                                    )
                                    return None

                    except aiohttp.ClientError as client_exc:
                        _LOGGER.error(
                            "Client error fetching external image (URL: %s): %s", 
                            image_url, 
                            str(client_exc)
                        )
                        return None
                    except Exception as fetch_exc:
                        _LOGGER.error(
                            "Unexpected error fetching external image (URL: %s): %s", 
                            image_url, 
                            str(fetch_exc)
                        )
                        return None

                # c) Local File
                else:
                    try:
                        full_path = self.hass.config.path(image_url)
                        
                        # Check file existence in executor
                        file_exists = await self.hass.async_add_executor_job(
                            os.path.isfile, full_path
                        )
                        if not file_exists:
                            _LOGGER.error("Local image file not found: %s", image_url)
                            return None

                        # Read file contents in executor
                        try:
                            image_data = await self.hass.async_add_executor_job(
                                lambda: open(full_path, "rb").read()
                            )
                        except IOError as io_exc:
                            _LOGGER.error(
                                "IO Error reading local image file (Path: %s): %s", 
                                full_path, 
                                str(io_exc)
                            )
                            return None

                    except Exception as local_exc:
                        _LOGGER.error(
                            "Unexpected error accessing local image file (Path: %s): %s", 
                            image_url, 
                            str(local_exc)
                        )
                        return None

                # Validate image data
                if not image_data:
                    _LOGGER.error("No image data retrieved for URL: %s", image_url)
                    return None

                # 2) Convert to Base64
                try:
                    image_base64 = base64.b64encode(image_data).decode("utf-8")
                except Exception as base64_exc:
                    _LOGGER.error(
                        "Error encoding image to base64 (URL: %s): %s", 
                        image_url, 
                        str(base64_exc)
                    )
                    return None
                images_b64.append(image_base64)

            # 3) Build request payload with stream=true
            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": images_b64,
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

        except Exception as exc:
            urls = image_url if isinstance(image_url, list) else [image_url]
            _LOGGER.error("Comprehensive error in image analysis (URLs: %s): %s",", ".join(str(u) for u in urls),exc,)
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