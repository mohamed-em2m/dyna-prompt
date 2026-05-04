"""Utility functions — object_merge and inspect_prompts."""
from __future__ import annotations

import sys
import json
from typing import Any, Dict, Optional


def object_merge(base: dict, override: dict) -> None:
    """
    Deep-merge `override` into `base` in-place.
    Dicts are merged recursively; all other types replace.
    Inspired by Dynaconf's object_merge utility.
    """
    for key, value in override.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, dict)
        ):
            object_merge(base[key], value)
        else:
            base[key] = value


def inspect_prompts(
    prompts,
    key: Optional[str] = None,
    print_report: bool = True,
    to_file: Optional[str] = None,
) -> dict:
    """
    Print or return the loading history of a DynaPrompt instance.
    Mirrors Dynaconf's inspect_settings().

    Args:
        prompts:      A DynaPrompt instance.
        key:          If provided, show history only for that prompt name.
        print_report: If True, print to stdout.
        to_file:      If provided, write JSON report to this file path.

    Returns:
        dict with 'current' and 'history' keys.
    """
    history = prompts.inspect(key)
    current = None

    if key:
        try:
            node = prompts.get(key)
            current = {"template": node.text, **node.metadata}
        except AttributeError:
            current = None
    else:
        current = {}
        if prompts._wrapped:
            for name, data in prompts._wrapped._store.items():
                current[name] = data

    report = {
        "header": {
            "env": prompts.current_env,
            "key_filter": str(key),
        },
        "current": current,
        "history": history,
    }

    if print_report:
        json.dump(report, sys.stdout, indent=2, default=str)
        print()

    if to_file:
        with open(to_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)

    return report
