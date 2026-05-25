# Walkthrough: `models/exception.py`

## Purpose

This file is the system's only boundary with the outside world at the schema level. Everything that enters Huginn must be valid by the time it reaches the agent. This file enforces that.

The file exists as a separate component — not defined inline in the API layer — because the schema is referenced by every other component in the system. The API layer validates against it. The agent state carries the serialized exception dict. The audit logger records every field. Centralizing the schema here means any component that needs to understand what a valid exception looks like has a single authoritative source.

The design decision to use a Pydantic model (Decision 14) rather than looser typing means validation failures are structural errors caught before the agent runs. The system never processes a malformed exception.

## Relationships

- **Imports from:** Standard library only (`pydantic`, `uuid`, `datetime`, `enum`)
- **Imported by:** `api/main.py` — the only caller; creates a `TradeException` instance before invoking the agent
- **Does not touch:** The agent graph, Mimir, the audit logger, or anything related to processing — this file knows nothing about what happens after validation

## Decision Rationale

**Why three separate enum classes** (`ExceptionType`, `SettlementMismatchSubType`, `Severity`) rather than embedding their values directly in the model fields: each enum is a distinct concept that will evolve independently. `ExceptionType` will gain new values in v3. `SettlementMismatchSubType` may gain new sub-types when the type taxonomy expands. `Severity` is currently inert but will become a reasoning input in v3. Separate classes keep the extension surface clean.

**Why the model_validator exists as a separate function** rather than being collapsed into the enum structure: the validator enforces that `sub_type` is appropriate for the given `type`. In v2, only one type exists so this appears redundant. It is not redundant — it exists because v3 will add new exception types with their own sub-types, and the validator is where that mapping logic lives. Collapsing it into the enum would make it harder to extend without touching the enum definition (Decision 15).

**Why all fields are required with no defaults**: In a compliance context, a missing field is a data quality problem that should be surfaced immediately, not silently papered over with a default value. Every field in the exception schema was deliberately placed there — if it's not present in the incoming payload, the submission is malformed.

**Why `severity` is in the schema but not used by the LLM**: The audit log captures `severity` on every record. V3 will use real v2 audit data to understand severity-outcome correlation before weighting it in the reasoning rubric. Including `severity` now — before it's used — means v3 can do that analysis without requiring a schema migration (Decisions 16, 42).

**Why `exception_id` is a `UUID` type** (not `str`): Pydantic validates UUID format at parse time. A malformed UUID fails with a structured 422 error before the agent runs. The `job_id` assigned by the API layer is also a UUID but a different one — the distinction between who submitted the exception (`exception_id`) and which processing job handled it (`job_id`) is meaningful in an audit trail.

## What It Does Not Do

- No helper methods on the model
- No custom JSON serializers
- No business logic — it validates structure, not semantics
- No routing, no LLM calls, no retrieval
- No default values on any field

The field `severity` is captured here but produces no behavior in v2. The API layer (`api/main.py`) is the component that decides what happens with a validated exception. This file's job ends at the validation step.

## V3 Touch Points

`ExceptionType` will gain at least one new value when trade reporting violations or other exception categories are added. The model_validator's `if self.type == ExceptionType.settlement_mismatch` block will become a lookup table mapping each type to its valid sub-types. The `Severity` field will be passed through to the agent state and injected into the LLM reasoning prompt, activating the v3 feature Decision 42 defers.
