from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/deskmate.db"
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    anthropic_api_key: str = ""
    backend_url: str = "http://localhost:8000"
    agent_url: str = "http://localhost:8001"


settings = Settings()
