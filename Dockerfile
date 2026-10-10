# numpy is pinned <2 in brain/requirements.txt; Python 3.12 has those wheels.
FROM node:22-bookworm-slim AS caregiver

WORKDIR /src
COPY web/caregiver/package.json web/caregiver/package-lock.json web/caregiver/
RUN npm ci --prefix web/caregiver
COPY web/caregiver web/caregiver
COPY web/fake-feed web/fake-feed
COPY brain/seed.json brain/seed.json
RUN npm run build --prefix web/caregiver

# opencv-python-headless needs libglib and libgomp on Debian slim.
FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY brain/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir \
      -r /tmp/requirements.txt \
      fastapi \
      "uvicorn[standard]" \
      python-multipart \
      websockets \
    && python -c "import cv2, fastapi, uvicorn, multipart, websockets"

COPY . /app
COPY --from=caregiver /src/web/caregiver/dist /app/web/caregiver/dist

ENV SINO_MODE=demo \
    SINO_MODEL=stub \
    CHIME=0 \
    ALWAYS_LISTEN=0 \
    HOST=0.0.0.0 \
    PORT=8000 \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# main() binds HOST/PORT and enables the hub process. Importing the app skips that.
CMD ["python", "brain/server.py"]
