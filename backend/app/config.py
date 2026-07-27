from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql://etf_user:change_me@localhost:5432/etf_risk"

    # External APIs
    fred_api_key: str = ""
    sec_user_agent: str = "Zubair Ali zubair@nyu.edu"

    # LLM
    groq_api_key: str = ""
    anthropic_api_key: str = ""

    # App
    app_env: str = "development"
    log_level: str = "INFO"


settings = Settings()
