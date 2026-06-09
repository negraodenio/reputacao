import os
import time
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("councilia.openrouter")

OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = os.environ.get("COUNCILIA_LLM_MODEL", "deepseek/deepseek-r1-0528")
FALLBACK_MODEL = os.environ.get("COUNCILIA_LLM_FALLBACK", "openai/gpt-4o-mini")

_MAX_RETRIES = 3
_BACKOFF_BASE = 3


def call_openrouter(
    prompt: str,
    temperature: float = 0.7,
    model: str | None = None,
    max_tokens: int | None = None,
    system_prompt: str | None = None,
) -> dict:
    """
    Chama OpenRouter com retry automático e fallback de modelo.

    Parâmetros:
        model: modelo a usar (padrão: COUNCILIA_LLM_MODEL env var)
        max_tokens: limite de tokens de saída
        system_prompt: mensagem de sistema separada (garante idioma/tom)
    """
    active_model = model or DEFAULT_MODEL

    for m in [active_model, FALLBACK_MODEL]:
        result = _call_with_retry(prompt, temperature, m, max_tokens, system_prompt)
        if result is not None:
            return result
        if m != FALLBACK_MODEL:
            logger.warning(f"Modelo {m} falhou. Tentando fallback {FALLBACK_MODEL}...")

    raise RuntimeError(f"OpenRouter falhou em todos os modelos após {_MAX_RETRIES} tentativas cada.")


def _call_with_retry(
    prompt: str,
    temperature: float,
    model: str,
    max_tokens: int | None,
    system_prompt: str | None = None,
) -> dict | None:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }

    # Constrói messages com system prompt separado se fornecido
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload: dict = {
        "model":       model,
        "messages":    messages,
        "temperature": temperature,
    }
    if max_tokens:
        payload["max_tokens"] = max_tokens

    last_error: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = httpx.post(OPENROUTER_URL, json=payload, headers=headers, timeout=90)
            response.raise_for_status()
            data = response.json()

            # OpenRouter pode retornar erro no body com HTTP 200
            if "error" in data:
                err = data["error"]
                logger.warning(f"OpenRouter ({model}) erro no body tentativa {attempt}: {err}")
                last_error = RuntimeError(str(err))
                _backoff(attempt)
                continue

            return data

        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.warning(f"OpenRouter ({model}) timeout tentativa {attempt}/{_MAX_RETRIES}: {e}")
            last_error = e
            _backoff(attempt)
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            logger.warning(f"OpenRouter ({model}) HTTP {status} tentativa {attempt}/{_MAX_RETRIES}")
            last_error = e
            if status == 429:
                _backoff(attempt, multiplier=5)
            elif status >= 500:
                _backoff(attempt)
            else:
                return None  # 4xx permanente — tentar outro modelo
        except Exception as e:
            logger.error(f"OpenRouter ({model}) erro inesperado tentativa {attempt}: {e}")
            last_error = e
            _backoff(attempt)

    logger.error(f"OpenRouter ({model}) falhou após {_MAX_RETRIES} tentativas: {last_error}")
    return None


def _backoff(attempt: int, multiplier: int = 1) -> None:
    wait = _BACKOFF_BASE ** attempt * multiplier
    logger.info(f"OpenRouter aguardando {wait}s antes de retry...")
    time.sleep(wait)
