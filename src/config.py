import os


# TODO: Clean up, decouple config to settings and bootstrap
def get_postgres_uri() -> str:
    host = os.environ.get("DB_HOST", "localhost")
    port = 5432 if host == "localhost" else 54321
    password = os.environ.get("DB_PASSWORD", "abc123")
    user, db_name = "allocation", "allocation"
    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"


def get_api_url() -> str:
    host = os.environ.get("API_HOST", "localhost")
    port = 5005 if host == "localhost" else 80
    return f"http://{host}:{port}"


# def postgres_db() -> Engine:
#     engine = create_engine(get_postgres_uri())
#     metadata.create_all(engine)
#     return engine
#
#
# def get_postgres_session() -> Session:
#     engine = postgres_db()
#     start_mappers()
#     pg_session = sessionmaker(bind=engine)
#     return pg_session()
