# DynaPrompt API Reference

## DynaPrompt

The main lazy-loading settings manager.

### `__init__`
- `settings_files`: List of files or directories to load.
- `environments`: (bool) Enable environment support. Default `True`.
- `env`: (str) Initial environment.
- `file_prefix`: (str) Optional prefix to filter files (e.g. `gpt_`).

### Attribute Access
Access prompts and schemas directly:
- `prompts.my_prompt`: Returns a `PromptNode`.
- `prompts.MySchema`: Returns a registered schema.

### Methods
- `get(name)`: Explicit getter for prompts.
- `using_env(env)`: Context manager for temporary environment switching.
- `inspect(name=None)`: Returns loading history for debugging.
- `reload()`: Discards cache and reloads all files from disk.

## PromptNode

The object representing a single loaded prompt.

### Methods
- `render(**kwargs)`: Renders the template using Jinja2 and returns a `RenderedPrompt`.
- `with_model(model_name)`: Returns a new `PromptNode` with the model overridden.

## RenderedPrompt

The result of calling `.render()`.

### Attributes
- `text`: The final rendered prompt string.
- `config`: A dictionary of all metadata (model, temperature, etc).
- `response_schema`: The resolved schema class/data.
- `current_env`: The environment used for this render.
