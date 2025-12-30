import os


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


DB_HOST = _env("DB_HOST", "localhost")
DB_PORT = _env("DB_PORT", "3306")
DB_NAME = _env("DB_NAME", "food")
DB_USER = _env("DB_USER", "test")
DB_PASSWORD = _env("DB_PASSWORD", "test1234")

DATABASE_URL = _env(
    "DATABASE_URL",
    f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}",
)

REDIS_URL = _env("REDIS_URL", "redis://localhost:6379/0")
