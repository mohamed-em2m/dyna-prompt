"""
YAML loader — loads .yaml/.yml files.
"""
from __future__ import annotations

import pathlib
from typing import Any, Dict

import yaml

from .base import PromptLoader


class YamlLoader(PromptLoader):
    def can_handle(self, path: pathlib.Path) -> bool:
        return path.suffix in (".yaml", ".yml")

    def load(self, path: pathlib.Path) -> Dict[str, Dict[str, Any]]:
        """
        Load a single .yaml file.
        Returns {env: {prompt_name: data}}.
        """
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if not isinstance(raw, dict):
            return {}

        # raw = {'default': {'prompt_name': {...}}}
        result: Dict[str, Dict[str, Any]] = {}
        for env_key, prompts in raw.items():
            if not isinstance(prompts, dict):
                continue
            result[env_key] = {}
            for prompt_name, data in prompts.items():
                if isinstance(data, dict):
                    result[env_key][prompt_name] = data

        return result
