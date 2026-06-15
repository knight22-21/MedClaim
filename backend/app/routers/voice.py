"""
MedClaim — Voice Router

Placeholder endpoints for the voice query interface.
Full implementation in Phase 3 (Whisper STT + Coqui TTS).

    POST /voice/query — Upload audio, get transcription + response + TTS audio
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel

from backend.app.models.responses import APIResponse
from backend.app.services.voice_service import process_voice_query

logger = logging.getLogger("medclaim.routers.voice")

router = APIRouter(prefix="/voice", tags=["Voice AI"])





class TextQueryRequest(BaseModel):
    query: str


@router.post("/query", response_model=APIResponse)
async def voice_query(audio: UploadFile = File(...)) -> APIResponse:
    """
    Process a voice query from billing staff.

    Accepts: WAV/MP3 audio file upload
    Returns: Transcription, intent, text response, and base64 TTS audio
    """
    filename = audio.filename or "unknown"
    content_type = audio.content_type or "unknown"
    logger.info("voice.query.received | filename=%s content_type=%s", filename, content_type)

    try:
        audio_bytes = await audio.read()
        result = await process_voice_query(audio_bytes=audio_bytes, filename=filename)

        return APIResponse(
            success=True,
            data=result,
            message="Voice query processed successfully",
        )
    except Exception as e:
        logger.error("voice.query.failed | error=%s", str(e))
        return APIResponse(
            success=False,
            data={},
            message=str(e),
        )


@router.post("/text-query", response_model=APIResponse)
async def text_query(request: TextQueryRequest) -> APIResponse:
    """
    Process a text query (skips STT, useful for dashboard chat).
    Returns text response and base64 TTS audio.
    """
    logger.info("voice.text_query.received | length=%d", len(request.query))

    try:
        result = await process_voice_query(audio_bytes=None, text_query=request.query)

        return APIResponse(
            success=True,
            data=result,
            message="Text query processed successfully",
        )
    except Exception as e:
        logger.error("voice.text_query.failed | error=%s", str(e))
        return APIResponse(
            success=False,
            data={},
            message=str(e),
        )
