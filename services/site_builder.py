"""
Site Builder — Gera site jornalístico estático profissional.
Pronto para deploy em Netlify, Vercel, GitHub Pages ou qualquer
hosting estático.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from datetime import datetime, timezone


def build_news_site(entity_name: str, articles: list[dict]) -> dict:
    """
    Gera um site jornalístico completo com os artigos produzidos.
    Retorna dict com nome dos arquivos e conteúdo HTML.

    articles: list of dicts from content_producer.produce_article()
    """
    files = {}
    slug = entity_name.lower().strip().replace(" ", "-").replace(".", "").replace(",", "")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # ── Homepage ──────────────────────────────────────────────────────
    articles_html = ""
    for i, a in enumerate(articles):
        base_slug = a.get("seo", {}).get("slug", "artigo-{}".format(i))
        asset_type = a.get("asset_type", "artigo-{}".format(i))
        art_slug = "{}-{}".format(base_slug, asset_type)
        label = a.get("label", "Artigo")
        seo_title = a.get("seo", {}).get("title", "Artigo")
        articles_html += """
        <article class="article-card">
          <div class="card-label">{label}</div>
          <h2><a href="/{slug}.html">{title}</a></h2>
          <p class="card-meta">Publicar em: {platform} &mdash; {time}</p>
        </article>
""".format(
            label=label,
            slug=art_slug,
            title=seo_title[:80],
            platform=a.get("platform", {}).get("platform", "—"),
            time=a.get("platform", {}).get("setup_time", "—"),
        )

    homepage = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{entity} — Reputation Intelligence</title>
  <style>
    * {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:#f8f8f8; color:#111; line-height:1.7; }}
    .page {{ max-width:900px; margin:0 auto; padding:48px 32px 80px; }}
    header {{ border-bottom:2px solid #111; padding-bottom:24px; margin-bottom:40px; }}
    .site-title {{ font-size:1.2rem; font-weight:700; text-transform:uppercase; letter-spacing:0.05em; color:#111; }}
    .site-desc {{ font-size:0.85rem; color:#666; margin-top:4px; }}
    h1 {{ font-size:2rem; font-weight:700; margin-bottom:8px; }}
    .article-card {{ background:#fff; border:1px solid #ddd; border-radius:6px; padding:24px; margin-bottom:16px; }}
    .card-label {{ font-size:0.7rem; font-weight:600; text-transform:uppercase; letter-spacing:0.1em; color:#888; margin-bottom:6px; }}
    .article-card h2 {{ font-size:1.15rem; margin-bottom:8px; }}
    .article-card h2 a {{ color:#111; text-decoration:none; }}
    .article-card h2 a:hover {{ text-decoration:underline; }}
    .card-meta {{ font-size:0.78rem; color:#888; }}
    footer {{ margin-top:48px; padding-top:16px; border-top:1px solid #ddd; font-size:0.78rem; color:#888; }}
  </style>
</head>
<body>
<div class="page">
  <header>
    <div class="site-title">{entity} &mdash; Narrative Intelligence</div>
    <div class="site-desc">Publica&ccedil;&atilde;o oficial de conte&uacute;do institucional e estrat&eacute;gico</div>
  </header>
  <h1>Artigos</h1>
  <p style="color:#888;margin-bottom:24px;">{count} artigos &middot; Gerado em {date}</p>
  {articles}
  <footer>
    <span>Gerado por CouncilIA &mdash; SERP Battle Planner</span>
  </footer>
</div>
</body>
</html>""".format(
        entity=entity_name,
        count=len(articles),
        date=now,
        articles=articles_html,
    )

    files["index.html"] = homepage

    # ── Individual article pages ───────────────────────────────────────
    for i, a in enumerate(articles):
        base_slug = a.get("seo", {}).get("slug", "artigo-{}".format(i))
        asset_type = a.get("asset_type", "artigo-{}".format(i))
        art_slug = "{}-{}".format(base_slug, asset_type)
        if art_slug in files:
            # Deduplicate by appending index
            art_slug = "{}-{}".format(art_slug, i)
        seo_title = a.get("seo", {}).get("title", "Artigo")
        seo_desc = a.get("seo", {}).get("meta_description", "")
        article_text = a.get("article", "")
        platform = a.get("platform", {})
        amplification = a.get("amplification", {})

        article_html = article_text.replace("\n", "</p><p>").replace("</p><p></p><p>", "</p><br><p>")

        page = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — {entity}</title>
  <meta name="description" content="{desc}">
  <style>
    * {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:#f8f8f8; color:#111; line-height:1.8; }}
    .page {{ max-width:750px; margin:0 auto; padding:48px 32px 80px; }}
    .back {{ display:inline-block; margin-bottom:24px; font-size:0.85rem; color:#888; text-decoration:none; }}
    .back:hover {{ color:#111; }}
    h1 {{ font-size:1.8rem; font-weight:700; margin-bottom:16px; }}
    .meta {{ font-size:0.78rem; color:#888; margin-bottom:24px; padding-bottom:16px; border-bottom:1px solid #ddd; }}
    .content p {{ margin-bottom:1.2em; font-size:1rem; color:#333; }}
    .publish-box {{ background:#f0f0f0; border:1px solid #ddd; border-radius:6px; padding:24px; margin-top:32px; }}
    .publish-box h3 {{ font-size:0.85rem; text-transform:uppercase; letter-spacing:0.08em; margin-bottom:12px; }}
    .publish-item {{ font-size:0.85rem; margin-bottom:6px; padding-left:14px; position:relative; }}
    .publish-item::before {{ content:'→'; position:absolute; left:0; color:#888; }}
    footer {{ margin-top:48px; padding-top:16px; border-top:1px solid #ddd; font-size:0.78rem; color:#888; }}
  </style>
</head>
<body>
<div class="page">
  <a href="/" class="back">&larr; Voltar</a>
  <h1>{title}</h1>
  <div class="meta">
    Publicar em: <strong>{platform}</strong> &middot; {setup}
  </div>
  <div class="content"><p>{article}</p></div>

  <div class="publish-box">
    <h3>Como Publicar</h3>
    {steps}
  </div>

  <div class="publish-box" style="margin-top:12px;">
    <h3>Como Amplificar</h3>
    <div class="publish-item"><strong>Estrat&eacute;gia:</strong> {amp_primary}</div>
    {amp_tactics}
    <div class="publish-item" style="margin-top:8px;"><strong>SEO Boost:</strong> {seo_boost}</div>
  </div>

  <footer>
    <span>CouncilIA &mdash; SERP Battle Planner</span>
  </footer>
</div>
</body>
</html>""".format(
            title=seo_title[:70],
            entity=entity_name,
            desc=seo_desc[:160].replace('"', "'"),
            article=article_html,
            platform=platform.get("platform", "—"),
            setup=platform.get("setup_time", "—"),
            steps="".join(
                '<div class="publish-item">{}</div>'.format(s)
                for s in platform.get("steps", [])
            ),
            amp_primary=amplification.get("primary", "—"),
            amp_tactics="".join(
                '<div class="publish-item">{}</div>'.format(t)
                for t in amplification.get("tactics", [])
            ),
            seo_boost=platform.get("seo_boost", "—"),
        )

        files["{}.html".format(art_slug)] = page

    # ── Generate deploy instructions ───────────────────────────────────
    files["_deploy_instructions.txt"] = """
SITE JORNALÍSTICO — {entity}
Gerado em: {date}

Para publicar:

1. Faça upload de TODOS os arquivos .html para um destes serviços:
   - Netlify (recomendado): arraste a pasta para app.netlify.com
   - Vercel: vercel.com --prod
   - GitHub Pages: crie repo, push, ative Pages
   - Qualquer hosting estático (S3, Firebase, Apache)

2. Aponte seu domínio (ex: entidade.com.br) para o hosting.

3. NO SEU BATTLE PLAN:
   - Use este site como landing page para TODAS as campanhas de Google Ads
   - Cada artigo é uma landing page pronta para campanha específica
   - A homepage serve como hub central de SEO

4. PRÓXIMOS PASSOS:
   - Adicionar Google Analytics
   - Adicionar Search Console
   - Submeter sitemap.xml
   - Criar perfis no Google Meu Negócio (se aplicável)

Arquivos gerados: {files}
""".format(
        entity=entity_name,
        date=now,
        files=", ".join(files.keys()),
    )

    return {
        "files": files,
        "count": len([k for k in files if k.endswith(".html") and k != "index.html"]) + 1,
        "entity": entity_name,
        "generated_at": now,
        "deploy_options": [
            {"name": "Netlify", "url": "https://app.netlify.com", "method": "Drag & drop folder"},
            {"name": "Vercel", "url": "https://vercel.com", "method": "vercel --prod"},
            {"name": "GitHub Pages", "url": "https://pages.github.com", "method": "Push to gh-pages branch"},
        ],
    }
