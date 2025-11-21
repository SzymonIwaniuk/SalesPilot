import os

from uvicorn.config import Config
from uvicorn.server import Server

from entrypoints.fastapi_app import make_app

HOST = os.environ.get("API_HOST", "localhost")
PORT = 10300 if HOST == "localhost" else 10400

app = make_app()


async def run_server():
    config = Config("run:app", host=HOST, port=PORT, log_level="info", access_log=True, use_colors=True)
    server = Server(config)
    await server.serve()


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_server())
