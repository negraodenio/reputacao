"""
SERP Occupation Strategy — Narrative Dominance Engine.

Gera plano operacional de ocupação de SERP para deslocamento
de resultados negativos via ativos controlados legítimos.

Heurísticas determinísticas resolvem ranking potential, velocidade e
dificuldade por tipo de ativo. O LLM apenas redige o plano estratégico.
"""
import re
from pathlib import Path
from services.openrouter_service import call_openrouter
from services.serpapi_service import search

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# ── Matrizes determinísticas ───────────────────────────────────────────────────

# Ranking potential: likelihood of occupying page-1 for branded queries
ASSET_RANKING: dict[str, str] = {
    "linkedin":                     "ALTO",
    "youtube":                      "ALTO",
    "wikipedia":                    "MUITO ALTO",
    "medium":                       "ALTO",
    "site_institucional":           "ALTO",
    "crunchbase":                   "ALTO",
    "entrevista_midia_setorial":    "MÉDIO",
    "entrevista_podcast":           "MÉDIO",
    "artigo_linkedin":              "ALTO",
    "biografia_executiva":          "ALTO",
    "perfil_institucional":         "ALTO",
    "esclarecimento_juridico":      "MÉDIO",
    "press_release":                "MÉDIO",
    "pdf_indexavel":                "BAIXO-MÉDIO",
    "afiliacao_universitaria":      "MÉDIO",
    "participacao_conferencia":     "MÉDIO",
}

# Ranking velocity: estimated days to influence branded search perception
ASSET_VELOCITY: dict[str, str] = {
    "linkedin":                     "3-7 dias",
    "youtube":                      "7-14 dias",
    "wikipedia":                    "14-30 dias",
    "medium":                       "2-5 dias",
    "site_institucional":           "7-14 dias",
    "crunchbase":                   "3-7 dias",
    "entrevista_midia_setorial":    "14-30 dias",
    "entrevista_podcast":           "14-21 dias",
    "artigo_linkedin":              "3-7 dias",
    "biografia_executiva":          "7-14 dias",
    "perfil_institucional":         "7-14 dias",
    "esclarecimento_juridico":      "7-14 dias",
    "press_release":                "7-21 dias",
    "pdf_indexavel":                "7-21 dias",
    "afiliacao_universitaria":      "14-30 dias",
    "participacao_conferencia":     "14-21 dias",
}

# Difficulty: operational effort required
ASSET_DIFFICULTY: dict[str, str] = {
    "linkedin":                     "BAIXA",
    "youtube":                      "MÉDIA",
    "wikipedia":                    "ALTA",
    "medium":                       "BAIXA",
    "site_institucional":           "BAIXA",
    "crunchbase":                   "BAIXA",
    "entrevista_midia_setorial":    "ALTA",
    "entrevista_podcast":           "MÉDIA",
    "artigo_linkedin":              "BAIXA",
    "biografia_executiva":          "BAIXA-MÉDIA",
    "perfil_institucional":         "BAIXA-MÉDIA",
    "esclarecimento_juridico":      "MÉDIA",
    "press_release":                "MÉDIA",
    "pdf_indexavel":                "BAIXA",
    "afiliacao_universitaria":      "ALTA",
    "participacao_conferencia":     "MÉDIA-ALTA",
}

# Impact: reputational effect when ranking
ASSET_IMPACT: dict[str, str] = {
    "artigo_linkedin":          "ALTO",
    "biografia_executiva":      "MÉDIO",
    "esclarecimento_juridico":  "CRÍTICO",
    "comunicado_imprensa":      "CRÍTICO",
    "faq_transparencia":        "ALTO",
    "site_institucional":       "ALTO",
    "perfil_institucional":     "MÉDIO",
    "medium":                   "MÉDIO",
    "youtube":                  "MÉDIO",
    "entrevista_midia_setorial": "ALTO",
    "entrevista_podcast":       "BAIXO",
    "wikipedia":                "ALTO",
}

ASSET_TIMING: dict[str, str] = {
    "esclarecimento_juridico":  "2-5 dias",
    "comunicado_imprensa":      "3-7 dias",
    "faq_transparencia":        "5-10 dias",
    "site_institucional":       "7-14 dias",
    "artigo_linkedin":          "3-7 dias",
    "biografia_executiva":      "7-14 dias",
    "perfil_institucional":     "7-14 dias",
    "medium":                   "7-14 dias",
    "youtube":                  "14-21 dias",
    "entrevista_midia_setorial": "14-30 dias",
    "entrevista_podcast":       "14-21 dias",
    "wikipedia":                "30-60 dias",
}

# Recommended sequence by threat level
OCCUPATION_SEQUENCE: dict[str, list[str]] = {
    # ── Default sequences (by threat level) ──────────────────────
    "CRITICAL": [
        "esclarecimento_juridico", "comunicado_imprensa",
        "site_institucional", "artigo_linkedin",
        "biografia_executiva", "youtube",
        "entrevista_midia_setorial", "perfil_institucional",
    ],
    "HIGH": [
        "artigo_linkedin", "site_institucional", "biografia_executiva",
        "perfil_institucional", "medium", "youtube",
    ],
    "MEDIUM": [
        "artigo_linkedin", "medium", "biografia_executiva",
        "perfil_institucional", "entrevista_podcast",
    ],
    "LOW": [
        "artigo_linkedin", "medium", "site_institucional",
        "perfil_institucional",
    ],
}

# ── Archetype-specific overrides ─────────────────────────────────
# These replace the default sequence when threat_archetype matches.
ARCHETYPE_SEQUENCE: dict[str, list[str]] = {
    "criminal": [
        "esclarecimento_juridico", "comunicado_imprensa",
        "faq_transparencia", "site_institucional",
        "perfil_institucional", "biografia_executiva",
        "artigo_linkedin", "entrevista_midia_setorial",
    ],
    "administrative": [
        "comunicado_imprensa", "site_institucional",
        "biografia_executiva", "artigo_linkedin",
        "perfil_institucional", "medium",
    ],
    "media": [
        "comunicado_imprensa", "artigo_linkedin",
        "site_institucional", "youtube",
        "entrevista_midia_setorial", "biografia_executiva",
        "perfil_institucional",
    ],
    "political": [
        "comunicado_imprensa", "site_institucional",
        "artigo_linkedin", "perfil_institucional",
        "entrevista_midia_setorial", "youtube",
        "biografia_executiva", "wikipedia",
    ],
    "association_based": [
        "esclarecimento_juridico", "faq_transparencia",
        "site_institucional", "biografia_executiva",
        "artigo_linkedin", "medium",
        "perfil_institucional",
    ],
}

# ── Phase labels for templates ────────────────────────────────────
PHASE_LABELS = {
    "criminal": {
        1: "FASE 1 — Contenção Jurídica",
        2: "FASE 2 — Estabilização Institucional",
        3: "FASE 3 — Reocupação de Autoridade",
    },
    "default": {
        1: "FASE 1 — Estabilização",
        2: "FASE 2 — Ocupação",
        3: "FASE 3 — Autoridade",
    },
}


def _clean(text: str) -> str:
    text = re.sub(r"[^\x00-\x7F\u00C0-\u024F\u1E00-\u1EFF\n]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _build_serp_context(serp_results: list[dict]) -> str:
    lines = []
    for r in serp_results:
        domain = re.sub(r"https?://(www\.)?", "", r.get("link", "")).split("/")[0]
        snippet = (r.get("snippet", "") or "")[:120]
        lines.append(
            f"#{r['position']} | {r['title'][:80]}\n"
            f"     Domínio: {domain} | Snippet: {snippet}"
        )
    return "\n".join(lines)


def generate_occupation(entity_name: str, threat_level: str = "",
                        intelligence: dict | None = None,
                        threat_archetype: str = "") -> dict:
    """
    Two modes:
    1. intelligence is None → auto-fetch all context live (standalone)
    2. intelligence is dict → use pre-extracted snapshot data (no API calls)
    """
    from services.expansion_service import expand_entity, format_expansion_context
    from services.constants import classify_domain
    from collections import Counter

    if intelligence is not None:
        # ── MODE 2: Snapshot inheritance ───────────────────────────
        serp_context = intelligence["serp_context"]
        neg_domains_str = intelligence["negative_domains_str"]
        negative_domains = intelligence.get("negative_domains_list", [])
        assoc_lines = intelligence["associations_str"]
        authority_vacuum = intelligence["authority_vacuum"]
        source_concentration = intelligence["source_concentration"]
        serp_results = intelligence.get("serp_results", [])
    else:
        # ── MODE 1: Live fetch ─────────────────────────────────────
        serp_results = search(entity_name)
        serp_context = _build_serp_context(serp_results)

        NEG_KW = ["fraude", "escândalo", "processo", "crise", "crime", "prisão",
                  "preso", "condenado", "investigação", "denúncia", "acusação",
                  "polêmica", "golpe", "fraud", "scandal", "criminal", "lawsuit"]
        negative_domains = []
        negative_count = 0
        for r in serp_results:
            snippet = (r.get("snippet", "") or "").lower()
            title = (r.get("title", "") or "").lower()
            if any(k in (snippet + " " + title) for k in NEG_KW):
                negative_count += 1
                domain = re.sub(r"https?://(www\.)?", "", r.get("link", "")).split("/")[0]
                if domain and domain not in negative_domains:
                    negative_domains.append(domain)

        neg_domains_str = ", ".join(negative_domains[:5]) if negative_domains else "Nenhum domínio negativo identificado."

        expansion = expand_entity(entity_name, serp_results, debug=False)
        assoc_lines = format_expansion_context(expansion)
        if "Nenhuma" in assoc_lines:
            assoc_lines = "Nenhuma associação crítica descoberta."

        if not threat_level:
            threat_level = "CRITICAL" if negative_count >= 5 else "HIGH" if negative_count >= 3 else "MEDIUM" if negative_count >= 1 else "LOW"

        controlled = sum(1 for r in serp_results
                         if classify_domain(
                             re.sub(r"https?://(www\.)?", "", r.get("link", "")).split("/")[0]
                         ) in ("institutional", "social"))
        authority_vacuum = "HIGH" if controlled == 0 else "MODERATE" if controlled <= 2 else "LOW"

        domain_counts = Counter()
        for r in serp_results:
            d = re.sub(r"https?://(www\.)?", "", r.get("link", "")).split("/")[0]
            domain_counts[d] += 1
        total = sum(domain_counts.values())
        top_domain, top_count = domain_counts.most_common(1)[0] if domain_counts else ("—", 0)
        source_concentration = "concentrated" if total > 0 and top_count / total > 0.5 else "distributed"

    # ── Deterministic asset table ──────────────────────────────────
    # Archetype-specific sequence overrides default threat-level sequence
    archetype_seq = ARCHETYPE_SEQUENCE.get(threat_archetype)
    if archetype_seq and threat_level in ("CRITICAL", "HIGH"):
        sequence = archetype_seq
    else:
        sequence = OCCUPATION_SEQUENCE.get(threat_level, OCCUPATION_SEQUENCE["MEDIUM"])

    phases = PHASE_LABELS.get(threat_archetype, PHASE_LABELS["default"])
    asset_table = []
    phase_size = max(1, len(sequence) // 3)
    for i, asset_key in enumerate(sequence[:8]):
        phase_num = (i // phase_size) + 1
        if phase_num == 1:
            timing = "7-14 dias"
        elif phase_num == 2:
            timing = "14-30 dias"
        else:
            timing = "30-60 dias"
        asset_table.append({
            "asset":      asset_key.replace("_", " ").title(),
            "rank":       i + 1,
            "phase":      phases.get(phase_num, f"FASE {phase_num}"),
            "timing":     ASSET_TIMING.get(asset_key, timing),
            "ranking":    ASSET_RANKING.get(asset_key, "MÉDIO"),
            "velocity":   ASSET_VELOCITY.get(asset_key, timing),
            "difficulty": ASSET_DIFFICULTY.get(asset_key, "MÉDIA"),
            "impact":     ASSET_IMPACT.get(asset_key, "MÉDIO"),
        })

    # ── Build and execute prompt ───────────────────────────────────
    prompt_template = (PROMPTS_DIR / "serp_occupation.txt").read_text(encoding="utf-8")
    prompt = prompt_template.format(
        entity_name            = entity_name,
        threat_level           = threat_level,
        authority_vacuum       = authority_vacuum,
        source_concentration   = source_concentration,
        negative_domains       = neg_domains_str,
        discovered_associations = assoc_lines,
        serp_context           = serp_context,
    )

    response = call_openrouter(prompt, temperature=0.4)
    raw = response["choices"][0]["message"]["content"]
    text = _clean(raw)

    return {
        "text":         text,
        "entity_name":  entity_name,
        "threat_level": threat_level,
        "threat_archetype": threat_archetype,
        "authority_vacuum":     authority_vacuum,
        "source_concentration": source_concentration,
        "negative_domains":     negative_domains,
        "serp_results": serp_results,
        "serp_context": serp_context,
        "asset_table":  asset_table,
    }


# ── Section parser ─────────────────────────────────────────────────────────────

OCCUPATION_SECTION_PATTERNS = [
    ("situacao_atual",      r"###\s+1\.\s+\**\s*SITUA[CÇ][AÃ]O ATUAL DO SERP\**"),
    ("mapa_ocupacao",       r"###\s+2\.\s+\**\s*MAPA DE OCUPA[CÇ][AÃ]O PRIORIT[ÁA]RIA\**"),
    ("deslocamento",        r"###\s+3\.\s+\**\s*ESTRAT[EÉ]GIA DE DESLOCAMENTO NARRATIVO\**"),
    ("dominio_entidades",   r"###\s+4\.\s+\**\s*DOM[ÍI]NIO DE ENTIDADES\**"),
    ("plano_ativos",        r"###\s+5\.\s+\**\s*PLANO DE ATIVOS CONTROLADOS\**"),
    ("distribuicao",        r"###\s+6\.\s+\**\s*ESTRAT[EÉ]GIA DE DISTRIBUI[CÇ][AÃ]O\**"),
    ("velocidade",          r"###\s+7\.\s+\**\s*VELOCIDADE DE RECUPERA[CÇ][AÃ]O\**"),
    ("war_room",            r"###\s+8\.\s+\**\s*WAR ROOM OPERACIONAL\**"),
]


def parse_occupation_sections(text: str) -> dict:
    boundaries = []
    for key, pattern in OCCUPATION_SECTION_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            boundaries.append((m.start(), m.end(), key))
    boundaries.sort()

    sections = {key: "" for key, _ in OCCUPATION_SECTION_PATTERNS}
    for i, (start, end, key) in enumerate(boundaries):
        next_start = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
        body = text[end:next_start].strip()
        body = re.sub(r"^\*\*[^*]+\*\*\s*$", "", body, flags=re.MULTILINE)
        body = re.sub(r"^---+\s*$", "", body, flags=re.MULTILINE)
        sections[key] = body.strip()
    return sections
