"""
MedClaim — Voice AI Tests

Tests for the STT transcription, intent classification,
query execution, and end-to-end voice processing logic.
"""

from __future__ import annotations

import base64
from unittest.mock import patch, MagicMock

import pytest

from backend.app.services.voice_service import (
    classify_intent,
    execute_query,
    generate_response,
    synthesize_speech,
    process_voice_query,
)


@pytest.mark.asyncio
class TestVoiceService:

    @patch("backend.app.services.voice_service.query_llm")
    async def test_classify_intent(self, mock_query_llm):
        """Test that user queries are correctly mapped to intents and entities."""
        mock_query_llm.return_value = {
            "json": {
                "intent": "CLAIM_STATUS",
                "extracted_entities": {"claim_id": "12345"}
            }
        }
        
        res = await classify_intent("What is the status of claim 12345?")
        assert res["intent"] == "CLAIM_STATUS"
        assert res["entities"]["claim_id"] == "12345"

    @patch("backend.app.services.voice_service.retrieve_with_scores")
    async def test_execute_query_coding(self, mock_retrieve):
        """Test RAG execution for coding questions."""
        class MockDoc:
            def __init__(self, content, metadata):
                self.page_content = content
                self.metadata = metadata

        mock_retrieve.return_value = [
            (MockDoc("Modifier 25 rules...", {"source": "CMS"}), 0.9)
        ]
        
        context, sources = await execute_query("CODING_QUESTION", {}, "What is modifier 25?")
        assert "Modifier 25 rules..." in context
        assert "CMS" in sources

    @patch("backend.app.services.voice_service.get_supabase_client")
    async def test_execute_query_analytics(self, mock_get_client):
        """Test database aggregate queries for analytics."""
        mock_db = MagicMock()
        mock_get_client.return_value = mock_db
        
        # Mock the chained supabase calls
        mock_table = mock_db.table.return_value
        mock_select = mock_table.select.return_value
        
        # We need to simulate the counts. We make the execute() return an object with a count property.
        class MockResult:
            def __init__(self, count):
                self.count = count
                
        # The execute method is called after gte/in_ or directly after select
        mock_db.table().select().gte().execute.return_value = MockResult(50)
        mock_db.table().select().in_().execute.return_value = MockResult(5)
        mock_db.table().select().execute.return_value = MockResult(100)
        
        context, sources = await execute_query("ANALYTICS", {}, "What's our denial rate?")
        assert "Total claims today" in context
        assert "Analytics DB" in sources

    @patch("backend.app.services.voice_service.query_llm")
    async def test_generate_response(self, mock_query_llm):
        """Test natural language response generation."""
        mock_query_llm.return_value = {"content": "The claim is approved."}
        
        res = await generate_response("Status?", "Claim is APPROVED.")
        assert res == "The claim is approved."

    @patch("backend.app.services.voice_service.gTTS")
    def test_synthesize_speech(self, mock_gtts):
        """Test TTS generation wraps correctly into a base64 string."""
        # Mock gTTS write_to_fp
        mock_instance = MagicMock()
        mock_gtts.return_value = mock_instance
        
        def fake_write(fp):
            fp.write(b"fake audio data")
            
        mock_instance.write_to_fp.side_effect = fake_write
        
        res = synthesize_speech("Hello")
        assert res.startswith("data:audio/mp3;base64,")
        
        # decode and verify
        b64_str = res.split(",")[1]
        decoded = base64.b64decode(b64_str)
        assert decoded == b"fake audio data"

    @patch("backend.app.services.voice_service.transcribe_audio")
    @patch("backend.app.services.voice_service.classify_intent")
    @patch("backend.app.services.voice_service.execute_query")
    @patch("backend.app.services.voice_service.generate_response")
    @patch("backend.app.services.voice_service.synthesize_speech")
    async def test_process_voice_query_audio(
        self, mock_tts, mock_gen, mock_exec, mock_class, mock_trans
    ):
        """Test full pipeline with audio input."""
        mock_trans.return_value = "Test query"
        mock_class.return_value = {"intent": "GENERAL", "entities": {}}
        mock_exec.return_value = ("Context", ["Source 1"])
        mock_gen.return_value = "Response text"
        mock_tts.return_value = "data:audio/mp3;base64,123"
        
        result = await process_voice_query(audio_bytes=b"audio data")
        
        assert result["transcription"] == "Test query"
        assert result["intent"] == "GENERAL"
        assert result["response_text"] == "Response text"
        assert result["audio_base64"] == "data:audio/mp3;base64,123"
        assert "Source 1" in result["sources"]
        
        mock_trans.assert_called_once_with(b"audio data", "audio.wav")

    @patch("backend.app.services.voice_service.classify_intent")
    @patch("backend.app.services.voice_service.execute_query")
    @patch("backend.app.services.voice_service.generate_response")
    @patch("backend.app.services.voice_service.synthesize_speech")
    async def test_process_voice_query_text(
        self, mock_tts, mock_gen, mock_exec, mock_class
    ):
        """Test full pipeline with text input (STT skipped)."""
        mock_class.return_value = {"intent": "GENERAL", "entities": {}}
        mock_exec.return_value = ("Context", [])
        mock_gen.return_value = "Response text"
        mock_tts.return_value = "data:audio/mp3;base64,123"
        
        result = await process_voice_query(audio_bytes=None, text_query="Direct text")
        
        assert result["transcription"] == "Direct text"
        mock_class.assert_called_once_with("Direct text")
