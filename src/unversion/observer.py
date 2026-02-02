"""Observer - Track prompt usage for analytics and debugging.

Provides lightweight logging of prompt usage with optional Langfuse integration.

Usage:
    from unversion import log_usage, get_stats

    # Log when a prompt is used
    log_usage("greeting", stage="chat", model="gpt-4")

    # Get usage statistics
    stats = get_stats("greeting")
"""

import json
import sqlite3
import os
import logging
import hashlib
import uuid
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Default DB path
DEFAULT_DB_PATH = os.path.expanduser("~/.unversion/usage.db")

# Langfuse configuration
LANGFUSE_PUBLIC_KEY = os.environ.get("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.environ.get("LANGFUSE_SECRET_KEY")
LANGFUSE_ENABLED = bool(LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY)

_langfuse_client = None


def _get_langfuse_client():
    """Lazy-load Langfuse client for tracing."""
    global _langfuse_client
    if _langfuse_client is None and LANGFUSE_ENABLED:
        try:
            from langfuse import get_client

            _langfuse_client = get_client()
            logger.info("Langfuse tracing enabled")
        except ImportError:
            logger.debug("langfuse not installed, tracing disabled")
        except Exception as e:
            logger.warning(f"Failed to initialize Langfuse: {e}")
    return _langfuse_client


@dataclass
class UsageLog:
    """Log entry for prompt usage."""

    id: str
    timestamp: str
    prompt_key: str
    prompt_hash: str
    stage: str
    model: Optional[str] = None
    session_id: Optional[str] = None
    variables_used: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    latency_ms: float = 0
    notes: Optional[str] = None


class UsageStore:
    """SQLite store for prompt usage logs."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS usage (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    prompt_key TEXT NOT NULL,
                    prompt_hash TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    model TEXT,
                    session_id TEXT,
                    variables_used TEXT,
                    success INTEGER DEFAULT 1,
                    latency_ms REAL DEFAULT 0,
                    notes TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_usage_key ON usage(prompt_key);
                CREATE INDEX IF NOT EXISTS idx_usage_stage ON usage(stage);
                CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage(timestamp);
                CREATE INDEX IF NOT EXISTS idx_usage_session ON usage(session_id);
            """
            )

    def log(self, entry: UsageLog) -> None:
        """Save a usage log entry."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO usage (
                    id, timestamp, prompt_key, prompt_hash, stage,
                    model, session_id, variables_used, success, latency_ms, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    entry.id,
                    entry.timestamp,
                    entry.prompt_key,
                    entry.prompt_hash,
                    entry.stage,
                    entry.model,
                    entry.session_id,
                    json.dumps(entry.variables_used),
                    1 if entry.success else 0,
                    entry.latency_ms,
                    entry.notes,
                ),
            )

    def get_stats(self, prompt_key: str) -> Dict[str, Any]:
        """Get usage statistics for a prompt."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            total = conn.execute(
                "SELECT COUNT(*) as count FROM usage WHERE prompt_key = ?",
                (prompt_key,),
            ).fetchone()["count"]

            success_count = conn.execute(
                "SELECT COUNT(*) as count FROM usage WHERE prompt_key = ? AND success = 1",
                (prompt_key,),
            ).fetchone()["count"]

            avg_latency = (
                conn.execute(
                    "SELECT AVG(latency_ms) as avg FROM usage WHERE prompt_key = ? AND latency_ms > 0",
                    (prompt_key,),
                ).fetchone()["avg"]
                or 0
            )

            stages = conn.execute(
                """
                SELECT stage, COUNT(*) as count
                FROM usage
                WHERE prompt_key = ?
                GROUP BY stage
                ORDER BY count DESC
            """,
                (prompt_key,),
            ).fetchall()

            recent = conn.execute(
                """
                SELECT timestamp, stage, model, success
                FROM usage
                WHERE prompt_key = ?
                ORDER BY timestamp DESC
                LIMIT 10
            """,
                (prompt_key,),
            ).fetchall()

            return {
                "prompt_key": prompt_key,
                "total_usage": total,
                "success_rate": (success_count / total * 100) if total > 0 else 0,
                "avg_latency_ms": avg_latency,
                "by_stage": {row["stage"]: row["count"] for row in stages},
                "recent": [dict(row) for row in recent],
            }

    def get_recent(
        self,
        limit: int = 50,
        prompt_key: Optional[str] = None,
        stage: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get recent usage logs with optional filters."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM usage WHERE 1=1"
            params = []

            if prompt_key:
                query += " AND prompt_key = ?"
                params.append(prompt_key)
            if stage:
                query += " AND stage = ?"
                params.append(stage)
            if session_id:
                query += " AND session_id = ?"
                params.append(session_id)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()

            results = []
            for row in rows:
                entry = dict(row)
                entry["variables_used"] = json.loads(entry["variables_used"] or "{}")
                results.append(entry)

            return results

    def get_top_prompts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get most frequently used prompts."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            rows = conn.execute(
                """
                SELECT
                    prompt_key,
                    COUNT(*) as usage_count,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                    AVG(latency_ms) as avg_latency,
                    MAX(timestamp) as last_used
                FROM usage
                GROUP BY prompt_key
                ORDER BY usage_count DESC
                LIMIT ?
            """,
                (limit,),
            ).fetchall()

            return [dict(row) for row in rows]


# Global store instance
_usage_store: Optional[UsageStore] = None


def _get_store() -> UsageStore:
    """Get or create the global usage store."""
    global _usage_store
    if _usage_store is None:
        _usage_store = UsageStore()
    return _usage_store


def _hash_prompt(text: str) -> str:
    """Create a short hash of prompt text."""
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def _send_to_langfuse(entry: UsageLog) -> None:
    """Send usage log to Langfuse asynchronously."""
    if not LANGFUSE_ENABLED:
        return

    client = _get_langfuse_client()
    if not client:
        return

    def send_async():
        try:
            span = client.start_observation(
                name=f"prompt:{entry.prompt_key}",
                as_type="span",
            )
            span.update(
                input={"prompt_key": entry.prompt_key, "variables": entry.variables_used},
                output={"success": entry.success},
                metadata={
                    "stage": entry.stage,
                    "model": entry.model,
                    "session_id": entry.session_id,
                    "prompt_hash": entry.prompt_hash,
                },
                level="ERROR" if not entry.success else "DEFAULT",
            )
            span.end()
            logger.debug(f"[Langfuse] Logged usage of {entry.prompt_key}")
        except Exception as e:
            logger.warning(f"[Langfuse] Failed to send log: {e}")

    thread = threading.Thread(target=send_async, daemon=True)
    thread.start()


def log_usage(
    prompt_key: str,
    stage: str,
    prompt_text: Optional[str] = None,
    model: Optional[str] = None,
    session_id: Optional[str] = None,
    variables_used: Optional[Dict[str, Any]] = None,
    success: bool = True,
    latency_ms: float = 0,
    notes: Optional[str] = None,
) -> str:
    """Log prompt usage.

    Args:
        prompt_key: The prompt key (e.g., "greeting")
        stage: Pipeline stage (e.g., "chat", "analysis")
        prompt_text: Optional full prompt text for hashing
        model: Model used (e.g., "gpt-4", "claude-3")
        session_id: Session ID for grouping related calls
        variables_used: Dict of variables passed to prompt
        success: Whether the call succeeded
        latency_ms: Call latency in milliseconds
        notes: Optional notes

    Returns:
        Log entry ID

    Example:
        log_usage("greeting", stage="chat", model="gpt-4", latency_ms=150)
    """
    log_id = str(uuid.uuid4())

    # Get prompt text for hashing if not provided
    if prompt_text is None:
        from .store import get_prompt

        prompt_text = get_prompt(prompt_key)

    prompt_hash = _hash_prompt(prompt_text) if prompt_text else "unknown"

    entry = UsageLog(
        id=log_id,
        timestamp=datetime.utcnow().isoformat(),
        prompt_key=prompt_key,
        prompt_hash=prompt_hash,
        stage=stage,
        model=model,
        session_id=session_id,
        variables_used=variables_used or {},
        success=success,
        latency_ms=latency_ms,
        notes=notes,
    )

    try:
        _get_store().log(entry)
        _send_to_langfuse(entry)
        logger.debug(f"[Observer] Logged usage of {prompt_key} in {stage}")
    except Exception as e:
        logger.warning(f"[Observer] Failed to log usage: {e}")

    return log_id


def get_stats(prompt_key: str) -> Dict[str, Any]:
    """Get usage statistics for a prompt.

    Args:
        prompt_key: The prompt key.

    Returns:
        Dict with total_usage, success_rate, avg_latency_ms, by_stage, recent.
    """
    return _get_store().get_stats(prompt_key)


def get_recent_logs(
    limit: int = 50,
    prompt_key: Optional[str] = None,
    stage: Optional[str] = None,
    session_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get recent usage logs.

    Args:
        limit: Maximum number of logs to return.
        prompt_key: Filter by prompt key.
        stage: Filter by stage.
        session_id: Filter by session ID.

    Returns:
        List of usage log dicts.
    """
    return _get_store().get_recent(
        limit=limit, prompt_key=prompt_key, stage=stage, session_id=session_id
    )


def get_top_prompts(limit: int = 20) -> List[Dict[str, Any]]:
    """Get most frequently used prompts.

    Args:
        limit: Maximum number of prompts to return.

    Returns:
        List of dicts with prompt_key, usage_count, success_count, avg_latency, last_used.
    """
    return _get_store().get_top_prompts(limit)
