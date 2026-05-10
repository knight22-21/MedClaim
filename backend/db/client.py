"""
MedClaim — Supabase Client

Provides a configured Supabase client singleton for use throughout
the backend. Uses the service role key for full table access (bypasses RLS).
"""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from backend.app.config import settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """
    Returns a cached Supabase client using the service role key.

    The service role key bypasses Row Level Security, allowing the
    backend to read/write all rows across all tables. This is
    intentional — RLS is enforced for direct client (dashboard) access,
    while the backend acts as a trusted service.

    Returns:
        Configured Supabase client instance.

    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is not set.
    """
    if not settings.SUPABASE_URL:
        raise ValueError("SUPABASE_URL is not configured. Check your .env file.")
    if not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY is not configured. Check your .env file.")

    return create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_SERVICE_ROLE_KEY,
    )


@lru_cache(maxsize=1)
def get_supabase_anon_client() -> Client:
    """
    Returns a cached Supabase client using the anon key.

    This client respects RLS policies and is used for operations
    that should be scoped to an authenticated user's permissions.

    Returns:
        Configured Supabase client instance with anon key.
    """
    if not settings.SUPABASE_URL:
        raise ValueError("SUPABASE_URL is not configured. Check your .env file.")
    if not settings.SUPABASE_ANON_KEY:
        raise ValueError("SUPABASE_ANON_KEY is not configured. Check your .env file.")

    return create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_ANON_KEY,
    )
