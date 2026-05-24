# Walkthrough: `models/exception.py`

## Purpose

This file is the schema definition for every trade exception that enters Huginn. It exists as a separate component because schema enforcement belongs at the system boundary, not inside the agent logic. Everything downstream — the agent, Mimir, the logger — assumes the data it receives is already valid. This file is what makes that assumption safe.

The placement in `models/` rather than inside `api/` or `agent/` is deliberate: the schema is a shared contract, not the property of any one component. Both the API layer and the test harness import directly from here.

Design Decisions 1, 2, 14, 15, and 16 collectively define the contents of this file.

## Relationships

- **Imported by:** `api/main.py` (FastAPI uses it as the request body type), test fixtures
- **Imports from:** nothing in the project — only standard library and Pydantic
- **Does not touch:** the agent, Mimir, the logger, or anything else

This file has no outward dependencies on Huginn's own code. That is intentional — the schema must be evaluable in complete isolation.

## Decision Rationale

**Why `str, Enum` instead of plain `Enum`:**
The `str` mixin means enum values serialize directly to their string representations in JSON without needing a custom serializer. FastAPI and the audit logger both receive clean strings rather than `ExceptionType.settlement_mismatch` objects. This is a Pydantic v2 convention, not boilerplate.

**Why `UUID` for `exception_id` instead of `str`:**
Decision 14 explicitly chooses UUID here. A plain string for `exception_id` pushes uniqueness enforcement onto the caller. UUID makes uniqueness a type constraint — if the field is present, it's unique by construction. It also serializes to a standard hyphenated string in JSON at no cost.

**Why `datetime` for `timestamp` instead of `str`:**
Decision 14 again. `datetime` enables date range queries directly in the SQLite audit log without parsing. A string timestamp requires the query writer to know the format and parse it themselves; a `datetime` type means the constraint is structural.

**Why `severity` is present but not used:**
Decision 16 establishes this explicitly. Including the field in v1 means no schema change is required in v2 when severity becomes a reasoning input. The data is captured from day one even though the agent ignores it. This is the vertical slicing principle applied directly to a field: adding it now costs nothing; adding it in v2 after the schema is in production would require a migration.

**Why the `model_validator` exists but does nothing in v1:**
Decision 15 explains this. The validator's job in v2 is to enforce that `sub_type` values are valid for their parent `type`. In v1 there is only one exception type, so all sub_types are always valid — but the validator is wired in now so the v2 expansion point is explicit and already in place. A comment in the code makes the intent plain.

## What It Does Not Do

This file does not validate the *meaning* of the exception — whether the description is coherent, whether the trade ID refers to a real trade, or whether the severity is accurate. It validates structure only. Semantic validation is the agent's job.

It does not define any routing logic, escalation logic, or defaults. Those belong to the agent and the API layer respectively.

## V2 Touch Points

The `model_validator` is the primary v2 touch point. When new exception types are added (Decision 1 defers this to v2), each new type brings its own sub_type enum and the validator begins enforcing the type/sub_type relationship. No other change to this file is needed — the validator is already wired, the pattern is already established.

The `severity` field becomes an active reasoning input in v2 (Decision 16). That change happens in `agent/nodes.py`, not here. The schema stays the same.
