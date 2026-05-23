# Huginn v1 — Subplan 1: Exception Schema

**Component:** `models/exception.py`
**Depends on:** Nothing. This is the foundation.
**Gate:** Pydantic model instantiates and validates correctly for all test fixture cases before Subplan 2 begins.

---

## Reference Documents

- `huginn_v1_interface_contract.md` — Component 1 (Exception Schema) is the authoritative spec
- `huginn_v1_design_decisions.md` — Decisions 1, 2, 14, 15, 16

---

## What to Build

A single file: `models/exception.py`

It contains:
- `ExceptionType` enum
- `SettlementMismatchSubType` enum
- `Severity` enum
- `TradeException` Pydantic model with a cross-field model validator

---

## Implementation

```python
# models/exception.py

from pydantic import BaseModel, model_validator
from uuid import UUID
from datetime import datetime
from enum import Enum


class ExceptionType(str, Enum):
    settlement_mismatch = "settlement_mismatch"


class SettlementMismatchSubType(str, Enum):
    price_mismatch = "price_mismatch"
    quantity_mismatch = "quantity_mismatch"
    wrong_settlement_date = "wrong_settlement_date"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class TradeException(BaseModel):
    exception_id: UUID
    trade_id: str
    type: ExceptionType
    sub_type: SettlementMismatchSubType
    description: str
    timestamp: datetime
    severity: Severity

    @model_validator(mode="after")
    def validate_sub_type_scope(self):
        # In v1 only settlement_mismatch is valid so all SettlementMismatchSubType
        # values are valid. This validator becomes meaningful in v2 when additional
        # ExceptionType values are added with their own sub_type enums.
        return self
```

---

## Test Fixtures

Create these in `tests/fixtures/` as JSON files. They are reused in every subsequent subplan and test suite.

### fixture_price_mismatch.json
```json
{
  "exception_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "trade_id": "TRD-001",
  "type": "settlement_mismatch",
  "sub_type": "price_mismatch",
  "description": "Counterparty confirms settlement at 102.50 but our records show 101.75 for bond CUSIP 123456789.",
  "timestamp": "2026-05-15T09:30:00Z",
  "severity": "high"
}
```

### fixture_quantity_mismatch.json
```json
{
  "exception_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "trade_id": "TRD-002",
  "type": "settlement_mismatch",
  "sub_type": "quantity_mismatch",
  "description": "Our records indicate 10,000 shares but counterparty confirms 9,500 shares for equity TICKER XYZ.",
  "timestamp": "2026-05-15T10:15:00Z",
  "severity": "medium"
}
```

### fixture_wrong_settlement_date.json
```json
{
  "exception_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "trade_id": "TRD-003",
  "type": "settlement_mismatch",
  "sub_type": "wrong_settlement_date",
  "description": "Settlement date recorded as 2026-05-16 in our system but counterparty expects settlement on 2026-05-17.",
  "timestamp": "2026-05-15T11:00:00Z",
  "severity": "low"
}
```

### fixture_mandatory_escalation.json
```json
{
  "exception_id": "d4e5f6a7-b8c9-0123-defa-234567890123",
  "trade_id": "TRD-004",
  "type": "settlement_mismatch",
  "sub_type": "price_mismatch",
  "description": "Price discrepancy flagged. Counterparty account subject to sanctions review. Settlement suspended pending compliance clearance.",
  "timestamp": "2026-05-15T11:30:00Z",
  "severity": "high"
}
```

### fixture_invalid_type.json — for validation error testing only
```json
{
  "exception_id": "e5f6a7b8-c9d0-1234-efab-345678901234",
  "trade_id": "TRD-005",
  "type": "corporate_action_failure",
  "sub_type": "price_mismatch",
  "description": "This exception type is not valid in v1.",
  "timestamp": "2026-05-15T12:00:00Z",
  "severity": "low"
}
```

---

## Validation Test Script

Run this directly with `python` (not pytest) to confirm the model works before proceeding:

```python
# Run from project root: python tests/test_schema_smoke.py

import json
from pathlib import Path
from pydantic import ValidationError
from models.exception import TradeException

fixtures_dir = Path("tests/fixtures")

# These four should instantiate successfully
for fixture_name in [
    "fixture_price_mismatch.json",
    "fixture_quantity_mismatch.json",
    "fixture_wrong_settlement_date.json",
    "fixture_mandatory_escalation.json",
]:
    data = json.loads((fixtures_dir / fixture_name).read_text())
    exc = TradeException(**data)
    print(f"PASS: {fixture_name} → {exc.type} / {exc.sub_type}")

# This one should raise ValidationError
try:
    data = json.loads((fixtures_dir / "fixture_invalid_type.json").read_text())
    TradeException(**data)
    print("FAIL: fixture_invalid_type.json should have raised ValidationError")
except ValidationError as e:
    print(f"PASS: fixture_invalid_type.json correctly rejected → {e.error_count()} error(s)")
```

**Expected output:**
```
PASS: fixture_price_mismatch.json → settlement_mismatch / price_mismatch
PASS: fixture_quantity_mismatch.json → settlement_mismatch / quantity_mismatch
PASS: fixture_wrong_settlement_date.json → settlement_mismatch / wrong_settlement_date
PASS: fixture_mandatory_escalation.json → settlement_mismatch / price_mismatch
PASS: fixture_invalid_type.json correctly rejected → 1 error(s)
```

---

## Gate Criteria

All five lines above print with PASS before Subplan 2 begins. If any line prints FAIL, fix the model first.

---

## What NOT to Do

- Do not import from `agent/`, `mimir/`, `logger/`, or `api/` — nothing else exists yet
- Do not add fields not in the spec — the schema is locked
- Do not skip the model validator — it is required for v2 expansion
