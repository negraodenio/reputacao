from pathlib import Path

# ---------------------------------------------------------------------------
# Prompt loader
# ---------------------------------------------------------------------------

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Public service function
# ---------------------------------------------------------------------------

def analyze_reputation(entity_name: str, context: str | None = None) -> dict:
    """
    Placeholder reputation analysis.
    Replace the body with real LLM calls when ready.
    """
    prompt_template = _load_prompt("reputation_analysis.txt")
    prompt = prompt_template.format(
        entity_name=entity_name,
        context=context or "no additional context provided",
    )

    # TODO: send `prompt` to LLM (OpenAI, Anthropic, etc.)
    # For now, return a stub response so the API is runnable immediately.
    return {
        "entity_name": entity_name,
        "score": None,
        "summary": f"[STUB] Reputation analysis for '{entity_name}' not yet implemented.",
        "raw": {"prompt_preview": prompt[:200]},
    }
