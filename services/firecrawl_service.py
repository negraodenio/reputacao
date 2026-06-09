import os
import time
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("councilia.firecrawl")

FIRECRAWL_API_KEY = os.environ["FIRECRAWL_API_KEY"]
FIRECRAWL_URL = "https://api.firecrawl.dev/v1/scrape"
MAX_CHARS = 15000

_MAX_RETRIES = 2
_BACKOFF_BASE = 2


def scrape(url: str) -> str:
    """
    Scrape de URL via Firecrawl com retry.
    Retorna string vazia em caso de falha — nunca levanta exceção
    (Firecrawl é melhor-esforço, não crítico para o audit).
    """
    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "url":     url,
        "formats": ["markdown"],
    }

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = httpx.post(
                FIRECRAWL_URL, json=payload, headers=headers, timeout=60
            )
            response.raise_for_status()
            text = response.json().get("data", {}).get("markdown", "")
            return text[:MAX_CHARS]

        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.warning(f"Firecrawl timeout ({url}) tentativa {attempt}/{_MAX_RETRIES}: {e}")
            if attempt < _MAX_RETRIES:
                time.sleep(_BACKOFF_BASE ** attempt)
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 429 and attempt < _MAX_RETRIES:
                logger.warning(f"Firecrawl rate limit ({url}), aguardando...")
                time.sleep(_BACKOFF_BASE ** attempt * 3)
            else:
                logger.warning(f"Firecrawl HTTP {status} ({url})")
                break
        except Exception as e:
            logger.warning(f"Firecrawl erro inesperado ({url}): {e}")
            break

    return ""
