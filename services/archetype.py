"""
Threat Archetype & Crisis State classification.
Separates CRITICAL/HIGH into criminal, administrative, media, political,
corporate, or association-based — each with a different operational playbook.
"""

import re
from services.constants import classify_domain

# ── Criminal keywords ───────────────────────────────────────────
CRIMINAL_KW = [
    "prisão", "prisao", "preso", "condenado", "réu", "ré",
    "criminal", "penal", "sentença", "sentenca", "STF", "TRF",
    "juiz", "juíza", "desembargador", "ministro", "mandado",
    "busca e apreensão", "quebra de sigilo", "indiciado",
    "operação", "operaçao", "farra", "esquema", "fraude",
    "corrupção", "corrupcao", "lavagem", "propina",
    "inquérito", "inquerito", "investigação", "investigacao",
    "polícia", "policia", "delegacia", "PF", "federal",
]

ADMINISTRATIVE_KW = [
    "CGU", "TCU", "multa", "sanção", "sancao", "licitação",
    "licitacao", "improbidade", "administrativo", "contrato",
    "convênio", "convenio", "processo administrativo",
    "ressarcimento", "dano ao erário", "dano ao erario",
    "inelegível", "inelegivel", "impedimento",
]

MEDIA_KW = [
    "escândalo", "escandalo", "polêmica", "polemica",
    "controvérsia", "controversia", "crise", "repercussão",
    "repercussao", "viral", "exclusivo", "revelação",
    "revelacao", "explosivo", "exposição", "exposicao",
]

POLITICAL_KW = [
    "eleição", "eleicao", "candidato", "partido", "político",
    "politico", "senador", "deputado", "vereador", "prefeito",
    "governador", "ministro", "cargo público", "cargo publico",
    "mandato", "campanha", "eleitoral", "voto",
]

ASSOCIATION_KW = [
    "sócio", "socio", "sócia", "associado", "envolvido",
    "ligado", "relacionado", "vínculo", "vinculo",
    "conexão", "conexao", "parceiro", "parceria",
    "contratado", "contratante",
]


def classify_archetype(
    snapshot: dict,
    negative_signals_text: str = "",
) -> str:
    """
    Returns one of: criminal, administrative, media, political,
    corporate, association_based.
    Uses snapshot metrics + negative_signals LLM text.
    """
    neg_text = negative_signals_text.lower()
    momentum = snapshot.get("narrative_pressure", {}).get("momentum", "Stable")
    legal_cnt = snapshot.get("legal_domain_count", 0)
    neg_ratio = snapshot.get("page_1_negative_ratio", 0)
    top3_neg = snapshot.get("top_3_negative_count", 0)

    # Domain-based signals
    legal_domains_found = set()
    media_domains_found = False
    for r in snapshot.get("serp", []):
        dtype = r.get("type", classify_domain(r.get("domain", "")))
        if dtype == "legal":
            legal_domains_found.add(r.get("domain", ""))
        if dtype == "media":
            media_domains_found = True

    # ── Criminal ──────────────────────────────────────────
    criminal_score = 0
    if legal_cnt >= 1 or legal_domains_found:
        if any(k in neg_text for k in ["prisão", "preso", "condenado", "STF", "réu"]):
            criminal_score += 3
        if any(k in neg_text for k in CRIMINAL_KW):
            criminal_score += 2
        if top3_neg >= 1:
            criminal_score += 1

    if criminal_score >= 3 and (neg_ratio >= 0.3 or legal_cnt >= 1):
        return "criminal"

    # ── Administrative ─────────────────────────────────────
    admin_score = 0
    if any(k in neg_text for k in ADMINISTRATIVE_KW):
        admin_score += 2
    if legal_cnt >= 1 and not criminal_score >= 2:
        admin_score += 1
    if "CGU" in neg_text or "TCU" in neg_text:
        admin_score += 2

    if admin_score >= 2:
        return "administrative"

    # ── Media ──────────────────────────────────────────────
    media_score = 0
    if momentum == "Escalating":
        media_score += 2
    if any(k in neg_text for k in MEDIA_KW):
        media_score += 2
    if media_domains_found:
        media_score += 1

    if media_score >= 3:
        return "media"

    # ── Political ──────────────────────────────────────────
    if any(k in neg_text for k in POLITICAL_KW):
        return "political"

    # ── Association-based ──────────────────────────────────
    assocs = snapshot.get("expansion_associations", [])
    if len(assocs) >= 2 or any(k in neg_text for k in ASSOCIATION_KW):
        return "association_based"

    # ── Default ────────────────────────────────────────────
    return "corporate"


def classify_crisis_state(snapshot: dict) -> str:
    """
    Returns: active_crisis or structural_toxicity.
    """
    momentum = snapshot.get("narrative_pressure", {}).get("momentum", "Stable")
    count_7d = snapshot.get("narrative_pressure", {}).get("count_7d", 0)
    neg_ratio = snapshot.get("page_1_negative_ratio", 0)
    legal_cnt = snapshot.get("legal_domain_count", 0)

    # Active crisis: high recent volume + negative ratio + escalation
    if momentum == "Escalating" and count_7d >= 3 and neg_ratio >= 0.3:
        return "active_crisis"

    # If there's no news momentum but legal is persistent
    if legal_cnt >= 1 and count_7d == 0:
        return "structural_toxicity"

    # If there's high negativity but no recent activity
    if neg_ratio >= 0.3 and count_7d == 0:
        return "structural_toxicity"

    # Default
    if momentum == "Escalating" or count_7d >= 3:
        return "active_crisis"

    return "structural_toxicity" if legal_cnt >= 1 else "stable"


# ── Archetype descriptions in Portuguese ─────────────────────────

ARCHETYPE_LABELS = {
    "criminal":           "Criminal",
    "administrative":     "Administrativo",
    "media":              "Midiático",
    "political":          "Político",
    "corporate":          "Corporativo",
    "association_based":  "Associação Indireta",
}

ARCHETYPE_DESCRIPTIONS = {
    "criminal": (
        "Passivo judicial ativo com risco de prisão, sentença condenatória "
        "ou investigação criminal em andamento. Estratégia deve priorizar "
        "contenção jurídica antes de qualquer reposicionamento público."
    ),
    "administrative": (
        "Sanções administrativas, multas ou processos em órgãos de controle "
        "(CGU, TCU). Exige resposta institucional com ênfase em compliance "
        "e governança."
    ),
    "media": (
        "Crise impulsionada por cobertura midiática recente. Requer "
        "estratégia de velocidade: resposta rápida, distribuição ampla e "
        "controle narrativo."
    ),
    "political": (
        "Exposiçao em contexto político-eleitoral. O jogo é de coalizão, "
        "narrativa e posicionamento junto a stakeholders institucionais."
    ),
    "corporate": (
        "Risco predominantemente corporativo: mercado, concorrência ou "
        "governança. Estratégia de ocupação e construção de autoridade."
    ),
    "association_based": (
        "Risco por associação indireta a terceiros (sócios, contratos, "
        "relações empresariais). Exige desassociação documentada antes de "
        "qualquer reposicionamento."
    ),
}

CRISIS_STATE_LABELS = {
    "active_crisis":      "Crise Ativa",
    "structural_toxicity": "Toxicidade Estrutural",
    "stable":             "Estável",
}

CRISIS_STATE_DESCRIPTIONS = {
    "active_crisis": (
        "Alto volume recente de artigos com momentum crescente. "
        "Janela de resposta é de dias, não semanas. Prioridade absoluta "
        "para contenção."
    ),
    "structural_toxicity": (
        "Momentum midiático reduzido, mas passivos estruturais persistentes "
        "(investigações, processos, condenações arquivadas). Janela operacional "
        "aberta — ocupar antes do próximo ciclo."
    ),
    "stable": (
        "Sem crise ativa ou toxicidade estrutural identificada."
    ),
}
