"""
Shared pytest fixtures for the DynaPrompt test suite.

All temporary files are created via `tmp_path` (pytest's built-in fixture)
so they are cleaned up automatically after each test.
"""
from __future__ import annotations

import json
import pathlib
import textwrap

import pytest


# ──────────────────────────────────────────────────────────────────────────────
# File fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture()
def md_prompt(tmp_path: pathlib.Path) -> pathlib.Path:
    """A simple Markdown prompt with YAML frontmatter."""
    p = tmp_path / "greet.md"
    p.write_text(
        textwrap.dedent("""\
            ---
            model: gpt-4o
            temperature: 0.5
            ---
            Hello, {{ name }}! You are using {{ app }}.
        """),
        encoding="utf-8",
    )
    return p


@pytest.fixture()
def md_prompt_with_schema(tmp_path: pathlib.Path) -> pathlib.Path:
    """Markdown prompt that references a schema by string name."""
    p = tmp_path / "analyze.md"
    p.write_text(
        textwrap.dedent("""\
            ---
            model: gpt-4o
            response_schema: MySchema
            ---
            Analyze: {{ text }}
        """),
        encoding="utf-8",
    )
    return p


@pytest.fixture()
def toml_prompts(tmp_path: pathlib.Path) -> pathlib.Path:
    """A TOML file with default + production environment overrides."""
    p = tmp_path / "prompts.toml"
    p.write_text(
        textwrap.dedent("""\
            [default.support]
            model = "gpt-3.5"
            template = "Help {{ user }} with: {{ issue }}"

            [production.support]
            model = "gpt-4o"
        """),
        encoding="utf-8",
    )
    return p


@pytest.fixture()
def json_vars(tmp_path: pathlib.Path) -> pathlib.Path:
    """A flat JSON file to be used as a variables source."""
    p = tmp_path / "vars.json"
    p.write_text(json.dumps({"app": "DynaPrompt", "version": "1.0"}), encoding="utf-8")
    return p


@pytest.fixture()
def yaml_vars(tmp_path: pathlib.Path) -> pathlib.Path:
    """A flat YAML file to be used as a variables source."""
    p = tmp_path / "vars.yaml"
    p.write_text("lang: English\nauthor: Emam\n", encoding="utf-8")
    return p


@pytest.fixture()
def toml_vars(tmp_path: pathlib.Path) -> pathlib.Path:
    """A flat TOML file to be used as a variables source."""
    p = tmp_path / "vars.toml"
    p.write_text('env_name = "dev"\ndebug = true\n', encoding="utf-8")
    return p


@pytest.fixture()
def py_schemas(tmp_path: pathlib.Path) -> pathlib.Path:
    """A Python file defining Pydantic models (schemas) and plain variables."""
    p = tmp_path / "schemas.py"
    p.write_text(
        textwrap.dedent("""\
            from pydantic import BaseModel

            GREETING = "hello"
            MAX_TOKENS = 512

            class UserSchema(BaseModel):
                name: str
                age: int

            class ResponseSchema(BaseModel):
                answer: str
        """),
        encoding="utf-8",
    )
    return p


@pytest.fixture()
def json_schema_file(tmp_path: pathlib.Path) -> pathlib.Path:
    """A JSON file to be used as a raw schema (not env-layered)."""
    p = tmp_path / "api_schema.json"
    p.write_text(
        json.dumps({"status": "string", "code": "integer"}),
        encoding="utf-8",
    )
    return p


@pytest.fixture()
def prompts_dir(tmp_path: pathlib.Path, md_prompt: pathlib.Path) -> pathlib.Path:
    """A directory containing mixed prompt and schema files."""
    # md_prompt is already in tmp_path/greet.md
    return tmp_path
