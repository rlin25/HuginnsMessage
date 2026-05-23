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
