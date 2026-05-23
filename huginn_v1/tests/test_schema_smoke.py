# Run from project root: python tests/test_schema_smoke.py

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

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
