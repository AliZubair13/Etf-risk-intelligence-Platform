"""
LLM-based explanation generation.
Calls Groq (Llama 3.3 70B) with the strict evidence-grounded prompt.
This is the ONLY place in the entire platform where an LLM generates
free-form text. All numbers, rankings, and scores come from upstream
deterministic services (Phases 4-14).
"""
import logging
from groq import Groq
from app.config import settings
from app.services.explanation_payload_service import build_explanation_payload
from app.services.explanation_prompt_service import SYSTEM_PROMPT, build_explanation_prompt

logger = logging.getLogger(__name__)

_client = None


def get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def generate_explanation(investigation: dict) -> dict:
    """
    Generate the evidence-backed explanation for an investigation.
    Returns the generated text plus the payload used (for guardrail verification).
    """
    payload = build_explanation_payload(investigation)
    prompt = build_explanation_prompt(payload)

    client = get_client()

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,  # low temperature - we want grounded, not creative
            max_tokens=1400,
        )
        generated_text = response.choices[0].message.content

        return {
            "generated_text": generated_text,
            "payload_used": payload,
            "model": "openai/gpt-oss-120b",
            "error": None,
        }
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        return {
            "generated_text": None,
            "payload_used": payload,
            "model": "openai/gpt-oss-120b",
            "error": str(e),
        }
