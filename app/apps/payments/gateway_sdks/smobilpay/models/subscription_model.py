from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class SubscriptionModel:
    serviceNumber: str
    serviceid: str
    merchant: str
    payItemId: str
    payItemDescr: str
    amountType: str
    name: str
    localCur: str
    amountLocalCur: float
    customerReference: str
    customerName: str
    customerNumber: str
    startDate: datetime
    dueDate: datetime
    endDate: datetime
    optStrg: Optional[str]
    optNmb: Optional[int]
