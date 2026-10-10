FROM node:20-slim AS caregiver

WORKDIR /src
COPY web/caregiver web/caregiver
COPY web/fake-feed web/fake-feed
COPY brain/seed.json brain/seed.json
RUN cd web/caregiver && npm ci && npm run build

FROM python:3.11-slim

WORKDIR /app

COPY brain/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY brain brain
COPY hub hub
COPY web web
COPY --from=caregiver /src/web/caregiver/dist web/caregiver/dist

ENV SINO_MODE=demo \
    SINO_MODEL=stub \
    CHIME=0 \
    ALWAYS_LISTEN=0 \
    PYTHONUNBUFFERED=1

EXPOSE 10000

CMD ["sh", "-c", "exec uvicorn brain.server:app --host 0.0.0.0 --port ${PORT:-10000}"]
