"""
Living Archive — TTS Server
Run locally or deploy to Railway / Render / Fly.io (NOT Vercel — too large for serverless).

Start:
    cd tts-server
    pip install -r requirements.txt
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Endpoints:
    POST /synthesize        — generate audio for a persona
    POST /clone-voice       — train a custom voice from a 10-sec recording
    GET  /voices            — list assigned voices per persona
    GET  /health            — health check
"""

import io
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

import scipy.io.wavfile
import torch
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel

# ── pocket-tts ─────────────────────────────────────────────────────────────
from pocket_tts.models.tts_model import TTSModel
from pocket_tts.utils.utils import (
    _ORIGINS_OF_PREDEFINED_VOICES,
    get_predefined_voice,
)
from pocket_tts.utils.weights_loading import get_flow_lm_state_dict, get_mimi_state_dict
from pocket_tts.utils.config import load_config, CONFIGS_DIR
from pocket_tts.models.mimi import MimiModel
from pocket_tts.models.flow_lm import FlowLMModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Living Archive TTS Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # lock down to your Vercel domain in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Paths ───────────────────────────────────────────────────────────────────
VOICE_DIR = Path("voices")          # uploaded 10-sec samples
STATE_DIR = Path("voice_states")    # cached pocket-tts voice states
VOICE_DIR.mkdir(exist_ok=True)
STATE_DIR.mkdir(exist_ok=True)

# ── Default voice mapping (predefined pocket-tts voices) ───────────────────
DEFAULT_VOICE_MAP: dict[str, str] = {
    "marcus":    "george",           # deep authoritative male
    "douglass":  "michael",          # strong resonant male
    "senna":     "paul",             # warm expressive male
    "newey":     "peter_yearsley",   # precise British male
    "lauda":     "charles",          # clipped formal male
    "carmack":   "bill_boerst",      # clear American male
    "torvalds":  "marius",           # Nordic-accented male
    "swartz":    "javert",           # earnest young male
    "satoshi":   "jean",             # neutral calm male
    "faker":     "paul",             # clear calm male
    "scump":     "michael",          # energetic American male
    "feynman":   "stuart_bell",      # playful professorial
    "ramanujan": "giovanni",         # warm gentle male
    "bourdain":  "peter_yearsley",   # gravel-edged male
    "voss":      "bill_boerst",      # deliberate authoritative
    "miyazaki":  "rafael",           # thoughtful male
    "curie":     "mary",             # clear female
    "trump":     "charles",          # loud formal male (parody)
}

# ── Model singleton (loaded once, reused) ───────────────────────────────────
_model: Optional[TTSModel] = None
_mimi: Optional[MimiModel] = None
_voice_cloning_available = False


def load_model() -> tuple[TTSModel, MimiModel, bool]:
    global _model, _mimi, _voice_cloning_available
    if _model is not None:
        return _model, _mimi, _voice_cloning_available

    logger.info("Loading pocket-tts model…")
    config = load_config(CONFIGS_DIR / "config.yaml")

    try:
        # Try to load voice-cloning enabled weights (requires HF auth)
        flow_state = get_flow_lm_state_dict(voice_cloning=True)
        _voice_cloning_available = True
        logger.info("Voice cloning weights loaded ✓")
    except Exception as e:
        logger.warning(f"Voice cloning weights unavailable ({e}). Using base model.")
        flow_state = get_flow_lm_state_dict(voice_cloning=False)
        _voice_cloning_available = False

    mimi_state = get_mimi_state_dict()
    _mimi = MimiModel(config.mimi)
    _mimi.load_state_dict(mimi_state)
    _mimi.eval()

    flow_lm = FlowLMModel(config.flow_lm)
    flow_lm.load_state_dict(flow_state)
    flow_lm.eval()

    _model = TTSModel(
        flow_lm=flow_lm,
        temp=config.temp,
        lsd_decode_steps=config.lsd_decode_steps,
        noise_clamp=config.noise_clamp,
        eos_threshold=config.eos_threshold,
        config=config,
    )
    logger.info("pocket-tts model ready ✓")
    return _model, _mimi, _voice_cloning_available


def get_voice_state(persona_id: str) -> dict:
    """
    Returns a voice state dict for the given persona.
    Priority: custom cloned voice > predefined voice.
    """
    model, mimi, cloning_ok = load_model()

    # 1. Custom cloned voice state saved on disk
    state_path = STATE_DIR / f"{persona_id}.pt"
    if state_path.exists() and cloning_ok:
        logger.info(f"Using cloned voice for {persona_id}")
        return torch.load(state_path, map_location="cpu")

    # 2. Predefined voice
    voice_name = DEFAULT_VOICE_MAP.get(persona_id, "alba")
    logger.info(f"Using predefined voice '{voice_name}' for {persona_id}")
    voice_audio = get_predefined_voice(voice_name)
    return model.get_state_for_audio_prompt(voice_audio)


def audio_tensor_to_wav_bytes(audio: torch.Tensor, sample_rate: int = 24000) -> bytes:
    audio_np = audio.squeeze().cpu().numpy()
    buf = io.BytesIO()
    scipy.io.wavfile.write(buf, sample_rate, audio_np)
    return buf.getvalue()


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "voice_cloning": _voice_cloning_available}


@app.get("/voices")
def list_voices():
    cloned = [p.stem for p in STATE_DIR.glob("*.pt")]
    return {
        "predefined": list(_ORIGINS_OF_PREDEFINED_VOICES.keys()),
        "persona_defaults": DEFAULT_VOICE_MAP,
        "cloned_personas": cloned,
    }


class SynthRequest(BaseModel):
    text: str
    persona_id: str
    max_tokens: int = 60


@app.post("/synthesize")
def synthesize(req: SynthRequest):
    """Generate speech for a persona. Returns WAV audio."""
    if not req.text.strip():
        raise HTTPException(400, "text is required")

    model, _, _ = load_model()

    try:
        voice_state = get_voice_state(req.persona_id)
        audio = model.generate_audio(
            model_state=voice_state,
            text_to_generate=req.text,
            max_tokens=req.max_tokens,
        )
        wav_bytes = audio_tensor_to_wav_bytes(audio)
        return Response(
            content=wav_bytes,
            media_type="audio/wav",
            headers={"X-Persona": req.persona_id},
        )
    except Exception as e:
        logger.error(f"Synthesis error: {e}")
        raise HTTPException(500, f"Synthesis failed: {e}")


@app.post("/clone-voice")
async def clone_voice(
    persona_id: str = Form(...),
    audio: UploadFile = File(...),
):
    """
    Upload a 10-second voice recording to clone for a specific persona.
    Requires HuggingFace authentication with the kyutai/pocket-tts model accepted.

    Run:  uvx hf auth login
    Then: https://huggingface.co/kyutai/pocket-tts  (accept terms)
    """
    model, _, cloning_ok = load_model()

    if not cloning_ok:
        raise HTTPException(
            503,
            detail={
                "error": "Voice cloning weights not available.",
                "fix": "Run `uvx hf auth login` and accept terms at https://huggingface.co/kyutai/pocket-tts",
            },
        )

    # Save uploaded audio to temp file
    suffix = Path(audio.filename).suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    try:
        logger.info(f"Cloning voice for persona '{persona_id}' from {audio.filename}…")
        voice_state = model.get_state_for_audio_prompt(tmp_path, truncate=True)

        # Cache state to disk
        state_path = STATE_DIR / f"{persona_id}.pt"
        torch.save(voice_state, state_path)

        logger.info(f"Voice cloned and saved for '{persona_id}' ✓")
        return JSONResponse({
            "success": True,
            "persona_id": persona_id,
            "message": f"Voice cloned successfully for {persona_id}. "
                       f"It will be used for all future Listen requests.",
        })
    except Exception as e:
        logger.error(f"Cloning error: {e}")
        raise HTTPException(500, f"Voice cloning failed: {e}")
    finally:
        os.unlink(tmp_path)
