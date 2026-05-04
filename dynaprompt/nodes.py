"""PromptNode and RenderedPrompt — the core data nodes."""
from __future__ import annotations

import datetime
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Type

import jinja2
from pydantic import BaseModel

from .secrets import SecretStore
from .validator import ValidatorList
from .hooking import hookable


@dataclass
class SourceMetadata:
    """Tracks where a prompt was loaded from — for audit and rollback."""
    loader: str
    identifier: str
    env: str = "default"
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now().isoformat(timespec="seconds")
    )

    def _asdict(self) -> dict:
        return {
            "loader": self.loader,
            "identifier": self.identifier,
            "env": self.env,
            "timestamp": self.timestamp,
        }


@dataclass
class RenderedPrompt:
    """The final output of PromptNode.render() — fully interpolated text + config."""
    text: str
    config: Dict[str, Any]
    response_schema: Optional[Type[BaseModel]] = None
    source_history: List[Tuple] = field(default_factory=list)

    def __str__(self) -> str:
        return self.text

    def __repr__(self) -> str:
        preview = self.text[:80].replace("\n", " ")
        return f"RenderedPrompt(text={preview!r}..., model={self.config.get('model')})"

    @property
    def schema_dict(self) -> dict:
        """Returns the response_schema as a JSON Schema dictionary."""
        if not self.response_schema:
            return {}
        try:
            return self.response_schema.model_json_schema()
        except AttributeError:
            if hasattr(self.response_schema, "schema"):
                return self.response_schema.schema()
            return {}

    @property
    def schema_json(self) -> str:
        """Returns the response_schema as a formatted JSON Schema string."""
        import json
        return json.dumps(self.schema_dict, indent=2)


class PromptNode:
    """
    Represents a single parsed prompt. Supports fluent config overrides and
    Jinja2 rendering with secret injection.
    """

    def __init__(
        self,
        name: str,
        text: str,
        metadata: Dict[str, Any] = None,
        response_schema: Optional[Type[BaseModel]] = None,
        parent_template: Optional[str] = None,
        history: List[Tuple] = None,
        variables: Dict[str, Any] = None,
        validators: ValidatorList = None,
        hooks: Dict[str, list] = None,
        current_env: str = "default",
    ):
        self.name = name
        self.text = text
        self.metadata = metadata or {}
        self.response_schema = response_schema
        self._parent_template = parent_template
        self._history = history or []
        self.variables = variables or {}
        self._validators = validators or ValidatorList()
        self._hooks = hooks or {}
        self._current_env = current_env
        self._overrides: Dict[str, Any] = {}
        self.bound_kwargs: Dict[str, Any] = {}

    # ─── Fluent API ───────────────────────────────────────────────────────────

    def with_model(self, model: str) -> "PromptNode":
        self._overrides["model"] = model
        return self

    def with_temperature(self, temperature: float) -> "PromptNode":
        self._overrides["temperature"] = temperature
        return self

    def with_max_tokens(self, max_tokens: int) -> "PromptNode":
        self._overrides["max_tokens"] = max_tokens
        return self

    def with_schema(self, schema: Type[BaseModel]) -> "PromptNode":
        self.response_schema = schema
        return self

    # ─── Rendering ────────────────────────────────────────────────────────────

    @hookable
    def render(self, **kwargs) -> RenderedPrompt:
        """
        Render the prompt template with the provided variables.
        Runs validators → Jinja2 → after_render hooks.
        Maintains state of previously passed kwargs in `self.bound_kwargs`.
        """
        self.bound_kwargs.update(kwargs)
        
        # 1. Run validators (raises ValidationError on failure)
        self._validators.validate(self, self.bound_kwargs, current_env=self._current_env)

        # 2. Resolve inheritance: replace {{ super() }} before Jinja2
        template_str = self.text
        if self._parent_template and "{{ super() }}" in template_str:
            template_str = template_str.replace("{{ super() }}", self._parent_template)

        # 3. Build Jinja2 rendering context
        context = {
            "secrets": SecretStore(),
            "env": os.environ.get,
            "today": datetime.date.today().isoformat(),
            "current_env": self._current_env,
        }

        # Auto-inject global variables
        context.update(self.variables)

        # Auto-inject JSON schema if a response_schema was resolved
        if self.response_schema:
            context["response_schema"] = self.schema_json

        context.update(self.bound_kwargs)

        # 4. Render via Jinja2
        jinja_env = jinja2.Environment(undefined=jinja2.Undefined)
        try:
            rendered_text = jinja_env.from_string(template_str).render(**context)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to render prompt '{self.name}': {exc}"
            ) from exc

        # 5. Run after_render hooks (can mutate the RenderedPrompt object) via @hookable
        final_config = {**self.metadata, **self._overrides}
        return RenderedPrompt(
            text=rendered_text,
            config=final_config,
            response_schema=self.response_schema,
            source_history=self._history,
        )

    def rerender(self, **kwargs) -> RenderedPrompt:
        """
        Alias for render(). Useful for explicitly updating a subset of previously 
        provided variables while retaining the rest.
        """
        return self.render(**kwargs)

    def invoke(self, **kwargs):
        """
        Render and (in the future) call an LLM provider directly.
        Currently returns the RenderedPrompt; LLM execution is a future feature.
        """
        rendered = self.render(**kwargs)
        model = rendered.config.get("model", "unknown-model")
        # Placeholder — future: dispatch to openai/anthropic/gemini
        print(f"[DynaPrompt] Would invoke '{model}' with prompt: {rendered.text[:60]}...")
        return rendered

    def __repr__(self) -> str:
        preview = self.text[:60].replace("\n", " ")
        return (
            f"PromptNode(name={self.name!r}, "
            f"model={self.metadata.get('model')!r}, "
            f"template={preview!r}...)"
        )

    @property
    def schema_dict(self) -> dict:
        """Returns the response_schema as a JSON Schema dictionary."""
        if not self.response_schema:
            return {}
        try:
            return self.response_schema.model_json_schema()
        except AttributeError:
            if hasattr(self.response_schema, "schema"):
                return self.response_schema.schema()
            return {}

    @property
    def schema_json(self) -> str:
        """Returns the response_schema as a formatted JSON Schema string."""
        import json
        return json.dumps(self.schema_dict, indent=2)
