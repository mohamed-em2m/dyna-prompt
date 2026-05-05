from dynaprompt import DynaPrompt

# Initialize DynaPrompt pointing to the examples folder
# It will auto-load .toml, .md, .py (schemas), and .json (schemas)
prompts = DynaPrompt(settings_files=["examples/"])


def run_example():
    print("--- 1. Auto-loaded Schemas ---")
    print(f"Available schemas: {list(prompts.schemas.keys())}")
    # AnalysisSchema was loaded from examples/schemas.py
    # config_schema was loaded from examples/config_schema.json
    print()

    print("--- 2. Rendering Markdown Prompt (analyzer.md) ---")
    # Accessing analyzer (from analyzer.md)
    # Note: it automatically picked up AnalysisSchema as response_schema
    rendered_md = prompts.analyzer.render(
        user_name="Emam",
        text_to_analyze="I love using DynaPrompt, it makes things so easy!",
    )
    print(f"Model: {rendered_md.config.get('model')}")
    schema_name = (
        rendered_md.response_schema.__name__ if rendered_md.response_schema else "None"
    )
    print(f"Schema attached: {schema_name}")
    print("Template snippet:")
    print(rendered_md.text[:100] + "...")
    print()

    print("--- 3. Rendering TOML Prompt (sentiment_analysis) ---")
    rendered_toml = prompts.sentiment_analysis.render(text="This is great!")
    print(f"Env: {prompts.current_env}")
    print(f"Model: {rendered_toml.config.get('model')}")
    schema_name = (
        rendered_toml.response_schema.__name__
        if rendered_toml.response_schema
        else "None"
    )
    print(f"Schema: {schema_name}")
    print()

    print("--- 4. Switching Environments ---")
    with prompts.using_env("production"):
        rendered_prod = prompts.sentiment_analysis.render(text="Production run")
        print(f"Production Model: {rendered_prod.config.get('model')}")


if __name__ == "__main__":
    # Ensure we are in the project root to find the 'examples' folder
    run_example()
