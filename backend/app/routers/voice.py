"""
MedClaim — Voice Router

Placeholder endpoints for the voice query interface.
Full implementation in Phase 3 (Whisper STT + Coqui TTS).

    POST /voice/query — Upload audio, get transcription + response + TTS audio
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, UploadFile, File

from backend.app.models.responses import APIResponse

logger = logging.getLogger("medclaim.routers.voice")

router = APIRouter(prefix="/voice", tags=["Voice AI"])


@router.post("/query", response_model=APIResponse)
async def voice_query(audio: UploadFile = File(...)) -> APIResponse:
    """
    Process a voice query from billing staff.

    Accepts: WAV/MP3 audio file upload
    Returns: Transcription, text response, and TTS audio URL

    Pipeline (Phase 3):
        1. Transcribe audio with Whisper
        2. Classify query type (CLAIM_STATUS, CODING, POLICY, ANALYTICS)
        3. Route to appropriate data source
        4. Generate text response
        5. Synthesize speech with Coqui XTTS-v2
        6. Return all three outputs
    """
    filename = audio.filename or "unknown"
    content_type = audio.content_type or "unknown"
    logger.info("voice.query.received | filename=%s content_type=%s", filename, content_type)

    # TODO: Phase 3 — Whisper transcription + query routing + Coqui TTS
    return APIResponse(
        success=True,
        data={
            "transcription": "(voice processing not yet implemented)",
            "response_text": "Voice interface will be available in Phase 3.",
            "audio_url": None,
            "query_type": "UNKNOWN",
        },
        message="Voice query received (processing not yet implemented)",
    )
