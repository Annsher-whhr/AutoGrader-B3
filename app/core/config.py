from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AutoGrader B3"
    app_port: int = 8003
    debug: bool = True
    database_url: str = "mysql+pymysql://root:password@127.0.0.1:3306/autograder_b3?charset=utf8mb4"
    default_time_limit_ms: int = 2000
    default_output_limit: int = 20000
    default_memory_limit_mb: int = 64


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
