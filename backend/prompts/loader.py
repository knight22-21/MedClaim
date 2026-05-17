"""
MedClaim — Jinja2 Prompt Template Loader

Loads and renders versioned prompt templates from the
backend/prompts/templates/ directory.

Usage:
    from backend.prompts.loader import render_prompt

    prompt = render_prompt("code_audit", {
        "diagnosis_codes": [...],
        "procedure_codes": [...],
        "payer_name": "Medicare",
        "rag_context": "...",
    })
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

logger = logging.getLogger("medclaim.prompts.loader")

# Template directory
TEMPLATE_DIR = Path(__file__).parent / "templates"


def _get_env() -> Environment:
    """Create a Jinja2 environment with the templates directory."""
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        autoescape=False,  # Prompts are plain text, not HTML
    )


def render_prompt(template_name: str, context: dict[str, Any]) -> str:
    """
    Render a prompt template with the given context variables.

    Args:
        template_name: Name of the template file (without .j2 extension).
        context: Dict of variables to inject into the template.

    Returns:
        Rendered prompt string.

    Raises:
        FileNotFoundError: If the template doesn't exist.
    """
    env = _get_env()

    # Try with .j2 extension first
    try:
        template = env.get_template(f"{template_name}.j2")
    except TemplateNotFound:
        try:
            template = env.get_template(template_name)
        except TemplateNotFound:
            raise FileNotFoundError(
                f"Prompt template '{template_name}' not found in {TEMPLATE_DIR}"
            )

    rendered = template.render(**context)
    logger.debug(
        "prompt.rendered | template=%s char_count=%d context_keys=%s",
        template_name,
        len(rendered),
        list(context.keys()),
    )
    return rendered


def list_templates() -> list[str]:
    """List all available prompt templates."""
    if not TEMPLATE_DIR.exists():
        return []
    return [f.stem for f in TEMPLATE_DIR.glob("*.j2")]
