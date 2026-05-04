"""
JSON loader — loads .json files for schemas.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict

from .base import PromptLoader


class JsonLoader(PromptLoader):
    def can_handle(self, path: pathlib.Path) -> bool:
        return path.suffix in (".json",)

    def load(self, path: pathlib.Path) -> Dict[str, Dict[str, Any]]:
        """
        Load a single .json file.
        Detects if it is a prompt collection or a raw schema.
        
        If it's a prompt collection (has 'default' or other env keys), it loads as prompts.
        Otherwise, it might be a raw schema, but we primarily use it for schemas in core.py.
        """
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check if it looks like a DynaPrompt file (env-based)
        # We check for 'default' key as a heuristic
        is_prompt_file = isinstance(data, dict) and "default" in data

        if is_prompt_file:
            return data
        
        # If not a prompt file, we return it as a special schema data
        # but the core logic handles .json files specifically for schemas if they don't match loaders.
        # Actually, for consistency with other loaders:
        return {"default": {path.stem: data}}
