"""Loader plugin interface."""
from __future__ import annotations

import pathlib
from abc import ABC, abstractmethod
from typing import Dict, Any


class PromptLoader(ABC):
    """
    Abstract base class for all prompt loaders.
    Each loader handles a specific file format.
    Returns data in the shape: {env: {prompt_name: {key: value}}}
    """

    @abstractmethod
    def load(self, path: pathlib.Path) -> Dict[str, Dict[str, Any]]:
        """Load and parse the file. Returns {env: {name: data}}."""
        raise NotImplementedError

    @abstractmethod
    def can_handle(self, path: pathlib.Path) -> bool:
        """Return True if this loader handles the given path."""
        raise NotImplementedError
