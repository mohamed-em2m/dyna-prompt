from dynaprompt import DynaPrompt


def test_loading_python_module_with_imports_does_not_crash(tmp_path):
    """
    Ensures that importing a module in a .py settings file doesn't
    cause deepcopy errors when creating PromptNodes.
    """
    py_file = tmp_path / "vars.py"
    py_file.write_text("import math\nmy_var = 123", encoding="utf-8")

    prompt_file = tmp_path / "test.md"
    prompt_file.write_text("Hello {{ my_var }}", encoding="utf-8")

    dp = DynaPrompt(settings_files=[str(py_file), str(prompt_file)])

    # This should not raise TypeError: cannot pickle 'module' object
    node = dp.test
    assert node.text == "Hello 123"
