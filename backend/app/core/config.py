from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Literal

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://opscontrol:opscontrol@localhost:5432/opscontrol"
    cors_origins: str = "http://localhost:5173"
    environment: Literal["development", "demo", "test", "staging", "production"] = "development"
    seed_demo_data: bool = False
    trusted_proxy_ips: str = ""
    collector_max_concurrency: int = Field(default=4, ge=1, le=16)
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=5, ge=0, le=50)
    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, value):
        return value.strip().lower() if isinstance(value, str) else value
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]
settings = Settings()
