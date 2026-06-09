"""Capture synthetic Google SERP screenshots using Playwright.

Em vez de acessar o Google real (bloqueado por CAPTCHA), renderiza uma página
HTML com os resultados SERP que já temos, estilizada como Google, e tira screenshot.
"""
from datetime import datetime, timezone
from pathlib import Path

SNAPSHOTS_DIR = Path(__file__).parent.parent / "snapshots"


def _build_serp_html(entity: str, results: list[dict]) -> str:
    rows = ""
    for r in results:
        pos = r.get("position", 0)
        title = r.get("title", "")
        link = r.get("link", "")
        snippet = r.get("snippet", "")
        domain = r.get("domain", "")
        rows += f"""
        <div class="g">
            <div class="r"><a href="{link}"><h3>{pos}. {title}</h3></a></div>
            <div class="cite">{domain}</div>
            <div class="s"><span class="st">{snippet}</span></div>
        </div>
        """
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>{entity} - Google Search</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family:Arial,sans-serif; background:#fff; color:#222; }}
  .bar {{ background:#f2f2f2; border-bottom:1px solid #e4e4e4; padding:20px 0 12px 160px; }}
  .bar h1 {{ font-size:16px; font-weight:normal; color:#545454; }}
  .bar h1 span {{ color:#c00; }}
  #main {{ max-width:652px; margin:16px 0 0 160px; }}
  .g {{ margin-bottom:24px; }}
  .r h3 {{ font-size:18px; font-weight:normal; color:#1a0dab; margin-bottom:2px; }}
  .cite {{ font-size:14px; color:#006621; margin-bottom:2px; }}
  .st {{ font-size:14px; color:#545454; line-height:1.58; word-wrap:break-word; }}
  .ad {{ background:#f0faf0; padding:4px 6px; font-size:10px; color:#888; display:inline-block; margin-bottom:4px; border:1px solid #ccc; }}
  .date {{ color:#888; font-size:12px; }}
</style></head>
<body>
<div class="bar"><h1>{entity} - <span>Pesquisa Google</span></h1></div>
<div id="main">{rows}</div>
</body></html>"""


async def capture_synthetic_serp(entity: str, results: list[dict]) -> bytes | None:
    """Render SERP results as a Google-like page and screenshot. Returns PNG bytes."""
    from playwright.async_api import async_playwright
    html = _build_serp_html(entity, results)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        try:
            await page.set_content(html, timeout=10000, wait_until="networkidle")
            await page.wait_for_timeout(500)
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(200)
            return await page.screenshot(full_page=True)
        except Exception:
            return None
        finally:
            await browser.close()


def screenshot_path(entity: str) -> tuple[Path, str]:
    slug = entity.lower().strip().replace(" ", "_")
    slug = "".join(c for c in slug if c.isalnum() or c in "_")
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return SNAPSHOTS_DIR / slug, f"serp_{date_str}.png"


def save_screenshot(entity: str, png: bytes) -> str | None:
    if not png:
        return None
    directory, fname = screenshot_path(entity)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / fname).write_bytes(png)
    return str((directory / fname).relative_to(SNAPSHOTS_DIR.parent))
