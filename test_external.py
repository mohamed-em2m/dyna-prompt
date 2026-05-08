import pathlib

from dynaprompt import DynaPrompt

# 1. Test template as a path
pathlib.Path("test_external_template.md").write_text("Hello {{ external_var }}")

# 2. Test variables as a path
pathlib.Path("test_vars.json").write_text('{"external_var": "world from json"}')

# 3. Create a toml defining a prompt that uses both
pathlib.Path("test_config.toml").write_text("""
[default.my_external_prompt]
template = "test_external_template.md"
variables = "test_vars.json"

[default.my_dict_prompt]
template = "test_external_template.md"
[default.my_dict_prompt.variables]
external_var = "world from dict"
""")

dp = DynaPrompt(settings_files=["test_config.toml"])

# Test 1: variables loaded from file path
r1 = dp.my_external_prompt.render()
print("Prompt 1:", r1.text)

# Test 2: variables loaded from inline dict
r2 = dp.my_dict_prompt.render()
print("Prompt 2:", r2.text)
