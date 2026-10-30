from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PaymentIntent:
    id: str
    provider: str
    payer_did: str
    asset: str
    amount: float
    address: str
    status: str
    created_at: str
    expires_at: str
    uri: str


class PaymentProvider(ABC):
    name: str

    @abstractmethod
    def create_intent(self, payer_did: str, amount: float, asset: str) -> PaymentIntent:
        """Create a payment intent and return the deposit details."""

    def get_status(self, payment_id: str, current: str) -> str:
        """Return the latest status. Adapters can override to poll their API."""
        return current
