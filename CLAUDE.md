# CLAUDE.md - Ollama Vision Integration

This document provides a comprehensive guide for AI assistants working on the Ollama Vision Home Assistant custom component.

## Project Overview

**Ollama Vision** is a Home Assistant custom component (HACS integration) that enables local image analysis using Ollama-powered vision models. It allows users to analyze images from various sources (cameras, URLs, local files) and optionally enhance descriptions using a separate text model.

### Key Features
- Vision model integration for image analysis
- Optional text model for enhanced descriptions
- Dynamic sensor creation for analyzed images
- Event-driven architecture
- Support for multiple Ollama instances
- HACS compatible installation

### Project Metadata
- **Domain**: `ollama_vision`
- **Current Version**: 1.0.7 (in `VERSION`, `manifest.json`, `const.py`)
- **Author**: @remimikalsen
- **Repository**: https://github.com/remimikalsen/ollama_vision
- **License**: See LICENSE file
- **Home Assistant Minimum**: 2025.2
- **HACS Minimum**: 2.0

## Repository Structure

```
ollama_vision/
├── custom_components/ollama_vision/    # Main integration code
│   ├── __init__.py                     # Integration setup and service handlers
│   ├── api.py                          # Ollama API client (NDJSON streaming)
│   ├── config_flow.py                  # Configuration UI flow
│   ├── const.py                        # Constants and defaults
│   ├── manifest.json                   # Integration metadata
│   ├── sensor.py                       # Sensor platform implementation
│   ├── services.yaml                   # Service definitions
│   └── translations/                   # Localization files
│       ├── en.json                     # English translations
│       ├── nb.json                     # Norwegian translations
│       └── pt.json                     # Portuguese translations
├── .github/workflows/                  # GitHub Actions CI/CD
│   ├── hacs.yaml                       # HACS validation
│   ├── hassfest.yaml                   # Home Assistant validation
│   └── publish.yaml                    # Automated release workflow
├── hacs.json                           # HACS configuration
├── LICENSE                             # License file
├── README.md                           # User documentation
└── VERSION                             # Version file (single source of truth)
```

## Architecture

### Core Components

#### 1. Integration Setup (`__init__.py`)

**Purpose**: Main entry point for the integration

**Key Functions**:
- `async_setup()` - Initialize integration data structure
- `async_setup_entry()` - Set up config entry, create OllamaClient, register services
- `handle_analyze_image()` - Service handler for image analysis
- `async_unload_entry()` - Clean up on unload
- `async_reload_entry()` - Reload configuration

**Data Structure**:
```python
hass.data[DOMAIN] = {
    "pending_sensors": {},           # Temporary storage for sensor data
    "created_sensors": {},           # Registry of created sensors
    "<entry_id>": {
        "client": OllamaClient,      # API client instance
        "sensors": {},               # Sensors for this entry
        "config": {...},             # Configuration
        "device_info": {...},        # Device metadata
        "async_add_entities": func   # Entity addition callback
    }
}
```

**Service Registration**:
- Service: `ollama_vision.analyze_image`
- Registered once per integration instance
- Handles multi-instance setups via `device_id` parameter

**Events**:
- `ollama_vision_create_sensor` - Internal event for sensor creation
- `ollama_vision_image_analyzed` - User-facing event with analysis results

#### 2. API Client (`api.py`)

**Purpose**: Handle communication with Ollama servers

**Key Class**: `OllamaClient`

**Features**:
- NDJSON streaming response parsing
- Support for both vision and text models
- Flexible URL parsing (full URLs, hostname:port, hostname only)
- Image source handling:
  - HTTP/HTTPS URLs
  - Internal Home Assistant APIs (starts with `/api`)
  - Local file paths (relative to Home Assistant config)
- Base64 image encoding
- Keep-alive model management

**Methods**:
- `analyze_image(image_url, prompt)` - Send image to vision model
- `elaborate_text(text, prompt_template)` - Enhance description with text model
- `_collect_ndjson(response)` - Parse streaming NDJSON responses

**URL Parsing**:
Supports three formats:
1. Full URL: `http://server.example.com/subpath`
2. Hostname:port: `192.168.1.1:11434`
3. Hostname only: `192.168.1.1` (defaults to port 11434)

#### 3. Configuration Flow (`config_flow.py`)

**Purpose**: UI-based configuration and options management

**Flow Classes**:
- `OllamaVisionConfigFlow` - Initial setup flow
- `OllamaVisionOptionsFlow` - Configuration update flow

**Setup Steps**:
1. **user** - Configure vision model (name, host, model, keepalive, enable text model)
2. **text_model** - Configure text model (conditional, only if enabled)

**Options Steps**:
1. **init** - Update vision settings
2. **text_model_options** - Update text model settings (conditional)

**Validation**:
- Tests Ollama server connectivity via `/api/version` endpoint
- Supports URL format migration (host:port → hostname:port)

#### 4. Sensor Platform (`sensor.py`)

**Purpose**: Create and manage sensor entities

**Sensor Types**:

1. **OllamaVisionInfoSensor**
   - Shows vision model configuration
   - State: `{model} @ {host}`
   - Icon: `mdi:information-outline`

2. **OllamaTextModelInfoSensor**
   - Shows text model configuration (if enabled)
   - State: `{model} @ {host}`
   - Icon: `mdi:information-outline`

3. **OllamaVisionImageSensor**
   - Dynamically created for each analyzed image
   - State: First 255 chars of description
   - Attributes:
     - `integration_id`
     - `image_url`
     - `prompt`
     - `full_description`
     - `used_text_model` (if applicable)
     - `text_prompt` (if applicable)
     - `final_description` (if applicable)
   - Icon: `mdi:image-text`

**Dynamic Sensor Creation**:
- Sensors created via event bus (`ollama_vision_create_sensor`)
- Unique ID: `{entry_id}_{slugified_image_name}`
- Sensors are **unavailable** after restart (by design, not persisted)
- Can create thousands of sensors dynamically

**Update Mechanism**:
- `async_update_from_pending()` - Pull data from pending_sensors
- Event-driven updates (not polled)
- State written immediately after analysis

#### 5. Constants (`const.py`)

**Purpose**: Centralized configuration values

**Key Constants**:
- Version: `__version__ = "1.0.7"`
- Domain: `DOMAIN = "ollama_vision"`
- Default models: `moondream` (vision), `llama3.1` (text)
- Default ports: 11434
- Default keepalive: -1 (indefinite)
- Service names, attribute keys, event names

## Development Workflows

### Version Management

**Version Sources** (must stay in sync):
1. `VERSION` file - Single line with version number
2. `custom_components/ollama_vision/manifest.json` - `"version"` field
3. `custom_components/ollama_vision/const.py` - `__version__` variable

**Versioning Strategy**:
- Semantic versioning (MAJOR.MINOR.PATCH)
- Auto-incremented by CI/CD on merge to main
- Patch bump by default
- Include `[minor]` or `[major]` in commit message to trigger version bump

**Manual Version Updates**:
If you need to update the version manually, update all three files:
```bash
NEW_VERSION="1.0.8"
echo "$NEW_VERSION" > VERSION
sed -i 's/"version": "[^"]*"/"version": "'$NEW_VERSION'"/' custom_components/ollama_vision/manifest.json
sed -i 's/__version__ = "[^"]*"/__version__ = "'$NEW_VERSION'"/' custom_components/ollama_vision/const.py
```

### Release Process

**Automated via GitHub Actions** (`.github/workflows/publish.yaml`):

**Trigger**: Push to `main` branch (typically via PR merge)

**Steps**:
1. Determine next version based on:
   - Latest git tag
   - Commit message keywords (`[major]`, `[minor]`)
   - Default: patch bump
2. Update VERSION, manifest.json, const.py
3. Commit changes with `[skip ci]` flag
4. Create and push git tag
5. Generate release notes from PR metadata
6. Create GitHub release

**Release Notes Format**:
```markdown
## {PR Title}

### Summary
{PR Body}

### Changes
• {commit message} ({short SHA})
• {commit message} ({short SHA})
```

**Commit Message Requirements**:
- Clear, descriptive messages
- Prefix with type (e.g., `feat:`, `fix:`, `docs:`, `ci:`)
- Include `[skip ci]` for version bump commits
- Include `[major]` or `[minor]` for version control

### Testing and Validation

**GitHub Actions Workflows**:

1. **HACS Validation** (`.github/workflows/hacs.yaml`)
   - Validates HACS compatibility
   - Runs on push and PR

2. **Hassfest Validation** (`.github/workflows/hassfest.yaml`)
   - Validates Home Assistant integration standards
   - Checks manifest.json, translations, etc.
   - Runs on push and PR

**Manual Testing**:
- Test with Home Assistant dev environment
- Verify vision model analysis
- Test text model enhancement
- Check sensor creation/updates
- Validate configuration UI
- Test error handling

### Adding New Features

**General Guidelines**:

1. **Constants**: Add new config keys to `const.py`
2. **Config Flow**: Update `config_flow.py` schemas if adding user-configurable options
3. **Translations**: Update all translation files in `translations/`
4. **Services**: Update `services.yaml` if adding/modifying services
5. **Documentation**: Update README.md with user-facing changes
6. **Version**: Will be auto-bumped by CI/CD

**Example: Adding a New Service Parameter**:

1. Add constant to `const.py`:
```python
ATTR_NEW_PARAM = "new_param"
DEFAULT_NEW_PARAM = "default_value"
```

2. Update service schema in `__init__.py`:
```python
ANALYZE_IMAGE_SCHEMA = vol.Schema({
    # ... existing params
    vol.Optional(ATTR_NEW_PARAM, default=DEFAULT_NEW_PARAM): cv.string,
})
```

3. Update service handler in `__init__.py`:
```python
async def handle_analyze_image(hass, call):
    new_param = call.data.get(ATTR_NEW_PARAM, DEFAULT_NEW_PARAM)
    # ... use new_param
```

4. Update `services.yaml`:
```yaml
analyze_image:
  fields:
    new_param:
      name: "New Parameter"
      description: "Description of the new parameter"
      required: false
      default: "default_value"
      selector:
        text:
```

5. Update all translation files (`translations/*.json`):
```json
{
  "services": {
    "analyze_image": {
      "fields": {
        "new_param": {
          "name": "New Parameter",
          "description": "Description of the new parameter."
        }
      }
    }
  }
}
```

### Code Style and Conventions

**Python Standards**:
- Follow PEP 8 style guide
- Use type hints where beneficial
- Prefer async/await for I/O operations
- Use Home Assistant's built-in helpers

**Naming Conventions**:
- Constants: `UPPER_SNAKE_CASE`
- Functions: `snake_case`
- Classes: `PascalCase`
- Private methods: `_leading_underscore`
- Async functions: `async_` prefix

**Error Handling**:
- Use `_LOGGER.error()` for errors with context
- Use `_LOGGER.warning()` for warnings
- Use `_LOGGER.debug()` for debugging info
- Return `None` on API failures (graceful degradation)
- Raise `HomeAssistantError` for user-facing errors

**Logging Best Practices**:
```python
# Good - includes context
_LOGGER.error("Failed to fetch image from URL: %s", url)

# Good - structured data in debug
_LOGGER.debug("Vision model: %s", self.model)

# Avoid - no context
_LOGGER.error("Failed")
```

**Comments**:
- Docstrings for all public functions/classes
- Inline comments for complex logic
- Type hints over comment-based type documentation

### Configuration Migration

**Migration Pattern** (see `__init__.py` and `config_flow.py`):

When configuration schema changes, handle backward compatibility:

```python
# Old format: separate host and port
# New format: host can be hostname:port or full URL

host = entry.data.get(CONF_HOST) or entry.options.get(CONF_HOST)
port = entry.data.get(CONF_PORT) or entry.options.get(CONF_PORT)

# Migrate old config
if port and host and ':' not in host and not host.startswith('http'):
    host = f"{host}:{port}"
    port = None
```

**Key Principles**:
- Never break existing configurations
- Auto-migrate on load
- Update options flow to use new format
- Document migration in README

## Key Conventions for AI Assistants

### When Modifying Code

1. **Always check version synchronization**
   - Don't manually update versions unless specifically requested
   - CI/CD handles version bumps automatically

2. **Test API changes carefully**
   - API client uses NDJSON streaming (not simple JSON)
   - Image sources have three distinct code paths
   - URL parsing supports multiple formats

3. **Respect sensor lifecycle**
   - Dynamic sensors are intentionally not persisted
   - Sensors become unavailable after restart
   - Use pending_sensors → created_sensors pattern

4. **Update all translation files**
   - Changes to UI strings need updates in all language files
   - At minimum: en.json, nb.json, pt.json

5. **Maintain backward compatibility**
   - Users may have existing configurations
   - Implement migrations for schema changes

6. **Follow Home Assistant patterns**
   - Use Home Assistant's aiohttp client for internal requests
   - Use executor for file I/O
   - Follow entity/device conventions

### Common Pitfalls to Avoid

1. **Breaking NDJSON parsing**
   - Don't change `_collect_ndjson()` without understanding streaming responses
   - Ollama uses `stream=true` with newline-delimited JSON

2. **Forgetting to slugify**
   - Image names must be slugified for entity IDs
   - Use `slugify()` from `homeassistant.util`

3. **Service registration conflicts**
   - Service is registered per integration instance
   - Check for existing service before registering
   - Unregister only when last instance is removed

4. **Breaking URL parsing**
   - `_parse_url_or_host_port()` appears in both `api.py` and `config_flow.py`
   - Keep implementations in sync
   - Handle all three formats: full URL, hostname:port, hostname

5. **Image data handling**
   - Different code paths for HTTP/HTTPS, internal API, local files
   - Must handle base64 encoding correctly
   - Validate image data exists before processing

6. **Entity registry issues**
   - Dynamic sensors need unique IDs
   - Clean up sensors on entry unload
   - Don't persist dynamic sensors

### Testing Checklist

Before submitting changes:

- [ ] All translation files updated
- [ ] README updated if user-facing changes
- [ ] services.yaml updated if service changes
- [ ] No hardcoded strings (use constants)
- [ ] Error handling with proper logging
- [ ] Backward compatibility maintained
- [ ] Code follows Home Assistant patterns
- [ ] Type hints added where beneficial
- [ ] Docstrings for new functions/classes

## Common Tasks

### Adding Support for a New Image Source

1. Identify the source pattern (URL prefix, path format, etc.)
2. Add handling in `api.py` → `analyze_image()` method
3. Add to documentation in README.md
4. Consider adding example automation

Example:
```python
# In api.py, analyze_image method
elif image_url.startswith("custom://"):
    # Handle custom source
    image_data = await self._fetch_custom_source(image_url)
```

### Adding a New Translation

1. Copy `translations/en.json` to `translations/{lang_code}.json`
2. Translate all strings
3. Update hacs.json if needed (though not required)
4. Test in Home Assistant UI

### Debugging Image Analysis Issues

**Common Issues**:

1. **Image not loading**
   - Check image URL format
   - Verify Home Assistant can reach the URL
   - Check file permissions for local files
   - Enable debug logging: `_LOGGER.debug()`

2. **Ollama not responding**
   - Verify Ollama server is running
   - Check OLLAMA_HOST environment variable
   - Test with curl: `curl http://host:port/api/version`
   - Check keep-alive settings

3. **Sensor not updating**
   - Check pending_sensors structure
   - Verify event is fired: `ollama_vision_create_sensor`
   - Check unique ID slugification
   - Look for errors in Home Assistant logs

4. **Text model not working**
   - Verify text model is enabled in config
   - Check `use_text_model=true` in service call
   - Verify text model server connectivity
   - Check model name is correct

### Extending Functionality

**Good candidates for extension**:
- Additional image sources (e.g., Ring cameras, UniFi Protect)
- Image preprocessing (resize, crop, filters)
- Batch image analysis
- Model response caching
- Custom prompt templates
- Integration with other Home Assistant components

**Follow these patterns**:
- Keep changes modular
- Add config options for new features
- Maintain backward compatibility
- Update documentation
- Add examples to README

## File Reference

### Critical Files (Modify with Care)

- `custom_components/ollama_vision/__init__.py` - Core integration logic
- `custom_components/ollama_vision/api.py` - API client
- `custom_components/ollama_vision/config_flow.py` - Configuration UI
- `custom_components/ollama_vision/sensor.py` - Sensor entities

### Configuration Files (Sync Required)

- `VERSION` - Version number
- `custom_components/ollama_vision/manifest.json` - Integration manifest
- `custom_components/ollama_vision/const.py` - Constants and version

### Documentation Files

- `README.md` - User documentation
- `CLAUDE.md` - This file (AI assistant guide)
- `custom_components/ollama_vision/services.yaml` - Service definitions

### CI/CD Files

- `.github/workflows/publish.yaml` - Automated releases
- `.github/workflows/hacs.yaml` - HACS validation
- `.github/workflows/hassfest.yaml` - HA validation

## Additional Resources

- **Home Assistant Developer Docs**: https://developers.home-assistant.io/
- **HACS Documentation**: https://hacs.xyz/
- **Ollama API Documentation**: https://github.com/ollama/ollama/blob/main/docs/api.md
- **Project Blog Post**: https://theawesomegarage.com/blog/ollama-vision-local-ai-image-processing-in-home-assistant

## Questions or Issues?

When encountering issues:

1. Check Home Assistant logs for errors
2. Enable debug logging: Set logger level to debug for `custom_components.ollama_vision`
3. Verify Ollama server connectivity
4. Review recent changes to integration configuration
5. Check GitHub issues: https://github.com/remimikalsen/ollama_vision/issues

## Summary

This integration provides a robust, event-driven system for local image analysis in Home Assistant. The architecture emphasizes:

- **Flexibility**: Support for multiple Ollama instances and models
- **Dynamic behavior**: Sensors created on-demand, not persisted
- **User experience**: Clear configuration flow, rich sensor attributes
- **Extensibility**: Modular design, easy to add new features
- **Reliability**: Graceful error handling, comprehensive logging

When working on this codebase, prioritize backward compatibility, user experience, and Home Assistant best practices.
