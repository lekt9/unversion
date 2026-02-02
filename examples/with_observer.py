#!/usr/bin/env python3
"""Example using unversion with the observer for usage tracking."""

import time
from pathlib import Path

from unversion import init_store, get_prompt, log_usage, get_stats, get_top_prompts


def simulate_llm_call(prompt: str) -> str:
    """Simulate an LLM API call."""
    time.sleep(0.1)  # Simulate latency
    return f"Response to: {prompt[:50]}..."


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
                    "text": "Hello {name}!",
                    "variables": ["name"],
                    "source": "example",
                    "notes": "Greeting prompt",
                },
                "analysis.sentiment": {
                    "text": "Analyze sentiment: {text}",
                    "variables": ["text"],
                    "source": "example",
                    "notes": "Sentiment analysis",
                },
            },
        }
        with open(prompts_file, "w") as f:
            json.dump(example_prompts, f, indent=2)

    init_store(str(prompts_file))

    # Simulate some API calls with logging
    print("=== Simulating API Calls ===\n")

    for name in ["Alice", "Bob", "Charlie"]:
        prompt = get_prompt("greeting", name=name)

        start = time.time()
        result = simulate_llm_call(prompt)
        latency_ms = (time.time() - start) * 1000

        # Log the usage
        log_usage(
            "greeting",
            stage="chat",
            model="gpt-4",
            variables_used={"name": name},
            latency_ms=latency_ms,
            success=True,
        )

        print(f"Called greeting with name={name}, latency={latency_ms:.0f}ms")

    # Log some analysis calls
    for text in ["Great product!", "Terrible service", "It's okay"]:
        prompt = get_prompt("analysis.sentiment", text=text)

        start = time.time()
        result = simulate_llm_call(prompt)
        latency_ms = (time.time() - start) * 1000

        log_usage(
            "analysis.sentiment",
            stage="analysis",
            model="gpt-4",
            variables_used={"text": text},
            latency_ms=latency_ms,
            success=True,
        )

        print(f"Called analysis.sentiment, latency={latency_ms:.0f}ms")

    # Show statistics
    print("\n=== Usage Statistics ===\n")

    stats = get_stats("greeting")
    print(f"greeting:")
    print(f"  Total usage: {stats['total_usage']}")
    print(f"  Success rate: {stats['success_rate']:.1f}%")
    print(f"  Avg latency: {stats['avg_latency_ms']:.0f}ms")

    print("\n=== Top Prompts ===\n")
    top = get_top_prompts(limit=5)
    for p in top:
        print(f"  {p['prompt_key']}: {p['usage_count']} uses")


if __name__ == "__main__":
    main()
