"""
SERP Battle Planner v2 — Inteligência de Deslocamento, Conteúdo e Anúncios.

Camadas adicionadas:
  - Displacement Difficulty (RECOVERABLE vs NON-DISPLACEABLE)
  - Organic Warfare × Paid Defense (separação explícita)
  - Search Intent Classification
  - Asset-to-Keyword Mapping por intent
  - Narrative Saturation
  - Owned Asset Gap
  - Recovery Probability
"""
from services.constants import domain_authority
from services.youtube_warfare import youtube_battle_section
from collections import Counter

# ═══════════════════════════════════════════════════════════════════════════
# 1. DISPLACEMENT DIFFICULTY MATRIX
# ═══════════════════════════════════════════════════════════════════════════

# Dificuldade de deslocamento por tipo de domínio + domínios específicos
DISPLACEMENT_DIFFICULTY: dict[str, dict] = {
    "EASY": {
        "label": "Recuperável — Baixo Esforço",
        "time": "7-30 dias",
        "time_range_days": (7, 30),
        "note": "Blogs, páginas antigas sem autoridade, conteúdo de baixo SEO. Outranking rápido com conteúdo próprio.",
        "domains": [],  # matched by type fallback
        "types": ["blog"],
    },
    "MEDIUM": {
        "label": "Recuperável — Esforço Moderado",
        "time": "30-90 dias",
        "time_range_days": (30, 90),
        "note": "Domínios regionais, YouTube, redes sociais, sites de média autoridade. Requer conteúdo consistente + SEO.",
        "domains": ["youtube.com", "instagram.com", "facebook.com", "twitter.com", "x.com",
                     "otempo.com.br", "em.com.br", "tribunaonline.com.br",
                     "metropoles.com", "gazetadopovo.com.br"],
        "types": ["social"],
    },
    "HARD": {
        "label": "Difícil — Esforço Alto",
        "time": "90-180 dias",
        "time_range_days": (90, 180),
        "note": "Veículos mainstream, Wikipedia, sites de grande autoridade. Requer campanha de ads + conteúdo institucional contínuo.",
        "domains": ["globo.com", "g1.globo.com", "oglobo.globo.com", "folha.uol.com.br",
                     "estadao.com.br", "uol.com.br", "veja.abril.com.br", "exame.com",
                     "cnnbrasil.com.br", "bbc.com", "reuters.com", "bloomberg.com",
                     "wikipedia.org", "linkedin.com", "poder360.com.br",
                     "correiobraziliense.com.br", "cartacapital.com.br"],
        "types": ["mainstream", "institutional"],
    },
    "VERY_HARD": {
        "label": "Não Deslocável — Permanente Estrutural",
        "time": "180-365+ dias (ou não deslocável)",
        "time_range_days": (180, 999),
        "note": "Registros legais permanentes, decisões judiciais, domínios governamentais. Impossível remover — requiere estratégia de convivência + supressão via ocupação de posições superiores.",
        "domains": ["stj.jus.br", "stf.jus.br", "jusbrasil.com.br", "conjur.com.br",
                     "jota.info", "migalhas.com.br", "gov.br", "cgu.gov.br",
                     "pgfn.gov.br", "planalto.gov.br", "offshorealert.com"],
        "types": ["legal", "investigative"],
    },
}

# Tática por nível de dificuldade
DIFFICULTY_TACTIC: dict[str, str] = {
    "EASY":       "content_outrank",
    "MEDIUM":     "seo_occupation",
    "HARD":       "outranking_ads",
    "VERY_HARD":  "suppression_strategy",
}

# Asset recomendado por nível de dificuldade
DIFFICULTY_ASSET: dict[str, str] = {
    "EASY":       "artigo_linkedin",
    "MEDIUM":     "perfil_institucional",
    "HARD":       "site_institucional",
    "VERY_HARD":  "esclarecimento_juridico",
}

# ═══════════════════════════════════════════════════════════════════════════
# 2. SEARCH INTENT CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════

SEARCH_INTENTS: dict[str, dict] = {
    "branded": {
        "label": "Branded",
        "description": "Pesquisa pelo nome da entidade. Intenção neutra ou positiva.",
        "keywords": ["{entity}"],
        "landing_page": "perfil_institucional, linkedin, wikipedia, biografia_executiva",
        "ads_priority": "ALTA",
    },
    "hostile": {
        "label": "Hostil",
        "description": "Nome + termos negativos (fraude, escândalo, crime). Alta intenção de due diligence.",
        "keywords": ["{entity} fraude", "{entity} escândalo", "{entity} crime",
                     "{entity} acusação", "{entity} processo"],
        "landing_page": "esclarecimento_juridico, faq_transparencia, comunicado_imprensa",
        "ads_priority": "CRÍTICA",
    },
    "institutional": {
        "label": "Institucional",
        "description": "Busca por empresa, site oficial, perfil corporativo.",
        "keywords": ["{entity} empresa", "{entity} site", "{entity} oficial",
                     "{entity} institucional", "{entity} perfil"],
        "landing_page": "site_institucional, perfil_institucional, linkedin",
        "ads_priority": "ALTA",
    },
    "crisis": {
        "label": "Crise",
        "description": "Nome + termos de crise aguda (prisão, condenação, investigação). Intenção urgente.",
        "keywords": ["{entity} prisão", "{entity} preso", "{entity} condenado",
                     "{entity} investigação", "{entity} denúncia"],
        "landing_page": "esclarecimento_juridico, comunicado_imprensa, nota_oficial",
        "ads_priority": "CRÍTICA",
    },
    "professional": {
        "label": "Profissional",
        "description": "Busca por carreira, LinkedIn, biografia, trajetória.",
        "keywords": ["{entity} linkedin", "{entity} carreira", "{entity} biografia",
                     "{entity} currículo", "quem é {entity}"],
        "landing_page": "linkedin, biografia_executiva, artigo_linkedin, medium",
        "ads_priority": "MÉDIA",
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# 3. ASSET-TO-KEYWORD MAPPING (por intent)
# ═══════════════════════════════════════════════════════════════════════════

ASSET_KEYWORD_MAP: dict[str, dict] = {
    "artigo_linkedin": {
        "intent": "professional",
        "keywords": ["{entity} linkedin", "{entity} carreira", "{entity} trajetória", "quem é {entity}"],
        "target_position": "#1-#3",
        "velocity": "3-7 dias",
    },
    "biografia_executiva": {
        "intent": ["professional", "branded"],
        "keywords": ["biografia {entity}", "quem é {entity}", "carreira {entity}", "{entity} história"],
        "target_position": "#1-#3",
        "velocity": "7-14 dias",
    },
    "perfil_institucional": {
        "intent": ["institutional", "branded"],
        "keywords": ["{entity} perfil", "{entity} empresa", "{entity} oficial", "{entity} institucional"],
        "target_position": "#1-#5",
        "velocity": "7-14 dias",
    },
    "site_institucional": {
        "intent": "institutional",
        "keywords": ["{entity} site oficial", "{entity} institucional", "{entity} empresa"],
        "target_position": "#1-#3",
        "velocity": "7-14 dias",
    },
    "comunicado_imprensa": {
        "intent": ["crisis", "hostile"],
        "keywords": ["{entity} comunicado", "{entity} nota oficial", "{entity} esclarecimento"],
        "target_position": "#3-#10",
        "velocity": "7-21 dias",
    },
    "esclarecimento_juridico": {
        "intent": ["crisis", "hostile"],
        "keywords": ["{entity} fraude", "{entity} processo", "{entity} investigação",
                     "{entity} explica", "{entity} versão", "{entity} defesa"],
        "target_position": "#1-#5",
        "velocity": "7-14 dias",
    },
    "faq_transparencia": {
        "intent": ["hostile", "crisis"],
        "keywords": ["{entity} transparência", "{entity} perguntas frequentes",
                     "{entity} compliance", "{entity} ética"],
        "target_position": "#3-#8",
        "velocity": "5-10 dias",
    },
    "medium": {
        "intent": "professional",
        "keywords": ["{entity} história", "{entity} carreira", "{entity} legado"],
        "target_position": "#3-#8",
        "velocity": "2-5 dias",
    },
    "entrevista_midia_setorial": {
        "intent": "institutional",
        "keywords": ["{entity} entrevista", "{entity} artigo", "{entity} opinião"],
        "target_position": "#5-#15",
        "velocity": "14-30 dias",
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# 4. ADS BUDGET MATRIX
# ═══════════════════════════════════════════════════════════════════════════

ADS_BUDGET_ESTIMATE = {
    "brand_defense":    {"monthly_min": 1500, "monthly_max": 5000,  "cpc_avg": "R$ 2-5",   "note": "Palavras de marca — CPC baixo, CTR alto. Essencial para defesa.", "intent": "branded"},
    "reputation_repair": {"monthly_min": 3000, "monthly_max": 8000,  "cpc_avg": "R$ 5-15",  "note": "Palavras de alto risco — CPC elevado por concorrência com veículos.", "intent": "hostile"},
    "content_distribution": {"monthly_min": 2000, "monthly_max": 6000, "cpc_avg": "R$ 3-8", "note": "Distribuição de conteúdo positivo (Medium, LinkedIn, site).", "intent": "professional"},
    "legal_counter":    {"monthly_min": 1000, "monthly_max": 3000,  "cpc_avg": "R$ 15-30", "note": "Palavras jurídicas — CPC alto, volume baixo. Público nichado.", "intent": "crisis"},
}

# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════


def build_battle_plan(serp: list[dict], clusters: list[dict],
                      score_data: dict, threat: str, archetype: str) -> dict:
    """
    Gera o plano operacional completo de guerra de SERP v2.
    Inclui difficulty, intent, organic × paid, saturation, asset gap, recovery prob.
    """
    negative_results = [r for r in serp if r.get("sentiment") == "negative"]
    neg_count = len(negative_results)
    total = len(serp) or 1
    neg_ratio = neg_count / total
    score = score_data.get("total", 50)

    # 1. Displacement targets com difficulty + recoverability
    displacement = _prioritize_v2(negative_results, clusters, threat)

    # 2. Organic warfare plan (SEO occupation)
    organic = _build_organic_warfare(displacement, threat)

    # 3. Paid defense plan (ads)
    paid = _build_paid_defense(threat, neg_ratio, score, organic["content_assets"])

    # 4. Narrative saturation
    saturation = _compute_narrative_saturation(serp, clusters)

    # 5. Owned asset gap
    asset_gap = _compute_owned_asset_gap(serp, threat)

    # 6. Recovery probability
    recovery = _estimate_recovery_probability(threat, neg_ratio, score, displacement,
                                               serp, asset_gap["current"], saturation)

    # 7. Timeline
    timeline = _build_timeline_v2(displacement, organic, paid)

    # 8. KPIs
    kpis = _project_kpis_v2(score, neg_ratio, neg_count, total, recovery)

    youtube_warfare = youtube_battle_section(serp)

    return {
        "summary": {
            "threat":          threat,
            "archetype":       archetype,
            "negative_count":  neg_count,
            "total_results":   total,
            "neg_share_pct":   round(neg_ratio * 100, 1),
            "serp_toxicity":   score,
        },
        "displacement":    displacement,
        "organic_warfare":  organic,
        "paid_defense":    paid,
        "youtube_warfare": youtube_warfare,
        "saturation":      saturation,
        "asset_gap":       asset_gap,
        "recovery":        recovery,
        "timeline":        timeline,
        "kpis":            kpis,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 1. DISPLACEMENT TARGETS v2 — com Difficulty + Recoverability
# ═══════════════════════════════════════════════════════════════════════════


def _classify_displacement_difficulty(domain: str, dtype: str) -> tuple[str, dict]:
    """Returns (difficulty_key, difficulty_dict) for a domain/type."""
    for level, config in DISPLACEMENT_DIFFICULTY.items():
        # Check specific domain first
        if any(d in domain for d in config["domains"]):
            return level, config
        # Then check type
        if dtype in config["types"]:
            return level, config
    # Default to MEDIUM
    return "MEDIUM", DISPLACEMENT_DIFFICULTY["MEDIUM"]


def _estimate_displacement_time(difficulty_key: str) -> str:
    return DISPLACEMENT_DIFFICULTY.get(difficulty_key, DISPLACEMENT_DIFFICULTY["MEDIUM"])["time"]


def _prioritize_v2(negative_results: list[dict],
                   clusters: list[dict], threat: str) -> list[dict]:
    """v2: prioriza com difficulty + recoverability + estimated time."""
    cluster_map = {c["domain"]: c for c in clusters}

    targets = []
    for r in negative_results:
        domain = r.get("domain", "unknown")
        pos = r.get("position", 99)
        auth = domain_authority(domain)
        dtype = r.get("type", "blog")
        cluster = cluster_map.get(domain, {})
        weighted = cluster.get("weighted_dominance", 0)

        pos_mult = 3.0 if pos <= 3 else 2.0 if pos <= 5 else 1.0
        priority = round(pos_mult * auth * (1 + weighted / 10), 1)

        diff_key, diff_config = _classify_displacement_difficulty(domain, dtype)
        is_recoverable = diff_key in ("EASY", "MEDIUM")
        is_hard = diff_key == "HARD"
        is_non_displaceable = diff_key == "VERY_HARD"

        tactic = DIFFICULTY_TACTIC.get(diff_key, "content_outrank")
        rec_asset = DIFFICULTY_ASSET.get(diff_key, "artigo_linkedin")
        if rec_asset == "site_institucional" and threat in ("MEDIUM", "LOW"):
            rec_asset = "artigo_linkedin"

        targets.append({
            "position":        pos,
            "domain":          domain,
            "title":           (r.get("title", "") or "")[:80],
            "type":            dtype,
            "authority":       auth,
            "weighted_dominance": weighted,
            "priority_score":  priority,
            "difficulty":      diff_key,
            "difficulty_label": diff_config["label"],
            "estimated_time":  diff_config["time"],
            "is_recoverable":  is_recoverable,
            "is_hard":         is_hard,
            "is_non_displaceable": is_non_displaceable,
            "tactic":          tactic,
            "recommended_asset": rec_asset,
            "note":            diff_config["note"],
            "ads_required":    diff_key in ("HARD", "VERY_HARD"),
        })

    targets.sort(key=lambda x: x["priority_score"], reverse=True)
    return targets


# ═══════════════════════════════════════════════════════════════════════════
# 2. ORGANIC WARFARE — SEO Occupation + Content Matrix
# ═══════════════════════════════════════════════════════════════════════════


def _build_organic_warfare(displacement: list[dict], threat: str) -> dict:
    """Gera plano de guerra orgânica (SEO) separado de ads.
    Inclui asset-to-keyword mapping por intent."""
    used_assets: set = set()
    content_assets = []

    for t in displacement:
        asset = t["recommended_asset"]
        if asset not in used_assets:
            used_assets.add(asset)
            mapping = ASSET_KEYWORD_MAP.get(asset, {})
            intent_key = mapping.get("intent", "branded")
            if isinstance(intent_key, list):
                intent_key = intent_key[0]
            intent_info = SEARCH_INTENTS.get(intent_key, SEARCH_INTENTS["branded"])
            kw = mapping.get("keywords", ["{entity}"])
            target_pos = mapping.get("target_position", "#5")
            velocity = mapping.get("velocity", "7-14 dias")

            content_assets.append({
                "asset":            asset,
                "label":            asset.replace("_", " ").title(),
                "intent":           intent_info["label"],
                "intent_description": intent_info["description"],
                "tactic":           t["tactic"],
                "targets_domain":   t["domain"],
                "target_position":  target_pos,
                "seo_keywords":     kw,
                "velocity":         velocity,
                "difficulty":       t["difficulty"],
                "estimated_time":   t["estimated_time"],
                "is_non_displaceable": t["is_non_displaceable"],
            })

    # Fill remaining slots
    remaining = [a for a, m in ASSET_KEYWORD_MAP.items() if a not in used_assets]
    filler_count = 4 if threat in ("CRITICAL", "HIGH") else 2
    for asset in remaining[:filler_count]:
        mapping = ASSET_KEYWORD_MAP.get(asset, {})
        intent_key = mapping.get("intent", "branded")
        if isinstance(intent_key, list):
            intent_key = intent_key[0]
        intent_info = SEARCH_INTENTS.get(intent_key, SEARCH_INTENTS["branded"])
        kw = mapping.get("keywords", ["{entity}"])
        target_pos = mapping.get("target_position", "#5")
        velocity = mapping.get("velocity", "7-14 dias")

        content_assets.append({
            "asset":            asset,
            "label":            asset.replace("_", " ").title(),
            "intent":           intent_info["label"],
            "intent_description": intent_info["description"],
            "tactic":           "preventive_occupation",
            "targets_domain":   "—",
            "target_position":  target_pos,
            "seo_keywords":     kw,
            "velocity":         velocity,
            "difficulty":       "—",
            "estimated_time":   velocity,
            "is_non_displaceable": False,
        })

    # Intent matrix: summary of all intents targeted
    intent_matrix = {}
    for c in content_assets:
        intent = c["intent"]
        if intent not in intent_matrix:
            intent_matrix[intent] = {"intent": intent, "assets": [], "landing_pages": set()}
        intent_matrix[intent]["assets"].append(c["label"])
        lp = SEARCH_INTENTS.get(intent.lower(), {}).get("landing_page", "")
        for p in lp.split(", "):
            intent_matrix[intent]["landing_pages"].add(p.strip())
    for v in intent_matrix.values():
        v["landing_pages"] = list(v["landing_pages"])

    # Recoverable vs non-displaceable summary
    recoverable = [t for t in displacement if t["is_recoverable"]]
    hard = [t for t in displacement if t["is_hard"]]
    permanent = [t for t in displacement if t["is_non_displaceable"]]

    return {
        "strategy_note": _organic_strategy_note(threat, displacement),
        "content_assets": content_assets,
        "intent_matrix": list(intent_matrix.values()),
        "recoverable_count": len(recoverable),
        "hard_count": len(hard),
        "permanent_count": len(permanent),
        "recoverable_targets": recoverable,
        "permanent_targets": permanent,
    }


def _organic_strategy_note(threat: str, displacement: list[dict]) -> str:
    recoverable = sum(1 for t in displacement if t["is_recoverable"])
    permanent = sum(1 for t in displacement if t["is_non_displaceable"])
    total = len(displacement) or 1
    rec_pct = round(recoverable / total * 100)
    if rec_pct >= 70:
        return "Maioria dos resultados negativos é recuperável via SEO + conteúdo próprio. Foco em produção de conteúdo de alta qualidade e otimização on-page."
    if permanent > 0:
        return "{} resultados são registros permanentes (legal, governamental). Estratégia de convivência + supressão via ocupação de posições superiores com anúncios.".format(permanent)
    return "Mix de dificuldades. Combinar conteúdo rápido (LinkedIn, Medium) com conteúdo de profundidade (site, FAQ) e anúncios direcionados."


# ═══════════════════════════════════════════════════════════════════════════
# 3. PAID DEFENSE — Google Ads Campaigns
# ═══════════════════════════════════════════════════════════════════════════


def _build_paid_defense(threat: str, neg_ratio: float,
                        score: float, content_assets: list[dict]) -> dict:
    """Gera campanhas de anúncio separadas por intent."""
    campaigns = []

    # Brand defense — sempre
    brand = dict(ADS_BUDGET_ESTIMATE["brand_defense"])
    brand.update({
        "name": "Defesa de Marca",
        "focus": "Proteger branded search — impedir que termos de marca sejam ocupados por resultados negativos",
        "keywords": ["{entity}", "{entity} site", "{entity} perfil", "{entity} oficial"],
        "intent_key": "branded",
        "intent": SEARCH_INTENTS["branded"]["label"],
        "landing_pages": ["site_institucional", "perfil_institucional", "biografia_executiva"],
    })
    campaigns.append(brand)

    # Reputation repair — CRITICAL/HIGH ou neg_ratio >= 0.4
    if threat in ("CRITICAL", "HIGH") or neg_ratio >= 0.4:
        rep = dict(ADS_BUDGET_ESTIMATE["reputation_repair"])
        rep.update({
            "name": "Reparo Reputacional",
            "focus": "Due diligence defense — ocupar pesquisas de alto risco com conteúdo institucional",
            "keywords": ["{entity} fraude", "{entity} processo", "{entity} investigação",
                         "{entity} crime", "{entity} escândalo", "{entity} acusação"],
            "intent_key": "hostile",
            "intent": SEARCH_INTENTS["hostile"]["label"],
            "landing_pages": ["esclarecimento_juridico", "faq_transparencia", "comunicado_imprensa"],
        })
        campaigns.append(rep)

    # Content distribution — CRITICAL/HIGH/MEDIUM
    if threat in ("CRITICAL", "HIGH", "MEDIUM"):
        cd = dict(ADS_BUDGET_ESTIMATE["content_distribution"])
        content_lps = [c["asset"] for c in content_assets[:4]] or ["artigo_linkedin", "medium"]
        cd.update({
            "name": "Distribuição de Conteúdo Positivo",
            "focus": "Amplificar ativos controlados — empurrar LinkedIn, Medium, biografia para posições superiores",
            "keywords": ["{entity} artigo", "{entity} entrevista", "{entity} carreira",
                         "{entity} história", "{entity} trajetória", "{entity} opinião"],
            "intent_key": "professional",
            "intent": SEARCH_INTENTS["professional"]["label"],
            "landing_pages": content_lps,
        })
        campaigns.append(cd)

    # Legal counter — CRITICAL only
    if threat == "CRITICAL":
        lc = dict(ADS_BUDGET_ESTIMATE["legal_counter"])
        lc.update({
            "name": "Contra-Narrativa Jurídica",
            "focus": "Deslocar JusBrasil/ConJur — ocupar consultas jurídicas com conteúdo de defesa institucional",
            "keywords": ["{entity} justiça", "{entity} defesa", "{entity} direito",
                         "{entity} advogado", "{entity} STF"],
            "intent_key": "crisis",
            "intent": SEARCH_INTENTS["crisis"]["label"],
            "landing_pages": ["esclarecimento_juridico", "faq_transparencia"],
        })
        campaigns.append(lc)

    total_min = sum(c["monthly_min"] for c in campaigns)
    total_max = sum(c["monthly_max"] for c in campaigns)

    # Classify campaigns into paid defense roles
    for c in campaigns:
        if c["intent_key"] in ("branded", "professional"):
            c["role"] = "SEO Amplification"
        else:
            c["role"] = "Crisis Containment"

    return {
        "campaigns": campaigns,
        "total_monthly_budget_min": total_min,
        "total_monthly_budget_max": total_max,
        "strategy_note": _paid_strategy_note(threat, neg_ratio, score),
        "defense_role_summary": _defense_role_summary(campaigns),
    }


def _paid_strategy_note(threat: str, neg_ratio: float, score: float) -> str:
    if score >= 70 or threat == "CRITICAL":
        return "OFENSIVA TOTAL: Ativar todas as campanhas. Ads são a única via rápida para conter dano em cenário crítico. Prioridade máxima para reparo reputacional + conteúdo."
    if score >= 40 or threat == "HIGH":
        return "DEFESA ATIVA: Brand defense + distribuição de conteúdo para reduzir toxicidade. Se neg_ratio > 40%, ativar reparo reputacional."
    return "PREVENÇÃO: Brand defense + conteúdo positivo para manter controle. Sem campanhas de crise — foco em SEO amplification."


def _defense_role_summary(campaigns: list[dict]) -> dict:
    amp = [c for c in campaigns if c.get("role") == "SEO Amplification"]
    crisis = [c for c in campaigns if c.get("role") == "Crisis Containment"]
    return {
        "seo_amplification": {
            "count": len(amp),
            "budget_min": sum(c["monthly_min"] for c in amp),
            "budget_max": sum(c["monthly_max"] for c in amp),
        },
        "crisis_containment": {
            "count": len(crisis),
            "budget_min": sum(c["monthly_min"] for c in crisis),
            "budget_max": sum(c["monthly_max"] for c in crisis),
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# 4. NARRATIVE SATURATION
# ═══════════════════════════════════════════════════════════════════════════


def _compute_narrative_saturation(serp: list[dict], clusters: list[dict]) -> list[dict]:
    """
    Calcula saturação narrativa por domínio.
    HIGH = muitos resultados + top positions + alta autoridade
    """
    total = len(serp) or 1
    saturation_results = []
    for c in clusters:
        domain = c["domain"]
        count = c["total"]
        positions = c.get("positions", [])
        auth = c.get("authority", 2)
        avg_pos = sum(positions) / max(len(positions), 1) if positions else 99
        neg_pct = c.get("neg_pct", 0)

        # Saturation score: count × authority / avg_position
        sat = round((count * auth) / max(avg_pos, 1), 1)

        if sat >= 5:
            level = "HIGH"
        elif sat >= 2:
            level = "MEDIUM"
        else:
            level = "LOW"

        saturation_results.append({
            "domain": domain,
            "count": count,
            "authority": auth,
            "avg_position": round(avg_pos, 1),
            "neg_pct": neg_pct,
            "saturation_score": sat,
            "saturation_level": level,
            "note": _saturation_note(level, domain, count, auth),
        })

    saturation_results.sort(key=lambda x: x["saturation_score"], reverse=True)
    return saturation_results


def _saturation_note(level: str, domain: str, count: int, auth: int) -> str:
    if level == "HIGH":
        return "Saturação alta — {} resultados x autoridade {}. Deslocamento requer múltiplas frentes e orçamento de ads.".format(count, auth)
    if level == "MEDIUM":
        return "Saturação média — deslocamento viável com conteúdo consistente + SEO."
    return "Saturação baixa — alvo prioritário para outranking rápido."


# ═══════════════════════════════════════════════════════════════════════════
# 5. OWNED ASSET GAP
# ═══════════════════════════════════════════════════════════════════════════


def _compute_owned_asset_gap(serp: list[dict], threat: str) -> dict:
    required = {"CRITICAL": 7, "HIGH": 5, "MEDIUM": 3, "LOW": 2}.get(threat, 3)
    current = sum(1 for r in serp if r.get("controlled"))
    gap = max(0, required - current)

    return {
        "required": required,
        "current": current,
        "gap": gap,
        "gap_pct": round(gap / max(required, 1) * 100, 0),
        "status": "CRÍTICO" if gap >= 4 else "MODERADO" if gap >= 2 else "OK",
    }


# ═══════════════════════════════════════════════════════════════════════════
# 6. RECOVERY PROBABILITY
# ═══════════════════════════════════════════════════════════════════════════


def _estimate_recovery_probability(threat: str, neg_ratio: float,
                                    score: float, displacement: list[dict],
                                    serp: list[dict], current_controlled: int,
                                    saturation: list[dict]) -> dict:
    """
    Estima probabilidade de reduzir toxicidade abaixo de 30% em 90 dias.
    Baseado em:
      - threat level (CRITICAL = pior)
      - non-displaceable ratio
      - momentum
      - current controlled assets
      - saturation média
    """
    # Threat penalty
    threat_penalty = {"CRITICAL": 0.40, "HIGH": 0.25, "MEDIUM": 0.10, "LOW": 0.0}.get(threat, 0.2)

    # Non-displaceable ratio
    permanent = sum(1 for t in displacement if t["is_non_displaceable"])
    total_displaceable = len(displacement) or 1
    perm_penalty = min(permanent / total_displaceable * 0.5, 0.35)

    # Controlled asset bonus
    ctrl_bonus = min(current_controlled / 5 * 0.15, 0.15)

    # Saturation penalty
    high_sat = sum(1 for s in saturation if s["saturation_level"] == "HIGH")
    sat_penalty = min(high_sat * 0.05, 0.20)

    # Base probability
    base = 0.85
    probability = base - threat_penalty - perm_penalty - sat_penalty + ctrl_bonus
    probability = max(0.05, min(probability, 0.98))
    probability_pct = round(probability * 100)

    # Confidence — sem banda numérica: não temos backtesting para calibrar ±pp.
    if probability_pct >= 65:
        confidence = "ALTA"
    elif probability_pct >= 40:
        confidence = "MÉDIA"
    else:
        confidence = "BAIXA"
    band = None  # removido: ±pp era inventado

    # Factors
    factors = []
    if threat_penalty > 0:
        factors.append("Nível de ameaça {} penaliza em {}pp".format(threat, round(threat_penalty * 100)))
    if perm_penalty > 0:
        factors.append("{} resultados não deslocáveis penalizam em {}pp".format(permanent, round(perm_penalty * 100)))
    if ctrl_bonus > 0:
        factors.append("{} ativos controlados bonus de {}pp".format(current_controlled, round(ctrl_bonus * 100)))
    if sat_penalty > 0:
        factors.append("{} domínios com saturação alta penalizam em {}pp".format(high_sat, round(sat_penalty * 100)))

    return {
        "probability_pct": probability_pct,
        "confidence": confidence,
        "band": None,
        "label": "{}% (confiança {}) — estimativa indicativa, não calibrada".format(probability_pct, confidence),
        "factors": factors,
        "breakeven": _estimate_recovery_breakeven(probability_pct),
    }


def _estimate_recovery_breakeven(prob_pct: int) -> str:
    if prob_pct >= 75:
        return "Recuperação provável em 60-90 dias com execução disciplinada do plano operacional."
    if prob_pct >= 50:
        return "Recuperação viável em 90-180 dias. Requer investimento contínuo em ads + conteúdo."
    if prob_pct >= 30:
        return "Recuperação possível mas longa (180-365+ dias). Resultados permanentes limitam velocidade."
    return "Recuperação improvável em menos de 365 dias. Estratégia recomendada: contenção + convivência gerenciada."


# ═══════════════════════════════════════════════════════════════════════════
# 7. TIMELINE v2
# ═══════════════════════════════════════════════════════════════════════════


def _build_timeline_v2(displacement: list[dict],
                       organic: dict, paid: dict) -> list[dict]:
    """Timeline 30/60/90 com organic × paid tracks."""
    fast_content = [c for c in organic["content_assets"]
                    if c["velocity"] and any(v in c["velocity"] for v in ("2-5", "3-7"))]
    medium_content = [c for c in organic["content_assets"]
                      if c["velocity"] and any(v in c["velocity"] for v in ("5-10", "7-14", "7-21"))]

    easy_targets = [t for t in displacement if t["is_recoverable"] and t["difficulty"] in ("EASY", "MEDIUM")]

    return [
        {
            "phase": 1,
            "label": "FASE 1 — ATAQUE RÁPIDO (Dias 1-30)",
            "focus": "Deslocar alvos fáceis + publicar conteúdo de alta velocidade + ativar ads",
            "organic": [
                "Publicar ativos rápidos: {}".format(
                    ", ".join(c["label"] for c in fast_content[:4])
                ),
                "Otimizar perfis institucionais (LinkedIn, site) para branded keywords",
                "SEO on-page para {} alvos recuperáveis".format(min(len(easy_targets), 5)),
            ],
            "paid": [
                "Ativar campanha de Defesa de Marca",
                "Ativar Reparo Reputacional (se CRITICAL/HIGH)",
                "Orçamento estimado: R$ {}-{}/m".format(
                    paid.get("total_monthly_budget_min", 0),
                    paid.get("total_monthly_budget_max", 0),
                ),
            ],
            "target_kpis": [
                "Reduzir negative share em 10-15pp",
                "1-2 ativos controlados na page 1",
                "Recuperar {} alvos fáceis".format(min(len(easy_targets), 3)),
            ],
        },
        {
            "phase": 2,
            "label": "FASE 2 — OCUPAÇÃO SUSTENTADA (Dias 31-60)",
            "focus": "Atacar alvos médios + consolidar ganhos orgânicos + refinar ads",
            "organic": [
                "Publicar conteúdo de profundidade: {}".format(
                    ", ".join(c["label"] for c in medium_content[:4])
                ),
                "Construir backlinks para ativos institucionais",
                "Produzir conteúdo de autoridade (YouTube, entrevista setorial)",
            ],
            "paid": [
                "Refinar campanhas com dados de CPC/CTR do mês 1",
                "Aumentar budget de campanhas com alto ROAS",
                "Testar landing pages alternativas por intent",
            ],
            "target_kpis": [
                "Negative share < 30%",
                "3+ ativos controlados no top 10",
                "Positive share > 20%",
            ],
        },
        {
            "phase": 3,
            "label": "FASE 3 — DOMINÂNCIA DE SERP (Dias 61-90)",
            "focus": "Consolidar page 1 com ativos controlados + reduzir ads gradualmente",
            "organic": [
                "Avaliar descontinuidade de campanhas de alto CPC se orgânico já domina",
                "Produzir conteúdo de autoridade final (entrevista, podcast)",
                "Novo audit completo para medir SERP toxicity delta",
                "Ajustar estratégia com base em dados do movimento",
            ],
            "paid": [
                "Manter apenas campanhas de brand defense + legal counter (se necessário)",
                "Reduzir budget de distribuição de conteúdo se orgânico sustenta",
                "Relatório de ROAS por campanha",
            ],
            "target_kpis": [
                "SERP Toxicity reduzido 40%+",
                "Negative share < 20%",
                "4+ ativos controlados posicionados",
            ],
        },
    ]


# ═══════════════════════════════════════════════════════════════════════════
# 8. KPI PROJECTION v2
# ═══════════════════════════════════════════════════════════════════════════


def _project_kpis_v2(score: float, neg_ratio: float,
                      neg_count: int, total: int,
                      recovery: dict) -> dict:
    """KPI projections calibradas por nível de toxicidade atual.

    AVISO: projeções são metas operacionais, não garantias.
    Casos CRITICAL com resultados legais permanentes (JusBrasil, STF)
    podem levar 180-365 dias para atingir negative share < 30%.
    Apresentar ao cliente como metas, não como resultados prometidos.
    """
    current_controlled = total - neg_count

    # Deltas realistas por nível de score (quanto mais alto o score, mais difícil cair)
    # CRITICAL/HIGH (score >= 50): mudanças lentas — legal e tier-1 resistem
    # MEDIUM/LOW (score < 50): mudanças mais rápidas — domínios mais fáceis
    if score >= 70:
        d30, d60, d90 = 8, 18, 28      # alta toxicidade: progresso lento
        share30 = 0.08; share60 = 0.18; neg_share_90 = "< 40%"
    elif score >= 50:
        d30, d60, d90 = 10, 22, 35     # toxicidade média-alta
        share30 = 0.10; share60 = 0.22; neg_share_90 = "< 30%"
    else:
        d30, d60, d90 = 12, 25, 40     # toxicidade baixa-média: mais fácil
        share30 = 0.12; share60 = 0.25; neg_share_90 = "< 20%"

    return {
        "current": {
            "serp_toxicity": score,
            "negative_share_pct": round(neg_ratio * 100, 1),
            "negative_count": neg_count,
            "controlled_count": current_controlled,
        },
        "target_30d": {
            "serp_toxicity": max(0, round(score - d30)),
            "negative_share_target": "{}%".format(round(max(0, neg_ratio - share30) * 100, 1)),
            "controlled_growth": "+1 a +2 ativos",
        },
        "target_60d": {
            "serp_toxicity": max(0, round(score - d60)),
            "negative_share_target": "{}%".format(round(max(0, neg_ratio - share60) * 100, 1)),
            "controlled_growth": "+2 a +4 ativos",
        },
        "target_90d": {
            "serp_toxicity": max(0, round(score - d90)),
            "negative_share_target": neg_share_90,
            "controlled_growth": "+4 a +6 ativos",
        },
        "recovery_probability": recovery["label"],
        "disclaimer": (
            "Metas indicativas. Resultados legais permanentes (JusBrasil, STF, TJ) "
            "não são removíveis — estratégia é supressão por ocupação. "
            "Timelines assumem execução disciplinada do plano."
        ),
    }
