"""
Tests for automatic schema loading from .py and .json/.yaml files.
"""

from __future__ import annotations

from pydantic import BaseModel

from dynaprompt import DynaPrompt


class TestPythonSchemaLoading:
    def test_loads_classes_as_schemas(self, py_schemas):
        dp = DynaPrompt(settings_files=[str(py_schemas)])
        dp.inspect()
        assert "UserSchema" in dp.schemas
        assert "ResponseSchema" in dp.schemas

    def test_schema_is_correct_class(self, py_schemas):
        dp = DynaPrompt(settings_files=[str(py_schemas)])
        dp.inspect()
        assert issubclass(dp.schemas["UserSchema"], BaseModel)

    def test_py_also_registers_plain_variables(self, py_schemas):
        dp = DynaPrompt(settings_files=[str(py_schemas)])
        dp.inspect()
        assert "GREETING" in dp._wrapped._variables
        assert dp._wrapped._variables["GREETING"] == "hello"
        assert dp._wrapped._variables["MAX_TOKENS"] == 512

    def test_py_classes_in_variables_too(self, py_schemas):
        dp = DynaPrompt(settings_files=[str(py_schemas)])
        dp.inspect()
        assert "UserSchema" in dp._wrapped._variables

    def test_schema_resolves_in_md_prompt(self, tmp_path, py_schemas):
        prompt = tmp_path / "check.md"
        prompt.write_text(
            "---\nmodel: gpt-4\nresponse_schema: UserSchema\n---\nHello {{ name }}",
            encoding="utf-8",
        )
        dp = DynaPrompt(settings_files=[str(py_schemas), str(prompt)])
        rendered = dp.check.render(name="Ali")
        assert rendered.response_schema is not None
        assert rendered.response_schema.__name__ == "UserSchema"


class TestJsonSchemaLoading:
    def test_loads_json_as_schema(self, json_schema_file):
        dp = DynaPrompt(settings_files=[str(json_schema_file)])
        dp.inspect()
        assert "api_schema" in dp.schemas
        assert dp.schemas["api_schema"] == {"status": "string", "code": "integer"}

    def test_json_schema_accessible_as_attribute(self, json_schema_file):
        dp = DynaPrompt(settings_files=[str(json_schema_file)])
        dp.inspect()
        assert dp.api_schema == {"status": "string", "code": "integer"}

    def test_json_registers_top_level_keys_as_variables(self, json_schema_file):
        dp = DynaPrompt(settings_files=[str(json_schema_file)])
        dp.inspect()
        # Container key
        assert "api_schema" in dp._wrapped._variables
        # Individual keys
        assert "status" in dp._wrapped._variables
        assert "code" in dp._wrapped._variables

    def test_json_schema_resolves_in_prompt(self, tmp_path, json_schema_file):
        prompt = tmp_path / "resp.md"
        prompt.write_text(
            "---\nmodel: gpt-4\nresponse_schema: api_schema\n---\nCheck {{ item }}",
            encoding="utf-8",
        )
        dp = DynaPrompt(settings_files=[str(json_schema_file), str(prompt)])
        rendered = dp.resp.render(item="data")
        assert rendered.response_schema == {"status": "string", "code": "integer"}


class TestYamlSchemaLoading:
    def test_loads_yaml_as_schema(self, yaml_vars, tmp_path):
        # Create a yaml schema file in tmp_path
        schema = tmp_path / "my_schema.yaml"
        schema.write_text("field1: string\nfield2: integer\n", encoding="utf-8")
        dp = DynaPrompt(settings_files=[str(schema)])
        dp.inspect()
        assert "my_schema" in dp.schemas

    def test_yaml_registers_variables(self, tmp_path):
        schema = tmp_path / "ctx.yaml"
        schema.write_text("lang: English\nauthor: Emam\n", encoding="utf-8")
        dp = DynaPrompt(settings_files=[str(schema)])
        dp.inspect()
        assert dp._wrapped._variables.get("lang") == "English"
        assert dp._wrapped._variables.get("author") == "Emam"
