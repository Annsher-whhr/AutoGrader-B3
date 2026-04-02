from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """项目的统一配置入口。

    这里的字段会优先从环境变量或 `.env` 文件中读取；
    如果外部没有提供，就使用这里写好的默认值。
    这样做的好处是：代码里只需要关心“我要什么配置”，
    不需要在很多地方重复写读取环境变量的逻辑。
    """

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
    """返回全局唯一的一份配置对象。

    使用缓存的原因是：
    1. 避免每次调用都重新读取环境变量。
    2. 保证整个进程里拿到的是同一套配置，行为更稳定。
    """

    return Settings()
