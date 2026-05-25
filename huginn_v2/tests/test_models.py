import pytest
from pydantic import ValidationError
from models.exception import TradeException, ExceptionType, SettlementMismatchSubType


VALID_EXCEPTION = {
    "exception_id": "550e8400-e29b-41d4-a716-446655440000",
    "trade_id": "TRD-001",
    "type": "settlement_mismatch",
    "sub_type": "price_mismatch",
    "description": "Counterparty confirms 142.50, we show 141.75 for 500 AAPL shares.",
    "timestamp": "2026-05-01T09:30:00",
    "severity": "high",
}


def test_valid_exception_passes():
    exc = TradeException(**VALID_EXCEPTION)
    assert exc.type == ExceptionType.settlement_mismatch
    assert exc.sub_type == SettlementMismatchSubType.price_mismatch


def test_invalid_type_raises():
    with pytest.raises(ValidationError):
        TradeException(**{**VALID_EXCEPTION, "type": "unknown_type"})


def test_invalid_sub_type_raises():
    with pytest.raises(ValidationError):
        TradeException(**{**VALID_EXCEPTION, "sub_type": "unknown_sub_type"})


def test_missing_field_raises():
    payload = {k: v for k, v in VALID_EXCEPTION.items() if k != "exception_id"}
    with pytest.raises(ValidationError):
        TradeException(**payload)


def test_all_sub_types_valid():
    for sub_type in ("price_mismatch", "quantity_mismatch", "wrong_settlement_date"):
        exc = TradeException(**{**VALID_EXCEPTION, "sub_type": sub_type})
        assert exc.sub_type.value == sub_type


def test_all_severity_values_valid():
    for severity in ("low", "medium", "high"):
        exc = TradeException(**{**VALID_EXCEPTION, "severity": severity})
        assert exc.severity.value == severity
