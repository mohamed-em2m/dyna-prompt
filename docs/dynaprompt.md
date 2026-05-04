# DynaPrompt Documentation

DynaPrompt is an LLM prompt management library built on the core principles of Dynaconf. It helps you separate prompt logic from your application code.

## Core Concepts

### 1. The DynaPrompt Object
The main entry point. It handles lazy loading, environment switching, and provides access to all your prompts and schemas as attributes.

```python
from dynaprompt import DynaPrompt
prompts = DynaPrompt(settings_files=["prompts/"])
```

### 2. Prompt Storage
Prompts can be stored in two main ways:

- **Markdown Files (`.md` / `.txt`)**: Best for long templates. Use YAML frontmatter for metadata.
- **TOML Files (`.toml`)**: Best for grouping multiple small prompts or managing configuration overrides.

### 3. Automatic Schema Loading
DynaPrompt automatically scans your `settings_files` for schemas:

- **Python (`.py`)**: Imports the file and registers all defined classes. This is designed for **Pydantic** models.
- **JSON (`.json`)**: Loads the file and registers the JSON structure under the filename.

Registered schemas can be referenced by name in your prompt frontmatter or accessed directly:
```python
schema = prompts.MyPydanticModel
```

## Advanced Features

### Environment Layering
Just like Dynaconf, DynaPrompt supports environments. You can override prompt metadata (like which model to use) per environment without changing the template.

```python
with prompts.using_env("production"):
    rendered = prompts.my_prompt.render(...)
```

### Hooks
Intercept the prompt lifecycle:
- `before_render`: Modify inputs.
- `after_render`: Redact sensitive info or log outputs.

### Validation
Register validators to ensure that rendered prompts meet certain criteria (e.g., token limits, specific keywords).
