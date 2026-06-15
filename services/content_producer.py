"""
Content Producer — Geração de Artigos Prontos para Publicação.
Cada asset vira artigo completo com SEO metadata, plataforma de
publicação e estratégia de amplificação.
"""
import json, re
from datetime import datetime, timezone
from pathlib import Path
from services.openrouter_service import call_openrouter
from services.asset_service import generate_asset

ASSET_TEMPLATES_DIR = Path(__file__).parent.parent / "asset_templates"
import os
if os.environ.get("VERCEL"):
    CACHE_DIR = Path("/tmp/articles_cache")
else:
    CACHE_DIR = Path(__file__).parent.parent / "articles_cache"

# ── Plataforma de publicação por tipo de asset ────────────────────────────

PUBLISHING_PLATFORM: dict[str, dict] = {
    "artigo_linkedin": {
        "platform": "LinkedIn Articles",
        "url": "linkedin.com/pulse",
        "type": "social_professional",
        "setup_time": "5 min (conta existente)",
        "steps": [
            "Acessar linkedin.com",
            "Clicar em 'Escrever artigo' no feed",
            "Colar título e conteúdo",
            "Adicionar imagem de capa institucional (opcional)",
            "Publicar e fixar no perfil",
        ],
        "amplification": "Compartilhar no feed + grupos estratégicos + impulsionar com LinkedIn Ads",
        "seo_boost": "ALTO — LinkedIn tem autoridade de domínio 98, indexa em horas",
    },
    "medium": {
        "platform": "Medium",
        "url": "medium.com",
        "type": "publishing_platform",
        "setup_time": "10 min (criar conta + configurar publicação)",
        "steps": [
            "Criar conta em medium.com",
            "Criar uma 'Publicação' com nome institucional",
            "Colar artigo formatado em Markdown",
            "Adicionar tags relevantes (5 máx)",
            "Publicar e submeter a publicações relevantes",
        ],
        "amplification": "Submeter a publicações Medium do setor + compartilhar no Twitter/LinkedIn",
        "seo_boost": "MUITO ALTO — Medium tem domínio 94, rankeia rápido para branded keywords",
    },
    "biografia_executiva": {
        "platform": "Site Institucional + LinkedIn",
        "url": "site_próprio + linkedin.com/about",
        "type": "institutional",
        "setup_time": "1-2 dias (criar página no site)",
        "steps": [
            "Publicar no site institucional como página 'Sobre' ou 'Equipe'",
            "Atualizar seção 'Sobre' do LinkedIn com o mesmo texto",
            "Adicionar ao Crunchbase / Escavador",
        ],
        "amplification": "Linkar em todos os perfis digitais + assinatura de email + Google Ads para 'quem é {entity}'",
        "seo_boost": "CRÍTICO — biografia oficial domina branded search quando otimizada",
    },
    "perfil_institucional": {
        "platform": "Site Institucional",
        "url": "site_próprio",
        "type": "institutional",
        "setup_time": "1-2 dias",
        "steps": [
            "Criar página de perfil no site institucional",
            "Adicionar foto profissional, cargo, breve biografia",
            "Otimizar meta title e description",
        ],
        "amplification": "Google Ads (brand defense) + link em todos os perfis + assinatura de email",
        "seo_boost": "ALTO — essencial para ocupar posições #1 em busca de marca",
    },
    "comunicado_imprensa": {
        "platform": "Site + Release Distributors",
        "url": "site_próprio + google news",
        "type": "press",
        "setup_time": "2-4 horas",
        "steps": [
            "Publicar no site institucional na seção 'Sala de Imprensa'",
            "Distribuir via Newswire / ReleaseWire / PRLog",
            "Enviar para jornalistas do setor por email",
        ],
        "amplification": "Google Ads (palavras de crise) + SEO on-page + press release indexing services",
        "seo_boost": "MÉDIO-ALTO — releases têm boa indexação, mas concorrem com veículos",
    },
    "esclarecimento_juridico": {
        "platform": "Site Institucional (seção jurídica)",
        "url": "site_próprio / jurídico",
        "type": "legal",
        "setup_time": "4-8 horas (requer revisão jurídica)",
        "steps": [
            "Redigir com assessoria jurídica",
            "Publicar em página dedicada no site",
            "Adicionar schema.org/LegalService no markup",
            "Registrar no Google Search Console",
        ],
        "amplification": "Google Ads (palavras jurídicas) + SEO para termos de crise + link em comunicados",
        "seo_boost": "MÉDIO — nichado, mas essencial para deslocar JusBrasil em páginas 2-3",
    },
    "faq_transparencia": {
        "platform": "Site Institucional (FAQ)",
        "url": "site_próprio / faq",
        "type": "institutional",
        "setup_time": "2-4 horas",
        "steps": [
            "Criar página FAQ no site institucional",
            "Estruturar com schema.org/FAQPage para rich snippets",
            "Abordar perguntas frequentes identificadas no audit",
        ],
        "amplification": "Google Ads (termos de transparência) + SEO on-page + featured snippet targeting",
        "seo_boost": "ALTO — FAQ pages frequentemente ganham featured snippets no Google",
    },
    "site_institucional": {
        "platform": "Site Próprio (WordPress, HTML, ou Netlify)",
        "url": "domínio_próprio",
        "type": "institutional",
        "setup_time": "1-3 dias (criação do site)",
        "steps": [
            "Registrar domínio (ex: entidade.com.br)",
            "Criar site com páginas: Home, Sobre, FAQ, Contato, Sala de Imprensa",
            "Instalar Google Analytics + Search Console",
            "Otimizar SEO técnico (meta tags, sitemap, robots.txt)",
        ],
        "amplification": "Base para TODAS as campanhas de ads. Todo conteúdo institucional hospedado aqui.",
        "seo_boost": "CRÍTICO — site próprio é a fundação da autoridade digital",
    },
    "entrevista_midia_setorial": {
        "platform": "YouTube + Medium + Site",
        "url": "youtube.com / medium / site",
        "type": "media",
        "setup_time": "1-2 semanas (agendar + gravar + editar)",
        "steps": [
            "Identificar podcasts/entrevistas do setor",
            "Agendar participação",
            "Publicar no YouTube e incorporar no site",
            "Transcrever e publicar como artigo no Medium",
        ],
        "amplification": "YouTube SEO + Google Ads (palavras de autoridade) + crosslink com site institucional",
        "seo_boost": "MÉDIO-ALTO — YouTube é o segundo maior mecanismo de busca",
    },
    "roteiro_youtube": {
        "platform": "YouTube",
        "url": "studio.youtube.com",
        "type": "video",
        "setup_time": "30-60 min (gravação) + 15 min (upload)",
        "steps": [
            "Gravar vídeo seguindo o roteiro gerado (4-6 minutos recomendado)",
            "Acessar studio.youtube.com com a conta do cliente",
            "Upload do vídeo → colar Título SEO, Descrição completa e Tags",
            "Thumbnail: foto profissional do cliente + texto do título",
            "Publicar e fixar como vídeo em destaque no canal",
            "Ativar legendas automáticas (transcrições indexam como texto no Google)",
        ],
        "amplification": "YouTube SEO + TrueView Ads + Google Ads (YouTube network) + transcrição indexável",
        "seo_boost": "EXTREMO — DA 100, segundo maior buscador, transcrições indexam como texto",
    },
}

# ── Estratégia de amplificação por intent ─────────────────────────────────

AMPLIFICATION_STRATEGY: dict[str, dict] = {
    "branded": {
        "primary": "SEO + Brand Defense Ads",
        "tactics": [
            "Otimizar página para 'nome da entidade' (meta title, H1, description)",
            "Criar Google Ads para 'nome da entidade' CPC baixo",
            "Distribuir link em todos os perfis sociais e assinatura de email",
        ],
        "target_ctr": "ALTO — intenção de descoberta",
        "kpi": "Posicionar no top 3 orgânico em 30 dias",
    },
    "hostile": {
        "primary": "Paid Defense + FAQ SEO",
        "tactics": [
            "Criar landing page específica para o termo de crise",
            "Google Ads (palavras negativas) — CPC mais alto, necessário",
            "Focar em featured snippet com FAQ schema",
        ],
        "target_ctr": "MÉDIO — tráfego defensivo, não de conversão",
        "kpi": "Deslocar resultados negativos da page 1 em 60 dias",
    },
    "institutional": {
        "primary": "SEO + Content Distribution",
        "tactics": [
            "Otimizar para 'entidade + empresa/site/oficial'",
            "Criar perfil em diretórios institucionais (Crunchbase, Escavador)",
            "Link building interno entre ativos do site",
        ],
        "target_ctr": "ALTO — busca por site oficial",
        "kpi": "Domínio completo do branded search institucional em 45 dias",
    },
    "crisis": {
        "primary": "Crisis Response Ads + SEO Urgente",
        "tactics": [
            "Publicar esclarecimento jurídico imediatamente",
            "Google Ads com palavras de crise — CPC alto, necessário",
            "Distribuir release para veículos setoriais",
            "Monitorar rankeamento hora a hora nas primeiras 72h",
        ],
        "target_ctr": "BAIXO-MÉDIO — tráfego de crise, alta intenção",
        "kpi": "Suprimir resultados de crise da page 1 em 7 dias com ads",
    },
    "professional": {
        "primary": "LinkedIn + SEO Profissional",
        "tactics": [
            "LinkedIn Article + perfil otimizado",
            "Medium post cross-linkado",
            "YouTube de carreira/trajetória",
            "Google Ads para 'nome + linkedin/carreira'",
        ],
        "target_ctr": "ALTO — recrutadores, parceiros, due diligence",
        "kpi": "Top 3 em busca profissional em 30 dias",
    },
}

# ── Article Cache ────────────────────────────────────────────────

def _entity_cache_slug(entity: str) -> str:
    """
    Normaliza o nome da entidade para uso como slug de diretório.
    Remove acentos, converte para ASCII, substitui espaços por underscores.
    Consistente com _entity_slug() em console.py.
    """
    import unicodedata
    slug = unicodedata.normalize("NFKD", entity.lower().strip())
    slug = "".join(c for c in slug if not unicodedata.combining(c))  # remove acentos
    slug = re.sub(r"[^\w\s]", "", slug)
    slug = re.sub(r"\s+", "_", slug)
    return slug

def _cache_path(entity: str, asset_type: str) -> Path:
    slug = _entity_cache_slug(entity)
    return CACHE_DIR / slug / f"{asset_type}.json"

def save_article(entity: str, asset_type: str, data: dict) -> None:
    path = _cache_path(entity, asset_type)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def load_article(entity: str, asset_type: str) -> dict | None:
    path = _cache_path(entity, asset_type)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None

def list_cached_articles(entity: str) -> list[dict]:
    slug = _entity_cache_slug(entity)
    dirpath = CACHE_DIR / slug
    if not dirpath.is_dir():
        return []
    articles = []
    for f in sorted(dirpath.glob("*.json")):
        # Skip non-article files (pipeline_log, etc.)
        if f.stem in ("pipeline_log", "semantic_variations", "variations"):
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            # Only include dicts with asset_type key (actual articles)
            if isinstance(data, dict) and "asset_type" in data:
                articles.append(data)
        except Exception:
            pass
    return articles


def produce_article(asset_type: str, entity_name: str,
                    battle_plan: dict | None = None,
                    strategic_context: str = "") -> dict:
    """
    Gera artigo completo + metadados + plataforma + amplificação.
    Retorna dict com tudo que o operador precisa para publicar.
    """
    # Map asset_type from battle plan naming to asset_service naming
    type_map = {
        "artigo_linkedin":           "linkedin_article",
        "biografia_executiva":       "executive_bio",
        "esclarecimento_juridico":   "legal_clarification",
        "perfil_institucional":      "institutional_profile",
        "entrevista_midia_setorial": "interview_talking_points",
        "comunicado_imprensa":       "press_release",
        "faq_transparencia":         "faq_transparencia",
        "roteiro_youtube":           "roteiro_youtube",
    }
    service_type = type_map.get(asset_type, asset_type)

    # Build rich strategic context from battle plan if available
    if battle_plan and not strategic_context:
        strategic_context = _build_rich_context(entity_name, asset_type, battle_plan)

    # Generate article via LLM
    article_text = generate_asset(service_type, entity_name, strategic_context)

    # Platform recommendation
    platform_info = PUBLISHING_PLATFORM.get(asset_type, {})

    # Determine intent from asset type
    intent_map = {
        "artigo_linkedin": "professional",
        "medium": "professional",
        "biografia_executiva": "branded",
        "perfil_institucional": "institutional",
        "comunicado_imprensa": "crisis",
        "esclarecimento_juridico": "hostile",
        "faq_transparencia": "hostile",
        "site_institucional": "institutional",
        "entrevista_midia_setorial": "institutional",
    }
    intent_key = intent_map.get(asset_type, "branded")
    amplification = AMPLIFICATION_STRATEGY.get(intent_key, AMPLIFICATION_STRATEGY["branded"])

    # SEO metadata
    seo = _generate_seo_metadata(entity_name, asset_type, article_text)

    # Structured data extraction
    structured_data = _extract_structured_data(asset_type, article_text, entity_name)

    return {
        "asset_type":      asset_type,
        "label":           asset_type.replace("_", " ").title(),
        "entity_name":     entity_name,
        "article":         article_text,
        "body_md":         article_text,   # alias para compatibilidade com format_for() e distribution
        "seo":             seo,
        "structured_data": structured_data,
        "platform":        platform_info,
        "amplification":   amplification,
        "generated_at":    datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def _generate_fanout_queries(entity_name: str, plan: dict | None = None) -> list[str]:
    """Gera queries relacionadas que o Google pode fazer (query fan-out).

    Retorna lista de perguntas/termos que um usuário pesquisaria depois
    de buscar pelo nome da entidade — covering People Also Ask, related
    searches, e intents adjacentes.
    """
    queries = []

    # Core branded variations
    tokens = entity_name.strip().split()
    if len(tokens) >= 2:
        queries.append("quem é {}".format(entity_name))
        queries.append("{} o que faz".format(tokens[0]))
        queries.append("{} onde trabalha".format(tokens[0]))

    # From battle plan displacement targets
    if plan:
        targets = plan.get("displacement", [])
        # Extract hostile terms from snippets
        for t in targets[:5]:
            domain = t.get("domain", "")
            if "jusbrasil" in domain or "conjur" in domain or "migalhas" in domain:
                queries.append("{} processo".format(entity_name))
                queries.append("{} justiça".format(entity_name))
            if any(k in domain for k in ["veja", "folha", "uol", "globo", "estadao"]):
                queries.append("{} notícia".format(entity_name))

        # Search intent terms — usar intent_matrix do organic_warfare (campo correto)
        organic = plan.get("organic_warfare", {})
        intent_matrix = organic.get("intent_matrix", [])
        for intent_obj in intent_matrix[:4]:
            # intent_obj: {"intent": "hostile", "landing_pages": [...], "assets": [...]}
            intent_name = intent_obj.get("intent", "")
            if intent_name in ("hostile", "crisis"):
                queries.append("{} esclarecimento".format(entity_name))
                queries.append("{} resposta oficial".format(entity_name))
            elif intent_name == "branded":
                queries.append("{} site oficial".format(entity_name))
            elif intent_name == "professional":
                queries.append("{} linkedin".format(entity_name))
                queries.append("{} perfil profissional".format(entity_name))

    # Deduplicate and limit
    seen = set()
    unique = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique.append(q)
    return unique[:8]


def _build_rich_context(entity_name: str, asset_type: str, plan: dict) -> str:
    """Constrói contexto estratégico rico a partir do battle plan.

    Inclui métricas, alvos com títulos reais, fan-out queries, nome da entidade
    e diretriz explícita de PT-BR + densidade de nome.
    """
    pieces = []

    # Contexto de identidade — crítico para o LLM usar o nome correto
    pieces.append(f"NOME COMPLETO DA ENTIDADE: {entity_name}")
    pieces.append(f"REGRA OBRIGATÓRIA: Use o nome completo '{entity_name}' pelo menos 5 vezes no texto gerado.")
    pieces.append(f"IDIOMA: Escreva TODA a resposta em português do Brasil.")
    pieces.append("")

    summary = plan.get("summary", {})
    pieces.append(f"NÍVEL DE AMEAÇA: {summary.get('threat', '?')}")
    pieces.append(f"TOXICIDADE SERP: {summary.get('serp_toxicity', '?')}/100")
    pieces.append(f"PARTICIPAÇÃO NEGATIVA: {summary.get('neg_share_pct', '?')}%")
    pieces.append(f"ARQUÉTIPO: {summary.get('archetype', '?')}")
    pieces.append("")

    # Top displacement targets — com título e snippet reais da SERP
    # Isso permite ao LLM escrever conteúdo mais autoritativo que os resultados negativos
    targets = plan.get("displacement", [])[:3]
    if targets:
        pieces.append("RESULTADOS NEGATIVOS QUE ESTE CONTEÚDO DEVE SUPERAR NO GOOGLE:")
        pieces.append("(Escreva conteúdo mais específico, completo e autoritativo do que estes)")
        for t in targets:
            line = f"  #{t['position']} {t['domain']} (dificuldade: {t['difficulty']})"
            title = t.get("title", "")
            snippet = t.get("snippet", "")
            if title:
                line += f"\n    Título: {title[:80]}"
            if snippet:
                line += f"\n    Snippet: {snippet[:120]}"
            pieces.append(line)
        pieces.append("")

    # Fan-out queries que o Google pode gerar a partir desta entidade
    fanout = _generate_fanout_queries(entity_name, plan)
    if fanout:
        pieces.append("QUERIES RELACIONADAS (Google fan-out — este conteúdo deve responder a estas buscas):")
        for q in fanout:
            pieces.append(f"  - {q}")
        pieces.append("")

    # Diretriz anti-commodity
    pieces.append("DIRETRIZ DE CONTEÚDO:")
    pieces.append("Este deve ser conteúdo NÃO-GENÉRICO.")
    pieces.append("Evite templates, conselhos genéricos ou resumos de conhecimento comum.")
    pieces.append("Inclua exemplos específicos, perspectiva única, afirmações verificáveis.")
    pieces.append("Escreva o que apenas um especialista real nesta posição saberia.")

    return "\n".join(pieces)


def _generate_seo_metadata(entity: str, asset_type: str, article: str) -> dict:
    """Extrai SEO metadata do artigo."""
    lines = article.strip().split("\n")
    title = lines[0] if lines else entity
    title = title.replace("#", "").replace("*", "").strip()

    description = ""
    for line in lines[1:6]:
        clean = line.replace("#", "").replace("*", "").strip()
        if clean and len(clean) > 20:
            description = clean[:160]
            break
    if not description:
        description = "Artigo sobre {}".format(entity)

    slug = entity.lower().strip()
    slug = slug.replace(" ", "-").replace(".", "").replace(",", "")
    slug = re.sub(r"[^a-z0-9-]", "", slug)

    # Tags incluem SEMPRE o nome completo da entidade para SEO de marca
    entity_lower = entity.lower()
    # Nome completo sem acentos para tag SEO (Google usa versão sem acento)
    import unicodedata as _ud
    entity_ascii = "".join(
        c for c in _ud.normalize("NFKD", entity_lower)
        if not _ud.combining(c)
    ).strip()

    tags_map = {
        "artigo_linkedin":           [entity_ascii, "carreira", "liderança"],
        "biografia_executiva":       [entity_ascii, "biografia", "trajetória"],
        "esclarecimento_juridico":   [entity_ascii, "esclarecimento", "transparência"],
        "perfil_institucional":      [entity_ascii, "perfil", "institucional"],
        "comunicado_imprensa":       [entity_ascii, "comunicado", "imprensa"],
        "faq_transparencia":         [entity_ascii, "perguntas frequentes", "transparência"],
        "roteiro_youtube":           [entity_ascii, "youtube", "vídeo"],
        "site_institucional":        [entity_ascii, "site oficial", "institucional"],
        "medium":                    [entity_ascii, "carreira", "história"],
        "entrevista_midia_setorial": [entity_ascii, "entrevista", "mercado"],
    }
    tags = tags_map.get(asset_type, [entity_ascii])

    return {
        "title":              title[:70],
        "meta_description":   description[:160],
        "slug":               slug,
        "tags":               tags,
        "suggested_filename": "{}-{}.html".format(slug, asset_type),
    }


def _extract_structured_data(asset_type: str, article: str, entity: str) -> dict | None:
    """Extrai structured data JSON-LD do artigo gerado (se presente)."""
    import json as _json
    # Procura por bloco ```json ... ``` no artigo
    m = re.search(r"```json\s*\n(.+?)\n\s*```", article, re.DOTALL)
    if m:
        try:
            data = _json.loads(m.group(1))
            return data
        except Exception:
            pass
    # Se não encontrou bloco JSON, gera schema mínimo por tipo
    if asset_type == "faq_transparencia":
        lines = [l.strip() for l in article.split("\n") if l.strip()]
        questions = [l for l in lines if l.startswith("###")]
        if questions:
            return {
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [{"@type": "Question", "name": q.replace("###", "").strip(), "acceptedAnswer": {"@type": "Answer", "text": ""}} for q in questions[:10]],
            }
    if asset_type == "biografia_executiva":
        return {
            "@context": "https://schema.org",
            "@type": "Person",
            "name": entity,
            "description": "",
        }
    return None


# ── Semantic Variation Engine ─────────────────────────────────────────────────

# 6 enquadramentos narrativos distintos para evitar footprint artificial.
# O Google penaliza: mesmo texto + mesmo dia + mesmas keywords + mesmo enquadramento.
# Solução: mesma narrativa core, 6 perspectivas diferentes.

_VARIATION_FRAMES: dict[str, dict] = {
    "institucional": {
        "label": "Declaração Institucional",
        "directive": (
            "Reescreva este conteúdo como uma declaração institucional formal. "
            "Tom: corporativo, impessoal, preciso. "
            "Perspectiva: a organização fala sobre si mesma em terceira pessoa. "
            "Destaque: posição de mercado, governança, compliance, responsabilidade. "
            "Evite: opiniões pessoais, informalidade, linguagem de marketing."
        ),
        "best_for": ["press_release", "boilerplate", "institutional_profile"],
        "platforms": ["einpresswire", "globenewswire", "prnewswire"],
    },
    "opiniao_tecnica": {
        "label": "Opinião Técnica",
        "directive": (
            "Reescreva este conteúdo como artigo de opinião técnica. "
            "Tom: especialista, analítico, direto. "
            "Perspectiva: o indivíduo compartilha análise baseada em dados e experiência prática. "
            "Destaque: metodologia, evidências, conclusões não-óbvias, exemplos concretos. "
            "Evite: clichês, afirmações sem suporte, superlativos."
        ),
        "best_for": ["linkedin_article", "thought_leadership", "hackernoon_post"],
        "platforms": ["linkedin", "medium", "hackernoon"],
    },
    "compliance_commentary": {
        "label": "Comentário de Compliance",
        "directive": (
            "Reescreva este conteúdo do ponto de vista de compliance e governança. "
            "Tom: cauteloso, preciso, orientado a riscos. "
            "Perspectiva: um profissional de compliance avalia implicações e salvaguardas. "
            "Destaque: regulatório, controles internos, transparência, due diligence. "
            "Evite: linguagem comercial, promessas, afirmações absolutas."
        ),
        "best_for": ["legal_clarification", "faq_transparencia", "compliance_note"],
        "platforms": ["substack", "wordpress", "ghost"],
    },
    "analise_mercado": {
        "label": "Análise de Mercado",
        "directive": (
            "Reescreva este conteúdo como análise de mercado e setor. "
            "Tom: analítico, contextualizado, orientado a tendências. "
            "Perspectiva: um analista de setor avalia o contexto macro e micro. "
            "Destaque: dados de mercado, comparações com peers, implicações setoriais, cenários. "
            "Evite: foco excessivo em uma única empresa, linguagem promocional."
        ),
        "best_for": ["market_commentary", "sector_analysis", "investor_note"],
        "platforms": ["substack", "medium", "globenewswire"],
    },
    "nota_fundador": {
        "label": "Nota do Fundador / Executivo",
        "directive": (
            "Reescreva este conteúdo como nota pessoal de um fundador ou executivo. "
            "Tom: direto, reflexivo, autêntico — sem ser informal. "
            "Perspectiva: a pessoa fala em primeira pessoa sobre decisões, aprendizados, contexto. "
            "Destaque: motivação por trás de decisões, contexto pessoal verificável, visão de futuro específica. "
            "Evite: discurso corporativo, frases feitas, autolouvação."
        ),
        "best_for": ["executive_bio", "founder_letter", "linkedin_personal"],
        "platforms": ["linkedin", "medium", "substack"],
    },
    "insight_operacional": {
        "label": "Insight Operacional",
        "directive": (
            "Reescreva este conteúdo como insight operacional de bastidores. "
            "Tom: prático, específico, orientado a processo. "
            "Perspectiva: um profissional compartilha o que aprendeu operando no dia a dia. "
            "Destaque: processos reais, erros cometidos, soluções encontradas, métricas concretas. "
            "Evite: teoria sem prática, generalidades, linguagem acadêmica."
        ),
        "best_for": ["how_to", "case_study", "operational_guide"],
        "platforms": ["hackernoon", "devto", "medium"],
    },
}


def generate_semantic_variations(
    entity: str,
    base_article: str,
    asset_type: str,
    frames: list[str] | None = None,
    model: str = "openai/gpt-4o-mini",
) -> dict[str, dict]:
    """
    Gera variações semânticas do artigo base usando enquadramentos diferentes.
    Cada variação usa a MESMA narrativa core mas com perspectiva, tom e ênfase distintos.

    Isso evita footprint artificial de mass-posting:
    - Mesma mensagem, 6 formatos distintos
    - Google não penaliza conteúdo que PARECE diferente mas é semanticamente coerente
    - LLMs citam fontes diferentes → mais pontos de entrada no AI Overview

    Args:
        frames: lista de chaves de _VARIATION_FRAMES a usar (None = todas as 6)

    Returns:
        dict {frame_key: {"label", "body", "platform_targets", "word_count", "frame_directive"}}
    """
    if frames is None:
        frames = list(_VARIATION_FRAMES.keys())

    results: dict[str, dict] = {}

    for frame_key in frames:
        frame = _VARIATION_FRAMES.get(frame_key)
        if not frame:
            continue

        prompt = f"""Você é um especialista em comunicação estratégica.

TAREFA: Reescreva o conteúdo abaixo usando o enquadramento especificado.
A mensagem central DEVE permanecer a mesma. O que muda é: perspectiva, tom, ênfase, estrutura narrativa.

ENTIDADE: {entity}
ENQUADRAMENTO: {frame['label']}
DIRETIVA: {frame['directive']}

CONTEÚDO ORIGINAL:
{base_article[:3000]}

REGRAS:
- Manter os fatos e afirmações centrais idênticos
- Extensão: 600-900 caracteres
- Sem introdução explicando que é uma reescrita
- Saída: apenas o texto reescrito, sem comentários adicionais
"""

        try:
            result = call_openrouter(prompt, model=model, max_tokens=600)
            body = result.get("content", "") if isinstance(result, dict) else str(result)
            results[frame_key] = {
                "label": frame["label"],
                "body": body.strip(),
                "platform_targets": frame["platforms"],
                "word_count": len(body.split()),
                "frame_directive": frame["directive"],
                "asset_type": asset_type,
                "entity": entity,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            results[frame_key] = {
                "label": frame["label"],
                "body": "",
                "error": str(e),
                "platform_targets": frame["platforms"],
            }

    return results


def get_variation_frames() -> dict:
    """Retorna metadados de todos os enquadramentos disponíveis."""
    return {
        k: {
            "label": v["label"],
            "best_for": v["best_for"],
            "platforms": v["platforms"],
        }
        for k, v in _VARIATION_FRAMES.items()
    }
