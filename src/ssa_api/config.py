"""Runtime configuration for the API gateway.

Values come from environment variables so the container contract
matches docker-compose. Defaults assume local dev without compose.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    model_server_url: str = "http://model-server:5001"
    mlflow_tracking_uri: str = "http://mlflow:5000"
    registry_model_name: str = "stock-sentiment"

    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "mlops"
    postgres_password: str = "mlops_local_dev"
    postgres_db: str = "mlops"

    # Simple allowlist for /model/rollback — only local docker network
    rollback_allowed_prefixes: str = "127.,10.,172.,192.168."

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
