# Living Archive — TTS Server

Runs locally or on Railway / Render / Fly.io.
**Cannot run on Vercel** (PyTorch is too large for serverless).

---

## Quick Start

```bash
cd tts-server
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Server runs at `http://localhost:8000`.

---

## Voice Cloning Setup (One-time)

pocket-tts voice cloning requires HuggingFace authentication:

```bash
# 1. Install HF CLI
pip install huggingface_hub

# 2. Login
huggingface-cli login

# 3. Accept model terms at:
#    https://huggingface.co/kyutai/pocket-tts
```

Once done, restart the server — it will load the cloning-capable weights automatically.

---

## Uploading a Voice Sample

Send a 10-second recording for any persona:

```bash
curl -X POST http://localhost:8000/clone-voice \
  -F "persona_id=marcus" \
  -F "audio=@/path/to/recording.wav"
```

Supported persona IDs: `marcus`, `douglass`, `senna`, `newey`, `lauda`,
`carmack`, `torvalds`, `swartz`, `satoshi`, `faker`, `scump`,
`feynman`, `ramanujan`, `kalam`, `bourdain`, `voss`, `miyazaki`,
`curie`, `trump`

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Server status + cloning availability |
| `GET` | `/voices` | List all voices and assignments |
| `POST` | `/synthesize` | Generate speech (returns WAV) |
| `POST` | `/clone-voice` | Upload 10-sec sample to clone a voice |

---

## Deploy to Railway

```bash
railway login
railway init
railway up
```

Set `TTS_SERVER_URL` in your Vercel dashboard to the Railway URL.
