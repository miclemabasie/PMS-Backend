from dataclasses import dataclass

@dataclass
class AccountModel:
    balance: float
    currency: str
    key: str
    agentId: str
    agentName: str
    agentAddress: str
    agentPhonenumber: str
    companyName: str
    companyAddress: str
    companyPhonenumber: str
    limitMax: float
    limitRemaining: float
