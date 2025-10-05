FROM python:3.13-slim

RUN addgroup --gid 1000 nonroot && adduser --uid 1000 --gid 1000 --system --no-create-home --disabled-password nonroot

RUN mkdir /src && chown nonroot:nonroot /src
WORKDIR /src

COPY --chown=nonroot:nonroot requirements.txt .
COPY --chown=nonroot:nonroot src/ .

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
ENV PYTHONPATH="/src"

RUN pip install --no-cache-dir -r requirements.txt

USER nonroot

CMD uvicorn run:app --host 0.0.0.0 --port 8000 --reload