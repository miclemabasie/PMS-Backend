# ping_model.py
from dataclasses import dataclass

@dataclass
class PingModel:
    time: str = None
    version: str = None
    nonce: str = None
    key: str = None
    error: str = None  # Field to store error message, if any

