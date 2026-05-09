# The Living Archive

> *Speak with history. Learn from greatness.*

A democratized mentorship platform — 20 conversational AI personas of history's greatest minds. Pluto TV theme, mobile-first, voice-enabled.

**[→ Live on Vercel](#)** · **[TTS Server Setup](tts-server/README.md)**

---

## Personas (20)

| Category | Personas |
|---|---|
| Philosophy & History | Marcus Aurelius, Frederick Douglass |
| Motorsport & Engineering | Ayrton Senna, Adrian Newey, Niki Lauda |
| Tech Visionaries | John Carmack, Linus Torvalds, Aaron Swartz, Satoshi Nakamoto |
| Esports & Gaming | Faker, Scump |
| Math & Science | Richard Feynman, Srinivasa Ramanujan |
| Visionaries & Nation Builders | Dr. A.P.J. Abdul Kalam |
| Strategy & Culture | Anthony Bourdain, Chris Voss, Hayao Miyazaki, Marie Curie |
| Special Archives | Donald Trump *(Parody)* |

---

## Features

- **20 AI personas** — distinct voice, reasoning style, safeguard rules
- **Listen button** — text-to-speech on every AI response via pocket-tts
- **Custom voice cloning** — upload a 10-sec recording, assign to any persona
- **Mobile start screen** — persona picker → full chat
- **Persona switcher drawer** — swap personas mid-conversation
- **Verified corpus citations** — every response cites its source
- **Confidence scoring** — transparency on how grounded each answer is
- **Groq API proxied** — API key never exposed to client
- **Pluto TV theme** — black + `#FEF200` yellow
- **Quicksand font** throughout

---

## Project Structure

```
/
├── index.html              # Frontend (single file)
├── vercel.json             # Vercel deployment config
├── requirements.txt        # Vercel serverless (lightweight)
├── .env.example            # Environment variable template
├── api/
│   ├── chat.py             # Groq API proxy (serverless)
│   └── tts_url.py          # TTS server URL endpoint (serverless)
└── tts-server/
    ├── main.py             # FastAPI TTS server (pocket-tts)
    ├── requirements.txt    # Heavy deps (torch, pocket-tts, scipy)
    └── README.md           # TTS server setup guide
```

---

## Vercel Deployment

### 1. Fork & Clone
```bash
git clone https://github.com/Alex-Goodwin1109/The-Living-Archive.git
cd The-Living-Archive
```

### 2. Set Environment Variables in Vercel Dashboard

| Variable | Value |
|---|---|
| `GROQ_API_KEY` | Your key from [console.groq.com](https://console.groq.com) |
| `TTS_SERVER_URL` | URL of your running TTS server |

### 3. Deploy
```bash
npx vercel --prod
```

---

## TTS Server (Voice)

The TTS server runs **separately** from Vercel (PyTorch is too large for serverless).

```bash
cd tts-server
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

See [tts-server/README.md](tts-server/README.md) for voice cloning setup and Railway deployment.

---

## Local Development

```bash
# Install Python env
python3 -m venv venv
venv/bin/pip install pocket-tts scipy

# Copy env template
cp .env.example .env
# Fill in GROQ_API_KEY in .env

# Run TTS server
cd tts-server && venv/bin/uvicorn main:app --reload

# Open index.html in browser (or use vercel dev)
npx vercel dev
```

---

## Safeguards

- All responses grounded in verified source corpus
- Hard-blocked from fabricating positions on unaddressed topics
- Confidence scoring on every output
- AI-mediated disclaimer on all conversations
- Groq API key server-side only, never in client code

---

## License

MIT
