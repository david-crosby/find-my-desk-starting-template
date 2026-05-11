from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/deskmate.db"
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    # Set true once Azure credentials are configured — gates MS Places API calls.
    ms_places_enabled: bool = False
    anthropic_api_key: str = ""
    backend_url: str = "http://localhost:8000"
    agent_url: str = "http://localhost:8001"
    allocation_run_time: str = "23:00"
    checkin_cutoff_time: str = "10:00"
    notification_webhook_url: str = ""


settings = Settings()
