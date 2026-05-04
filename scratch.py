from dynaprompt import DynaPrompt

def main():
    prompts = DynaPrompt(
        settings_files=["examples"],
        auto_render=True,
    )
    print("----- Raw Text -----")
    print(prompts.customer_service.text)

if __name__ == "__main__":
    main()
