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
    Busca no Google via SerpAPI — retrocompatível com todos os callers existentes.

    Retorna apenas a lista de organic_results (igual ao comportamento original).
    Para acessar dados brutos (ai_overview, related_questions, etc.),
    use search_raw() diretamente.
    """
    raw = search_raw(query, num=num, start=0)
    return _extract_organic(raw)


def search_raw(query: str, num: int = 10, start: int = 0) -> dict:
    """
    Busca no Google via SerpAPI e retorna o JSON completo da resposta.

    Parâmetros:
        query: string de busca
        num:   resultados por página (max 10 para Google padrão)
        start: offset de paginação (0=p.1, 80=p.9, 90=p.10, 100=p.11)

    Retorna o dict raw com todos os campos SerpAPI:
        organic_results, ai_overview, related_questions, knowledge_graph, etc.

    Raises:
        RuntimeError: se todas as tentativas falharem
    """
    params = {
        "api_key": SERPAPI_API_KEY,
        "engine":  "google",
        "q":       query,
        "num":     num,
    }
    if start > 0:
        params["start"] = start

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
                    raise RuntimeError(f"SerpAPI quota esgotada: {msg}")
                last_error = RuntimeError(msg)
                _backoff(attempt)
                continue

            return data

        except RuntimeError:
            raise
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.warning(f"SerpAPI timeout/rede na tentativa {attempt}/{_MAX_RETRIES}: {e}")
            last_error = e
            _backoff(attempt)
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            logger.warning(f"SerpAPI HTTP {status} na tentativa {attempt}/{_MAX_RETRIES}")
            last_error = e
            if status == 429:
                _backoff(attempt, multiplier=4)
            elif status >= 500:
                _backoff(attempt)
            else:
                raise
        except Exception as e:
            logger.error(f"SerpAPI erro inesperado na tentativa {attempt}/{_MAX_RETRIES}: {e}")
            last_error = e
            _backoff(attempt)

    raise RuntimeError(f"SerpAPI falhou após {_MAX_RETRIES} tentativas: {last_error}")


def search_page(query: str, page: int) -> list[dict]:
    """
    Busca uma página específica do Google (1-based).

    Exemplos:
        search_page("João Silva", 9)  → resultados 81-90
        search_page("João Silva", 10) → resultados 91-100
        search_page("João Silva", 11) → resultados 101-110

    Retorna lista de organic_results com position corrigida globalmente.
    """
    if page < 1:
        raise ValueError("page deve ser >= 1")
    start = (page - 1) * 10
    raw = search_raw(query, num=10, start=start)
    results = _extract_organic(raw)

    # Corrige positions para serem globais (não reiniciam a cada página)
    global_offset = start
    for r in results:
        pos = r.get("position")
        if pos is not None:
            r["position"] = pos + global_offset
            r["page"] = page

    return results


def fetch_ai_overview_by_token(page_token: str) -> dict:
    """
    Resolve um AI Overview lazy-loaded via page_token.

    Deve ser chamado dentro de ~60s da busca original (o token expira).
    Retorna o dict completo do AI Overview ou {} em caso de falha.
    """
    params = {
        "api_key":    SERPAPI_API_KEY,
        "engine":     "google_ai_overview",
        "page_token": page_token,
    }
    try:
        response = httpx.get(SERPAPI_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            logger.warning(f"AI Overview token error: {data['error']}")
            return {}
        return data.get("ai_overview", {})
    except Exception as e:
        logger.warning(f"AI Overview token fetch falhou: {e}")
        return {}


def _extract_organic(raw: dict) -> list[dict]:
    """Extrai organic_results do raw dict SerpAPI."""
    results = []
    for item in raw.get("organic_results", []):
        results.append({
            "position": item.get("position"),
            "title":    item.get("title"),
            "link":     item.get("link"),
            "snippet":  item.get("snippet"),
        })
    return results


def _backoff(attempt: int, multiplier: int = 1) -> None:
    wait = _BACKOFF_BASE ** attempt * multiplier
    logger.info(f"SerpAPI aguardando {wait}s antes de retry...")
    time.sleep(wait)
