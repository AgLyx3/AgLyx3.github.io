"""Voice API endpoints: STT token vending and TTS streaming."""

import asyncio
import json
import os
import urllib.error
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Optional

from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.services import RateLimiter, flush_tracing, observe, trace_id_for

router = APIRouter(tags=["voice"])
tts_rate_limiter = RateLimiter(10)


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    # Links this sentence back to the chat turn that produced it. Successful
    # synthesis emits no span — one per sentence would triple a voice turn's
    # trace cost for no insight — but failures do, since a silent answer is
    # exactly the bug that is otherwise invisible.
    turn_id: Optional[str] = Field(default=None, max_length=64)


class VoiceTurnReport(BaseModel):
    """End-of-turn summary from the browser.

    Speech-to-text runs browser-to-AssemblyAI over a WebSocket, so the backend
    never sees it. Without this the most common cause of a bad voice answer —
    a misheard question — leaves no trace at all.
    """

    turn_id: str = Field(min_length=1, max_length=64)
    session_id: Optional[str] = Field(default=None, max_length=128)
    transcript: Optional[str] = Field(default=None, max_length=8000)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    audio_duration_ms: Optional[int] = Field(default=None, ge=0, le=600_000)
    tts_sentences: Optional[int] = Field(default=None, ge=0, le=200)
    tts_chars: Optional[int] = Field(default=None, ge=0, le=100_000)
    tts_ms: Optional[int] = Field(default=None, ge=0, le=600_000)


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
                with observe(
                    "tts-error",
                    trace_id=trace_id_for(body.turn_id) if body.turn_id else None,
                    input={"text": body.text},
                ) as span:
                    span.update(level="ERROR", status_message=str(chunk))
                flush_tracing()
                raise HTTPException(status_code=502, detail="TTS upstream error")
            yield chunk
        await fut

    return StreamingResponse(generate(), media_type="audio/mpeg")


@router.post("/voice/turn")
def voice_turn_report(body: VoiceTurnReport) -> dict:
    """Attach the browser-side legs of a voice turn to its existing trace.

    Seeding the trace id from `turn_id` joins these spans to the /chat turn
    that already ran, so one voice exchange reads as a single trace rather than
    three unrelated requests. Durations are recorded as metadata: the spans are
    created at report time, so their wall-clock is not the real timing.
    """
    trace_id = trace_id_for(body.turn_id)
    if trace_id is None:
        return {"accepted": False, "reason": "tracing disabled"}

    if body.transcript is not None or body.confidence is not None:
        with observe(
            "stt",
            trace_id=trace_id,
            session_id=body.session_id,
            input={"transcript": body.transcript},
            metadata={
                "confidence": body.confidence,
                "audio_duration_ms": body.audio_duration_ms,
                "provider": "assemblyai",
            },
        ) as span:
            # Low-confidence transcripts are the usual root cause of a bad
            # voice answer, so make the rate queryable rather than buried.
            if body.confidence is not None:
                span.score("stt_confidence", body.confidence)

    if body.tts_sentences is not None:
        with observe(
            "tts",
            trace_id=trace_id,
            session_id=body.session_id,
            metadata={
                "sentences": body.tts_sentences,
                "chars": body.tts_chars,
                "duration_ms": body.tts_ms,
                "provider": "openai",
            },
        ):
            pass

    flush_tracing()
    return {"accepted": True}
