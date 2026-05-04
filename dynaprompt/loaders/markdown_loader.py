"""
Markdown loader — loads .md files with optional YAML frontmatter.

Expected file format::

    ---
    model: gemini-1.5-pro
    temperature: 0.1
    response_schema: CallAnalysisResult
    env: default
    ---
    # ROLE
    You are an expert analyst.

    Date: {{ today }}
    {% if requires_api_access %}
    Token: {{ secrets.API_TOKEN }}
    {% endif %}

The filename (without extension) becomes the prompt name.
The `env:` frontmatter key controls which environment bucket it lands in (default: "default").
"""
from __future__ import annotations

import pathlib
from typing import Any, Dict

import yaml

from .base import PromptLoader


class MarkdownLoader(PromptLoader):
    def can_handle(self, path: pathlib.Path) -> bool:
        return path.suffix in (".md", ".txt")

    def load(self, path: pathlib.Path) -> Dict[str, Dict[str, Any]]:
        """
        Load a single .md file.
        Returns {env: {prompt_name: {template: ..., **frontmatter}}}.
        """
        content = path.read_text(encoding="utf-8")
        prompt_name = path.stem  # filename without extension
        metadata: dict = {}
        body = content

        # Parse YAML frontmatter if present
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    metadata = yaml.safe_load(parts[1]) or {}
                except yaml.YAMLError:
                    metadata = {}
                body = parts[2].strip()

        env = metadata.pop("env", "default")
        data = {"template": body, **metadata}

        return {env: {prompt_name: data}}
