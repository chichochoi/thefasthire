# backend/app/services/audio_service.py
import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi.responses import StreamingResponse

# OpenAI official SDK
from openai import OpenAI

MEDIA_DIR = Path(os.getenv("MEDIA_DIR", "./media"))

AUDIO_DIR = MEDIA_DIR / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "tts-1")
OPENAI_TTS_VOICE = os.getenv("OPENAI_TTS_VOICE", "alloy")
OPENAI_TTS_FORMAT = os.getenv("OPENAI_TTS_FORMAT", "mp3")

client = OpenAI(api_key=OPENAI_API_KEY)


def synthesize_to_file(text: str, filename_hint: Optional[str] = None) -> str:
    """
    Create TTS audio file and save under AUDIO_DIR. Returns public path (to be served by static).
    """
    fname = f"{filename_hint or 'tts'}-{uuid.uuid4().hex}.{OPENAI_TTS_FORMAT}"
    out_path = AUDIO_DIR / fname

    # Non-streaming simple generation to file
    with client.audio.speech.with_streaming_response.create(
        model=OPENAI_TTS_MODEL,
        voice=OPENAI_TTS_VOICE,
        response_format=OPENAI_TTS_FORMAT,
        input=text,
    ) as response:
        response.stream_to_file(out_path)

    # 백엔드 서버 URL을 포함한 절대 경로 반환
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    return f"{backend_url}/media/audio/{fname}"


def stream_tts(text: str):
    """
    Generator for streaming audio bytes (optional WebSocket or HTTP streaming).
    """
    # reference implementation uses chunk streaming similar to community examples
    # Frontend can reconstruct blobs between |AUDIO_START| and |AUDIO_END|
    def _gen():
        with client.audio.speech.with_streaming_response.create(
            model=OPENAI_TTS_MODEL,
            voice=OPENAI_TTS_VOICE,
            response_format=OPENAI_TTS_FORMAT,
            input=text,
        ) as response:
            for chunk in response.iter_bytes(chunk_size=1024):
                yield chunk
    return StreamingResponse(_gen(), media_type=f"audio/{OPENAI_TTS_FORMAT}")
