"""Loader registry — maps file extensions to loader instances."""

from __future__ import annotations

import pathlib

from .base import PromptLoader
from .json_loader import JsonLoader
from .markdown_loader import MarkdownLoader
from .toml_loader import TomlLoader
from .yaml_loader import YamlLoader

# Registry: ordered list of available loaders
_LOADERS = [
    TomlLoader(),
    MarkdownLoader(),
    JsonLoader(),
    YamlLoader(),
]


def get_loader_for(path: pathlib.Path) -> PromptLoader:
    """Return the appropriate loader for the given file path."""
    for loader in _LOADERS:
        if loader.can_handle(path):
            return loader
    raise ValueError(
        f"No loader found for file: {path}. "
        f"Supported extensions: .toml, .md, .txt, .json, .yaml, .yml"
    )


def register_loader(loader: PromptLoader) -> None:
    """Register a custom loader (inserted at highest priority)."""
    _LOADERS.insert(0, loader)


__all__ = [
    "get_loader_for",
    "register_loader",
    "PromptLoader",
    "TomlLoader",
    "MarkdownLoader",
]
