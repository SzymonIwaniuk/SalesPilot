import os


# TODO: Clean up, decouple config to settings and bootstrap
def get_postgres_uri() -> str:
    host = os.environ.get("DB_HOST", "localhost")
    port = 5432
    password = os.environ.get("DB_PASSWORD", "allocate")
    user, db_name = "allocation", "allocation"
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"


def get_api_url() -> str:
    host = os.environ.get("API_HOST", "localhost")
    port = 5005 if host == "localhost" else 80
    return f"http://{host}:{port}"
