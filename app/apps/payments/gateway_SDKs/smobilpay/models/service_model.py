from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Label:
    language: str
    localText: str

@dataclass
class Hint:
    language: str
    localText: str

@dataclass
class ServiceModel:
    serviceid: int
    merchant: str
    title: str
    description: str
    category: str
    country: str
    localCur: str
    type: str
    status: str
    isReqCustomerName: bool
    isReqCustomerAddress: bool
    isReqCustomerNumber: bool
    isReqServiceNumber: bool
    isVerifiable: bool  # This and subsequent fields should not have default values before fields with defaults
    validationMask: str
    denomination: int
    labelCustomerNumber: List[Label] = field(default_factory=list)
    labelServiceNumber: List[Label] = field(default_factory=list)
    hint: List[Hint] = field(default_factory=list)
