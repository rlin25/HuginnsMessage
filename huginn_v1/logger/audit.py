# logger/audit.py

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

LOGS_DIR = Path("logs")
AUDIT_JSONL = LOGS_DIR / "audit.jsonl"
AUDIT_DB = LOGS_DIR / "audit.db"
ESCALATION_JSONL = LOGS_DIR / "escalation_queue.jsonl"

_db_initialized = False


def _ensure_logs_dir():
    LOGS_DIR.mkdir(exist_ok=True)


def _init_db():
    global _db_initialized
    if _db_initialized and AUDIT_DB.exists():
        return
    _ensure_logs_dir()
    conn = sqlite3.connect(AUDIT_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            job_id TEXT PRIMARY KEY,
            exception_id TEXT,
            trade_id TEXT,
            type TEXT,
            sub_type TEXT,
            outcome TEXT,
            confidence_score REAL,
            triggered_keyword TEXT,
            retrieved_document_id TEXT,
            escalation_reason TEXT,
            decision_timestamp TEXT,
            exception_timestamp TEXT,
            severity TEXT,
            full_event_json TEXT
        )
    """)
    conn.commit()
    conn.close()
    _db_initialized = True


def _write_jsonl(path: Path, event: dict):
    _ensure_logs_dir()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, default=str) + "\n")


def _write_sqlite(event: dict):
    _init_db()
    conn = sqlite3.connect(AUDIT_DB)
    conn.execute(
        """
        INSERT OR REPLACE INTO audit_log (
            job_id, exception_id, trade_id, type, sub_type,
            outcome, confidence_score, triggered_keyword,
            retrieved_document_id, escalation_reason,
            decision_timestamp, exception_timestamp, severity,
            full_event_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(event.get("job_id")),
            str(event.get("exception_id")),
            event.get("trade_id"),
            event.get("type"),
            event.get("sub_type"),
            event.get("outcome"),
            event.get("confidence_score"),
            event.get("triggered_keyword"),
            event.get("retrieved_document_id"),
            event.get("escalation_reason"),
            event.get("decision_timestamp"),
            event.get("timestamp"),
            event.get("severity"),
            json.dumps(event, default=str),
        ),
    )
    conn.commit()
    conn.close()


def log(event: dict) -> None:
    """
    Accepts a structured event dict and writes it to all applicable destinations:
      - Always: logs/audit.jsonl (append-only)
      - Always: logs/audit.db (SQLite)
      - If outcome == "escalate": logs/escalation_queue.jsonl (append-only)

    Callers do not specify destinations. Routing is internal.
    """
    event_to_write = dict(event)
    event_to_write["log_written_at"] = datetime.now(timezone.utc).isoformat()

    _write_jsonl(AUDIT_JSONL, event_to_write)
    _write_sqlite(event_to_write)

    if event.get("outcome") == "escalate":
        _write_jsonl(ESCALATION_JSONL, event_to_write)
