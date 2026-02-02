"""unversion - Simple prompt versioning for AI applications.

Store prompts in JSON, track usage, no hardcoding.

Usage:
    from unversion import init_store, get_prompt, list_prompts

    # Initialize with path to your prompts file
    init_store("prompts/bundled.json")

    # Get a prompt
    prompt = get_prompt("greeting", name="Alice")

    # List all prompts
    keys = list_prompts()

Observer Integration:
    from unversion import log_usage, get_stats

    # Log when a prompt is used
    log_usage("greeting", stage="chat", model="gpt-4")

    # Get usage statistics
    stats = get_stats("greeting")
"""

from .store import (
    PromptStore,
    Prompt,
    init_store,
    get_store,
    get_prompt,
    list_prompts,
    reload_prompts,
    has_prompt,
)

from .observer import (
    log_usage,
    get_stats,
    get_recent_logs,
    get_top_prompts,
    UsageLog,
    UsageStore,
)

__all__ = [
    # Store
    "PromptStore",
    "Prompt",
    "init_store",
    "get_store",
    "get_prompt",
    "list_prompts",
    "reload_prompts",
    "has_prompt",
    # Observer
    "log_usage",
    "get_stats",
    "get_recent_logs",
    "get_top_prompts",
    "UsageLog",
    "UsageStore",
]

__version__ = "0.1.0"
