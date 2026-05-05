"""
Tests for validators, hooks, inspect/history, reload, and RenderedPrompt helpers.
"""

from __future__ import annotations

import pytest

from dynaprompt import DynaPrompt
from dynaprompt.nodes import RenderedPrompt
from dynaprompt.validator import PromptValidator

# ──────────────────────────────────────────────────────────────────────────────
# Validators
# ──────────────────────────────────────────────────────────────────────────────


class TestValidators:
    def test_validator_passes(self, md_prompt):
        class AlwaysPass(PromptValidator):
            def validate(self, node, kwargs, current_env="default"):
                pass  # No error

        dp = DynaPrompt(
            settings_files=[str(md_prompt)],
            validators=[AlwaysPass()],
        )
        rendered = dp.greet.render(name="x", app="y")
        assert rendered is not None

    def test_validator_raises(self, md_prompt):
        from dynaprompt.validator import ValidationError

        class AlwaysFail(PromptValidator):
            def validate(self, node, kwargs, current_env="default"):
                raise ValidationError("Always fails")

        dp = DynaPrompt(
            settings_files=[str(md_prompt)],
            validators=[AlwaysFail()],
        )
        with pytest.raises(ValidationError):
            dp.greet.render(name="x", app="y")


# ──────────────────────────────────────────────────────────────────────────────
# Hooks
# ──────────────────────────────────────────────────────────────────────────────


class TestHooks:
    def test_after_render_hook(self, md_prompt):
        called = []

        dp = DynaPrompt(settings_files=[str(md_prompt)])
        dp.inspect()

        def my_hook(node, rendered, **kwargs):
            called.append(rendered.text)

        dp.add_hook("after_render", "greet", my_hook)
        dp.greet.render(name="Emam", app="Test")
        assert len(called) == 1
        assert "Emam" in called[0]

    def test_after_render_hook_can_replace_result(self, md_prompt):
        dp = DynaPrompt(settings_files=[str(md_prompt)])
        dp.inspect()

        def redact_hook(node, rendered, **kwargs):
            return RenderedPrompt(
                text="[REDACTED]",
                config=rendered.config,
                response_schema=rendered.response_schema,
            )

        dp.add_hook("after_render", "greet", redact_hook)
        rendered = dp.greet.render(name="Secret", app="App")
        assert rendered.text == "[REDACTED]"


# ──────────────────────────────────────────────────────────────────────────────
# Inspect / history
# ──────────────────────────────────────────────────────────────────────────────


class TestInspect:
    def test_inspect_returns_dict(self, md_prompt):
        dp = DynaPrompt(settings_files=[str(md_prompt)])
        result = dp.inspect()
        assert isinstance(result, dict)

    def test_inspect_with_key(self, md_prompt):
        dp = DynaPrompt(settings_files=[str(md_prompt)])
        result = dp.inspect("greet")
        assert isinstance(result, list)

    def test_inspect_records_loader(self, md_prompt):
        dp = DynaPrompt(settings_files=[str(md_prompt)])
        history = dp.inspect("greet")
        assert len(history) >= 1
        assert "loader" in history[0]
        assert "MarkdownLoader" in history[0]["loader"]


# ──────────────────────────────────────────────────────────────────────────────
# Reload
# ──────────────────────────────────────────────────────────────────────────────


class TestReload:
    def test_reload_picks_up_changes(self, tmp_path):
        prompt = tmp_path / "dynamic.md"
        prompt.write_text("---\nmodel: gpt-3.5\n---\nVersion 1", encoding="utf-8")
        dp = DynaPrompt(settings_files=[str(prompt)])
        assert "Version 1" in dp.dynamic.render().text

        # Update the file
        prompt.write_text("---\nmodel: gpt-4\n---\nVersion 2", encoding="utf-8")
        dp.reload()
        assert "Version 2" in dp.dynamic.render().text
        assert dp.dynamic.render().config["model"] == "gpt-4"


# ──────────────────────────────────────────────────────────────────────────────
# RenderedPrompt helpers
# ──────────────────────────────────────────────────────────────────────────────


class TestRenderedPromptHelpers:
    def test_schema_dict_empty_without_schema(self, md_prompt):
        dp = DynaPrompt(settings_files=[str(md_prompt)])
        rendered = dp.greet.render(name="x", app="y")
        assert rendered.schema_dict == {}

    def test_schema_dict_with_pydantic(self, md_prompt):
        from pydantic import BaseModel

        class MyModel(BaseModel):
            result: str

        dp = DynaPrompt(settings_files=[str(md_prompt)])
        rendered = dp.greet.with_schema(MyModel).render(name="x", app="y")
        schema = rendered.schema_dict
        assert "properties" in schema

    def test_schema_json_is_string(self, md_prompt):
        from pydantic import BaseModel

        class MyModel(BaseModel):
            result: str

        dp = DynaPrompt(settings_files=[str(md_prompt)])
        rendered = dp.greet.with_schema(MyModel).render(name="x", app="y")
        assert isinstance(rendered.schema_json, str)
        assert "result" in rendered.schema_json

    def test_response_schema_auto_injected_into_context(self, tmp_path):
        """{{ response_schema }} in template is replaced with the JSON schema."""
        from pydantic import BaseModel

        class MyModel(BaseModel):
            answer: str

        prompt = tmp_path / "schema_prompt.md"
        prompt.write_text(
            "---\nmodel: gpt-4\n---\nRespond with: {{ response_schema }}",
            encoding="utf-8",
        )
        dp = DynaPrompt(settings_files=[str(prompt)])
        rendered = dp.schema_prompt.with_schema(MyModel).render()
        assert "answer" in rendered.text


# ──────────────────────────────────────────────────────────────────────────────
# Name sanitisation
# ──────────────────────────────────────────────────────────────────────────────


class TestNameSanitisation:
    def test_spaces_become_underscores(self, tmp_path):
        p = tmp_path / "My Prompt.md"
        p.write_text("---\nmodel: gpt-4\n---\nHi", encoding="utf-8")
        dp = DynaPrompt(settings_files=[str(tmp_path)])
        dp.inspect()
        assert "my_prompt" in dp._wrapped._store

    def test_hyphens_become_underscores(self, tmp_path):
        p = tmp_path / "call-analysis.md"
        p.write_text("---\nmodel: gpt-4\n---\nAnalyze", encoding="utf-8")
        dp = DynaPrompt(settings_files=[str(tmp_path)])
        dp.inspect()
        assert "call_analysis" in dp._wrapped._store

    def test_digit_prefix_is_escaped(self, tmp_path):
        p = tmp_path / "01_intro.md"
        p.write_text("---\nmodel: gpt-4\n---\nIntro", encoding="utf-8")
        dp = DynaPrompt(settings_files=[str(tmp_path)])
        dp.inspect()
        assert "p_01_intro" in dp._wrapped._store
