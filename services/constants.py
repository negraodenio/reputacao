"""
Shared domain constants — single source of truth for all services.
Update here, applies everywhere: audit_service, snapshot_service,
expansion_service, console.py.
"""

# ── Scraping priority / exclusion ─────────────────────────────────────────────

PRIORITY_DOMAINS: list[str] = [
    "wikipedia.org",
    "infomoney.com.br", "exame.com", "folha.uol.com.br", "oglobo.globo.com",
    "estadao.com.br", "uol.com.br", "bbc.com", "bbc.co.uk", "reuters.com",
    "valor.com.br", "valor.globo.com", "veja.abril.com.br", "isto.com.br",
    "conjur.com.br", "g1.globo.com", "cnnbrasil.com.br", "poder360.com.br",
    "metropoles.com", "gazetadopovo.com.br", "jota.info", "cartacapital.com.br",
]

EXCLUDED_DOMAINS: list[str] = [
    "instagram.com", "tiktok.com", "twitter.com", "x.com",
    "linkedin.com", "youtube.com", "facebook.com",
]

# ── Domain type classification ────────────────────────────────────────────────
# Used for NPA, snapshot sentiment, and source concentration analysis.
# Order matters: first match wins inside _classify_domain().

DOMAIN_TYPES: dict[str, list[str]] = {
    "mainstream": [
        # Nacional tier-1
        "folha.uol.com.br", "estadao.com.br", "oglobo.globo.com", "g1.globo.com",
        "uol.com.br", "cnnbrasil.com.br", "veja.abril.com.br", "exame.com",
        "infomoney.com.br", "valor.com.br", "valor.globo.com", "poder360.com.br",
        "r7.com", "terra.com.br", "band.uol.com.br", "cartacapital.com.br",
        "bbc.com", "bbc.co.uk", "reuters.com", "bloomberg.com", "ft.com",
        "wsj.com", "nytimes.com", "theguardian.com",
        # Regional tier-1 (alta autoridade)
        "gazetadopovo.com.br",    # Paraná
        "otempo.com.br",          # Minas Gerais
        "em.com.br",              # Estado de Minas
        "diariodepernambuco.com.br",
        "correiobraziliense.com.br",
        "acritica.com",           # Amazonas
        "agazeta.com.br",         # Espírito Santo
        "tribunadabahia.com.br",
        "correio24horas.com.br",
        "nhonline.com.br",
        "metropoles.com",
        "jornalcruzeiro.com.br",  # regional MG
        "tribunaonline.com.br",   # regional MG
        "diariodoabc.com.br",
        "noticiasdatv.com.br",
        "bnews.com.br",
        "noticias.uol.com.br",
    ],
    "legal": [
        "conjur.com.br", "jota.info", "migalhas.com.br", "jusbrasil.com.br",
        "stj.jus.br", "stf.jus.br", "tjsp.jus.br", "trf1.jus.br",
        "pgfn.gov.br", "cgu.gov.br", "offshorealert.com",
    ],
    "institutional": [
        "wikipedia.org", "gov.br", "bcb.gov.br", "cvm.gov.br",
        "anbima.com.br", "b3.com.br", "planalto.gov.br",
        "crunchbase.com", "linkedin.com",
    ],
    "social": [
        "instagram.com", "tiktok.com", "twitter.com", "x.com",
        "facebook.com", "youtube.com", "threads.net",
    ],
    "investigative": [
        "theintercept.com", "agenciapublica.org.br", "metropoles.com",
        "reporterbrasil.org.br", "offshorealert.com",
        "occrp.org",
    ],
}


def classify_domain(domain: str) -> str:
    """Returns the type of a domain. Falls back to 'blog' for unknowns."""
    d = domain.lower().replace("www.", "")
    for dtype, domains in DOMAIN_TYPES.items():
        if any(known in d for known in domains):
            return dtype
    return "blog"


# ── Domain authority weights ──────────────────────────────────────────────────
# Used by _parse_npa_struct in console.py to weight aggressiveness score.
# Higher = more authoritative / more reputationally damaging.

DOMAIN_AUTHORITY: dict[str, int] = {
    # Tier-1 nacional
    "folha.uol.com.br": 10, "estadao.com.br": 10, "oglobo.globo.com": 10,
    "g1.globo.com": 10, "veja.abril.com.br": 10, "cnnbrasil.com.br": 9,
    "valor.com.br": 9, "valor.globo.com": 9, "exame.com": 8,
    "poder360.com.br": 8, "uol.com.br": 8, "infomoney.com.br": 7,
    "cartacapital.com.br": 7, "r7.com": 6,
    # Internacional
    "reuters.com": 10, "bloomberg.com": 10, "ft.com": 10,
    "bbc.com": 9, "bbc.co.uk": 9, "wsj.com": 9, "nytimes.com": 9,
    "theguardian.com": 8,
    # Investigativo
    "theintercept.com": 8, "agenciapublica.org.br": 8, "occrp.org": 9,
    "offshorealert.com": 7, "reporterbrasil.org.br": 7,
    # Jurídico
    "conjur.com.br": 7, "jota.info": 7, "migalhas.com.br": 6,
    "jusbrasil.com.br": 6,
    # Regional
    "gazetadopovo.com.br": 6, "metropoles.com": 6, "correiobraziliense.com.br": 6,
    "otempo.com.br": 4, "em.com.br": 5, "tribunaonline.com.br": 3,
    "jornalcruzeiro.com.br": 3,
    # Institucional
    "wikipedia.org": 8, "crunchbase.com": 5,
}


def domain_authority(domain: str) -> int:
    """Returns authority weight (1-10). Default 2 for unknown domains."""
    d = domain.lower().replace("www.", "")
    for known, weight in DOMAIN_AUTHORITY.items():
        if known in d:
            return weight
    return 2
