FROM python:3.13-slim

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN addgroup --gid 1000 nonroot && adduser --uid 1000 --gid 1000 --system --no-create-home --disabled-password nonroot

RUN mkdir /app && chown nonroot:nonroot /app
WORKDIR /app

COPY --chown=nonroot:nonroot requirements.txt .
COPY --chown=nonroot:nonroot pyproject.toml .

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir pytest pytest-asyncio httpx

COPY --chown=nonroot:nonroot src/ ./src/
COPY --chown=nonroot:nonroot tests/ ./tests/

USER nonroot

CMD ["uvicorn", "src.run:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]