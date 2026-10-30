from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "TrustGraph API"
    version: str = "0.1.0"
    app_env: str = "development"

    api_cors_origins: str = "http://localhost:3000"
    verified_ngo_wallets: str = ""

    tg_host: str | None = None
    tg_username: str | None = None
    tg_password: str | None = None
    tg_graph: str = "TrustGraph"
    tg_secret: str | None = None

    payment_provider: str = "cake"
    cake_monero_wallet_rpc_url: str | None = None
    cake_monero_wallet_rpc_user: str | None = None
    cake_monero_wallet_rpc_password: str | None = None

    rodo_api_base_url: str | None = None
    rodo_api_key: str | None = None
    rodo_webhook_secret: str | None = None

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]

    @property
    def tigergraph_configured(self) -> bool:
        return bool(self.tg_host and self.tg_secret)

    @property
    def cake_wallet_configured(self) -> bool:
        return bool(
            self.cake_monero_wallet_rpc_url
            and self.cake_monero_wallet_rpc_user
            and self.cake_monero_wallet_rpc_password
        )

    @property
    def ngo_wallet_allowlist(self) -> set[str]:
        return {
            wallet.strip().lower()
            for wallet in self.verified_ngo_wallets.split(",")
            if wallet.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
