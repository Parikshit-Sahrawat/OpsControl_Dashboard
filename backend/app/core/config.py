from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://opscontrol:opscontrol@localhost:5432/opscontrol"
    cors_origins: str = "http://localhost:5173"
    environment: str = "development"
    seed_demo_data: bool = False
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]
settings = Settings()
