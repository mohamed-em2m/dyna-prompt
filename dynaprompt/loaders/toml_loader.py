"""
TOML loader — primary configuration format.

Expected file structure::

    [default.customer_support]
    version = "1.0"
    template = "You are a helpful assistant. Customer: {{ user_name }}"
    model = "gpt-4.1"
    temperature = 0.3

    [production.customer_support]
    model = "gpt-4.1"          # override only what changes

    [development.customer_support]
    model = "gpt-4.1-mini"
    temperature = 0.7
"""

from __future__ import annotations

import pathlib
from typing import Any

from .base import PromptLoader

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # pip install tomli for < 3.11
    except ImportError:
        tomllib = None


class TomlLoader(PromptLoader):
    def can_handle(self, path: pathlib.Path) -> bool:
        return path.suffix in (".toml",)

    def load(self, path: pathlib.Path) -> dict[str, dict[str, Any]]:
        if tomllib is None:
            raise ImportError(
                "TOML support requires Python 3.11+ or `pip install tomli`"
            )

        with open(path, "rb") as f:
            raw = tomllib.load(f)

        # raw = {'default': {'customer_support': {...}}, 'production': {...}}
        # Validate the top-level keys are env names
        result: dict[str, dict[str, Any]] = {}
        for env_key, prompts in raw.items():
            if not isinstance(prompts, dict):
                continue
            result[env_key] = {}
            for prompt_name, data in prompts.items():
                if isinstance(data, dict):
                    result[env_key][prompt_name] = data

        return result
