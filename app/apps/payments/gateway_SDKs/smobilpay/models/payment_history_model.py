from dataclasses import dataclass
from datetime import datetime

@dataclass
class PaymentHistoryModel:
    ptn: str
    serviceid: str
    merchant: str
    timestamp: datetime
    receiptNumber: str
    veriCode: str
    clearingDate: datetime
    trid: str
    priceLocalCur: float
    priceSystemCur: float
    localCur: str
    systemCur: str
    pin: str
    status: str
    payItemId: str
    payItemDescr: str
    errorCode: int
    tag: str
