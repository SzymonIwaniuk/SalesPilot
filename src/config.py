import os


# TODO: Clean up, decouple config to settings and bootstrap
def get_postgres_uri() -> str:
    host = os.environ.get("DB_HOST", "localhost")
    port = 5432
    password = os.environ.get("DB_PASSWORD", "allocate")
    user, db_name = "allocation", "allocation"
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"
