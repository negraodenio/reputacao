"""
Google News Distribution Engine — Release distribution for Google News indexed portals.

Google News is the fastest channel to appear on SERP (15-60 min) during crisis.
Top Stories box occupies positions 0-3 above organic results.

This module:
  - Maintains categorized portal list by sector + archetype
  - Generates formatted releases per portal
  - Integrates with PRWeb/MaxPress APIs (payload generation)
  - Generates pre-formatted emails for manual portals
  - Monitors indexing post-distribution
  - Computes News Occupation Score
"""
from datetime import datetime, timezone
from urllib.parse import urlparse
from services.constants import domain_authority


# ── PORTAL DATABASE ────────────────────────────────────────────────────────
# Categorized by sector, archetype suitability, and distribution method.

PORTALS = [
    # Negócios / Empresarial
    {"name": "Segs", "url": "segs.com.br", "sectors": ["business", "corporate"],
     "archetypes": ["corporate", "administrative", "association_based"],
     "method": "free", "speed": "15-30 min", "authority": 5,
     "instructions": "Cadastrar em segs.com.br/colaborar e submeter release via formulário. "
                     "Aceita texto com até 3000 caracteres + 1 foto."},
    {"name": "Mercado & Consumidor", "url": "mercadoeconsumo.com.br",
     "sectors": ["business", "consumer"],
     "archetypes": ["corporate", "media"],
     "method": "free", "speed": "30-60 min", "authority": 4,
     "instructions": "Enviar release para redacao@mercadoconsumo.com.br com título + lead + corpo + "
                     "dados do autor. Máximo 2500 caracteres."},
    {"name": "MaxPress", "url": "maxpress.com.br",
     "sectors": ["business", "general"],
     "archetypes": ["corporate", "media", "political"],
     "method": "paid_api", "speed": "15-30 min", "authority": 5,
     "instructions": "API disponível via plano pago. Enviar JSON com título, lead, corpo, "
                     "tags, categoria. Retorna URL da publicação em 15-30 min."},
    {"name": "Assessoria de Imprensa Online (AION)", "url": "aion.com.br",
     "sectors": ["general"],
     "archetypes": ["corporate", "media"],
     "method": "paid", "speed": "1-2h", "authority": 4,
     "instructions": "Plano pago. Submeter release via painel AION. Distribui para mailing próprio."},

    # Jurídico / Institucional
    {"name": "Migalhas", "url": "migalhas.com.br",
     "sectors": ["legal"],
     "archetypes": ["criminal", "administrative", "legal"],
     "method": "email", "speed": "1-24h", "authority": 6,
     "instructions": "Enviar release para pauta@migalhas.com.br. Título direto, máximo 2000 chars. "
                     "Incluir dados do advogado/escritório. Priorizam conteúdo jurídico."},
    {"name": "ConJur", "url": "conjur.com.br",
     "sectors": ["legal"],
     "archetypes": ["criminal", "administrative", "legal"],
     "method": "email", "speed": "1-24h", "authority": 7,
     "instructions": "Enviar release para redacao@conjur.com.br. Linguagem técnica-jurídica. "
                     "Mínimo 1500 caracteres. Incluir referência a dispositivos legais."},

    # Geral / Nacional
    {"name": "Brasil 247 (Branded)", "url": "brasil247.com.br",
     "sectors": ["general", "political"],
     "archetypes": ["political", "media"],
     "method": "paid", "speed": "1-4h", "authority": 6,
     "instructions": "Branded content pago. Contatar comercial@brasil247.com. "
                     "Conteúdo editorial com selo 'Conteúdo de Marca'."},

    # Distribuidores
    {"name": "PRWeb Brasil", "url": "prweb.com.br",
     "sectors": ["general"],
     "archetypes": ["corporate", "media", "political", "administrative"],
     "method": "paid_api", "speed": "15-60 min", "authority": 7,
     "instructions": "API REST disponível. Enviar release + metadados. Distribui para Google News, "
                     "Yahoo Finance, e centenas de portais parceiros. SLA de indexação: 15-60 min."},

    # Tecnologia / Startup
    {"name": "StartupBase", "url": "startupbase.com.br",
     "sectors": ["tech", "startup"],
     "archetypes": ["corporate"],
     "method": "free", "speed": "30-60 min", "authority": 3,
     "instructions": "Cadastrar perfil da empresa + submeter release no painel."},
]


def select_portals(archetype: str, sectors: list[str] | None = None, max_count: int = 4) -> list[dict]:
    """Select the best portals for a given archetype + sectors.

    Deterministic scoring:
      - Archetype match: +3
      - Sector match: +2
      - Authority: +1 per point
    Returns top `max_count` portals sorted by score.
    """
    scored = []
    for p in PORTALS:
        score = 0
        if archetype in p.get("archetypes", []):
            score += 3
        if sectors:
            for s in sectors:
                if s in p.get("sectors", []):
                    score += 2
        score += p.get("authority", 1)
        scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:max_count]]


def generate_release_payload(entity: str, release_text: str,
                              portal: dict, asset_type: str = "comunicado_imprensa") -> dict:
    """Generate the formatted payload for a specific portal.

    Returns dict with:
      - method: how to send (email / api / free / paid)
      - payload: formatted text or API JSON
      - instructions: portal-specific delivery instructions
    """
    method = portal.get("method", "email")

    # Truncate to portal limits
    max_chars = {"email": 2500, "paid_api": 5000, "free": 3000, "paid": 3000}
    limit = max_chars.get(method, 3000)
    text = release_text[:limit]

    if method == "paid_api":
        payload = {
            "title": text.split("\n")[0][:120] if text else f"Release - {entity}",
            "lead": (text.split("\n")[1] if len(text.split("\n")) > 1 else text)[:300],
            "body": text,
            "source": entity,
            "category": _portal_category(portal),
            "tags": [entity, asset_type],
        }
    else:
        payload = {
            "subject": f"Release: {entity} — {portal.get('name', '')}",
            "body": text,
            "to": portal.get("instructions", "").split(" ")[0] if "enviar" in portal.get("instructions", "").lower() else "",
        }

    return {
        "method": method,
        "portal": portal["name"],
        "portal_url": portal["url"],
        "payload": payload,
        "instructions": portal.get("instructions", ""),
        "estimated_speed": portal.get("speed", "N/A"),
        "expected_indexing": f"Indexação esperada em {portal.get('speed', 'N/A')}",
    }


def _portal_category(portal: dict) -> str:
    """Map portal sectors to GNews categories."""
    sectors = portal.get("sectors", [])
    if "legal" in sectors:
        return "Law & Government"
    if "business" in sectors or "corporate" in sectors:
        return "Business"
    if "tech" in sectors:
        return "Technology"
    if "political" in sectors:
        return "Politics"
    return "General"


def compute_news_occupation_score(news_articles: list[dict],
                                   distributed_releases: list[dict]) -> dict:
    """News Occupation Score (0-100).

    Measures how well the entity's narrative occupies Google News.

    Components:
      - Positive coverage share (30 pts): % of news that are positive
      - Controlled release presence (25 pts): releases indexed in top stories
      - Portal authority (20 pts): average authority of portals with positive coverage
      - Velocity (15 pts): how fast releases got indexed
      - Saturation (10 pts): breadth across different portals
    """
    total = len(news_articles) or 1
    pos = sum(1 for a in news_articles if a.get("sentiment") == "positive")
    neg = sum(1 for a in news_articles if a.get("sentiment") == "negative")

    # Positive coverage share (30 pts)
    pos_share = pos / total
    pos_score = round(pos_share * 30, 1)

    # Controlled release presence (25 pts)
    indexed = [r for r in distributed_releases if r.get("indexed")]
    indexed_score = min(len(indexed) * 5, 25)

    # Portal authority (20 pts)
    portal_auths = []
    for a in news_articles:
        if a.get("sentiment") == "positive":
            domain = a.get("domain", "") or urlparse(a.get("url", "")).netloc.replace("www.", "")
            portal_auths.append(domain_authority(domain))
    avg_auth = sum(portal_auths) / max(len(portal_auths), 1) if portal_auths else 0
    auth_score = round((avg_auth / 10) * 20, 1)

    # Velocity (15 pts) — releases indexed within 2h
    fast = sum(1 for r in distributed_releases
               if r.get("indexed") and r.get("indexing_time_minutes", 999) <= 120)
    velocity_score = min(fast * 5, 15)

    # Saturation (10 pts) — distinct portals with coverage
    portals_set = set()
    for a in news_articles:
        if a.get("sentiment") == "positive":
            portals_set.add(a.get("domain", ""))
    sat_score = min(len(portals_set) * 2, 10)

    total_score = min(pos_score + indexed_score + auth_score + velocity_score + sat_score, 100)

    return {
        "total": total_score,
        "breakdown": {
            "positive_coverage_share": {"score": pos_score, "max": 30, "raw": round(pos_share * 100, 1)},
            "controlled_releases":     {"score": indexed_score, "max": 25, "raw": len(indexed)},
            "portal_authority":        {"score": auth_score, "max": 20, "raw": round(avg_auth, 1)},
            "indexing_velocity":       {"score": velocity_score, "max": 15, "raw": fast},
            "portal_saturation":       {"score": sat_score, "max": 10, "raw": len(portals_set)},
        },
        "label": _news_label(total_score),
    }


def _news_label(score: float) -> str:
    if score >= 70:
        return "DOMINAÇÃO — Narrativa positiva ocupa o Google News"
    if score >= 45:
        return "OCUPAÇÃO PARCIAL — Presença positiva mas com espaço para crescimento"
    if score >= 20:
        return "PRESENÇA INICIAL — Releases começando a indexar"
    return "AUSENTE — Sem ocupação positiva no Google News"


def distribution_battle_section(archetype: str, sectors: list[str] | None = None) -> dict:
    """Generate the 'TOP STORIES WARFARE' section for the battle plan."""
    portals = select_portals(archetype, sectors)
    return {
        "present": len(portals) > 0,
        "selected_portals": [
            {"name": p["name"], "url": p["url"], "method": p["method"],
             "speed": p["speed"], "authority": p["authority"]}
            for p in portals
        ],
        "strategy_note": f"Distribuir release para {len(portals)} portais selecionados "
                         f"por arquétipo '{archetype}'. "
                         f"Priorizar envio via {' e '.join(p['name'] for p in portals[:2])} "
                         f"para indexação rápida (< 2h).",
        "recommended_actions": [
            "Gerar comunicado_imprensa no Content Studio",
            "Selecionar portais-alvo por arquétipo e setor",
            "Enviar release via API (PRWeb/MaxPress) para indexação em 15-60 min",
            "Enviar email formatado para portais sem API (ConJur, Migalhas)",
            "Monitorar indexação a cada 30 min após envio",
            "Se indexado: atualizar snapshot com resultado positivo no News",
        ],
    }
