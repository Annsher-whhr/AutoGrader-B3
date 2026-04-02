from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings


class Base(DeclarativeBase):
    """所有数据库模型的共同父类。

    只要一个类继承它，SQLAlchemy 就会把这个类当成 ORM 模型来处理。
    后面定义的 `Question`、`TestCase`、`EvaluationRecord` 等表，
    都是基于这个基类创建出来的。
    """

    pass


settings = get_settings()
engine_kwargs = {"future": True}
if settings.database_url.startswith("sqlite"):
    # 如果当前使用的是 SQLite，需要额外设置连接参数。
    # `check_same_thread=False` 允许同一个数据库连接在不同线程中被访问，
    # 这在 FastAPI 测试场景里比较常见。
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    if ":memory:" in settings.database_url:
        # 内存数据库本来只存在于“当前连接”里。
        # 这里强制复用同一个连接，避免每新建一次 Session，
        # 数据表就重新变成空的。
        engine_kwargs["poolclass"] = StaticPool
engine = create_engine(settings.database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    """为每次请求提供一个数据库会话。

    FastAPI 会在进入接口函数时拿到 `yield` 出去的 `db`，
    等接口处理完之后，再执行 `finally` 里的 `close()`。
    这样可以避免数据库连接长时间不释放。
    """

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
