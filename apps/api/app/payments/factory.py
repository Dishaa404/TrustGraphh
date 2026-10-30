from app.config import get_settings
from app.payments.base import PaymentProvider
from app.payments.cake import CakeWalletProvider
from app.payments.rodo import RodoPaymentProvider

_providers: dict[str, PaymentProvider] = {}


def get_payment_provider(name: str | None = None) -> PaymentProvider:
    settings = get_settings()
    key = (name or settings.payment_provider).lower()

    if key not in _providers:
        if key == "cake":
            _providers[key] = CakeWalletProvider(settings)
        elif key == "rodo":
            _providers[key] = RodoPaymentProvider(settings)
        else:
            raise ValueError(f"Unsupported payment provider: {key}")

    return _providers[key]
