from dataclasses import dataclass, field

@dataclass
class MerchantModel:
    merchant: str
    name: str
    description: str
    category: str
    country: str
    status: str
    logo: str
    logoHash: str

    def __post_init__(self):
        """Post-initialization processing."""
        # Example of converting an optional field to a default if None:
        self.description = self.description if self.description is not None else "No description provided"

    def __repr__(self):
        return f"<MerchantModel(name={self.name}, status={self.status})>"
