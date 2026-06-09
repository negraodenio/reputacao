import os
import time
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("councilia.serpapi")

SERPAPI_API_KEY = os.environ["SERPAPI_API_KEY"]
SERPAPI_URL = "https://serpapi.com/search"

_MAX_RETRIES = 3
_BACKOFF_BASE = 2  # segundos — dobra a cada tentativa: 2s, 4s, 8s


def search(query: str, num: int = 10) -> list[dict]:
    """
    Busca no Google via SerpAPI com retry automático (3 tentativas, backoff exponencial).

    Detecta explicitamente erros de quota no corpo da resposta JSON
    (SerpAPI retorna HTTP 200 com {"error": "..."} quando quota excedida).

    Raises:
        RuntimeError: se todas as tentativas falharem (para não silenciar falhas críticas)
    """
    params = {
        "api_key": SERPAPI_API_KEY,
        "engine":  "google",
        "q":       query,
        "num":     num,
    }

    last_error: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = httpx.get(SERPAPI_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            # SerpAPI retorna erro de quota no body mesmo com HTTP 200
            if "error" in data:
                msg = data["error"]
                logger.warning(f"SerpAPI erro na tentativa {attempt}/{_MAX_RETRIES}: {msg}")
                if "out of searches" in msg.lower() or "quota" in msg.lower():
                    # Quota esgotada — não adianta retry
                    raise RuntimeError(f"SerpAPI quota esgotada: {msg}")
                last_error = RuntimeError(msg)
                _backoff(attempt)
                continue

            results = []
            for item in data.get("organic_results", []):
                results.append({
                    "position": item.get("position"),
                    "title":    item.get("title"),
                    "link":     item.get("link"),
                    "snippet":  item.get("snippet"),
                })
            return results

        except RuntimeError:
            raise  # quota errors não fazem retry
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.warning(f"SerpAPI timeout/rede na tentativa {attempt}/{_MAX_RETRIES}: {e}")
            last_error = e
            _backoff(attempt)
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            logger.warning(f"SerpAPI HTTP {status} na tentativa {attempt}/{_MAX_RETRIES}")
            last_error = e
            if status == 429:
                _backoff(attempt, multiplier=4)  # rate limit — backoff mais agressivo
            elif status >= 500:
                _backoff(attempt)
            else:
                raise  # 4xx (exceto 429) não fazem retry
        except Exception as e:
            logger.error(f"SerpAPI erro inesperado na tentativa {attempt}/{_MAX_RETRIES}: {e}")
            last_error = e
            _backoff(attempt)

    raise RuntimeError(f"SerpAPI falhou após {_MAX_RETRIES} tentativas: {last_error}")


def _backoff(attempt: int, multiplier: int = 1) -> None:
    wait = _BACKOFF_BASE ** attempt * multiplier
    logger.info(f"SerpAPI aguardando {wait}s antes de retry...")
    time.sleep(wait)
