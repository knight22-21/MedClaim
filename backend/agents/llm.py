"""
MedClaim — Unified LLM Wrapper with Observability

Provides a robust interface for querying LLM models (Groq and Gemini)
with automatic fallback, token tracking, latency measurement, and
structured logging.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import redis.asyncio as redis_async  # type: ignore[import-untyped]
import structlog
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from backend.app.config import settings
from backend.llmops.metrics import LLM_CALL_LATENCY, LLM_TOKENS

# Setup structured logger
logger = structlog.get_logger("medclaim.llm")


class GroqRateLimiter:
    """
    Redis-backed rolling window rate limiter to prevent Groq 429 errors.
    Tracks tokens consumed in the last 60 seconds.
    """

    def __init__(self, limit: int = 5400, window_sec: int = 60):
        self.limit = limit
        self.window_sec = window_sec
        # Initialize redis client safely if url is provided
        try:
            url = settings.UPSTASH_REDIS_URL or os.getenv("REDIS_URL")
            if url and url.startswith("redis"):
                self.redis = redis_async.from_url(url, decode_responses=True)
            else:
                self.redis = None
                logger.warning(
                    "llm.rate_limiter.no_redis",
                    reason="No valid redis URL found. Using in-memory fallback is not implemented, rate limits are unmanaged.",
                )
        except Exception as e:
            self.redis = None
            logger.warning("llm.rate_limiter.init_failed", error=str(e))

    async def check_and_add(self, estimated_tokens: int) -> tuple[bool, int]:
        """
        Check if adding estimated_tokens exceeds the limit.
        If it does not, add the tokens to the sorted set.
        Returns (is_allowed, current_usage).
        """
        if not self.redis:
            return True, 0

        now_ms = int(time.time() * 1000)
        window_start_ms = now_ms - (self.window_sec * 1000)
        key = "groq_token_usage_window"

        try:
            # 1. Remove old entries outside the window
            await self.redis.zremrangebyscore(key, 0, window_start_ms)

            # 2. Get current token sum (zrange returning values, we sum them)
            # In Redis, zrange with WITHSCORES returns (value, score).
            # Our value needs to be unique, so we store "timestamp_random:tokens"
            entries = await self.redis.zrange(key, 0, -1)
            current_usage = sum([int(entry.split(":")[1]) for entry in entries if ":" in entry])

            if current_usage + estimated_tokens > self.limit:
                return False, current_usage

            # 3. Add new token prediction
            import uuid

            unique_val = f"{now_ms}_{uuid.uuid4().hex[:6]}:{estimated_tokens}"
            await self.redis.zadd(key, {unique_val: now_ms})

            # 4. Set TTL on the key to clean up automatically if idle
            await self.redis.expire(key, self.window_sec)

            return True, current_usage + estimated_tokens
        except Exception as e:
            logger.error("llm.rate_limiter.check_failed", error=str(e))
            return True, 0  # Fail open


# Global instance
rate_limiter = GroqRateLimiter()


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
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
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

    messages.append(HumanMessage(content=prompt))

    start_time = time.time()
    last_error = None

    # Step 1: Try preferred provider
    providers_to_try = [preferred_provider]
    if preferred_provider == "groq":
        providers_to_try.append("google")
    else:
        providers_to_try.append("groq")

    run_config = {}
    if tags or metadata:
        run_config = {"tags": tags or [], "metadata": metadata or {}}

    for provider in providers_to_try:
        try:
            if provider == "groq":
                if not settings.GROQ_API_KEY:
                    raise ValueError("GROQ_API_KEY is not configured")

                # Enforce Rate Limiting before calling Groq
                estimated_cost = (max_tokens or 1000) + int(len(prompt) / 4)
                allowed, current_usage = await rate_limiter.check_and_add(estimated_cost)
                if not allowed:
                    logger.warning(
                        "llm.rate_limit_exceeded",
                        provider="groq",
                        usage=current_usage,
                        limit=rate_limiter.limit,
                    )
                    raise RuntimeError(
                        "Groq RateLimitApproachingException: Circuit breaker open. Too many tokens used in last 60s."
                    )

                model_name = "llama-3.3-70b-versatile"
                logger.debug("llm.invoking", provider="groq", model=model_name, usage=current_usage)

                # Setup model
                model_kwargs = {}
                if json_mode:
                    model_kwargs["response_format"] = {"type": "json_object"}

                chat = ChatGroq(
                    api_key=settings.GROQ_API_KEY,
                    model=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    model_kwargs=model_kwargs,
                )

                # Execute query
                response = await chat.ainvoke(messages, config=run_config)
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
                        logger.warning(
                            "llm.json_parse_failed", provider="groq", error=str(json_err)
                        )

                logger.info("llm.success", provider="groq", model=model_name, latency_ms=latency)

                return {
                    "content": content,
                    "json": parsed_json,
                    "provider": "groq",
                    "model": model_name,
                    "latency_ms": latency,
                    **usage,
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

                response = await chat.ainvoke(messages, config=run_config)
                latency = int((time.time() - start_time) * 1000)

                LLM_CALL_LATENCY.labels(model=model_name, provider="google").observe(
                    latency / 1000.0
                )
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
                        logger.warning(
                            "llm.json_parse_failed", provider="google", error=str(json_err)
                        )

                logger.info("llm.success", provider="google", model=model_name, latency_ms=latency)

                return {
                    "content": content,
                    "json": parsed_json or {},
                    "provider": "google",
                    "model": model_name,
                    "latency_ms": latency,
                    **usage,
                }

        except Exception as err:
            logger.warning(
                "llm.provider_failed",
                provider=provider,
                error=str(err),
                next_action="trying fallback"
                if len(providers_to_try) > 1 and provider == providers_to_try[0]
                else "fail",
            )
            last_error = err

    raise RuntimeError(f"All LLM providers failed. Last error: {str(last_error)}")
