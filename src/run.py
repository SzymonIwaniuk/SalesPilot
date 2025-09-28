import uvicorn

from entrypoints.fastapi_app import make_app

app = make_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
