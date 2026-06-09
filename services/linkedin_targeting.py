"""
LinkedIn Ads Targeting Engine — Stakeholder Exposure Matrix,
archetype-driven audience segments with CPM/budget estimation.

LinkedIn Ads has the highest CPM (R$30-80) of any digital channel.
Generic targeting like 'profissionais do setor' wastes budget.
Each archetype requires specific job functions, seniorities, industries, and interests.
"""
import re


# ── ARCHETYPE SEGMENTATION PROFILES ───────────────────────────────────────
# Each archetype has derived targeting parameters.

SEGMENTATION_PROFILES = {
    "criminal": {
        "label": "Criminal / Jurídico",
        "job_functions": ["Legal", "Compliance", "Risk Management", "Corporate Governance"],
        "job_titles": ["Advogado Sênior", "Sócio", "Diretor Jurídico", "Head de Compliance",
                        "Chief Compliance Officer", "Procurador", "Juiz", "Promotor"],
        "seniority": ["Director", "VP", "C-Suite", "Partner"],
        "industries": ["Law Practice", "Legal Services", "Government Administration",
                        "Judiciary", "Compliance & Risk"],
        "interests": ["Direito", "Compliance", "Governança Corporativa", "Due Diligence",
                       "Contencioso", "Direito Empresarial"],
        "company_size": ["11-50", "51-200", "201-500"],
        "min_audience": 50000,
        "max_audience": 300000,
    },
    "reputacional": {
        "label": "Corporativo / Reputacional",
        "job_functions": ["Corporate Communications", "Public Relations", "Marketing",
                           "Brand Management", "Executive Management"],
        "job_titles": ["Diretor de Comunicação", "Head de PR", "CEO", "CMO",
                        "Gerente de Marketing", "Diretor de Reputação",
                        "Sócio-Diretor", "VP de Comunicação"],
        "seniority": ["Manager", "Director", "VP", "C-Suite"],
        "industries": ["Public Relations", "Corporate Communications", "Marketing & Advertising",
                        "Management Consulting", "Financial Services"],
        "interests": ["Reputação Corporativa", "Gestão de Crise", "Comunicação Estratégica",
                       "Branding", "PR Digital", "LinkedIn Ads"],
        "company_size": ["51-200", "201-500", "501-1000", "1001+"],
        "min_audience": 80000,
        "max_audience": 500000,
    },
    "politico": {
        "label": "Político / Governo",
        "job_functions": ["Government Relations", "Public Policy", "Public Administration",
                           "Political Organization"],
        "job_titles": ["Deputado", "Senador", "Vereador", "Secretário", "Ministro",
                        "Assessor Parlamentar", "Chefe de Gabinete", "Diretor de Comunicação",
                        "Coordenador de Campanha"],
        "seniority": ["Manager", "Director", "VP", "C-Suite", "Owner"],
        "industries": ["Government Administration", "Political Organization", "Public Policy",
                        "Legislative Office", "Executive Office"],
        "interests": ["Política", "Administração Pública", "Gestão Pública",
                       "Campanhas Eleitorais", "Marketing Político"],
        "company_size": ["1-10", "11-50", "51-200", "201-500"],
        "min_audience": 30000,
        "max_audience": 200000,
    },
    "media": {
        "label": "Mídia / Imprensa",
        "job_functions": ["Media and Communication", "Journalism", "Publishing",
                           "Content Production"],
        "job_titles": ["Jornalista", "Repórter", "Editor", "Diretor de Redação",
                        "Produtor de Conteúdo", "Âncora", "Apresentador",
                        "Publisher", "CEO de Veículo"],
        "seniority": ["Entry", "Senior", "Manager", "Director", "Owner"],
        "industries": ["Media Production", "Newspapers", "Online Media", "Broadcast Media",
                        "Publishing", "Digital Media"],
        "interests": ["Jornalismo", "Comunicação", "Mídia Digital", "Reportagem",
                       "Investigação", "Fact-Checking"],
        "company_size": ["1-10", "11-50", "51-200", "201-500"],
        "min_audience": 40000,
        "max_audience": 250000,
    },
    "administrativo": {
        "label": "Administrativo / Regulatório",
        "job_functions": ["Administrative", "Regulatory", "Compliance", "Legal",
                           "Government Relations"],
        "job_titles": ["Diretor Administrativo", "Superintendente", "Coordenador de Licitação",
                        "Analista de Compliance", "Procurador", "Auditor",
                        "Secretário Executivo", "Conselheiro"],
        "seniority": ["Senior", "Manager", "Director", "VP", "C-Suite"],
        "industries": ["Government Administration", "Regulatory Agencies", "Compliance",
                        "Auditing", "Legal Services", "Public Administration"],
        "interests": ["Licitação", "Contratos Públicos", "Regulação", "Compliance",
                       "Administração Pública", "Governança"],
        "company_size": ["51-200", "201-500", "501-1000", "1001+"],
        "min_audience": 40000,
        "max_audience": 200000,
    },
    "associativo": {
        "label": "Associação Indireta / Sócios",
        "job_functions": ["Business Development", "Partner Management", "Corporate Development",
                           "Executive Management"],
        "job_titles": ["Sócio", "CEO", "Diretor de Novos Negócios", "Head de Parcerias",
                        "Conselheiro", "Investidor", "Business Development Manager",
                        "Corporate Venture Director"],
        "seniority": ["Director", "VP", "C-Suite", "Partner", "Owner"],
        "industries": ["Venture Capital", "Private Equity", "Investment Banking",
                        "Management Consulting", "Corporate Development",
                        "Business Consulting"],
        "interests": ["M&A", "Investimento", "Parcerias Estratégicas", "Novos Negócios",
                       "Corporate Venture", "Business Development"],
        "company_size": ["11-50", "51-200", "201-500", "501-1000"],
        "min_audience": 30000,
        "max_audience": 150000,
    },
}

DEFAULT_PROFILE = SEGMENTATION_PROFILES["reputacional"]


def generate_linkedin_ads_plan(archetype: str, industry: str = "",
                                company_name: str = "",
                                target_companies: list[str] | None = None,
                                location: str = "Brasil") -> dict:
    """Generate complete LinkedIn Ads plan for the entity's archetype.

    Returns:
      - segmentation: detailed targeting parameters
      - audience: estimated size and validation
      - campaigns: recommended campaign structure with budgets
      - cpm_estimate: expected CPM range
      - stakeholder_matrix: who to reach and why
    """
    profile = SEGMENTATION_PROFILES.get(archetype, DEFAULT_PROFILE)

    # Segmentation
    segmentation = {
        "job_functions": profile["job_functions"],
        "job_titles": profile["job_titles"][:5],
        "seniority": profile["seniority"],
        "industries": _resolve_industries(profile["industries"], industry),
        "interests": profile["interests"],
        "company_size": profile["company_size"],
        "location": location,
        "target_companies": target_companies or [],
        "excluded_companies": [],
    }

    # Audience estimate
    audience_size = _estimate_audience(segmentation, profile)
    audience_valid = _validate_audience(audience_size, profile)

    # CPM estimate
    cpm = _estimate_cpm(archetype, audience_size["estimated"])

    # Campaigns
    campaigns = _generate_campaigns(archetype, segmentation, cpm)

    # Stakeholder matrix
    stakeholder_matrix = _stakeholder_exposure_matrix(archetype)

    return {
        "archetype": archetype,
        "archetype_label": profile["label"],
        "segmentation": segmentation,
        "audience": audience_size,
        "audience_validation": audience_valid,
        "cpm_estimate": cpm,
        "campaigns": campaigns,
        "stakeholder_matrix": stakeholder_matrix,
        "total_daily_budget": {
            "min": sum(c["daily_min"] for c in campaigns),
            "max": sum(c["daily_max"] for c in campaigns),
            "recommended": sum(c["daily_recommended"] for c in campaigns),
        },
        "total_monthly_budget": {
            "min": sum(c["daily_min"] for c in campaigns) * 22,
            "max": sum(c["daily_max"] for c in campaigns) * 22,
            "recommended": sum(c["daily_recommended"] for c in campaigns) * 22,
        },
    }


def _resolve_industries(profile_industries: list[str], entity_industry: str) -> list[str]:
    """Merge profile industries with entity-specific industry."""
    if entity_industry and entity_industry not in profile_industries:
        return [entity_industry] + profile_industries
    return profile_industries


def _estimate_audience(segmentation: dict, profile: dict) -> dict:
    """Estimate audience size based on targeting params.

    Rough LinkedIn audience estimator based on:
      - Job function: ~200k baseline per function
      - Seniority filter: ~30% of base
      - Industry filter: ~40% of base
      - Location (Brasil): ~15% of base
      - Company size: ~50% of base
    """
    base = 200000
    functions_n = len(segmentation.get("job_functions", profile.get("job_functions", [])))
    industries_n = len(segmentation.get("industries", profile.get("industries", [])))
    seniority_n = len(segmentation.get("seniority", profile.get("seniority", [])))

    # Simple multiplicative model
    est = base * (functions_n / 3) * (seniority_n / 4) * (industries_n / 4) * 0.15
    est = max(est, 10000)

    return {
        "estimated": round(est),
        "estimated_range": f"{round(est * 0.7):,} - {round(est * 1.3):,}",
        "formula": "Base 200k × (job_functions/3) × (seniority/4) × (industries/4) × 0.15 (Brasil)",
    }


def _validate_audience(audience: dict, profile: dict) -> dict:
    """Validate if audience is properly sized for LinkedIn Ads."""
    est = audience["estimated"]
    issues = []
    if est < profile.get("min_audience", 50000):
        issues.append(f"Audiência muito pequena ({est:,}) — ampliar funções ou setores")
    if est > profile.get("max_audience", 500000):
        issues.append(f"Audiência muito grande ({est:,}) — refinar senioridade ou adicionar empresas-alvo")
    if not issues:
        issues.append(f"Audiência dentro do range ideal ({profile.get('min_audience', 50000):,}-{profile.get('max_audience', 500000):,})")

    return {
        "valid": len([i for i in issues if "pequena" in i or "grande" in i]) == 0,
        "issues": issues,
        "recommendation": "Segmentação OK" if not [i for i in issues if "pequena" in i or "grande" in i]
                         else "Ajustar segmentação antes de ativar campanhas",
    }


def _estimate_cpm(archetype: str, audience_size: int) -> dict:
    """Estimate CPM range based on archetype competitiveness.

    General market: R$30-50 CPM
    Legal/Criminal: R$50-80 CPM (more competitive keywords)
    Political: R$40-70 CPM
    Corporate: R$35-55 CPM
    """
    ranges = {
        "criminal": (50, 80),
        "politico": (40, 70),
        "media": (35, 60),
        "administrativo": (40, 65),
        "associativo": (55, 85),
        "reputacional": (35, 55),
    }
    cpm_min, cpm_max = ranges.get(archetype, (30, 50))
    return {
        "cpm_range": f"R$ {cpm_min}-{cpm_max}",
        "cpm_min": cpm_min,
        "cpm_max": cpm_max,
        "cpm_average": round((cpm_min + cpm_max) / 2),
        "note": f"CPM mais alto que Google Ads (R$5-15) porque LinkedIn tem menor inventário e "
                f"maior intenção profissional. Para arquétipo '{archetype}', "
                f"a concorrência por palavras-chave jurídicas/diretivas eleva o CPM.",
    }


def _generate_campaigns(archetype: str, segmentation: dict, cpm: dict) -> list[dict]:
    """Generate LinkedIn Ads campaign structure per archetype."""
    cpm_avg = cpm["cpm_average"]
    campaigns = []

    # Brand Awareness — Sponsored Content
    campaigns.append({
        "name": "Brand Awareness — Líderes do Setor",
        "objective": "Fazer tomadores de decisão verem posicionamento positivo antes de buscar no Google",
        "format": "Sponsored Content (artigo LinkedIn / single image)",
        "daily_min": round(cpm_avg * 3),
        "daily_max": round(cpm_avg * 6),
        "daily_recommended": round(cpm_avg * 4),
        "ctr_expected": "0.4-0.8%",
        "landing_page": "Artigo LinkedIn ou Site Institucional",
        "audience_note": f"Segmentação por função ({segmentation['job_functions'][0]}) + senioridade",
    })

    # Engagement — Document Ad
    campaigns.append({
        "name": "Engagement — Conteúdo Técnico",
        "objective": "Distribuir FAQ ou esclarecimento para quem está avaliando a entidade",
        "format": "Document Ad (PDF do esclarecimento / FAQ)",
        "daily_min": round(cpm_avg * 2),
        "daily_max": round(cpm_avg * 4),
        "daily_recommended": round(cpm_avg * 3),
        "ctr_expected": "0.8-1.5%",
        "landing_page": "PDF direto ou página de FAQ",
        "audience_note": f"Empresas do setor ({segmentation['industries'][0]}) + tomadores de decisão",
    })

    # Account-Based — Target Companies
    if segmentation.get("target_companies"):
        campaigns.append({
            "name": "Account-Based — Empresas-Alvo",
            "objective": "Atingir funcionários de empresas específicas (clientes, parceiros, prospects)",
            "format": "Sponsored Content segmentado por empresa",
            "daily_min": round(cpm_avg * 4),
            "daily_max": round(cpm_avg * 8),
            "daily_recommended": round(cpm_avg * 5),
            "ctr_expected": "0.3-0.6%",
            "landing_page": "Site Institucional / Case Study",
            "audience_note": f"Empresas: {', '.join(segmentation['target_companies'][:5])}",
        })

    return campaigns


def _stakeholder_exposure_matrix(archetype: str) -> list[dict]:
    """Generate stakeholder matrix for the archetype.

    Each stakeholder group has: who they are, why they matter, what asset to show them.
    """
    matrices = {
        "criminal": [
            {"stakeholder": "Parceiros de Negócios", "concern": "Due diligence de compliance",
             "asset": "Esclarecimento Jurídico + Certidões"},
            {"stakeholder": "Clientes Corporativos", "concern": "Continuidade de contratos",
             "asset": "Comunicado Institucional + FAQ"},
            {"stakeholder": "Órgãos Reguladores", "concern": "Conformidade legal",
             "asset": "Documentação Jurídica + Posicionamento"},
            {"stakeholder": "Imprensa Especializada", "concern": "Cobertura do caso",
             "asset": "Release para ConJur + Migalhas"},
        ],
        "reputacional": [
            {"stakeholder": "Conselho de Administração", "concern": "Impacto reputacional no valuation",
             "asset": "Relatório de NPA + Recovery Probability"},
            {"stakeholder": "Clientes Estratégicos", "concern": "Associação de marca a risco",
             "asset": "Artigo LinkedIn + Perfil Institucional"},
            {"stakeholder": "Investidores", "concern": "Continuidade operacional",
             "asset": "Campanha de Posicionamento + Release"},
            {"stakeholder": "Mercado / Concorrência", "concern": "Vantagem competitiva",
             "asset": "Biografia Executiva + Site Institucional"},
        ],
        "politico": [
            {"stakeholder": "Eleitorado / Base", "concern": "Confiança no mandato",
             "asset": "Vídeo Posicionamento + Redes Sociais"},
            {"stakeholder": "Partido / Coligação", "concern": "Impacto na imagem partidária",
             "asset": "Release + Entrevista em veículo aliado"},
            {"stakeholder": "Imprensa Política", "concern": "Ângulo da cobertura",
             "asset": "Release para Brasília 247 + Entrevistas"},
            {"stakeholder": "Financiadores / Apoiadores", "concern": "Continuidade do apoio",
             "asset": "Relatório de Atividades + Prestação de Contas"},
        ],
        "media": [
            {"stakeholder": "Fonte / Pauta", "concern": "Credibilidade da informação",
             "asset": "Release + Documentos Comprobatórios"},
            {"stakeholder": "Audiência", "concern": "Confiança no veículo",
             "asset": "Nota de Esclarecimento + Vídeo"},
            {"stakeholder": "Anunciantes", "concern": "Associação a polêmica",
             "asset": "Comunicado Institucional"},
            {"stakeholder": "Concorrência", "concern": "Oportunidade de pauta negativa",
             "asset": "Posicionamento Antecipado + FAQ"},
        ],
        "administrativo": [
            {"stakeholder": "Órgão Regulador", "concern": "Conformidade normativa",
             "asset": "Documentação + Esclarecimento Técnico"},
            {"stakeholder": "Fornecedores", "concern": "Continuidade de contratos públicos",
             "asset": "Certidões + Comunicado"},
            {"stakeholder": "Funcionários", "concern": "Estabilidade do emprego",
             "asset": "Comunicado Interno + Town Hall"},
            {"stakeholder": "Tribunal de Contas", "concern": "Regularidade fiscal",
             "asset": "Prestação de Contas + Documentação"},
        ],
        "associativo": [
            {"stakeholder": "Sócios / Investidores", "concern": "Desassociação de risco reputacional",
             "asset": "Esclarecimento Jurídico + Cronologia de Desassociação"},
            {"stakeholder": "Conselho", "concern": "Governança e compliance",
             "asset": "Due Diligence Report + Plano de Ação"},
            {"stakeholder": "Parceiros Comerciais", "concern": "Contágio reputacional",
             "asset": "FAQ Transparência + Release"},
            {"stakeholder": "Mercado Financeiro", "concern": "Impacto no valuation",
             "asset": "Recovery Probability Report + Timeline"},
        ],
    }
    return matrices.get(archetype, matrices["reputacional"])


def linkedin_battle_section(archetype: str, industry: str = "",
                              target_companies: list[str] | None = None) -> dict:
    """Generate the LinkedIn Ads section for the battle plan."""
    ads_plan = generate_linkedin_ads_plan(archetype, industry, target_companies=target_companies)
    return {
        "present": True,
        "archetype": archetype,
        "segmentation_summary": {
            "job_functions": ads_plan["segmentation"]["job_functions"][:3],
            "seniority": ads_plan["segmentation"]["seniority"],
            "industries": ads_plan["segmentation"]["industries"][:3],
        },
        "audience": ads_plan["audience"],
        "audience_validation": ads_plan["audience_validation"],
        "cpm": ads_plan["cpm_estimate"],
        "campaigns": ads_plan["campaigns"],
        "budget": ads_plan["total_monthly_budget"],
        "stakeholders": ads_plan["stakeholder_matrix"],
        "strategy_note": f"LinkedIn Ads segmentado por arquétipo '{archetype}'. "
                         f"Audiência estimada: {ads_plan['audience']['estimated_range']}. "
                         f"CPM estimado: {ads_plan['cpm_estimate']['cpm_range']}. "
                         f"Budget mensal recomendado: R$ {ads_plan['total_monthly_budget']['recommended']:,}.",
    }
