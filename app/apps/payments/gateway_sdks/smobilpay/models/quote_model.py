from dataclasses import dataclass
from datetime import datetime

@dataclass
class QuoteModel:
    quoteId: str
    expiresAt: datetime
    payItemId: str
    amountLocalCur: float
    priceLocalCur: float
    priceSystemCur: float
    localCur: str
    systemCur: str
    promotion: str
