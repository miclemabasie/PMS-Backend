from dataclasses import dataclass
from datetime import datetime

@dataclass
class BillModel:
    billType: str
    penaltyAmount: float
    payOrder: int
    payItemId: str
    payItemDescr: str
    serviceNumber: str
    serviceid: int
    merchant: str
    amountType: str
    localCur: str
    amountLocalCur: float
    billNumber: str
    customerNumber: str
    billMonth: str
    billYear: str
    billDate: datetime
    billDueDate: datetime
    optStrg: str
    optNmb: int
