"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "Corrup.ORG API"
    app_version: str = "0.1.0"
    app_description: str = (
        "API for integrating and analysing public organization financial data "
        "to detect missing funds and irregularities."
    )
    debug: bool = False

    database_url: str = "sqlite:///./corrup.db"

    # Optional: Brazilian Portal da Transparência API key
    transparencia_api_key: str = ""
    # Base URL for Portal da Transparência
    transparencia_base_url: str = "https://api.portaldatransparencia.gov.br/api-de-dados"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
