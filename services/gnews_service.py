import os
import httpx
from dotenv import load_dotenv

load_dotenv()

GNEWS_API_KEY = os.environ["GNEWS_API_KEY"]
GNEWS_URL = "https://gnews.io/api/v4/search"


def fetch_news(query: str) -> list[dict]:
    """
    Fetches news articles for a given query.
    No language filter — reputation intelligence requires all-language coverage.
    """
    try:
        params = {
            "q": query,
            "max": 10,
            "apikey": GNEWS_API_KEY,
        }
        response = httpx.get(GNEWS_URL, params=params, timeout=30)
        response.raise_for_status()
        articles = response.json().get("articles", [])
        return [
            {
                "title":        a.get("title", ""),
                "url":          a.get("url", ""),
                "source":       a.get("source", {}).get("name", ""),
                "published_at": a.get("publishedAt", ""),
            }
            for a in articles
        ]
    except Exception:
        return []
