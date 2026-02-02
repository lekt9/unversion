"""Tests for the observer."""

import tempfile
from pathlib import Path

import pytest

from unversion.observer import (
    UsageStore,
    UsageLog,
    log_usage,
    get_stats,
    get_recent_logs,
    get_top_prompts,
)


@pytest.fixture
def temp_db():
    """Create a temporary database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        return f.name


def test_usage_store_init(temp_db):
    """Test store initialization."""
    store = UsageStore(temp_db)
    assert store.db_path == temp_db


def test_usage_store_log(temp_db):
    """Test logging usage."""
    store = UsageStore(temp_db)

    entry = UsageLog(
        id="test-id",
        timestamp="2024-01-01T00:00:00",
        prompt_key="greeting",
        prompt_hash="abc123",
        stage="chat",
        model="gpt-4",
        success=True,
        latency_ms=100,
    )

    store.log(entry)

    # Verify it was saved
    logs = store.get_recent(limit=1)
    assert len(logs) == 1
    assert logs[0]["prompt_key"] == "greeting"


def test_usage_store_stats(temp_db):
    """Test getting stats."""
    store = UsageStore(temp_db)

    # Log some usage
    for i in range(5):
        entry = UsageLog(
            id=f"test-{i}",
            timestamp=f"2024-01-01T00:00:0{i}",
            prompt_key="greeting",
            prompt_hash="abc123",
            stage="chat",
            success=i < 4,  # 4 successes, 1 failure
            latency_ms=100 + i * 10,
        )
        store.log(entry)

    stats = store.get_stats("greeting")
    assert stats["total_usage"] == 5
    assert stats["success_rate"] == 80.0


def test_usage_store_top_prompts(temp_db):
    """Test getting top prompts."""
    store = UsageStore(temp_db)

    # Log usage for multiple prompts
    for prompt_key in ["a", "a", "a", "b", "b", "c"]:
        entry = UsageLog(
            id=f"test-{prompt_key}-{id(prompt_key)}",
            timestamp="2024-01-01T00:00:00",
            prompt_key=prompt_key,
            prompt_hash="hash",
            stage="test",
            success=True,
        )
        store.log(entry)

    top = store.get_top_prompts(limit=10)
    assert len(top) == 3
    assert top[0]["prompt_key"] == "a"
    assert top[0]["usage_count"] == 3


def test_log_usage_function(temp_db):
    """Test the log_usage convenience function."""
    # This would need mocking the global store
    # For now, just verify the function exists and is callable
    assert callable(log_usage)
    assert callable(get_stats)
    assert callable(get_recent_logs)
    assert callable(get_top_prompts)
