import json
import sqlite3
from pathlib import Path

LOGS_DIR = Path("logs")
AUDIT_JSONL = LOGS_DIR / "audit.jsonl"
AUDIT_DB = LOGS_DIR / "audit.db"
ESCALATION_JSONL = LOGS_DIR / "escalation_queue.jsonl"

_db_initialized = False


def _init_db() -> None:
    global _db_initialized
    if _db_initialized and AUDIT_DB.exists():
        return
    LOGS_DIR.mkdir(exist_ok=True)
    con = sqlite3.connect(AUDIT_DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            job_id TEXT PRIMARY KEY,
            exception_id TEXT,
            trade_id TEXT,
            type TEXT,
            sub_type TEXT,
            outcome TEXT,
            confidence_score REAL,
            triggered_keyword TEXT,
            retrieved_document_ids TEXT,
            escalation_reason TEXT,
            decision_timestamp TEXT,
            exception_timestamp TEXT,
            severity TEXT,
            full_event_json TEXT
        )
    """)
    con.commit()
    con.close()
    _db_initialized = True


def log(event: dict) -> None:
    _init_db()
    LOGS_DIR.mkdir(exist_ok=True)

    # JSONL — audit log
    with AUDIT_JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, default=str) + "\n")

    # SQLite
    con = sqlite3.connect(AUDIT_DB)
    con.execute(
        """INSERT OR REPLACE INTO audit_log VALUES (
            :job_id, :exception_id, :trade_id, :type, :sub_type,
            :outcome, :confidence_score, :triggered_keyword,
            :retrieved_document_ids, :escalation_reason,
            :decision_timestamp, :exception_timestamp,
            :severity, :full_event_json
        )""",
        {
            "job_id": event.get("job_id"),
            "exception_id": event.get("exception_id"),
            "trade_id": event.get("trade_id"),
            "type": event.get("type"),
            "sub_type": event.get("sub_type"),
            "outcome": event.get("outcome"),
            "confidence_score": event.get("confidence_score"),
            "triggered_keyword": event.get("triggered_keyword"),
            "retrieved_document_ids": json.dumps(event.get("retrieved_document_ids", [])),
            "escalation_reason": event.get("escalation_reason"),
            "decision_timestamp": event.get("decision_timestamp"),
            "exception_timestamp": event.get("timestamp"),
            "severity": event.get("severity"),
            "full_event_json": json.dumps(event, default=str),
        },
    )
    con.commit()
    con.close()

    # Escalation queue
    if event.get("outcome") == "escalate":
        with ESCALATION_JSONL.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")
