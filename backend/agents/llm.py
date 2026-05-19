"""
MedClaim — Unified LLM Wrapper with Observability

Provides a robust interface for querying LLM models (Groq and Gemini)
with automatic fallback, token tracking, latency measurement, and
structured logging.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import structlog
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from backend.app.config import settings
from backend.llmops.metrics import LLM_CALL_LATENCY, LLM_TOKENS

# Setup structured logger
logger = structlog.get_logger("medclaim.llm")


def _extract_usage(response: Any, model: str) -> dict[str, int]:
    """Extract token usage information from LangChain response."""
    prompt_tokens = 0
    completion_tokens = 0

    try:
        # Check standard response_metadata
        meta = getattr(response, "response_metadata", {})
        if "token_usage" in meta:
            usage = meta["token_usage"]
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
        elif "usage_metadata" in getattr(response, "additional_kwargs", {}):
            usage = response.additional_kwargs["usage_metadata"]
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
        elif hasattr(response, "usage_metadata") and response.usage_metadata:
            prompt_tokens = response.usage_metadata.get("input_tokens", 0)
            completion_tokens = response.usage_metadata.get("output_tokens", 0)
    except Exception as e:
        logger.debug("llm.usage_extraction_failed", error=str(e))

    # Update Prometheus metrics
    if prompt_tokens > 0:
        LLM_TOKENS.labels(model=model, token_type="prompt").inc(prompt_tokens)
    if completion_tokens > 0:
        LLM_TOKENS.labels(model=model, token_type="completion").inc(completion_tokens)

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }


async def query_llm(
    prompt: str,
    system_prompt: str | None = None,
    preferred_provider: str = "groq",
    temperature: float = 0.1,
    max_tokens: int | None = None,
    json_mode: bool = True,
) -> dict[str, Any]:
    """
    Query an LLM provider (Groq or Google Gemini) with automatic fallback.

    Args:
        prompt: The main user prompt content.
        system_prompt: Optional system-level instructions.
        preferred_provider: "groq" or "google".
        temperature: Creative temperature (default 0.1 for high precision).
        max_tokens: Optional maximum tokens to output.
        json_mode: Whether to expect structured JSON output.

    Returns:
        Dict with keys:
            - "content": Raw string content
            - "json": Parsed dict if json_mode and parseable
            - "provider": Provider actually used ("groq" or "google")
            - "model": Model name used
            - "latency_ms": Latency in milliseconds
            - "prompt_tokens": Input tokens used
            - "completion_tokens": Output tokens used
    """
    messages: list[BaseMessage] = []
    if system_prompt:
        # LangChain Message structure
        from langchain_core.messages import SystemMessage
        messages.append(SystemMessage(content=system_prompt))
    
    from langchain_core.messages import HumanMessage
    messages.append(HumanMessage(content=prompt))

    start_time = time.time()
    last_error = None

    # Step 1: Try preferred provider
    providers_to_try = [preferred_provider]
    if preferred_provider == "groq":
        providers_to_try.append("google")
    else:
        providers_to_try.append("groq")

    for provider in providers_to_try:
        try:
            if provider == "groq":
                if not settings.GROQ_API_KEY:
                    raise ValueError("GROQ_API_KEY is not configured")
                
                model_name = "llama-3.3-70b-versatile"
                logger.debug("llm.invoking", provider="groq", model=model_name)
                
                # Setup model
                model_kwargs = {}
                if json_mode:
                    model_kwargs["response_format"] = {"type": "json_object"}

                chat = ChatGroq(
                    api_key=settings.GROQ_API_KEY,
                    model_name=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model_kwargs=model_kwargs,
                )
                
                # Execute query
                response = await chat.ainvoke(messages)
                latency = int((time.time() - start_time) * 1000)
                
                # Track metrics
                LLM_CALL_LATENCY.labels(model=model_name, provider="groq").observe(latency / 1000.0)
                usage = _extract_usage(response, model_name)
                
                content = response.content
                parsed_json = None
                if json_mode:
                    try:
                        parsed_json = json.loads(content)
                    except Exception as json_err:
                        logger.warning("llm.json_parse_failed", provider="groq", error=str(json_err))
                
                logger.info("llm.success", provider="groq", model=model_name, latency_ms=latency)
                
                return {
                    "content": content,
                    "json": parsed_json,
                    "provider": "groq",
                    "model": model_name,
                    "latency_ms": latency,
                    **usage
                }

            elif provider == "google":
                if not settings.GOOGLE_API_KEY:
                    raise ValueError("GOOGLE_API_KEY is not configured")

                model_name = "gemini-1.5-flash"
                logger.debug("llm.invoking", provider="google", model=model_name)

                chat = ChatGoogleGenerativeAI(
                    google_api_key=settings.GOOGLE_API_KEY,
                    model=model_name,
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )

                response = await chat.ainvoke(messages)
                latency = int((time.time() - start_time) * 1000)

                LLM_CALL_LATENCY.labels(model=model_name, provider="google").observe(latency / 1000.0)
                usage = _extract_usage(response, model_name)

                content = response.content
                parsed_json = None
                
                # Cleanup triple backticks sometimes returned by Google
                cleaned_content = content.strip()
                if cleaned_content.startswith("```json"):
                    cleaned_content = cleaned_content[7:]
                if cleaned_content.endswith("```"):
                    cleaned_content = cleaned_content[:-3]
                cleaned_content = cleaned_content.strip()

                if json_mode:
                    try:
                        parsed_json = json.loads(cleaned_content)
                    except Exception as json_err:
                        logger.warning("llm.json_parse_failed", provider="google", error=str(json_err))

                logger.info("llm.success", provider="google", model=model_name, latency_ms=latency)

                return {
                    "content": content,
                    "json": parsed_json or {},
                    "provider": "google",
                    "model": model_name,
                    "latency_ms": latency,
                    **usage
                }

        except Exception as err:
            logger.warning(
                "llm.provider_failed",
                provider=provider,
                error=str(err),
                next_action="trying fallback" if len(providers_to_try) > 1 and provider == providers_to_try[0] else "fail"
            )
            last_error = err

    raise RuntimeError(f"All LLM providers failed. Last error: {str(last_error)}")
