#!/usr/bin/env python3
"""Basic usage example for unversion."""

from pathlib import Path

from unversion import init_store, get_prompt, list_prompts, has_prompt


def main():
    # Initialize with path to prompts file
    prompts_file = Path(__file__).parent / "prompts.json"

    # Create example prompts file if it doesn't exist
    if not prompts_file.exists():
        import json

        example_prompts = {
            "version": "1.0",
            "prompts": {
                "greeting": {
                    "text": "Hello {name}! Welcome to {app_name}.",
                    "variables": ["name", "app_name"],
                    "source": "example",
                    "notes": "A simple greeting prompt",
                },
                "analysis.sentiment": {
                    "text": "Analyze the sentiment of the following text:\n\n{text}\n\nRespond with: positive, negative, or neutral.",
                    "variables": ["text"],
                    "source": "example",
                    "notes": "Basic sentiment analysis prompt",
                },
                "chat.system": {
                    "text": "You are a helpful assistant. Be concise and clear in your responses.",
                    "variables": [],
                    "source": "example",
                    "notes": "Default system prompt for chat",
                },
            },
        }
        with open(prompts_file, "w") as f:
            json.dump(example_prompts, f, indent=2)
        print(f"Created example prompts file: {prompts_file}")

    # Initialize the store
    init_store(str(prompts_file))

    # List all prompts
    print("\n=== Available Prompts ===")
    for key in list_prompts():
        print(f"  - {key}")

    # Check if a prompt exists
    print(f"\n'greeting' exists: {has_prompt('greeting')}")
    print(f"'nonexistent' exists: {has_prompt('nonexistent')}")

    # Get a prompt without formatting
    print("\n=== Raw Prompt ===")
    raw = get_prompt("greeting")
    print(f"greeting: {raw}")

    # Get a prompt with formatting
    print("\n=== Formatted Prompt ===")
    formatted = get_prompt("greeting", name="Alice", app_name="MyApp")
    print(f"greeting: {formatted}")

    # Get a more complex prompt
    print("\n=== Sentiment Analysis Prompt ===")
    sentiment = get_prompt("analysis.sentiment", text="I love this product!")
    print(sentiment)


if __name__ == "__main__":
    main()
