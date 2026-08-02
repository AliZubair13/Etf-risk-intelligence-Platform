from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), '..', '..', '.env'),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql://etf_user:etfpass123@localhost:5433/etf_risk"
    fred_api_key: str = ""
    sec_user_agent: str = "Zubair Ali zubair@nyu.edu"
    groq_api_key: str = ""
    anthropic_api_key: str = ""
    app_env: str = "development"
    log_level: str = "INFO"

settings = Settings()
