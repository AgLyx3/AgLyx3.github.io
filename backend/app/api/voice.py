"""Voice API endpoints: STT token vending and TTS streaming."""

import asyncio
import json
import os
import urllib.error
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.services import RateLimiter

router = APIRouter(tags=["voice"])
tts_rate_limiter = RateLimiter(10)


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)


@router.get("/voice/stt-token")
def stt_token(settings: Settings = Depends(get_settings)) -> dict:
    """Vend a short-lived AssemblyAI v3 streaming token to the frontend."""
    if not settings.assemblyai_api_key:
        raise HTTPException(status_code=503, detail="STT not configured")

    req = urllib.request.Request(
        "https://streaming.assemblyai.com/v3/token?expires_in_seconds=300",
        headers={"Authorization": settings.assemblyai_api_key},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise HTTPException(status_code=503, detail=f"STT token request failed: {exc.code}") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="STT token request failed") from exc

    token = payload.get("token")
    if not token:
        raise HTTPException(status_code=503, detail="STT token missing in response")

    return {"token": token}


@router.post("/voice/tts")
async def tts(
    body: TTSRequest,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """Stream TTS audio (MP3) from OpenAI for a short text snippet."""
    client_key = request.client.host if request.client else "unknown"
    tts_rate_limiter.check(f"tts-ip:{client_key}", limit_per_minute=10)

    tts_payload = json.dumps(
        {
            "model": settings.tts_model,
            "voice": settings.tts_voice,
            "input": body.text,
            "response_format": "mp3",
        }
    ).encode()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="TTS not configured")

    req = urllib.request.Request(
        "https://api.openai.com/v1/audio/speech",
        data=tts_payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    async def generate():
        q: asyncio.Queue[bytes | None] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _fetch():
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    while True:
                        chunk = resp.read(4096)
                        if not chunk:
                            break
                        loop.call_soon_threadsafe(q.put_nowait, chunk)
            except Exception as exc:
                loop.call_soon_threadsafe(q.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(q.put_nowait, None)

        fut = loop.run_in_executor(None, _fetch)
        while True:
            if await request.is_disconnected():
                break
            try:
                chunk = await asyncio.wait_for(q.get(), timeout=10.0)
            except asyncio.TimeoutError:
                break
            if chunk is None:
                break
            if isinstance(chunk, Exception):
                raise HTTPException(status_code=502, detail="TTS upstream error")
            yield chunk
        await fut

    return StreamingResponse(generate(), media_type="audio/mpeg")
