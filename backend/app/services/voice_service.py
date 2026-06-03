"""
MedClaim — Voice AI Service

Implements the complete Voice AI backend pipeline:
1. Whisper STT (Groq API)
2. Query Classification (Groq LLM)
3. Data Retrieval (RAG or Supabase)
4. Response Generation (Gemini or Groq LLM)
5. Text-to-Speech (gTTS)
"""

from __future__ import annotations

import base64
import io
import json
import logging
from typing import Any

from groq import Groq
from gtts import gTTS
import structlog

from backend.app.config import settings
from backend.agents.llm import query_llm
from backend.rag.retrievers import retrieve_with_scores
from backend.db.client import get_supabase_client

logger = structlog.get_logger("medclaim.services.voice")


async def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    """Transcribe audio using Groq Whisper API."""
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not configured")

    logger.info("voice.stt.start", filename=filename, size_bytes=len(audio_bytes))
    
    # We use sync Groq client for whisper since there's no native async audio endpoint in the library
    # Or we can just use the sync client normally
    client = Groq(api_key=settings.GROQ_API_KEY)
    
    # Groq whisper requires file tuple: (filename, file_object)
    file_obj = io.BytesIO(audio_bytes)
    file_obj.name = filename
    
    try:
        transcription = client.audio.transcriptions.create(
            file=(filename, file_obj),
            model="whisper-large-v3",
            response_format="text",
        )
        # response_format="text" returns a string directly
        logger.info("voice.stt.complete", length=len(transcription))
        return transcription.strip()
    except Exception as e:
        logger.error("voice.stt.failed", error=str(e))
        raise RuntimeError(f"Speech-to-text failed: {str(e)}")


async def classify_intent(transcription: str) -> dict[str, Any]:
    """Classify the user's intent to route the query correctly."""
    system_prompt = (
        "You are an AI assistant for a medical billing system. "
        "Classify the user's voice query into one of these intents:\n"
        "- CLAIM_STATUS: Asking about a specific claim (needs claim ID or patient name).\n"
        "- CODING_QUESTION: Asking about CPT/ICD-10 codes, modifiers, or coding guidelines.\n"
        "- POLICY_QUESTION: Asking about specific insurance payer rules or coverage.\n"
        "- ANALYTICS: Asking about dashboard stats, denial rates, or volume.\n"
        "- GENERAL: Any other general greetings or questions.\n\n"
        "Return strict JSON with keys: 'intent' (string), 'extracted_entities' (dict of what you found like patient_name, claim_id, payer_name, code)."
    )
    
    res = await query_llm(
        prompt=transcription,
        system_prompt=system_prompt,
        preferred_provider="groq",
        json_mode=True,
        tags=["voice_ai", "intent_classification"],
    )
    
    json_data = res.get("json", {})
    return {
        "intent": json_data.get("intent", "GENERAL"),
        "entities": json_data.get("extracted_entities", {}),
    }


async def execute_query(intent: str, entities: dict, transcription: str) -> tuple[str, list[str]]:
    """Execute the data retrieval based on intent."""
    context = ""
    sources = []
    
    try:
        if intent == "CLAIM_STATUS":
            claim_id = entities.get("claim_id")
            patient = entities.get("patient_name")
            
            db = get_supabase_client()
            query = db.table("claims").select("*")
            if claim_id:
                query = query.eq("id", claim_id)
            elif patient:
                # Basic ilike search for patient name
                query = query.ilike("patient_name", f"%{patient}%")
            else:
                return "No claim ID or patient name identified in query.", []
                
            res = query.limit(3).execute()
            claims = res.data or []
            if not claims:
                context = "No matching claims found."
            else:
                context = "Found claims:\n" + json.dumps(claims, indent=2)
                sources = [f"Claim DB ({c['id']})" for c in claims]
                
        elif intent == "CODING_QUESTION":
            docs = retrieve_with_scores("coding_rules", transcription, top_k=3)
            if docs:
                context = "\n\n".join([d.page_content for d, _ in docs])
                sources = [d.metadata.get("source", "Coding Guidelines") for d, _ in docs]
            else:
                context = "No coding rules found matching the query."
                
        elif intent == "POLICY_QUESTION":
            docs = retrieve_with_scores("payer_policies", transcription, top_k=3)
            if docs:
                context = "\n\n".join([d.page_content for d, _ in docs])
                sources = [d.metadata.get("source", "Payer Policies") for d, _ in docs]
            else:
                context = "No payer policies found matching the query."
                
        elif intent == "ANALYTICS":
            db = get_supabase_client()
            # Just grab the basic summary stats
            today_res = db.table("claims").select("id", count="exact").gte("created_at", "today").execute()
            denied_res = db.table("claims").select("id", count="exact").in_("status", ["DENIED", "FINAL_DENIED"]).execute()
            all_res = db.table("claims").select("id", count="exact").execute()
            
            total_today = today_res.count or 0
            denied = denied_res.count or 0
            total_all = all_res.count or 1
            rate = round((denied / total_all) * 100, 1)
            
            context = f"Total claims today: {total_today}. Overall denial rate: {rate}%."
            sources = ["Analytics DB"]
            
        else:
            context = "General query. Use your base knowledge."
            
    except Exception as e:
        logger.error("voice.execute_query.failed", intent=intent, error=str(e))
        context = f"Error retrieving data: {str(e)}"
        
    return context, list(set(sources))


async def generate_response(transcription: str, context: str) -> str:
    """Generate conversational response using LLM."""
    system_prompt = (
        "You are an AI assistant for a medical billing dashboard. "
        "Answer the user's query conversationally and concisely, "
        "using the provided context. Do not use markdown formatting "
        "like asterisks or hashes, as this text will be spoken via TTS."
    )
    
    prompt = f"User Query: {transcription}\n\nContext Data:\n{context}"
    
    res = await query_llm(
        prompt=prompt,
        system_prompt=system_prompt,
        preferred_provider="groq",
        json_mode=False,
        tags=["voice_ai", "response_generation"],
    )
    return res.get("content", "I'm sorry, I couldn't generate a response.")


def synthesize_speech(text: str) -> str:
    """Synthesize speech using gTTS and return base64 encoded MP3."""
    logger.info("voice.tts.start", text_length=len(text))
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        encoded = base64.b64encode(fp.read()).decode('utf-8')
        logger.info("voice.tts.complete")
        return f"data:audio/mp3;base64,{encoded}"
    except Exception as e:
        logger.error("voice.tts.failed", error=str(e))
        return ""


async def process_voice_query(audio_bytes: bytes | None, filename: str = "audio.wav", text_query: str | None = None) -> dict[str, Any]:
    """
    Main pipeline for voice queries.
    If text_query is provided, skips STT.
    """
    # 1. STT
    if text_query:
        transcription = text_query
    elif audio_bytes:
        transcription = await transcribe_audio(audio_bytes, filename)
    else:
        raise ValueError("Must provide either audio_bytes or text_query")
        
    # 2. Intent Classification
    classification = await classify_intent(transcription)
    intent = classification["intent"]
    entities = classification["entities"]
    
    logger.info("voice.intent.classified", intent=intent, entities=entities)
    
    # 3. Data Retrieval
    context, sources = await execute_query(intent, entities, transcription)
    
    # 4. Response Generation
    response_text = await generate_response(transcription, context)
    
    # 5. TTS
    audio_data_uri = synthesize_speech(response_text)
    
    return {
        "transcription": transcription,
        "intent": intent,
        "response_text": response_text,
        "audio_base64": audio_data_uri,
        "sources": sources,
    }
