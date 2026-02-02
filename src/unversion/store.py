"""Prompt store - loads prompts from a JSON file.

The JSON file is the single source of truth for all prompts.
"""

import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Prompt:
    """A prompt record."""

    key: str
    text: str
    variables: List[str]
    source: str
    notes: str

    def format(self, **kwargs) -> str:
        """Format the prompt with variables."""
        if not kwargs:
            return self.text
        try:
            return self.text.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing format key {e} for prompt '{self.key}'")
            # Partial format - only substitute what we have
            result = self.text
            for key, value in kwargs.items():
                result = result.replace("{" + key + "}", str(value))
            return result


class PromptStore:
    """Prompt store that loads from a JSON file.

    The JSON file should have this structure:
    {
        "version": "1.0",
        "prompts": {
            "key": {
                "text": "prompt text with {variables}",
                "variables": ["variables"],
                "source": "origin",
                "notes": "documentation"
            }
        }
    }
    """

    def __init__(self, path: Optional[Path] = None):
        """Initialize the store.

        Args:
            path: Path to the prompts JSON file. If None, store is empty
                  until init() is called.
        """
        self._path: Optional[Path] = None
        self._prompts: Dict[str, Prompt] = {}
        self._version: str = "1.0"

        if path:
            self.init(path)

    def init(self, path: Path) -> None:
        """Initialize or reinitialize the store with a prompts file.

        Args:
            path: Path to the prompts JSON file.
        """
        self._path = Path(path)
        self._load()

    def _load(self) -> None:
        """Load prompts from the JSON file."""
        if not self._path:
            return

        if not self._path.exists():
            logger.warning(f"Prompts file not found: {self._path}")
            return

        try:
            with open(self._path) as f:
                data = json.load(f)

            self._version = data.get("version", "1.0")
            prompts = data.get("prompts", {})

            self._prompts.clear()
            for key, prompt_data in prompts.items():
                self._prompts[key] = Prompt(
                    key=key,
                    text=prompt_data.get("text", ""),
                    variables=prompt_data.get("variables", []),
                    source=prompt_data.get("source", "bundled"),
                    notes=prompt_data.get("notes", ""),
                )

            logger.info(f"Loaded {len(self._prompts)} prompts from {self._path}")

        except Exception as e:
            logger.error(f"Failed to load prompts: {e}")

    def get(self, key: str) -> Optional[Prompt]:
        """Get a prompt by key."""
        return self._prompts.get(key)

    def list_keys(self) -> List[str]:
        """List all prompt keys."""
        return sorted(self._prompts.keys())

    def has(self, key: str) -> bool:
        """Check if a prompt exists."""
        return key in self._prompts

    def reload(self) -> None:
        """Reload prompts from the file."""
        self._load()

    @property
    def path(self) -> Optional[Path]:
        """Get the path to the prompts file."""
        return self._path

    @property
    def version(self) -> str:
        """Get the prompts file version."""
        return self._version

    def __len__(self) -> int:
        """Return the number of prompts."""
        return len(self._prompts)

    def __contains__(self, key: str) -> bool:
        """Check if a prompt exists."""
        return key in self._prompts

    def __iter__(self):
        """Iterate over prompt keys."""
        return iter(self._prompts)

    def items(self):
        """Iterate over (key, prompt) pairs."""
        return self._prompts.items()


# Global store instance
_store: Optional[PromptStore] = None


def init_store(path: str) -> PromptStore:
    """Initialize the global prompt store.

    Args:
        path: Path to the prompts JSON file.

    Returns:
        The initialized store.

    Example:
        from unversion import init_store

        init_store("prompts/bundled.json")
    """
    global _store
    _store = PromptStore(Path(path))
    return _store


def get_store() -> PromptStore:
    """Get the global prompt store.

    Returns:
        The global store. Creates an empty store if not initialized.
    """
    global _store
    if _store is None:
        _store = PromptStore()
    return _store


def get_prompt(key: str, **format_kwargs) -> str:
    """Get a prompt by key and optionally format it.

    Args:
        key: The prompt key (e.g., "greeting" or "analysis.sentiment")
        **format_kwargs: Variables to format into the prompt

    Returns:
        The formatted prompt text, or empty string if not found

    Example:
        prompt = get_prompt("greeting", name="Alice", app_name="MyApp")
    """
    store = get_store()
    prompt = store.get(key)

    if not prompt:
        logger.warning(f"Prompt '{key}' not found")
        return ""

    return prompt.format(**format_kwargs)


def list_prompts() -> List[str]:
    """List all available prompt keys.

    Returns:
        Sorted list of prompt keys.
    """
    return get_store().list_keys()


def reload_prompts() -> None:
    """Reload all prompts from the file."""
    get_store().reload()


def has_prompt(key: str) -> bool:
    """Check if a prompt exists.

    Args:
        key: The prompt key.

    Returns:
        True if the prompt exists.
    """
    return get_store().has(key)
