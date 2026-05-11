# Welcome to DynaPrompt

Dynamic prompt management and configuration library for LLM applications. Powerful, lazy-loading, and supports Jinja2 templates and Pydantic schemas.

## Quick Start

```bash
pip install dynaprompt
```

## Basic Usage

```python
from dynaprompt import DynaPrompt

# Initialize from a directory
prompts = DynaPrompt(settings_files=["prompts/"])

# Render a prompt
rendered = prompts.customer_service.render(user="Ahmed")
print(rendered.text)
```

## Key Features

- **🚀 Lazy Loading**: Prompts are only loaded and compiled when first accessed.
- **🌍 Environment Awareness**: Switch between `development`, `production`, and `testing` with zero code changes.
- **🛡️ Type Safety**: Native Pydantic support for structured LLM outputs.
- **🔧 Jinja2 Power**: Use filters, loops, and inheritance in your prompt templates.
- **🔌 Extensible**: Add custom validators and lifecycle hooks easily.
- **⚡ Async Support**: Non-blocking rendering for FastAPI and high-performance apps.

Explore the [Guide](dynaprompt.md) to learn more!
