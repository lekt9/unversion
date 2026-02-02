"""Tests for the prompt store."""

import json
import tempfile
from pathlib import Path

import pytest

from unversion import (
    PromptStore,
    Prompt,
    init_store,
    get_store,
    get_prompt,
    list_prompts,
    has_prompt,
)


@pytest.fixture
def sample_prompts():
    """Create a sample prompts file."""
    data = {
        "version": "1.0",
        "prompts": {
            "greeting": {
                "text": "Hello {name}!",
                "variables": ["name"],
                "source": "test",
                "notes": "A greeting prompt",
            },
            "analysis.sentiment": {
                "text": "Analyze: {text}",
                "variables": ["text"],
                "source": "test",
                "notes": "Sentiment analysis",
            },
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        return Path(f.name)


def test_store_init(sample_prompts):
    """Test store initialization."""
    store = PromptStore(sample_prompts)
    assert len(store) == 2
    assert "greeting" in store
    assert "analysis.sentiment" in store


def test_store_get(sample_prompts):
    """Test getting a prompt."""
    store = PromptStore(sample_prompts)
    prompt = store.get("greeting")
    assert prompt is not None
    assert prompt.key == "greeting"
    assert prompt.text == "Hello {name}!"
    assert prompt.variables == ["name"]


def test_store_list_keys(sample_prompts):
    """Test listing keys."""
    store = PromptStore(sample_prompts)
    keys = store.list_keys()
    assert keys == ["analysis.sentiment", "greeting"]


def test_store_has(sample_prompts):
    """Test checking if prompt exists."""
    store = PromptStore(sample_prompts)
    assert store.has("greeting")
    assert not store.has("nonexistent")


def test_prompt_format():
    """Test prompt formatting."""
    prompt = Prompt(
        key="test",
        text="Hello {name}, welcome to {app}!",
        variables=["name", "app"],
        source="test",
        notes="",
    )
    result = prompt.format(name="Alice", app="MyApp")
    assert result == "Hello Alice, welcome to MyApp!"


def test_prompt_format_partial():
    """Test partial prompt formatting."""
    prompt = Prompt(
        key="test",
        text="Hello {name}, welcome to {app}!",
        variables=["name", "app"],
        source="test",
        notes="",
    )
    result = prompt.format(name="Alice")
    assert result == "Hello Alice, welcome to {app}!"


def test_global_store(sample_prompts):
    """Test global store functions."""
    init_store(str(sample_prompts))

    assert has_prompt("greeting")
    assert not has_prompt("nonexistent")

    keys = list_prompts()
    assert "greeting" in keys

    prompt = get_prompt("greeting", name="Bob")
    assert prompt == "Hello Bob!"


def test_get_prompt_not_found(sample_prompts):
    """Test getting nonexistent prompt."""
    init_store(str(sample_prompts))
    result = get_prompt("nonexistent")
    assert result == ""
