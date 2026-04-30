from dataclasses import dataclass
from datetime import datetime

@dataclass
class CollectionModel:
    ptn: str
    timestamp: datetime
    agentBalance: float
    receiptNumber: str
    veriCode: str
    priceLocalCur: float
    priceSystemCur: float
    localCur: str
    systemCur: str
    trid: str
    pin: str
    status: str
    payItemId: str
    payItemDescr: str
    tag: str
