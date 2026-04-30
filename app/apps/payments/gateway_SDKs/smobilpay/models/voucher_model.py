from dataclasses import dataclass

@dataclass
class VoucherModel:
    serviceid: int
    merchant: str
    payItemId: str
    payItemDescr: str
    amountType: str
    localCur: str
    name: str
    amountLocalCur: float
    description: str
    optStrg: str
    optNmb: int
