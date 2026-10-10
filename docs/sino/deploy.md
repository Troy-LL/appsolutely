# Public demo on Render

The public demo is simulated: stub decisions, seeded data, no Ollama, no microphone, no camera. Render's free tier (no card) hosts it. The service sleeps after about 15 minutes idle and takes about 30–60 seconds to wake. Disk does not survive a restart. Each visitor's session lives in memory.

OpenCV is not in the image. The Kainan box is the pre-scanned file `brain/clips/cache/scan.json`. The raw `.MOV` files are not in the image.

## Deploy

Render → New → Blueprint → pick Troy-LL/appsolutely → branch `troy/public-demo` → Apply.

## Local check

```bash
docker build -t sino-demo . && docker run -p 10000:10000 -e PORT=10000 sino-demo
```

Open `http://localhost:10000`.
