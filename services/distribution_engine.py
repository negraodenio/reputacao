"""
Distribution Engine — Narrative Synchronization Across All Channels.

Três camadas:
  CAMADA 1 — Controlled Media (WordPress, Medium, LinkedIn, YouTube, Ghost)
  CAMADA 2 — Newswire Distribution (EIN, GlobeNewswire, PR Newswire, Dino)
  CAMADA 3 — Ads (Google Ads, LinkedIn Ads, Meta Ads, YouTube Ads)

Cada plataforma tem:
  - Distribution Authority Score (0-100)
  - Outranking Potential (composto de authority, speed, permanence, CTR, EEAT, entity trust)
  - Status: free / freemium / paid / enterprise
  - API wrapper quando disponível
"""
import json, re, os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ── Distribution Authority Matrix ───────────────────────────────────────────

@dataclass
class Platform:
    name: str
    type: str                 # newswire / portal / social / blog / video / newsletter / directory
    region: str               # BR / PT / ES / US / LATAM / GLOBAL
    authority: int            # 0-100 (domain authority aproximada)
    speed: str                # Muito rápida / Rápida / Média / Lenta
    permanence: str           # Permanente / Alta / Média / Baixa
    google_news: bool
    api: bool
    api_type: str             # REST/OAuth / REST/JWT / REST / Google API / OAuth
    pricing: str              # free / freemium / paid / enterprise
    tier: str                 # S / A / B / C
    estimated_cost: str = "—"
    notes: str = ""
    # ── Novos scores v2 ──────────────────────────────────────────────────
    # persistence: quão duradouro é o conteúdo publicado
    #   "Muito Alta" (Forbes, YouTube, LinkedIn = permanente indexado)
    #   "Alta" (Medium, Substack = raramente desindexado)
    #   "Média" (newswires = 1-5 anos no índice)
    #   "Baixa" (PR syndication farms = removido em meses)
    persistence: str = "Alta"
    # ai_citation: probabilidade de ser citado por LLMs (ChatGPT, Gemini, Perplexity)
    #   Baseado em: DA + frequência nos dados de treino + tipo de conteúdo
    #   0-100, baseado em análise de fontes citadas por LLMs em 2025/2026
    ai_citation: int = 50

    def outranking_potential(self) -> int:
        """
        Score composto 0-100 v2:
          authority(30%) + speed(15%) + permanence(10%)
          + google_news(10%) + api(5%) + persistence(15%) + ai_citation(15%)
        """
        a = self.authority * 0.30
        speed_map = {"Muito rápida": 100, "Rápida": 75, "Média": 50, "Lenta": 25}
        s = speed_map.get(self.speed, 50) * 0.15
        perm_map = {"Permanente": 100, "Alta": 80, "Média": 50, "Baixa": 20}
        p = perm_map.get(self.permanence, 50) * 0.10
        gn = (100 if self.google_news else 0) * 0.10
        api_score = (100 if self.api else 0) * 0.05
        pers_map = {"Muito Alta": 100, "Alta": 75, "Média": 45, "Baixa": 15}
        pers = pers_map.get(self.persistence, 45) * 0.15
        ai = self.ai_citation * 0.15
        return int(a + s + p + gn + api_score + pers + ai)


PLATFORM_REGISTRY: dict[str, Platform] = {
    # ── TIER S ─────────────────────────────────────────────────────────
    "linkedin": Platform("LinkedIn Articles", "social", "GLOBAL", 98, "Muito rápida", "Permanente", True, True, "OAuth", "free", "S", notes="Thought leadership, DA 98, indexa em horas", persistence="Muito Alta", ai_citation=92),
    "youtube": Platform("YouTube", "video", "GLOBAL", 100, "Muito rápida", "Permanente", True, True, "Google API", "free", "S", notes="Segundo maior mecanismo de busca, CTR 2-5x texto. Transcrições automáticas indexam como texto.", persistence="Muito Alta", ai_citation=85),
    "medium": Platform("Medium", "blog", "GLOBAL", 94, "Muito rápida", "Permanente", True, True, "REST API", "free", "S", notes="Cross-publicação, indexa palavras-chave de marca em dias", persistence="Alta", ai_citation=88),
    "globenewswire": Platform("GlobeNewswire", "newswire", "GLOBAL", 92, "Muito rápida", "Permanente", True, True, "REST/JWT", "paid", "S", estimated_cost="$150-500/mês", notes="Muito forte para visibilidade em IA + Google News", persistence="Alta", ai_citation=82),
    "prnewswire": Platform("PR Newswire", "newswire", "GLOBAL", 93, "Muito rápida", "Permanente", True, True, "REST/OAuth", "enterprise", "S", estimated_cost="$500-2000/mês", notes="Distribuição premium global", persistence="Alta", ai_citation=84),
    "einpresswire": Platform("EIN Presswire", "newswire", "GLOBAL", 88, "Muito rápida", "Permanente", True, True, "API", "paid", "S", estimated_cost="$50-200/mês", notes="Melhor custo-benefício, indexação muito rápida", persistence="Média", ai_citation=62),

    # ── TIER A ──────────────────────────────────────────────────────────
    "businesswire": Platform("Business Wire", "newswire", "GLOBAL", 94, "Muito rápida", "Permanente", True, True, "REST/HMAC", "enterprise", "A", estimated_cost="$500+/mês", notes="Enterprise + financeiro, muito respeitado", persistence="Alta", ai_citation=80),
    "wordpress": Platform("WordPress.com", "blog", "GLOBAL", 92, "Rápida", "Permanente", True, True, "REST", "freemium", "A", notes="Microsites + blogs, controle total", persistence="Alta", ai_citation=72),
    "substack": Platform("Substack", "newsletter", "GLOBAL", 85, "Rápida", "Alta", True, False, "—", "free", "A", notes="Newsletter + SEO, API não oficial", persistence="Alta", ai_citation=70),
    "ghost": Platform("Ghost CMS", "blog", "GLOBAL", 88, "Rápida", "Permanente", True, True, "Admin API", "paid", "A", estimated_cost="$9-25/mês", notes="Newsroom próprio, API limpa", persistence="Alta", ai_citation=60),
    "newswire": Platform("Newswire.com", "newswire", "GLOBAL", 86, "Rápida", "Alta", True, True, "API", "paid", "A", estimated_cost="$100-400/mês", notes="Automação PR moderna", persistence="Média", ai_citation=58),
    "dino": Platform("Dino (Knewin)", "newswire", "BR", 82, "Muito rápida", "Alta", True, True, "REST", "paid", "A", estimated_cost="R$ 500-2000/mês", notes="Melhor custo-benefício BR, indexação rápida", persistence="Média", ai_citation=45),
    "einpresswire_br": Platform("EIN Presswire BR", "newswire", "BR", 85, "Muito rápida", "Permanente", True, True, "API", "paid", "A", estimated_cost="$50-200/mês", notes="Versão BR do EIN, syndication agressiva", persistence="Média", ai_citation=55),

    # ── TIER A — ADICIONADOS ─────────────────────────────────────────────
    "accesswire": Platform("Accesswire", "newswire", "GLOBAL", 82, "Rápida", "Permanente", True, True, "REST", "paid", "A", estimated_cost="$350/release", notes="Taxa fixa, word count ilimitado, distribui Yahoo Finance e MarketWatch", persistence="Média", ai_citation=65),
    "ereleases": Platform("eReleases", "newswire", "GLOBAL", 80, "Rápida", "Alta", True, True, "REST", "paid", "A", estimated_cost="$105-200/release", notes="Revendedor da PR Newswire. Acesso à rede premium por fração do custo", persistence="Média", ai_citation=60),
    "crunchbase": Platform("Crunchbase", "directory", "GLOBAL", 81, "Rápida", "Permanente", True, True, "REST/OAuth", "freemium", "A", notes="Perfil de fundador + empresa. Citação permanente. Essencial para executivos tech e Painel de Conhecimento", persistence="Muito Alta", ai_citation=78),
    "google_business": Platform("Google Business Profile", "directory", "GLOBAL", 100, "Muito rápida", "Permanente", True, True, "Google API", "free", "A", notes="DA efetivo 100 (Google). Posts indexam em horas. Obrigatório para executivos com empresa", persistence="Muito Alta", ai_citation=90),

    # ── TIER B — CONTEÚDO DE AUTORIDADE (adicionados) ───────────────────
    "hackernoon": Platform("HackerNoon", "blog", "GLOBAL", 85, "Muito rápida", "Permanente", True, True, "REST", "free", "B", notes="Guest posts indexam em horas. Público tech/fundadores global.", persistence="Alta", ai_citation=72),
    "devto": Platform("Dev.to", "blog", "GLOBAL", 75, "Rápida", "Alta", True, True, "REST", "free", "B", notes="Comunidade dev ativa. Indexação rápida. Nicho: fundadores técnicos.", persistence="Alta", ai_citation=55),
    "vimeo": Platform("Vimeo", "video", "GLOBAL", 93, "Rápida", "Permanente", True, True, "REST", "freemium", "B", notes="DA 93, menos competição que YouTube. Indexa para buscas de marca.", persistence="Alta", ai_citation=50),
    "github": Platform("GitHub", "social", "GLOBAL", 98, "Rápida", "Permanente", False, True, "REST", "free", "B", notes="Perfil + README indexa para fundadores técnicos. Gists ranqueiam para nome.", persistence="Muito Alta", ai_citation=65),
    "24press": Platform("24-7 Press Release", "newswire", "US", 74, "Média", "Alta", True, True, "API", "freemium", "B", estimated_cost="$29-389/release", notes="Freemium funcional para testar mensagens. Google News não garantido no plano básico.", persistence="Baixa", ai_citation=30),
    "angellist": Platform("AngelList / Wellfound", "directory", "GLOBAL", 72, "Rápida", "Permanente", False, True, "REST", "free", "B", notes="Perfil de startup + equipe. Backlink dofollow. Relevante para fundadores.", persistence="Alta", ai_citation=48),

    # ── TIER B — BRASIL ─────────────────────────────────────────────────
    "canaltech": Platform("Canaltech", "portal", "BR", 80, "Rápida", "Média", True, False, "—", "free", "B", notes="Tecnologia, aceita guest posts"),
    "itforum": Platform("IT Forum", "portal", "BR", 76, "Rápida", "Média", True, False, "—", "free", "B", notes="TI, setorial"),
    "startse": Platform("StartSe", "portal", "BR", 78, "Rápida", "Média", True, False, "—", "free", "B", notes="Startups/Tech"),
    "baguete": Platform("Baguete", "portal", "BR", 72, "Média", "Média", True, False, "—", "free", "B", notes="TI setorial"),
    "infomoney": Platform("InfoMoney", "portal", "BR", 85, "Rápida", "Alta", True, False, "—", "free", "B", notes="Financeiro, alto authority"),
    "investnews": Platform("InvestNews", "portal", "BR", 80, "Rápida", "Alta", True, False, "—", "free", "B", notes="Financeiro"),
    "moneytimes": Platform("MoneyTimes", "portal", "BR", 79, "Rápida", "Média", True, False, "—", "free", "B", notes="Financeiro"),
    "suno": Platform("Suno Notícias", "portal", "BR", 82, "Rápida", "Alta", True, False, "—", "free", "B", notes="Financeiro/investimentos"),
    "exame": Platform("Exame", "portal", "BR", 90, "Rápida", "Alta", True, False, "—", "free", "B", notes="Negócios, alto DA"),
    "estadao_empresas": Platform("Estadão Empresas", "portal", "BR", 91, "Rápida", "Alta", True, False, "—", "free", "B", notes="Negócios, alto DA"),
    "pegn": Platform("PEGN", "portal", "BR", 84, "Rápida", "Média", True, False, "—", "free", "B", notes="PME"),
    "uol_economia": Platform("UOL Economia", "portal", "BR", 92, "Rápida", "Alta", True, False, "—", "free", "B", notes="Geral, alto DA"),
    "terra_economia": Platform("Terra Economia", "portal", "BR", 86, "Rápida", "Média", True, False, "—", "free", "B", notes="Geral"),
    "ti_inside": Platform("TI Inside", "portal", "BR", 74, "Rápida", "Média", True, False, "—", "free", "B", notes="TI corporativa, CIOs, transformação digital. Audiência B2B qualificada."),
    "valor_economico": Platform("Valor Econômico", "portal", "BR", 93, "Rápida", "Alta", True, False, "—", "free", "A", notes="Maior jornal de negócios BR. DA 93. Referência para Google News financeiro e AI citation.", persistence="Muito Alta", ai_citation=82),

    # ── TIER B — PORTUGAL ───────────────────────────────────────────────
    "pplware": Platform("Pplware", "portal", "PT", 76, "Rápida", "Média", True, False, "—", "free", "B", notes="Tecnologia PT"),
    "4gnews": Platform("4gnews", "portal", "PT", 74, "Rápida", "Média", True, False, "—", "free", "B", notes="Tecnologia PT"),
    "leakpt": Platform("Leak.pt", "portal", "PT", 72, "Rápida", "Média", True, False, "—", "free", "B", notes="Tecnologia PT"),
    "eco": Platform("ECO", "portal", "PT", 82, "Rápida", "Alta", True, False, "—", "free", "B", notes="Economia PT"),
    "jornal_economico": Platform("Jornal Económico", "portal", "PT", 80, "Rápida", "Alta", True, False, "—", "free", "B", notes="Economia PT"),
    "observador": Platform("Observador", "portal", "PT", 86, "Rápida", "Alta", True, False, "—", "free", "B", notes="Geral PT"),
    "dinheiro_vivo": Platform("Dinheiro Vivo", "portal", "PT", 78, "Rápida", "Média", True, False, "—", "free", "B", notes="Economia PT"),
    "cision_pt": Platform("Cision Portugal", "newswire", "PT", 78, "Rápida", "Alta", True, True, "REST", "paid", "B", estimated_cost="Plano mensal", notes="Distribuição de releases para media PT. API disponível com plano pago.", persistence="Média", ai_citation=40),
    "presspoint_pt": Platform("Press Point Portugal", "newswire", "PT", 72, "Rápida", "Média", True, True, "API", "paid", "B", estimated_cost="Por release", notes="Distribuição PT/PALOP. Indexação Google News PT.", persistence="Média", ai_citation=30),
    "pressrelease_pt": Platform("Press Release Portugal", "newswire", "PT", 68, "Rápida", "Média", True, False, "—", "freemium", "B", notes="Portal de releases PT. Freemium com plano básico gratuito.", persistence="Baixa", ai_citation=25),

    # ── TIER B — ESPANHA ────────────────────────────────────────────────
    "xataka": Platform("Xataka", "portal", "ES", 84, "Rápida", "Alta", True, False, "—", "free", "B", notes="Tecnologia ES"),
    "genbeta": Platform("Genbeta", "portal", "ES", 80, "Rápida", "Média", True, False, "—", "free", "B", notes="Tecnologia ES"),
    "expansion": Platform("Expansión", "portal", "ES", 88, "Rápida", "Alta", True, False, "—", "free", "B", notes="Economia ES"),
    "cincodias": Platform("Cinco Días", "portal", "ES", 86, "Rápida", "Alta", True, False, "—", "free", "B", notes="Economia ES"),
    "elpais": Platform("El País", "portal", "ES", 95, "Rápida", "Permanente", True, False, "—", "free", "A", notes="Maior jornal ES. DA 95. Referência global em espanhol. Alto AI citation.", persistence="Muito Alta", ai_citation=88),
    "elmundo": Platform("El Mundo", "portal", "ES", 93, "Rápida", "Permanente", True, False, "—", "free", "A", notes="Segundo maior jornal ES. DA 93. Forte Google News ES.", persistence="Muito Alta", ai_citation=80),
    "abc_es": Platform("ABC España", "portal", "ES", 90, "Rápida", "Alta", True, False, "—", "free", "B", notes="Jornal tradicional ES. DA 90. Forte para negócios e política.", persistence="Muito Alta", ai_citation=72),
    "lavanguardia": Platform("La Vanguardia", "portal", "ES", 91, "Rápida", "Permanente", True, False, "—", "free", "B", notes="Jornal ES. DA 91. Muito forte para audiência catalã e internacional.", persistence="Muito Alta", ai_citation=75),

    # ── TIER B — EUA ────────────────────────────────────────────────────
    "techcrunch": Platform("TechCrunch", "portal", "US", 93, "Rápida", "Permanente", True, False, "—", "free", "B", notes="Tech, DA 93, guest post raro", persistence="Muito Alta", ai_citation=80),
    "venturebeat": Platform("VentureBeat", "portal", "US", 90, "Rápida", "Permanente", True, False, "—", "free", "B", notes="Tech/VC", persistence="Muito Alta", ai_citation=72),
    "forbes": Platform("Forbes", "portal", "US", 95, "Rápida", "Permanente", True, False, "—", "free", "B", notes="Negócios, DA 95, conselho editorial", persistence="Muito Alta", ai_citation=90),
    "businessinsider": Platform("Business Insider", "portal", "US", 92, "Rápida", "Permanente", True, False, "—", "free", "B", notes="Negócios", persistence="Muito Alta", ai_citation=75),
    "fastcompany": Platform("Fast Company", "portal", "US", 90, "Rápida", "Permanente", True, False, "—", "free", "B", notes="Inovação", persistence="Muito Alta", ai_citation=70),
    "inc": Platform("Inc.", "portal", "US", 89, "Rápida", "Permanente", True, False, "—", "free", "B", notes="Empreendedorismo", persistence="Muito Alta", ai_citation=68),
    "wired": Platform("Wired", "portal", "US", 91, "Rápida", "Permanente", True, False, "—", "free", "B", notes="Tech e cultura digital. DA 91. Forte AI citation — muito citado por LLMs para tópicos tech.", persistence="Muito Alta", ai_citation=78),

    # ── TIER C — PORTAIS ADICIONAIS BR ──────────────────────────────────
    "maxpress": Platform("Maxpress", "portal", "BR", 78, "Média", "Média", True, True, "REST", "paid", "C", estimated_cost="R$ 200-500/mês", notes="Muito usado em PR BR"),
    "b2press": Platform("B2Press LATAM", "newswire", "LATAM", 80, "Rápida", "Alta", True, True, "REST", "paid", "C", estimated_cost="$100-300/mês", notes="Excelente para expansão LATAM"),
    "prwirenow": Platform("PRWireNOW Brasil", "newswire", "BR", 78, "Rápida", "Média", True, True, "API", "paid", "C", estimated_cost="$30-100/mês", notes="Syndication agressiva BR"),
    "issuewire": Platform("IssueWire", "newswire", "GLOBAL", 68, "Rápida", "Média", False, True, "API", "paid", "C", estimated_cost="$21-65/release", notes="Custo baixo, foco financeiro. Google News não garantido — verificar plano antes de usar.", persistence="Baixa", ai_citation=20),
    "clutch": Platform("Clutch.co", "directory", "GLOBAL", 80, "Média", "Permanente", False, False, "—", "free", "C", notes="Diretório B2B com avaliações. Indexa bem para buscas de marca de empresas.", persistence="Alta", ai_citation=45),

    # ── TIER B — NEWSWIRES VERIFICADAS (dados reais do site) ─────────────
    "prunderground": Platform(
        "PR Underground", "newswire", "US", 76, "Muito rápida", "Alta", True, False, "—", "paid", "B",
        estimated_cost="$74.99–419.99/release",
        notes="Google News direto. 150+ sites incluindo FOX TV regional, DigitalJournal. "
              "Plano US National ($419): Yahoo Finance + PRNewswire.com. "
              "Top 3 G2Crowd. Verificado e legítimo.",
        persistence="Média", ai_citation=42,
    ),
    "redpress": Platform(
        "RedPress", "newswire", "GLOBAL", 75, "Rápida", "Média", True, False, "—", "paid", "B",
        estimated_cost="$89–949/release",
        notes="Aggregator de syndication. Plano Basic ($89) DA 72, 300+ sites. "
              "Plano Growth ($279) DA 94, 530+ sites incluindo AP e Business Insider. "
              "Google News indexado. Usar plano Core ($219) ou superior para impacto real.",
        persistence="Baixa", ai_citation=30,
    ),
    "prweb": Platform(
        "PRWeb Brasil", "newswire", "BR", 74, "Rápida", "Média", True, True, "API", "paid", "B",
        estimated_cost="R$200-500/release",
        notes="Distribui releases para media BR. API disponível com conta ativa.",
        persistence="Média", ai_citation=35,
    ),
    "aion": Platform(
        "AION (Assessoria de Imprensa Online)", "newswire", "BR", 65, "Rápida", "Média", True, False, "—", "paid", "C",
        estimated_cost="R$150-300/release",
        notes="Portal de distribuição BR. Formulário público. Indexa no Google.",
        persistence="Baixa", ai_citation=20,
    ),
    "glassdoor": Platform("Glassdoor", "directory", "GLOBAL", 92, "Média", "Permanente", False, False, "—", "free", "C", notes="Perfil de empresa + CEO. Alto DA mas baixo controle de narrativa.", persistence="Alta", ai_citation=60),
    "trustpilot": Platform("Trustpilot", "directory", "GLOBAL", 91, "Média", "Alta", False, False, "—", "free", "C", notes="Avaliações de empresa. Influencia SERP para buscas de marca. Risco: avaliações negativas.", persistence="Alta", ai_citation=55),
    "startupranking": Platform("StartupRanking", "directory", "GLOBAL", 62, "Lenta", "Permanente", False, False, "—", "free", "C", notes="DA 60+, perfil de startup com link dofollow. Complementar.", persistence="Média", ai_citation=20),
}


# ── Platform type groupings ─────────────────────────────────────────────────

def platforms_by_region(region: str) -> dict[str, Platform]:
    """Filter platforms by region: BR / PT / ES / US / LATAM / GLOBAL."""
    return {k: v for k, v in PLATFORM_REGISTRY.items() if v.region == region}


def platforms_by_tier(tier: str) -> dict[str, Platform]:
    return {k: v for k, v in PLATFORM_REGISTRY.items() if v.tier == tier}


def platforms_by_type(ptype: str) -> dict[str, Platform]:
    return {k: v for k, v in PLATFORM_REGISTRY.items() if v.type == ptype}


def platforms_with_api() -> dict[str, Platform]:
    return {k: v for k, v in PLATFORM_REGISTRY.items() if v.api}


def free_platforms() -> dict[str, Platform]:
    return {k: v for k, v in PLATFORM_REGISTRY.items() if v.pricing == "free"}


# ── Manual Publishing Guides ─────────────────────────────────────────────────
# Para cada plataforma não-automatizável, instruções detalhadas com:
#   - URL exata para abrir (deep link quando possível)
#   - Passos numerados com o que fazer em cada campo
#   - O que copiar de onde
#   - Dicas específicas da plataforma

MANUAL_GUIDES: dict[str, dict] = {

    # ── CONTEÚDO CONTROLADO ──────────────────────────────────────────────
    "linkedin": {
        "name": "LinkedIn Articles",
        "icon": "🔗",
        "automatable": True,
        "api_status": "API disponível — configurar LINKEDIN_TOKEN",
        "publish_url": "https://www.linkedin.com/pulse/write/",
        "login_url": "https://www.linkedin.com/login",
        "time_estimate": "5 minutos",
        "best_for": "Thought leadership, posicionamento profissional, branded search",
        "steps": [
            {"step": 1, "action": "Abrir LinkedIn e fazer login na conta do cliente"},
            {"step": 2, "action": "Clicar em 'Escrever artigo' no campo de post do feed (ou acessar o link direto acima)"},
            {"step": 3, "action": "No campo TÍTULO: colar o título do artigo gerado"},
            {"step": 4, "action": "No corpo do artigo: colar o texto completo"},
            {"step": 5, "action": "Adicionar imagem de capa: usar foto profissional do cliente ou imagem institucional"},
            {"step": 6, "action": "Clicar 'Publicar'"},
            {"step": 7, "action": "Após publicar: clicar nos 3 pontinhos do artigo → 'Fixar no topo do perfil'"},
            {"step": 8, "action": "Copiar a URL do artigo publicado e registrar para monitoramento"},
        ],
        "tips": [
            "Publicar entre 8h-10h ou 17h-19h em dias úteis — maior alcance orgânico",
            "Não adicionar hashtags no corpo — o LinkedIn penaliza densidade de hashtags",
            "Responder todos os comentários nas primeiras 2h aumenta distribuição orgânica",
            "Não compartilhar o artigo imediatamente após publicar — aguardar 1h",
        ],
        "seo_impact": "Indexado em 2-6h. Ranqueia para '[nome] linkedin' e '[nome] artigo'",
        "warning": None,
    },

    "medium": {
        "name": "Medium",
        "icon": "✍️",
        "automatable": True,
        "api_status": "API disponível (publica como draft) — configurar MEDIUM_TOKEN",
        "publish_url": "https://medium.com/new-story",
        "login_url": "https://medium.com/m/signin",
        "time_estimate": "8 minutos",
        "best_for": "Cross-publicação, indexação rápida de branded keywords, audiência global",
        "steps": [
            {"step": 1, "action": "Acessar medium.com e fazer login"},
            {"step": 2, "action": "Clicar no ícone de lápis (canto superior direito) ou acessar o link direto"},
            {"step": 3, "action": "No campo de TÍTULO: colar o título do artigo"},
            {"step": 4, "action": "No corpo: colar o texto (Medium aceita Markdown automaticamente)"},
            {"step": 5, "action": "Clicar em 'Publicar' (canto superior direito)"},
            {"step": 6, "action": "Adicionar tags (máximo 5): usar as tags do SEO metadata gerado"},
            {"step": 7, "action": "Em 'Publicação': adicionar em publicações do setor se disponível"},
            {"step": 8, "action": "Confirmar publicação"},
        ],
        "tips": [
            "Se tiver MEDIUM_TOKEN configurado, o sistema publica automaticamente como DRAFT — só precisa confirmar",
            "Submeter a publicações Medium do setor aumenta o alcance 3-5x",
            "Importação de URL disponível: Medium pode importar de WordPress/Ghost automaticamente",
        ],
        "seo_impact": "Indexado em 2-8h. DA 94 — ranqueia bem para branded e topic searches",
        "warning": None,
    },

    "youtube": {
        "name": "YouTube",
        "icon": "📺",
        "automatable": False,
        "api_status": "Requer gravação do vídeo — não automatizável",
        "publish_url": "https://studio.youtube.com",
        "login_url": "https://accounts.google.com/signin",
        "time_estimate": "30-60 min (gravação) + 15 min (upload)",
        "best_for": "Transcrições automáticas indexam como texto. CTR 2-5x maior que resultados de texto",
        "steps": [
            {"step": 1, "action": "Gravar o vídeo seguindo o roteiro gerado (4-6 minutos recomendado)"},
            {"step": 2, "action": "Acessar studio.youtube.com com a conta do cliente"},
            {"step": 3, "action": "Clicar em 'Criar' → 'Fazer upload de vídeos'"},
            {"step": 4, "action": "Selecionar o arquivo de vídeo"},
            {"step": 5, "action": "TÍTULO: colar o título SEO gerado (máx 100 caracteres)"},
            {"step": 6, "action": "DESCRIÇÃO: colar a descrição completa gerada (máx 5.000 caracteres)"},
            {"step": 7, "action": "TAGS: colar as tags geradas separadas por vírgula"},
            {"step": 8, "action": "Thumbnail: usar foto profissional do cliente + texto do título"},
            {"step": 9, "action": "Definir visibilidade: Público (para indexação imediata) ou Não listado (para controle)"},
            {"step": 10, "action": "Publicar e copiar URL para monitoramento"},
        ],
        "tips": [
            "Ativar legendas automáticas: as transcrições geradas pelo YouTube indexam como texto no Google",
            "Vídeos de 4-8 minutos têm o melhor balanço de retenção e indexação",
            "Adicionar o nome completo da entidade nos primeiros 30 segundos da fala",
            "Fixar o vídeo na aba 'Em destaque' do canal",
        ],
        "seo_impact": "Indexado em 24-48h. Aparece em Google Video results. Transcrições indexam como texto.",
        "warning": "Requer equipamento de gravação. O sistema gera o roteiro completo — a câmera é sua.",
    },

    "substack": {
        "name": "Substack",
        "icon": "📧",
        "automatable": False,
        "api_status": "Sem API pública — publicação manual obrigatória",
        "publish_url": "https://substack.com/publish",
        "login_url": "https://substack.com/sign-in",
        "time_estimate": "10 minutos",
        "best_for": "Newsletter para assinantes + indexação web como post permanente",
        "steps": [
            {"step": 1, "action": "Acessar substack.com e fazer login na conta do cliente"},
            {"step": 2, "action": "Clicar em 'New post' (canto superior direito)"},
            {"step": 3, "action": "TÍTULO: colar o título gerado"},
            {"step": 4, "action": "SUBTÍTULO: usar a meta_description do SEO gerado"},
            {"step": 5, "action": "CORPO: colar o texto (Substack aceita Markdown)"},
            {"step": 6, "action": "Adicionar imagem de capa"},
            {"step": 7, "action": "Seção 'Publicar': escolher 'Todos' para publicar para assinantes E web"},
            {"step": 8, "action": "Clicar 'Publicar agora'"},
        ],
        "tips": [
            "Publicar simultaneamente como post web e newsletter maximiza alcance",
            "O URL público do Substack ranqueia como um post normal no Google",
            "Adicionar links para artigos LinkedIn e Medium no corpo aumenta o link juice entre os ativos",
        ],
        "seo_impact": "Indexado em 6-24h. Posts públicos ranqueiam no Google como páginas normais.",
        "warning": None,
    },

    "hackernoon": {
        "name": "HackerNoon",
        "icon": "👾",
        "automatable": False,
        "api_status": "Sem API de publicação — submissão editorial manual",
        "publish_url": "https://app.hackernoon.com/new",
        "login_url": "https://app.hackernoon.com/login",
        "time_estimate": "15 minutos",
        "best_for": "Founders tech, executives de produto, autoridade em setor tecnológico",
        "steps": [
            {"step": 1, "action": "Criar conta em hackernoon.com (gratuito) ou fazer login"},
            {"step": 2, "action": "Clicar em 'Write' (canto superior direito)"},
            {"step": 3, "action": "TÍTULO: colar o título do artigo (variação 'Opinião Técnica' recomendada)"},
            {"step": 4, "action": "CORPO: colar o texto em Markdown"},
            {"step": 5, "action": "Adicionar tags: usar as tags do SEO metadata"},
            {"step": 6, "action": "Clicar 'Submit for Review' — os editores do HackerNoon revisam (24-72h)"},
            {"step": 7, "action": "Após aprovação, o artigo é publicado automaticamente"},
        ],
        "tips": [
            "HackerNoon tem revisão editorial — artigos genéricos são rejeitados",
            "Usar a variação 'Opinião Técnica' ou 'Insight Operacional' do Motor de Variação Semântica",
            "Mencionar dados concretos, números e experiência real aumenta chance de aprovação",
            "Tempo médio de aprovação: 24-72h",
        ],
        "seo_impact": "Indexado em 2-6h após aprovação. DA ~85. Ranqueia muito bem para topic searches.",
        "warning": "Revisão editorial obrigatória. Conteúdo puramente promocional é rejeitado.",
    },

    # ── PORTAIS EDITORIAIS BR ────────────────────────────────────────────
    "exame": {
        "name": "Exame",
        "icon": "📰",
        "automatable": False,
        "api_status": "Sem API — earned media ou conteúdo patrocinado",
        "publish_url": "https://exame.com/colaboradores/",
        "login_url": None,
        "time_estimate": "Variável — depende de aprovação editorial",
        "best_for": "Negócios, empreendedorismo, finanças. DA 90. Altíssima credibilidade BR.",
        "steps": [
            {"step": 1, "action": "Opção A (Colaborador): Acessar exame.com/colaboradores e submeter proposta"},
            {"step": 2, "action": "Opção B (Assessoria): Enviar press release para redação@exame.com"},
            {"step": 3, "action": "Opção C (Patrocinado): Contatar comercial@exame.com para branded content"},
            {"step": 4, "action": "Usar o press release gerado pelo sistema como base da submissão"},
        ],
        "tips": [
            "Exame aceita colaboradores com autoridade comprovada no setor",
            "O press release gerado pelo CouncilIA está no formato correto para submissão",
            "Conteúdo patrocinado tem label 'PATROCINADO' — menor peso editorial mas indexa",
        ],
        "seo_impact": "Publicação editorial ranqueia em 24h. Backlink de DA 90 é muito valioso.",
        "warning": "Não é possível garantir publicação — depende de decisão editorial.",
    },

    "infomoney": {
        "name": "InfoMoney",
        "icon": "💰",
        "automatable": False,
        "api_status": "Sem API — earned media ou assessoria de imprensa",
        "publish_url": "https://www.infomoney.com.br/contato/",
        "login_url": None,
        "time_estimate": "Variável",
        "best_for": "Clientes financeiros, investidores, setor econômico. DA 85.",
        "steps": [
            {"step": 1, "action": "Enviar press release para redacao@infomoney.com.br"},
            {"step": 2, "action": "Assunto do email: '[PAUTA] ' + título do release"},
            {"step": 3, "action": "No corpo: primeiros 3 parágrafos do release (gancho)"},
            {"step": 4, "action": "Anexar o release completo em PDF"},
            {"step": 5, "action": "Incluir contato do porta-voz para entrevista"},
        ],
        "tips": [
            "InfoMoney foca em finanças pessoais, investimentos e economia",
            "Pautas com dados de mercado têm maior chance de cobertura",
            "Melhor horário para envio: 8h-10h em dias úteis",
        ],
        "seo_impact": "Artigo editorial ranqueia em Google News em 2-4h. DA 85.",
        "warning": "Sem garantia de publicação.",
    },

    "estadao_empresas": {
        "name": "Estadão Empresas",
        "icon": "📋",
        "automatable": False,
        "api_status": "Sem API — assessoria de imprensa",
        "publish_url": "https://www.estadao.com.br/contato/",
        "login_url": None,
        "time_estimate": "Variável",
        "best_for": "Negócios, grandes empresas, executivos. DA 91. Altíssima credibilidade.",
        "steps": [
            {"step": 1, "action": "Contatar via assessor de imprensa (não enviar diretamente à redação)"},
            {"step": 2, "action": "Para releases: redacao@estadao.com.br (pauta empresarial)"},
            {"step": 3, "action": "Usar o press release gerado + contexto estratégico do battle plan"},
        ],
        "tips": [
            "Estadão tem jornalistas setoriais — tentar identificar o repórter que cobre o setor do cliente",
            "Releases com números e dados têm muito mais chance",
        ],
        "seo_impact": "Uma citação no Estadão vale mais do que 50 releases em portais menores.",
        "warning": "Não enviar releases genéricos. Estadão ignora conteúdo sem ângulo jornalístico claro.",
    },

    # ── PORTAIS PT ───────────────────────────────────────────────────────
    "observador": {
        "name": "Observador",
        "icon": "🇵🇹",
        "automatable": False,
        "api_status": "Sem API — earned media",
        "publish_url": "https://observador.pt/sobre/contactos/",
        "login_url": None,
        "time_estimate": "Variável",
        "best_for": "Clientes em Portugal. DA 86. Maior portal de notícias PT.",
        "steps": [
            {"step": 1, "action": "Enviar press release para redacao@observador.pt"},
            {"step": 2, "action": "Para branded content: publicidade@observador.pt"},
            {"step": 3, "action": "Usar release gerado pelo sistema em PT-PT (não PT-BR)"},
        ],
        "tips": [
            "Usar variação do release em PT-PT, não PT-BR — vocabulário diferente",
            "O CouncilIA gera em PT-BR por padrão — rever termos como 'você' → 'você/tu'",
        ],
        "seo_impact": "Indexação em Google News PT em 2-4h.",
        "warning": "Conteúdo deve estar em português europeu.",
    },

    # ── DIRETÓRIOS DE AUTORIDADE ─────────────────────────────────────────
    "crunchbase": {
        "name": "Crunchbase",
        "icon": "🏢",
        "automatable": False,
        "api_status": "API de leitura disponível. Escrita requer plano pago ou manual.",
        "publish_url": "https://www.crunchbase.com/add-new",
        "login_url": "https://www.crunchbase.com/login",
        "time_estimate": "20 minutos (setup único)",
        "best_for": "Knowledge Panel, entity graph do Google, AI citation. Setup único, benefício permanente.",
        "steps": [
            {"step": 1, "action": "Criar conta em crunchbase.com (gratuito)"},
            {"step": 2, "action": "Clicar em 'Add to Crunchbase' → 'Person' (para executivo) ou 'Organization'"},
            {"step": 3, "action": "NOME: nome completo exato como aparece em outras plataformas"},
            {"step": 4, "action": "CARGO: título atual exato"},
            {"step": 5, "action": "BIO: usar a Biografia Executiva gerada pelo CouncilIA (versão curta)"},
            {"step": 6, "action": "LINKS: adicionar LinkedIn, site institucional, Twitter se existir"},
            {"step": 7, "action": "EMPRESA: vincular à organização — criar perfil de organização se não existir"},
            {"step": 8, "action": "Submeter para revisão (aprovação em 24-72h)"},
        ],
        "tips": [
            "Consistência de nome é crítica — usar exatamente o mesmo nome que está no LinkedIn",
            "Preencher TODOS os campos disponíveis — perfis incompletos têm menos peso para o Google",
            "Adicionar investimentos, board seats, conquistas verificáveis aumenta o AI citation score",
            "Vincular o perfil da pessoa à organização cria um grafo de entidades que o Google usa para KP",
        ],
        "seo_impact": "Crunchbase ranqueia na primeira página para '[nome] crunchbase' em 1-2 semanas. Alimenta Knowledge Panel.",
        "warning": "Aprovação editorial obrigatória — pode levar 24-72h.",
    },

    "google_business": {
        "name": "Google Business Profile",
        "icon": "🗺️",
        "automatable": False,
        "api_status": "API existe mas requer OAuth por conta — manual por cliente",
        "publish_url": "https://business.google.com/create",
        "login_url": "https://business.google.com/",
        "time_estimate": "30 minutos (setup único) + verificação postal 5-14 dias",
        "best_for": "Âncora do Knowledge Panel. DA efetivo 100. Obrigatório para executivos com empresa.",
        "steps": [
            {"step": 1, "action": "Acessar business.google.com com a conta Google do cliente"},
            {"step": 2, "action": "Clicar 'Gerenciar agora' ou 'Adicionar empresa'"},
            {"step": 3, "action": "NOME DA EMPRESA: nome exato da empresa do cliente"},
            {"step": 4, "action": "CATEGORIA: escolher a categoria principal do negócio"},
            {"step": 5, "action": "ENDEREÇO: endereço físico real (necessário para verificação)"},
            {"step": 6, "action": "TELEFONE: telefone comercial"},
            {"step": 7, "action": "SITE: URL do site institucional"},
            {"step": 8, "action": "Solicitar verificação (Google envia cartão postal com código)"},
            {"step": 9, "action": "Após verificação: preencher DESCRIÇÃO com o perfil institucional gerado"},
            {"step": 10, "action": "Adicionar fotos, horários, serviços"},
            {"step": 11, "action": "Publicar primeiro 'Post' com o artigo LinkedIn do cliente"},
        ],
        "tips": [
            "Verificação por cartão postal leva 5-14 dias — iniciar imediatamente",
            "Verificação por telefone ou email disponível para alguns negócios (mais rápido)",
            "Posts no Google Business indexam em 2-4h — usar para amplificar narrativa",
            "Manter perfil atualizado com posts semanais aumenta relevância para Google Maps e Knowledge Panel",
            "NAP (Nome, Endereço, Telefone) deve ser IDÊNTICO em todas as plataformas",
        ],
        "seo_impact": "Crítico para Knowledge Panel. Posts indexam como resultados regulares.",
        "warning": "Verificação física necessária. Processo não pode ser pulado.",
    },

    "glassdoor": {
        "name": "Glassdoor",
        "icon": "🏛️",
        "automatable": False,
        "api_status": "Sem API de escrita — manual",
        "publish_url": "https://www.glassdoor.com/employers/index.htm",
        "login_url": "https://www.glassdoor.com/employers/index.htm",
        "time_estimate": "20 minutos (setup único)",
        "best_for": "Perfil de empresa ranqueia para '[empresa] glassdoor'. DA 92.",
        "steps": [
            {"step": 1, "action": "Acessar glassdoor.com/employers e criar conta de empregador"},
            {"step": 2, "action": "Buscar a empresa — pode já existir um perfil criado por funcionários"},
            {"step": 3, "action": "Reivindicar o perfil como representante oficial"},
            {"step": 4, "action": "Preencher DESCRIÇÃO DA EMPRESA com o perfil institucional gerado"},
            {"step": 5, "action": "Adicionar missão, valores, benefícios, fotos do escritório"},
            {"step": 6, "action": "Verificar via email corporativo"},
        ],
        "tips": [
            "Reivindicar o perfil antes de um concorrente ou ex-funcionário o faça",
            "Perfil reivindicado permite responder a avaliações — importante para gestão de reputação",
        ],
        "seo_impact": "Ranqueia para '[empresa] avaliações' e '[empresa] glassdoor' em 1-2 semanas.",
        "warning": "RISCO: avaliações negativas de ex-funcionários aparecem publicamente. Configurar monitoramento antes.",
    },

    "startse": {
        "name": "StartSe",
        "icon": "🚀",
        "automatable": False,
        "api_status": "Sem API — submissão editorial",
        "publish_url": "https://startse.com/contato",
        "login_url": None,
        "time_estimate": "Variável",
        "best_for": "Founders, startups, inovação no Brasil. DA 78.",
        "steps": [
            {"step": 1, "action": "Enviar proposta de conteúdo para conteudo@startse.com"},
            {"step": 2, "action": "Assunto: 'Proposta de colaboração — [Nome do Cliente]'"},
            {"step": 3, "action": "Incluir: quem é o cliente, tema do artigo, por que é relevante para a audiência StartSe"},
            {"step": 4, "action": "Anexar artigo LinkedIn gerado como exemplo do nível de conteúdo"},
        ],
        "tips": [
            "StartSe foca em tech, inovação, startups e transformação digital",
            "Artigos com perspectiva de founder/empreendedor têm mais chance",
        ],
        "seo_impact": "Indexação em Google News BR em 2-4h.",
        "warning": None,
    },

    # ── NEWSWIRES MANUAIS ────────────────────────────────────────────────
    "globenewswire": {
        "name": "GlobeNewswire",
        "icon": "🌐",
        "automatable": True,
        "api_status": "API disponível — plano pago necessário ($150-500/mês)",
        "publish_url": "https://www.globenewswire.com/ReleaseApplication/",
        "login_url": "https://www.globenewswire.com/login",
        "time_estimate": "15 minutos",
        "best_for": "Distribuição global, AI Overview, Yahoo Finance, MarketWatch. Melhor para AI citation.",
        "steps": [
            {"step": 1, "action": "Criar conta em globenewswire.com ou fazer login"},
            {"step": 2, "action": "Clicar 'Submit a Release'"},
            {"step": 3, "action": "HEADLINE: colar o título do press release gerado"},
            {"step": 4, "action": "BODY: colar o press release completo"},
            {"step": 5, "action": "LANGUAGE: Portuguese (Brazil)"},
            {"step": 6, "action": "INDUSTRY: selecionar o setor do cliente"},
            {"step": 7, "action": "Revisar preview e confirmar distribuição"},
            {"step": 8, "action": "Pagar pela distribuição (cobrado por release)"},
        ],
        "tips": [
            "GlobeNewswire é uma das fontes mais citadas por LLMs — alto AI citation score (82)",
            "Indexado no Yahoo Finance e MarketWatch automaticamente",
            "Distribuição em PT-BR está disponível e indexa no Google News BR",
        ],
        "seo_impact": "Google News em 2-4h. Yahoo Finance em 4-8h. AI Overview em 24-72h.",
        "warning": "Cobrado por release. Verificar custo antes de confirmar.",
    },

    "einpresswire": {
        "name": "EIN Presswire",
        "icon": "📡",
        "automatable": True,
        "api_status": "API disponível — configurar EIN_API_KEY",
        "publish_url": "https://www.einpresswire.com/add-a-press-release/",
        "login_url": "https://www.einpresswire.com/account/login/",
        "time_estimate": "10 minutos",
        "best_for": "Melhor custo-benefício. Google News + 200+ portais. $50-200/release.",
        "steps": [
            {"step": 1, "action": "Fazer login em einpresswire.com"},
            {"step": 2, "action": "Clicar 'Add a Press Release'"},
            {"step": 3, "action": "HEADLINE: título do press release"},
            {"step": 4, "action": "BODY: corpo completo do release"},
            {"step": 5, "action": "LANGUAGE: Portuguese"},
            {"step": 6, "action": "INDUSTRY TAGS: setor do cliente"},
            {"step": 7, "action": "Selecionar plano de distribuição"},
            {"step": 8, "action": "Submit"},
        ],
        "tips": [
            "Se EIN_API_KEY estiver configurado, usar POST /api/publish/{slug} para automatizar",
            "Plano básico ($50) já inclui Google News — não precisa do plano premium para indexação",
        ],
        "seo_impact": "Google News em 1-4h. 200+ portais em 24h.",
        "warning": None,
    },

    # ── NOVOS — ES ───────────────────────────────────────────────────────
    "elpais": {
        "name": "El País",
        "icon": "🇪🇸",
        "automatable": False,
        "api_status": "Sem API — earned media ou conteúdo patrocinado",
        "publish_url": "https://elpais.com/sobre-el-pais/",
        "login_url": None,
        "time_estimate": "Variável — depende de relação com editor",
        "best_for": "Clientes com presença na Espanha ou América Latina. DA 95. Mais alto AI citation em ES.",
        "steps": [
            {"step": 1, "action": "Opção A: Contatar seção de negócios — economia@elpais.es"},
            {"step": 2, "action": "Opção B: Branded content — publicidad@elpais.es"},
            {"step": 3, "action": "Usar o press release gerado em ES (variação Cross-Language do Motor Semântico)"},
            {"step": 4, "action": "Para op-ed/coluna: proposta editorial com CV do cliente e resumo do artigo"},
        ],
        "tips": [
            "El País tem edição América Latina — forte para clientes BR com presença regional",
            "Artigos de opinião assinados por executivos têm mais peso editorial que press releases",
            "Conteúdo em espanhol neutro (não castelhano regional) tem alcance maior",
        ],
        "seo_impact": "DA 95. Uma citação no El País alimenta AI Overview em ES e LATAM.",
        "warning": "Sem garantia de publicação — editorial independente.",
    },

    "elmundo": {
        "name": "El Mundo",
        "icon": "🇪🇸",
        "automatable": False,
        "api_status": "Sem API — earned media",
        "publish_url": "https://www.elmundo.es/contacto.html",
        "login_url": None,
        "time_estimate": "Variável",
        "best_for": "Audiência conservadora e empresarial ES. DA 93.",
        "steps": [
            {"step": 1, "action": "Enviar press release para redaccion@elmundo.es"},
            {"step": 2, "action": "Seção Economia: economia@elmundo.es"},
            {"step": 3, "action": "Usar variação ES do press release gerado"},
        ],
        "tips": ["Foco em negócios, política econômica e empresas. Evitar tópicos sociais."],
        "seo_impact": "Google News ES em 2-4h.",
        "warning": None,
    },

    "lavanguardia": {
        "name": "La Vanguardia",
        "icon": "🇪🇸",
        "automatable": False,
        "api_status": "Sem API — earned media",
        "publish_url": "https://www.lavanguardia.com/participacion/",
        "login_url": None,
        "time_estimate": "Variável",
        "best_for": "Audiência catalã e espanhola. DA 91. Forte para tech e economia.",
        "steps": [
            {"step": 1, "action": "Contato redação: redaccio@lavanguardia.es"},
            {"step": 2, "action": "Seção economia: economia@lavanguardia.es"},
        ],
        "tips": ["La Vanguardia tem forte presença digital — artigos indexam rapidamente."],
        "seo_impact": "Google News ES em 2-4h. Forte presença em buscas catalãs.",
        "warning": None,
    },

    "wired": {
        "name": "Wired",
        "icon": "💡",
        "automatable": False,
        "api_status": "Sem API — earned media ou contribuição editorial",
        "publish_url": "https://www.wired.com/about/editorial-guidelines/",
        "login_url": None,
        "time_estimate": "Variável — alta exigência editorial",
        "best_for": "Founders tech, executivos de inovação, startups com tese forte. DA 91. AI citation 78.",
        "steps": [
            {"step": 1, "action": "Wired não aceita releases diretos — contato deve ser via assessor de imprensa"},
            {"step": 2, "action": "Para contribuição: editorial@wired.com com proposta de artigo (não o artigo pronto)"},
            {"step": 3, "action": "Proposta: 1 parágrafo sobre o argumento principal + por que é relevante AGORA"},
            {"step": 4, "action": "Usar a variação 'Opinião Técnica' do Motor Semântico como base"},
        ],
        "tips": [
            "Wired quer teses, não notícias — 'X vai mudar Y porque Z' funciona melhor que press release",
            "Referência a dados originais ou pesquisa própria aumenta drasticamente a chance de aceite",
            "AI citation altíssimo — uma publicação no Wired alimenta respostas do ChatGPT sobre o tema",
        ],
        "seo_impact": "DA 91. Backlink do Wired vale mais do que 100 releases em portais médios. AI citation 78.",
        "warning": "Muito difícil de publicar — reservar para clientes com histórico comprovado em tech.",
    },

    # ── NOVOS — PT ───────────────────────────────────────────────────────
    "cision_pt": {
        "name": "Cision Portugal",
        "icon": "🇵🇹",
        "automatable": True,
        "api_status": "API disponível com plano pago — contato comercial necessário",
        "publish_url": "https://www.cision.com/pt-pt/",
        "login_url": "https://app.cision.com/login",
        "time_estimate": "10 minutos (após conta configurada)",
        "best_for": "Distribuição de releases para media PT. Equivalente ao PR Newswire no mercado PT.",
        "steps": [
            {"step": 1, "action": "Criar conta em cision.com/pt-pt ou contatar vendas"},
            {"step": 2, "action": "Fazer login no painel Cision"},
            {"step": 3, "action": "Clicar 'Criar comunicado'"},
            {"step": 4, "action": "Colar título e corpo do press release gerado (versão PT-PT)"},
            {"step": 5, "action": "Selecionar lista de distribuição: Portugal — Geral ou por setor"},
            {"step": 6, "action": "Agendar ou publicar imediatamente"},
        ],
        "tips": [
            "Cision PT distribui para os principais media PT incluindo Público, Expresso, Jornal de Negócios",
            "Usar variação PT-PT do press release — vocabulário diferente do PT-BR",
        ],
        "seo_impact": "Google News PT em 2-4h. Distribuição para 200+ media PT.",
        "warning": "Plano pago necessário — verificar pricing antes.",
    },

    "presspoint_pt": {
        "name": "Press Point Portugal",
        "icon": "🇵🇹",
        "automatable": False,
        "api_status": "Sem API gratuita — envio via formulário web",
        "publish_url": "https://www.presspoint.pt/submeter-comunicado/",
        "login_url": "https://www.presspoint.pt/login/",
        "time_estimate": "10 minutos",
        "best_for": "Distribuição de releases PT/PALOP. Custo menor que Cision.",
        "steps": [
            {"step": 1, "action": "Criar conta em presspoint.pt"},
            {"step": 2, "action": "Aceder a 'Submeter Comunicado'"},
            {"step": 3, "action": "Preencher: título, texto, setor, contacto"},
            {"step": 4, "action": "Selecionar plano de distribuição"},
            {"step": 5, "action": "Submeter"},
        ],
        "tips": ["Boa opção para releases de menor custo em PT", "Indexa no Google News PT em algumas horas"],
        "seo_impact": "Google News PT em 2-8h.",
        "warning": None,
    },

    # ── NOVOS — BR ───────────────────────────────────────────────────────
    "valor_economico": {
        "name": "Valor Econômico",
        "icon": "💼",
        "automatable": False,
        "api_status": "Sem API — earned media ou anúncio publicitário",
        "publish_url": "https://valor.globo.com/contato.ghtml",
        "login_url": None,
        "time_estimate": "Variável — alta exigência editorial",
        "best_for": "Maior jornal de negócios BR. DA 93. Altíssimo AI citation (82). Referência para executivos e mercado financeiro.",
        "steps": [
            {"step": 1, "action": "Para releases: redacao@valor.com.br (triagem editorial rigorosa)"},
            {"step": 2, "action": "Para anúncios: publicidade@valor.com.br"},
            {"step": 3, "action": "Para opinião assinada: artigo@valor.com.br com proposta + CV"},
            {"step": 4, "action": "Usar press release gerado com dados financeiros reais e números concretos"},
        ],
        "tips": [
            "Valor só cobre o que tem impacto econômico verificável — evitar press releases genéricos",
            "Artigos de opinião de CFOs, CEOs e economistas têm muito mais chance que releases de assessoria",
            "Uma citação no Valor alimenta o AI Overview em buscas financeiras por meses",
        ],
        "seo_impact": "DA 93. Google News BR em 1-2h. AI citation 82 — muito citado por LLMs em consultas financeiras.",
        "warning": "Editorial completamente independente. Releases sem ângulo jornalístico são ignorados.",
    },

    "ti_inside": {
        "name": "TI Inside",
        "icon": "🖥️",
        "automatable": False,
        "api_status": "Sem API — earned media ou conteúdo patrocinado",
        "publish_url": "https://tiinside.com.br/contato/",
        "login_url": None,
        "time_estimate": "Variável",
        "best_for": "CIOs, CTOs, transformação digital, tecnologia corporativa. Audiência B2B qualificada.",
        "steps": [
            {"step": 1, "action": "Enviar press release para redacao@tiinside.com.br"},
            {"step": 2, "action": "Assunto: '[RELEASE] ' + título"},
            {"step": 3, "action": "Usar variação 'Insight Operacional' ou 'Opinião Técnica' do Motor Semântico"},
        ],
        "tips": [
            "TI Inside foca em tecnologia para empresas — cliente deve ter ângulo tech/digital",
            "Conteúdo sobre transformação digital, cloud, segurança e inovação corporativa tem preferência",
        ],
        "seo_impact": "DA 74. Google News BR em 2-6h. Audiência B2B qualificada.",
        "warning": None,
    },

    # ── PORTAIS BR — guias simplificados ─────────────────────────────────
    "uol_economia": {
        "name": "UOL Economia",
        "icon": "📰",
        "automatable": False,
        "api_status": "Sem API — earned media ou branded content",
        "publish_url": "https://economia.uol.com.br/",
        "login_url": None,
        "time_estimate": "Variável",
        "best_for": "Clientes BR com amplo alcance. DA 92. Alta audiência geral.",
        "steps": [
            {"step": 1, "action": "Enviar press release para redacao@uol.com.br"},
            {"step": 2, "action": "Para conteúdo patrocinado: publicidade@uol.com.br"},
            {"step": 3, "action": "Usar comunicado gerado com dados e cifras concretas"},
        ],
        "tips": ["UOL indexa no Google News imediatamente. Alto alcance mas editorial independente."],
        "seo_impact": "DA 92. Google News BR em 1-4h.",
        "warning": None,
    },

    "infomoney": {
        "name": "InfoMoney",
        "icon": "💰",
        "automatable": False,
        "api_status": "Sem API — earned media ou assessoria de imprensa",
        "publish_url": "https://www.infomoney.com.br/contato/",
        "login_url": None,
        "time_estimate": "Variável",
        "best_for": "Clientes financeiros, investidores, setor econômico. DA 85.",
        "steps": [
            {"step": 1, "action": "Enviar press release para redacao@infomoney.com.br"},
            {"step": 2, "action": "Assunto: '[PAUTA] ' + título do release"},
            {"step": 3, "action": "No corpo: primeiros 3 parágrafos do release (gancho)"},
            {"step": 4, "action": "Anexar o release completo em PDF"},
            {"step": 5, "action": "Incluir contato do porta-voz para entrevista"},
        ],
        "tips": ["InfoMoney foca em finanças pessoais e mercado. Dados de mercado aumentam chance de cobertura."],
        "seo_impact": "DA 85. Google News BR em 2-4h.",
        "warning": None,
    },

    "suno": {
        "name": "Suno Notícias",
        "icon": "📈",
        "automatable": False,
        "api_status": "Sem API — earned media",
        "publish_url": "https://www.suno.com.br/noticias/",
        "login_url": None,
        "time_estimate": "Variável",
        "best_for": "Investimentos, fundos, mercado financeiro BR. DA 82.",
        "steps": [
            {"step": 1, "action": "Enviar press release para redacao@suno.com.br"},
            {"step": 2, "action": "Foco em dados financeiros verificáveis"},
            {"step": 3, "action": "Usar versão do comunicado com ângulo de mercado/investimento"},
        ],
        "tips": ["Suno cobre principalmente mercado de capitais e investimentos pessoais."],
        "seo_impact": "DA 82. Google News BR em 2-4h.",
        "warning": None,
    },

    "pegn": {
        "name": "PEGN",
        "icon": "🏪",
        "automatable": False,
        "api_status": "Sem API — earned media (Globo)",
        "publish_url": "https://pegn.globo.com/",
        "login_url": None,
        "time_estimate": "Variável",
        "best_for": "PMEs, empreendedorismo, pequenos negócios BR. DA 84.",
        "steps": [
            {"step": 1, "action": "Enviar sugestão de pauta para pegn@globo.com"},
            {"step": 2, "action": "Foco em histórias de empreendedorismo com dados e resultados"},
            {"step": 3, "action": "Incluir ângulo de impacto no ecossistema de PMEs"},
        ],
        "tips": ["PEGN prefere histórias de empreendedores com resultados concretos."],
        "seo_impact": "DA 84. Indexa no Google News via Globo.",
        "warning": None,
    },

    "canaltech": {
        "name": "Canaltech",
        "icon": "💻",
        "automatable": False,
        "api_status": "Sem API — aceita guest posts e releases",
        "publish_url": "https://canaltech.com.br/colabore/",
        "login_url": None,
        "time_estimate": "2-5 dias úteis",
        "best_for": "Tecnologia, produtos digitais, startups tech. DA 80.",
        "steps": [
            {"step": 1, "action": "Aceder a canaltech.com.br/colabore para enviar artigo"},
            {"step": 2, "action": "Para releases: release@canaltech.com.br"},
            {"step": 3, "action": "Usar variação 'Opinião Técnica' do Motor Semântico"},
            {"step": 4, "action": "Incluir imagens de produto ou infográfico"},
        ],
        "tips": ["Canaltech aceita colaboradores — artigo de opinião com autoridade tem boa taxa de aprovação."],
        "seo_impact": "DA 80. Google News BR em 2-6h.",
        "warning": None,
    },

    "itforum": {
        "name": "IT Forum",
        "icon": "🖥️",
        "automatable": False,
        "api_status": "Sem API — earned media",
        "publish_url": "https://itforum.com.br/contato/",
        "login_url": None,
        "time_estimate": "2-5 dias úteis",
        "best_for": "TI corporativa, CIOs, CTOs, transformação digital. DA 76.",
        "steps": [
            {"step": 1, "action": "Enviar press release para redacao@itforum.com.br"},
            {"step": 2, "action": "Para artigos de opinião: editorial@itforum.com.br"},
            {"step": 3, "action": "Foco em perspectiva de CIO/gestor de TI"},
        ],
        "tips": ["IT Forum foca em decisores de TI — ângulo de gestão e estratégia tem mais aceitação."],
        "seo_impact": "DA 76. Google News BR. Audiência B2B qualificada.",
        "warning": None,
    },

    # ── PORTAIS PT — guias adicionais ────────────────────────────────────
    "eco": {
        "name": "ECO",
        "icon": "🇵🇹",
        "automatable": False,
        "api_status": "Sem API — earned media",
        "publish_url": "https://eco.pt/contato/",
        "login_url": None,
        "time_estimate": "Variável",
        "best_for": "Economia e negócios em Portugal. DA 82.",
        "steps": [
            {"step": 1, "action": "Enviar press release para redacao@eco.pt"},
            {"step": 2, "action": "Usar release em PT-PT (vocabulário europeu)"},
            {"step": 3, "action": "Incluir ângulo com relevância para mercado português"},
        ],
        "tips": ["ECO cobre principalmente economia, negócios e mercados financeiros PT."],
        "seo_impact": "DA 82. Google News PT em 2-4h.",
        "warning": None,
    },

    "jornal_economico": {
        "name": "Jornal Económico",
        "icon": "🇵🇹",
        "automatable": False,
        "api_status": "Sem API — earned media",
        "publish_url": "https://jornaleconomico.sapo.pt/contato",
        "login_url": None,
        "time_estimate": "Variável",
        "best_for": "Economia e empresas em Portugal. DA 80.",
        "steps": [
            {"step": 1, "action": "Enviar press release para redacao@jornaleconomico.pt"},
            {"step": 2, "action": "Para opinião assinada: opiniao@jornaleconomico.pt"},
            {"step": 3, "action": "Usar release em PT-PT"},
        ],
        "tips": ["Foco em empresas, gestão e economia portuguesa."],
        "seo_impact": "DA 80. Google News PT.",
        "warning": None,
    },

    "dinheiro_vivo": {
        "name": "Dinheiro Vivo",
        "icon": "🇵🇹",
        "automatable": False,
        "api_status": "Sem API — earned media (Público/Global Media)",
        "publish_url": "https://www.dinheirovivo.pt/",
        "login_url": None,
        "time_estimate": "Variável",
        "best_for": "Finanças pessoais, investimento e economia PT. DA 78.",
        "steps": [
            {"step": 1, "action": "Enviar press release para redacao@dinheirovivo.pt"},
            {"step": 2, "action": "Foco em ângulo de finanças pessoais ou investimento"},
        ],
        "tips": ["Dinheiro Vivo é suplemento do jornal Público — standards editoriais altos."],
        "seo_impact": "DA 78. Google News PT.",
        "warning": None,
    },

    "pplware": {
        "name": "Pplware",
        "icon": "🇵🇹",
        "automatable": False,
        "api_status": "Sem API — earned media ou comunicados de imprensa",
        "publish_url": "https://pplware.sapo.pt/comunicados/",
        "login_url": None,
        "time_estimate": "1-3 dias",
        "best_for": "Tecnologia, gadgets, apps em Portugal. DA 76.",
        "steps": [
            {"step": 1, "action": "Enviar press release para imprensa@pplware.com"},
            {"step": 2, "action": "Para artigos técnicos: editorial@pplware.com"},
            {"step": 3, "action": "Incluir imagens de produto se aplicável"},
        ],
        "tips": ["Pplware tem secção dedicada a comunicados de imprensa tech."],
        "seo_impact": "DA 76. Google News PT em 2-6h.",
        "warning": None,
    },

    # ── PORTAIS ES — guias adicionais ────────────────────────────────────
    "expansion": {
        "name": "Expansión",
        "icon": "🇪🇸",
        "automatable": False,
        "api_status": "Sem API — earned media",
        "publish_url": "https://www.expansion.com/contacto.html",
        "login_url": None,
        "time_estimate": "Variável",
        "best_for": "Economia, empresas e finanças em Espanha. DA 88.",
        "steps": [
            {"step": 1, "action": "Enviar press release para redaccion@expansion.com"},
            {"step": 2, "action": "Para branded content: publicidad@expansion.com"},
            {"step": 3, "action": "Usar release em ES com dados de mercado espanhol"},
        ],
        "tips": ["Expansión é o principal jornal económico ES — standards altos."],
        "seo_impact": "DA 88. Google News ES em 1-4h.",
        "warning": None,
    },

    "xataka": {
        "name": "Xataka",
        "icon": "🇪🇸",
        "automatable": False,
        "api_status": "Sem API — earned media (Webedia)",
        "publish_url": "https://www.xataka.com/redaccion",
        "login_url": None,
        "time_estimate": "Variável",
        "best_for": "Tecnologia, gadgets e ciência em ES. DA 84.",
        "steps": [
            {"step": 1, "action": "Enviar press release para redaccion@xataka.com"},
            {"step": 2, "action": "Para produtos tech: prensa@xataka.com"},
            {"step": 3, "action": "Incluir specs técnicas e imagens de produto"},
        ],
        "tips": ["Xataka cobre tech de consumo — ângulo de produto/inovação."],
        "seo_impact": "DA 84. Google News ES.",
        "warning": None,
    },

    # ── PORTAIS PARA NEWS DISTRIBUTION ──────────────────────────────────
    "migalhas": {
        "name": "Migalhas",
        "icon": "⚖️",
        "automatable": False,
        "api_status": "Sem API — envio por email",
        "publish_url": "https://www.migalhas.com.br/quentes/enviar",
        "login_url": None,
        "time_estimate": "1-24h",
        "best_for": "Clientes com contexto jurídico. DA 72. Altamente lido por advogados e juristas.",
        "steps": [
            {"step": 1, "action": "Aceder a migalhas.com.br/quentes/enviar"},
            {"step": 2, "action": "Preencher o formulário com título, texto e categoria"},
            {"step": 3, "action": "Usar o esclarecimento jurídico ou comunicado gerado pelo CouncilIA"},
            {"step": 4, "action": "Categoria: selecionar área jurídica mais próxima do tema"},
        ],
        "tips": [
            "Migalhas tem formulário público de envio — não precisa de credencial nem conta",
            "Conteúdo jurídico sobre esclarecimentos e decisões tem alta taxa de publicação",
            "Evitar linguagem comercial — Migalhas é editorial jurídico",
        ],
        "seo_impact": "DA 72. Indexa no Google News Jurídico. Muito lido por decision makers legais.",
        "warning": None,
    },

    "conjur": {
        "name": "ConJur",
        "icon": "⚖️",
        "automatable": False,
        "api_status": "Sem API — envio por email",
        "publish_url": "https://www.conjur.com.br/redacao/",
        "login_url": None,
        "time_estimate": "1-24h",
        "best_for": "Contexto jurídico, decisões de tribunais, artigos de advogados. DA 72.",
        "steps": [
            {"step": 1, "action": "Enviar email para redacao@conjur.com.br"},
            {"step": 2, "action": "Assunto: 'Artigo — [título]' ou 'Release — [título]'"},
            {"step": 3, "action": "Para artigos de opinião: incluir CV do autor (advogado/jurista)"},
            {"step": 4, "action": "Para comunicados: usar esclarecimento jurídico gerado pelo CouncilIA"},
        ],
        "tips": [
            "ConJur publica artigos de opinião de advogados e juristas com regularidade",
            "Se o cliente tem advogado/jurista, assinar o artigo aumenta a taxa de publicação",
            "Linguagem técnica-jurídica é bem recebida",
        ],
        "seo_impact": "DA 72. Referência jurídica — indexa para buscas de processos e decisões.",
        "warning": None,
    },

    "segs": {
        "name": "Segs",
        "icon": "📋",
        "automatable": False,
        "api_status": "Sem API — formulário público gratuito",
        "publish_url": "https://www.segs.com.br/divulgar-nota",
        "login_url": None,
        "time_estimate": "15-30 minutos",
        "best_for": "Releases corporativos gerais. Gratuito. Indexa no Google. DA baixo mas rápido.",
        "steps": [
            {"step": 1, "action": "Aceder a segs.com.br/divulgar-nota"},
            {"step": 2, "action": "Preencher formulário: título, texto, categoria, contato"},
            {"step": 3, "action": "Usar o comunicado à imprensa gerado pelo CouncilIA"},
            {"step": 4, "action": "Publicação em 15-30 minutos"},
        ],
        "tips": [
            "Segs é gratuito e publica quase tudo — bom para volume de releases",
            "DA baixo mas gera link dofollow indexável",
        ],
        "seo_impact": "DA baixo mas indexa rapidamente. Útil para volume de presença digital.",
        "warning": None,
    },

    "investnews": {
        "name": "InvestNews",
        "icon": "💹",
        "automatable": False,
        "api_status": "Sem API — earned media",
        "publish_url": "https://investnews.com.br/contato/",
        "login_url": None,
        "time_estimate": "Variável",
        "best_for": "Investimentos, mercado de capitais, economia. DA 80.",
        "steps": [
            {"step": 1, "action": "Enviar press release para redacao@investnews.com.br"},
            {"step": 2, "action": "Foco em ângulo de impacto para investidores"},
        ],
        "tips": ["InvestNews foca em mercado financeiro e investimentos pessoais."],
        "seo_impact": "DA 80. Google News BR.",
        "warning": None,
    },

    "dino": {
        "name": "Dino (Knewin)",
        "icon": "📡",
        "automatable": True,
        "api_status": "API disponível — configurar DINO_API_KEY no .env",
        "publish_url": "https://dino.com.br/enviar-release/",
        "login_url": "https://dino.com.br/login",
        "time_estimate": "15-30 minutos",
        "best_for": "Melhor custo-benefício para Google News BR. DA 82. Distribui para 200+ portais.",
        "steps": [
            {"step": 1, "action": "Criar conta em dino.com.br ou fazer login"},
            {"step": 2, "action": "Clicar em 'Enviar Release'"},
            {"step": 3, "action": "TÍTULO: colar o título do press release gerado"},
            {"step": 4, "action": "TEXTO: colar o corpo completo do release"},
            {"step": 5, "action": "SETOR: selecionar o setor do cliente"},
            {"step": 6, "action": "Selecionar plano de distribuição"},
            {"step": 7, "action": "Publicar — aparece no Google News em 1-4h"},
        ],
        "tips": [
            "Se DINO_API_KEY estiver configurado, usar POST /api/publish/{slug} para automatizar",
            "Melhor relação custo-indexação para o mercado BR",
            "Distribui automaticamente para portais parceiros incluindo InfoMoney e outros",
        ],
        "seo_impact": "DA 82. Google News BR em 1-4h. 200+ portais parceiros.",
        "warning": None,
    },

    "prunderground": {
        "name": "PR Underground",
        "icon": "📡",
        "automatable": False,
        "api_status": "Sem API — formulário web. Publicação manual mas rápida.",
        "publish_url": "https://www.prunderground.com/submit/",
        "login_url": "https://www.prunderground.com/login/",
        "time_estimate": "15-30 minutos (publicação em minutos após submissão)",
        "best_for": "Google News direto garantido. 150+ sites incluindo FOX TV regional. $74.99/release. "
                    "Plano US National ($419): Yahoo Finance + PRNewswire.com.",
        "steps": [
            {"step": 1, "action": "Criar conta em prunderground.com ou fazer login"},
            {"step": 2, "action": "Clicar em 'Submit Press Release'"},
            {"step": 3, "action": "HEADLINE: colar o título do press release gerado"},
            {"step": 4, "action": "BODY: colar o corpo completo do release"},
            {"step": 5, "action": "CATEGORY: selecionar o setor do cliente"},
            {"step": 6, "action": "CONTACT INFO: preencher dados de contacto do porta-voz"},
            {"step": 7, "action": "Escolher plano: Basic ($74.99) para Google News, US National ($419.99) para Yahoo Finance"},
            {"step": 8, "action": "Pagar e submeter — aparece no Google News em minutos"},
        ],
        "tips": [
            "Google News indexa o release em minutos após publicação — diferencial real",
            "Plano Basic ($74.99) já inclui 150+ sites e Google News — suficiente para maioria dos casos",
            "Plano US National ($419.99) inclui Yahoo Finance e PRNewswire.com — usar para clientes financeiros",
            "Top 3 em satisfação no G2Crowd. Verificado e com histórico comprovado.",
            "Alternativa mais barata ao EIN Presswire para mercado americano",
        ],
        "seo_impact": "Google News imediato. 150+ sites regionais. DA do plano Basic ~72. Plano National: Yahoo Finance (DA 93).",
        "warning": "Focado no mercado americano/inglês — usar com releases em inglês para maior alcance.",
    },

    "redpress": {
        "name": "RedPress",
        "icon": "📰",
        "automatable": False,
        "api_status": "Sem API — formulário web",
        "publish_url": "https://redpresswire.net/pricing/",
        "login_url": "https://redpresswire.net/login/",
        "time_estimate": "5 dias (publicação planejada)",
        "best_for": "Aggregator de syndication com múltiplos planos. "
                    "Plano Core ($219): DA 91+, 130+ sites, Yahoo Finance. "
                    "Plano Growth ($279): DA 94+, 530+ sites, AP, Business Insider.",
        "steps": [
            {"step": 1, "action": "Aceder a redpresswire.net e escolher plano"},
            {"step": 2, "action": "RECOMENDADO: Plano Core ($219) ou Growth ($279) — Basic ($89) tem DA máx 72 e impacto limitado"},
            {"step": 3, "action": "Submeter o press release gerado"},
            {"step": 4, "action": "HEADLINE: título com nome da entidade"},
            {"step": 5, "action": "BODY: corpo completo do release"},
            {"step": 6, "action": "Publicação em ~5 dias úteis"},
        ],
        "tips": [
            "Usar plano Core ($219) ou superior — plano Basic tem DA 72 e valor limitado para displacement de SERP",
            "Plano Growth ($279) inclui Associated Press e Business Insider — muito mais impacto",
            "Releases em inglês têm mais sites de destino disponíveis",
            "6.000+ clientes mundiais — serviço verificado e legítimo",
        ],
        "seo_impact": "Plano Basic: DA 72, 300+ sites, Google/Bing. Plano Growth: DA 94, 530+ sites, AP + Business Insider.",
        "warning": "Plano Basic ($89) tem valor limitado para displacement. Usar Core ou Growth para impacto real.",
    },

    "prweb": {
        "name": "PRWeb Brasil",
        "icon": "📋",
        "automatable": False,
        "api_status": "API disponível com conta ativa",
        "publish_url": "https://www.prweb.com.br/",
        "login_url": "https://www.prweb.com.br/login",
        "time_estimate": "30-60 minutos",
        "best_for": "Distribuição de releases BR. Indexa no Google. DA 74.",
        "steps": [
            {"step": 1, "action": "Criar conta em prweb.com.br"},
            {"step": 2, "action": "Fazer login e clicar em 'Novo Release'"},
            {"step": 3, "action": "Colar título e corpo do release gerado"},
            {"step": 4, "action": "Selecionar categoria e região"},
            {"step": 5, "action": "Pagar e submeter"},
        ],
        "tips": ["Alternativa ao Maxpress para distribuição BR com menor custo."],
        "seo_impact": "DA 74. Google News BR.",
        "warning": None,
    },

    "aion": {
        "name": "AION (Assessoria de Imprensa Online)",
        "icon": "📋",
        "automatable": False,
        "api_status": "Formulário público — sem API",
        "publish_url": "https://aion.com.br/enviar-release/",
        "login_url": "https://aion.com.br/login/",
        "time_estimate": "1-2 horas",
        "best_for": "Release corporativo geral para media BR. Custo baixo. DA 65.",
        "steps": [
            {"step": 1, "action": "Aceder a aion.com.br e criar conta gratuita"},
            {"step": 2, "action": "Clicar em 'Enviar Release'"},
            {"step": 3, "action": "Preencher título, texto, categoria e contacto"},
            {"step": 4, "action": "Publicação em 1-2 horas"},
        ],
        "tips": [
            "Custo baixo — usar em paralelo com newswires de maior autoridade",
            "Bom para volume — aumentar presença digital geral",
        ],
        "seo_impact": "DA 65. Google indexável. Alcance limitado mas gratuito/barato.",
        "warning": None,
    },
}


def get_manual_guide(platform_key: str) -> dict | None:
    """Retorna o guia de publicação manual para uma plataforma."""
    return MANUAL_GUIDES.get(platform_key)


def get_all_manual_guides() -> dict:
    """Retorna todos os guias de publicação manual."""
    return MANUAL_GUIDES


def get_manual_platforms_for_entity(archetype: str, region: str = "BR") -> list[str]:
    """
    Retorna as plataformas manuais prioritárias para um arquétipo e região.
    Ordem: impacto > facilidade.
    """
    # Base universal — todas as regiões
    base = ["crunchbase", "google_business", "linkedin", "medium", "youtube", "substack"]

    if region == "BR":
        base += ["valor_economico", "exame", "infomoney", "estadao_empresas",
                 "uol_economia", "pegn", "suno", "startse", "ti_inside",
                 "canaltech", "itforum"]
    elif region == "PT":
        base += ["observador", "eco", "jornal_economico", "dinheiro_vivo",
                 "pplware", "cision_pt", "presspoint_pt"]
    elif region == "ES":
        base += ["elpais", "elmundo", "expansion", "cincodias", "lavanguardia",
                 "xataka", "genbeta"]
    elif region == "US":
        base += ["techcrunch", "venturebeat", "forbes", "businessinsider",
                 "fastcompany", "inc", "wired"]

    # Portais por arquétipo
    if archetype in ("tech_executive", "startup_founder"):
        base += ["hackernoon", "wired", "devto"]
        if region == "BR":
            base += ["startse"]
    elif archetype == "corporate":
        base += ["glassdoor", "clutch"]
    elif archetype == "financial":
        if region == "BR":
            base += ["infomoney", "suno", "investnews", "moneytimes"]
    elif archetype in ("criminal", "associative"):
        base += ["glassdoor"]  # credibilidade institucional crítica

    # Newswires sempre relevantes (manual ou semi-automático)
    if region == "BR":
        base += ["einpresswire", "globenewswire", "dino"]
    elif region == "PT":
        base += ["einpresswire_br", "globenewswire"]
    elif region == "ES":
        base += ["einpresswire", "globenewswire"]
    else:
        base += ["einpresswire", "globenewswire"]

    # Remover duplicatas mantendo ordem
    seen = set()
    result = []
    for p in base:
        if p not in seen:
            seen.add(p)
            result.append(p)
    return result


# ── Content format per platform ─────────────────────────────────────────────

def format_for(platform_key: str, entity: str, article_text: str, seo: dict | None = None) -> dict:
    """Formata o artigo para o formato específico de cada plataforma."""
    platform = PLATFORM_REGISTRY.get(platform_key)
    if not platform:
        return {"error": f"Unknown platform: {platform_key}"}

    title = (seo or {}).get("title", entity)
    desc = (seo or {}).get("meta_description", "")
    tags = (seo or {}).get("tags", [])

    if platform_key == "linkedin":
        return _format_linkedin(title, article_text, entity)
    elif platform_key == "medium":
        return _format_medium(title, article_text, tags)
    elif platform_key == "wordpress":
        return _format_wordpress(title, article_text, desc, tags)
    elif platform_key == "youtube":
        return _format_youtube(title, article_text, entity)
    elif platform_key == "substack":
        return _format_substack(title, article_text)
    elif platform_key == "ghost":
        return _format_ghost(title, article_text, tags)
    elif platform.type == "newswire":
        return _format_newswire(platform_key, title, article_text, entity, desc)
    else:
        return {"title": title, "body": article_text, "platform": platform.name}


def _md_to_plain(text: str) -> str:
    """Converte Markdown para texto plano — remove símbolos de formatação.
    Usado para plataformas que não suportam Markdown (LinkedIn API, UGC posts).
    """
    import re as _re
    t = text
    # Headings: ## Title → Title (em maiúsculas para hierarquia visual)
    t = _re.sub(r"^#{1,6}\s+(.+)$", lambda m: m.group(1).upper(), t, flags=_re.MULTILINE)
    # Bold: **text** ou __text__ → text
    t = _re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = _re.sub(r"__(.+?)__", r"\1", t)
    # Italic: *text* ou _text_ → text
    t = _re.sub(r"\*(.+?)\*", r"\1", t)
    t = _re.sub(r"_(.+?)_", r"\1", t)
    # Horizontal rule
    t = _re.sub(r"^---+$", "—" * 20, t, flags=_re.MULTILINE)
    # Links: [text](url) → text
    t = _re.sub(r"\[(.+?)\]\(.+?\)", r"\1", t)
    # Code blocks
    t = _re.sub(r"```.*?```", "", t, flags=_re.DOTALL)
    t = _re.sub(r"`(.+?)`", r"\1", t)
    return t.strip()


def _md_to_html(text: str) -> str:
    """Converte Markdown para HTML básico — para WordPress e Ghost."""
    import re as _re
    t = text
    lines = t.split("\n")
    html_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            html_lines.append("")
            continue
        # H1-H6
        h_match = _re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if h_match:
            level = len(h_match.group(1))
            content = h_match.group(2)
            # Bold e italic dentro dos headings
            content = _re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", content)
            content = _re.sub(r"\*(.+?)\*", r"<em>\1</em>", content)
            html_lines.append(f"<h{level}>{content}</h{level}>")
            continue
        # Horizontal rule
        if _re.match(r"^---+$", stripped):
            html_lines.append("<hr>")
            continue
        # Paragraph — aplicar bold e italic inline
        p = stripped
        p = _re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", p)
        p = _re.sub(r"__(.+?)__", r"<strong>\1</strong>", p)
        p = _re.sub(r"\*(.+?)\*", r"<em>\1</em>", p)
        p = _re.sub(r"_(.+?)_", r"<em>\1</em>", p)
        p = _re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', p)
        html_lines.append(f"<p>{p}</p>")
    return "\n".join(l for l in html_lines if l is not None)


def _format_linkedin(title: str, text: str, entity: str) -> dict:
    """Formata para LinkedIn.

    Dois formatos:
    - manual (publish_url/steps): texto com Markdown básico para colar no editor web
    - api (body_plain): texto limpo sem Markdown para UGC API post

    Nota: a API do LinkedIn (ugcPosts) cria feed posts, não Articles.
    Para LinkedIn Articles completos, usar a interface web (manual).
    """
    lines = text.strip().split("\n")
    headline = lines[0] if lines else title
    headline_clean = headline.replace("#", "").replace("*", "").strip()[:120]

    # Body para uso manual (editor web aceita Markdown)
    body_md = "\n\n".join(l for l in lines[1:] if l.strip()) if len(lines) > 1 else text

    # Body para API (ugcPosts não renderiza Markdown — limpar símbolos)
    body_plain = _md_to_plain(body_md)

    return {
        "platform": "LinkedIn Articles",
        "headline": headline_clean,
        "body": body_md[:5000],          # para uso manual (editor web)
        "body_plain": body_plain[:3000],  # para API ugcPosts
        "format": "plain_text",
        "publish_url": "https://www.linkedin.com/pulse/write/",
        "note": "API cria feed post (UGC). Para LinkedIn Article completo usar editor web.",
        "steps": [
            "Acessar linkedin.com/pulse/write",
            "No campo TÍTULO: colar o headline acima",
            "No corpo: colar o texto (o editor web renderiza os headings ##)",
            "Adicionar imagem de capa institucional",
            "Publicar e fixar no topo do perfil",
        ],
    }


def _format_medium(title: str, text: str, tags: list[str]) -> dict:
    """Formata para Medium (Markdown nativo)."""
    body = text.strip()
    return {
        "platform": "Medium",
        "title": title[:120],
        "body": body,          # Medium aceita Markdown completo
        "format": "markdown",
        "tags": (tags or [])[:5],
        "publish_url": "https://medium.com/new-story",
        "api_note": "API publica como DRAFT — confirmar publicação no painel Medium.",
        "steps": [
            "Acessar medium.com e fazer login",
            "Clicar no ícone de lápis (canto superior direito)",
            "TÍTULO: colar o título gerado",
            "CORPO: colar o Markdown (Medium renderiza automaticamente)",
            "Adicionar tags: " + ", ".join((tags or [])[:5]),
            "Publicar e submeter a publicações do setor se disponível",
        ],
    }


def _format_wordpress(title: str, text: str, excerpt: str, tags: list[str]) -> dict:
    """Formata para WordPress REST API (HTML completo com headings e bold)."""
    html_body = _md_to_html(text)
    return {
        "platform": "WordPress",
        "title": title[:120],
        "excerpt": excerpt[:200],
        "body_html": html_body,      # HTML com H2/H3/strong/em corretos
        "body_markdown": text.strip(),  # mantido para fallback manual
        "tags": (tags or [])[:10],
        "format": "html",
        "publish_url": "/wp-admin/post-new.php",
        "api_note": "API publica como DRAFT — publicar manualmente após revisão.",
        "steps": [
            "Via API: configurar WP_URL, WP_USER, WP_PASS no .env e usar Quick Publish",
            "Via manual: acessar /wp-admin → Posts → Adicionar Novo",
            "Colar o título e o HTML no editor",
            "Adicionar tags e categorias",
            "Publicar",
        ],
    }


def _format_youtube(title: str, text: str, entity: str) -> dict:
    """Formata para YouTube (descrição + SEO)."""
    lines = text.strip().split("\n")
    description = "\n".join(lines)
    seo_tags = [entity.lower(), "reputação digital", "gestão de crise"] if entity else []
    return {
        "platform": "YouTube",
        "title": title[:100],
        "description": description[:5000],
        "tags": seo_tags,
        "format": "plain_text",
        "publish_url": "https://studio.youtube.com",
        "steps": [
            "Gravar vídeo seguindo o roteiro",
            "Acessar YouTube Studio",
            "Fazer upload do vídeo",
            "Colar título, descrição e tags abaixo",
            "Publicar (não listado ou público conforme estratégia)",
        ],
    }


def _format_substack(title: str, text: str) -> dict:
    return {
        "platform": "Substack",
        "title": title[:120],
        "body": text.strip(),
        "format": "markdown",
        "publish_url": "https://substack.com/publish",
        "steps": [
            "Acessar substack.com",
            "Criar nova publicação",
            "Colar título e conteúdo",
            "Adicionar imagem de capa",
            "Enviar para assinantes + publicar web",
        ],
    }


def _format_ghost(title: str, text: str, tags: list[str]) -> dict:
    paragraphs = text.strip().split("\n")
    html = "".join(f"<!--kg-card-begin: html--><p>{p}</p><!--kg-card-end: html-->" for p in paragraphs if p.strip())
    return {
        "platform": "Ghost CMS",
        "title": title[:120],
        "body_html": html,
        "tags": (tags or [])[:5],
        "format": "html",
        "publish_url": "/ghost/#/editor",
        "steps": [
            "Acessar /ghost do site",
            "Criar novo post",
            "Colar o HTML abaixo no editor",
            "Adicionar tags",
            "Publicar",
        ],
    }


def _format_newswire(platform_key: str, title: str, text: str, entity: str, desc: str) -> dict:
    """Formata para newswire distribution (press release format)."""
    platform = PLATFORM_REGISTRY.get(platform_key, None)
    body = text.strip()
    return {
        "platform": platform.name if platform else platform_key,
        "headline": title[:120],
        "summary": desc[:300] or body[:200],
        "body": body[:5000],
        "format": "plain_text",
        "publish_url": "—",
        "payload": {
            "title": title[:120],
            "content": body[:5000],
            "contact_name": entity,
            "language": "pt" if platform and platform.region in ("BR", "PT") else "en",
        },
    }


# ── API Publishing ──────────────────────────────────────────────────────────

async def publish_to(platform_key: str, entity: str, article_text: str, seo: dict | None = None, credentials: dict | None = None) -> dict:
    """Publica artigo em uma plataforma via API. Retorna resultado."""
    formatted = format_for(platform_key, entity, article_text, seo)
    if "error" in formatted:
        return formatted

    platform = PLATFORM_REGISTRY.get(platform_key)

    # Sem API → retorna formatted para publicação manual
    if not platform or not platform.api:
        return {**formatted, "status": "manual", "message": "Publicação manual necessária — API não disponível"}

    creds = credentials or {}

    if platform_key == "medium":
        return await _publish_medium(formatted, creds)
    elif platform_key == "linkedin":
        return await _publish_linkedin(formatted, creds)
    elif platform_key == "wordpress":
        return await _publish_wordpress(formatted, creds)
    elif platform_key == "einpresswire":
        return await _publish_einpresswire(formatted, creds)
    elif platform_key == "ghost":
        return await _publish_ghost(formatted, creds)
    elif platform.type == "newswire":
        return await _publish_newswire_generic(platform_key, platform, formatted, creds)
    else:
        return {**formatted, "status": "manual", "message": f"API wrapper não implementado: {platform_key}"}


async def _publish_medium(formatted: dict, creds: dict) -> dict:
    """Publica no Medium via REST API. Publica como DRAFT — confirmar no painel Medium."""
    token = creds.get("medium_token", os.getenv("MEDIUM_TOKEN", ""))
    if not token:
        return {**formatted, "status": "setup_required",
                "message": "Configure MEDIUM_TOKEN no .env"}
    import httpx
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    async with httpx.AsyncClient() as client:
        r = await client.get("https://api.medium.com/v1/me", headers=headers)
        if r.status_code != 200:
            return {**formatted, "status": "error",
                    "message": f"Medium auth falhou: {r.text}"}
        user_id = r.json()["data"]["id"]
        payload = {
            "title":          formatted.get("title", formatted.get("headline", "")),
            "contentFormat":  "markdown",
            "content":        formatted.get("body", ""),
            "tags":           formatted.get("tags", []),
            "publishStatus":  "draft",  # sempre draft — publicar manualmente
        }
        r2 = await client.post(
            f"https://api.medium.com/v1/users/{user_id}/posts",
            headers=headers, json=payload
        )
        if r2.status_code in (200, 201):
            data = r2.json()["data"]
            return {
                **formatted,
                "status":  "draft",  # correto — Medium API não publica direto
                "message": "Rascunho criado no Medium. Aceder ao painel e clicar Publish.",
                "url":     data.get("url", ""),
                "id":      data.get("id", ""),
            }
        return {**formatted, "status": "error",
                "message": f"Medium falhou: {r2.text}"}


async def _publish_linkedin(formatted: dict, creds: dict) -> dict:
    """
    Publica no LinkedIn via OAuth API (UGC Post = feed post, não Article).

    IMPORTANTE: Esta rota cria um feed post, não um LinkedIn Article.
    Para LinkedIn Articles completos, usar a interface web manualmente.
    O body_plain (sem Markdown) é usado para evitar símbolos literais no feed.
    """
    token = creds.get("linkedin_token", os.getenv("LINKEDIN_TOKEN", ""))
    if not token:
        return {**formatted, "status": "setup_required",
                "message": "Configure LINKEDIN_TOKEN no .env"}
    import httpx
    headers = {
        "Authorization":             f"Bearer {token}",
        "Content-Type":              "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    async with httpx.AsyncClient() as client:
        r = await client.get("https://api.linkedin.com/v2/userinfo", headers=headers)
        if r.status_code != 200:
            return {**formatted, "status": "error",
                    "message": f"LinkedIn auth falhou: {r.text}"}
        sub = r.json().get("sub", "")

        # Usar body_plain (sem Markdown) para feed post
        headline = formatted.get("headline", "")
        body_api = formatted.get("body_plain", formatted.get("body", ""))
        text = f"{headline}\n\n{body_api}"[:3000]

        payload = {
            "author": f"urn:li:person:{sub}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary":  {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        r2 = await client.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=headers, json=payload
        )
        if r2.status_code in (200, 201):
            post_id = r2.json().get("id", "")
            return {
                **formatted,
                "status":  "published",
                "id":      post_id,
                "message": "Feed post publicado. Para LinkedIn Article completo usar interface web.",
                "note":    "Este é um UGC feed post, não um LinkedIn Article. Para Articles completos: linkedin.com/pulse/write",
            }
        return {**formatted, "status": "error",
                "message": f"LinkedIn falhou: {r2.text}"}


async def _publish_wordpress(formatted: dict, creds: dict) -> dict:
    """Publica no WordPress via REST API."""
    site_url = creds.get("wp_url", os.getenv("WP_URL", "")).rstrip("/")
    username = creds.get("wp_user", os.getenv("WP_USER", ""))
    password = creds.get("wp_pass", os.getenv("WP_PASS", ""))
    if not all([site_url, username, password]):
        return {**formatted, "status": "setup_required", "message": "Configure WP_URL, WP_USER, WP_PASS no dashboard"}
    import httpx, base64
    auth = base64.b64encode(f"{username}:{password}".encode()).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
    payload = {
        "title": formatted.get("title", ""),
        "content": formatted.get("body_html", formatted.get("body", "")),
        "excerpt": formatted.get("excerpt", ""),
        "status": "draft",
        "tags": formatted.get("tags", []),
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{site_url}/wp-json/wp/v2/posts", headers=headers, json=payload)
        if r.status_code in (200, 201):
            return {**formatted, "status": "draft", "url": r.json().get("link", ""), "id": r.json().get("id", 0)}
        return {**formatted, "status": "error", "message": f"WordPress publish failed: {r.text}"}


async def _publish_einpresswire(formatted: dict, creds: dict) -> dict:
    """Envia release para EIN Presswire via API v2."""
    api_key = creds.get("ein_api_key", os.getenv("EIN_API_KEY", ""))
    if not api_key:
        return {**formatted, "status": "setup_required",
                "message": "Configure EIN_API_KEY no .env"}
    import httpx
    from datetime import datetime, timezone

    base_payload = formatted.get("payload", {})

    # EIN Presswire API v2 campos completos
    payload = {
        "api_key":       api_key,
        "headline":      base_payload.get("title", formatted.get("headline", ""))[:120],
        "body":          base_payload.get("content", formatted.get("body", ""))[:5000],
        "summary":       (formatted.get("summary") or
                          formatted.get("meta_description") or
                          base_payload.get("content", "")[:200]),
        "language":      base_payload.get("language", "pt"),
        "contact_name":  base_payload.get("contact_name", ""),
        "contact_email": creds.get("ein_contact_email",
                                   os.getenv("EIN_CONTACT_EMAIL", "")),
        "contact_phone": creds.get("ein_contact_phone",
                                   os.getenv("EIN_CONTACT_PHONE", "")),
        # Distribuição
        "distribution":  "global",
        "date":          datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }

    # Remover campos vazios para não causar erro de validação
    payload = {k: v for k, v in payload.items() if v}

    if not payload.get("contact_email"):
        return {
            **formatted,
            "status": "setup_required",
            "message": "EIN Presswire requer EIN_CONTACT_EMAIL no .env. "
                       "Adicionar o email de contacto do porta-voz.",
            "payload_ready": payload,
        }

    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://www.einpresswire.com/api/v2/press_release",
            json=payload, timeout=30
        )
        if r.status_code in (200, 201, 202):
            return {
                **formatted,
                "status":  "submitted",
                "message": "Release submetido ao EIN Presswire. Indexação em 1-4h.",
                "id":      r.json().get("id", ""),
            }
        return {**formatted, "status": "error",
                "message": f"EIN Presswire falhou HTTP {r.status_code}: {r.text[:300]}"}


async def _publish_ghost(formatted: dict, creds: dict) -> dict:
    """Publica no Ghost CMS via Admin API."""
    api_url = creds.get("ghost_url", os.getenv("GHOST_URL", "")).rstrip("/")
    admin_key = creds.get("ghost_admin_key", os.getenv("GHOST_ADMIN_KEY", ""))
    if not all([api_url, admin_key]):
        return {**formatted, "status": "setup_required", "message": "Configure GHOST_URL e GHOST_ADMIN_KEY no dashboard"}
    import httpx, jwt, time
    # Ghost Admin API uses JWT tokens
    key_parts = admin_key.split(":")
    if len(key_parts) != 2:
        return {**formatted, "status": "error", "message": "Invalid GHOST_ADMIN_KEY format (expected id:secret)"}
    now = int(time.time())
    token_payload = {
        "iat": now,
        "exp": now + 300,
        "aud": f"/admin/",
    }
    token = jwt.encode(token_payload, key_parts[1], algorithm="HS256", headers={"kid": key_parts[0]})
    headers = {"Authorization": f"Ghost {token}", "Content-Type": "application/json"}
    payload = {
        "posts": [{
            "title": formatted.get("title", ""),
            "html": formatted.get("body_html", formatted.get("body", "")),
            "status": "draft",
            "tags": [{"name": t} for t in formatted.get("tags", [])],
        }]
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{api_url}/ghost/api/admin/posts", headers=headers, json=payload)
        if r.status_code in (200, 201):
            return {**formatted, "status": "draft", "url": r.json().get("posts", [{}])[0].get("url", "")}
        return {**formatted, "status": "error", "message": f"Ghost publish failed: {r.text}"}


async def _publish_newswire_generic(
    platform_key: str,
    platform,
    formatted: dict,
    creds: dict,
) -> dict:
    """
    Dispatcher genérico para newswires.

    Cada newswire tem API diferente — este wrapper mapeia para o endpoint
    correto baseado no platform_key. Para newswires sem integração completa,
    retorna "payload_ready" com os dados formatados para envio manual ou
    integração futura.

    Credenciais esperadas no .env ou no dict creds:
      GlobeNewswire:  GLOBENEWSWIRE_TOKEN
      PR Newswire:    PRNEWSWIRE_API_KEY + PRNEWSWIRE_ACCOUNT_ID
      Dino (Knewin):  DINO_API_KEY
      B2Press:        B2PRESS_API_KEY
      Accesswire:     ACCESSWIRE_API_KEY
      eReleases:      ERELEASES_API_KEY
    """
    import httpx

    headline = formatted.get("headline", formatted.get("title", ""))
    body = formatted.get("body", formatted.get("summary", ""))
    payload_base = formatted.get("payload", {
        "title": headline,
        "content": body,
        "language": "pt",
    })

    # ── GlobeNewswire ──────────────────────────────────────────────────
    if platform_key == "globenewswire":
        token = creds.get("globenewswire_token") or os.getenv("GLOBENEWSWIRE_TOKEN", "")
        if not token:
            return {**formatted, "status": "payload_ready",
                    "message": "GLOBENEWSWIRE_TOKEN não configurado. Payload pronto para envio manual.",
                    "submit_url": "https://www.globenewswire.com/ReleaseApplication/",
                    "payload": payload_base}
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://api.globenewswire.com/v1/releases",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={**payload_base, "distributionType": "GLOBAL"},
                timeout=30,
            )
            if r.status_code in (200, 201, 202):
                return {**formatted, "status": "submitted",
                        "id": r.json().get("id", ""), "message": "Release submetido ao GlobeNewswire"}
            return {**formatted, "status": "error", "message": f"GlobeNewswire: HTTP {r.status_code} — {r.text[:200]}"}

    # ── PR Newswire ────────────────────────────────────────────────────
    elif platform_key == "prnewswire":
        api_key = creds.get("prnewswire_api_key") or os.getenv("PRNEWSWIRE_API_KEY", "")
        account_id = creds.get("prnewswire_account_id") or os.getenv("PRNEWSWIRE_ACCOUNT_ID", "")
        if not api_key:
            return {**formatted, "status": "payload_ready",
                    "message": "PRNEWSWIRE_API_KEY não configurado. Payload pronto para envio manual.",
                    "submit_url": "https://www.prnewswire.com/send-a-press-release/",
                    "payload": payload_base}
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"https://api.prnewswire.com/v1/accounts/{account_id}/releases",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={**payload_base, "distributionCode": "BRAZ"},
                timeout=30,
            )
            if r.status_code in (200, 201, 202):
                return {**formatted, "status": "submitted",
                        "message": "Release submetido à PR Newswire"}
            return {**formatted, "status": "error", "message": f"PR Newswire: HTTP {r.status_code}"}

    # ── Dino / Knewin ─────────────────────────────────────────────────
    elif platform_key in ("dino", "einpresswire_br"):
        api_key = (creds.get("dino_api_key") or os.getenv("DINO_API_KEY", "")
                   if platform_key == "dino"
                   else creds.get("ein_api_key") or os.getenv("EIN_API_KEY", ""))
        if not api_key:
            return {**formatted, "status": "payload_ready",
                    "message": f"Credencial não configurada para {platform.name}. Payload pronto.",
                    "submit_url": ("https://dino.com.br/enviar-release" if platform_key == "dino"
                                   else "https://www.einpresswire.com/add-a-press-release/"),
                    "payload": payload_base}
        # Dino usa REST similar ao EIN
        endpoint = ("https://dino.com.br/api/v1/releases" if platform_key == "dino"
                    else "https://www.einpresswire.com/api/v2/press_release")
        async with httpx.AsyncClient() as client:
            payload_with_key = {**payload_base, "api_key": api_key}
            r = await client.post(endpoint, json=payload_with_key, timeout=30)
            if r.status_code in (200, 201, 202):
                return {**formatted, "status": "submitted",
                        "message": f"Release submetido ao {platform.name}"}
            return {**formatted, "status": "error",
                    "message": f"{platform.name}: HTTP {r.status_code} — {r.text[:200]}"}

    # ── B2Press LATAM ─────────────────────────────────────────────────
    elif platform_key == "b2press":
        api_key = creds.get("b2press_api_key") or os.getenv("B2PRESS_API_KEY", "")
        if not api_key:
            return {**formatted, "status": "payload_ready",
                    "message": "B2PRESS_API_KEY não configurado. Payload pronto para envio manual.",
                    "submit_url": "https://b2press.com/submit",
                    "payload": payload_base}
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://api.b2press.com/v1/releases",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={**payload_base, "regions": ["BR", "LATAM"]},
                timeout=30,
            )
            if r.status_code in (200, 201, 202):
                return {**formatted, "status": "submitted",
                        "message": "Release submetido ao B2Press LATAM"}
            return {**formatted, "status": "error",
                    "message": f"B2Press: HTTP {r.status_code}"}

    # ── Accesswire / eReleases (flat fee) ─────────────────────────────
    elif platform_key in ("accesswire", "ereleases"):
        api_key = (creds.get("accesswire_api_key") or os.getenv("ACCESSWIRE_API_KEY", "")
                   if platform_key == "accesswire"
                   else creds.get("ereleases_api_key") or os.getenv("ERELEASES_API_KEY", ""))
        if not api_key:
            return {**formatted, "status": "payload_ready",
                    "message": f"Credencial não configurada para {platform.name}. Payload pronto para envio manual.",
                    "submit_url": ("https://accesswire.com/submit" if platform_key == "accesswire"
                                   else "https://www.ereleases.com/submit/"),
                    "payload": payload_base}
        # Retorna payload_ready mesmo com key — Accesswire/eReleases cobram por release
        # Não disparar automaticamente sem confirmação humana
        return {**formatted, "status": "payload_ready",
                "message": f"{platform.name}: credencial configurada. "
                           f"Confirmar envio manual — cada release tem custo. "
                           f"Aceder a {platform.name} e usar o payload abaixo.",
                "payload": {**payload_base, "api_key": "***configurado***"}}

    # ── Maxpress / PRWireNOW / PRWeb ──────────────────────────────────
    elif platform_key in ("maxpress", "prwirenow"):
        env_key = f"{platform_key.upper()}_API_KEY"
        api_key = creds.get(f"{platform_key}_api_key") or os.getenv(env_key, "")
        if not api_key:
            return {**formatted, "status": "payload_ready",
                    "message": f"{platform.name}: configurar {env_key} no .env. Payload pronto.",
                    "payload": payload_base}
        # Simples POST com API key
        endpoints = {
            "maxpress": "https://api.maxpress.com.br/v1/releases",
            "prwirenow": "https://api.prwirenow.com.br/v1/press_release",
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(
                endpoints.get(platform_key, ""),
                json={**payload_base, "api_key": api_key},
                timeout=30,
            )
            if r.status_code in (200, 201, 202):
                return {**formatted, "status": "submitted",
                        "message": f"Release submetido ao {platform.name}"}
            return {**formatted, "status": "error",
                    "message": f"{platform.name}: HTTP {r.status_code}"}

    # ── Fallback — newswire sem wrapper específico ────────────────────
    else:
        return {**formatted, "status": "payload_ready",
                "message": (f"{platform.name}: payload gerado. "
                            f"Aceder ao portal e submeter manualmente."),
                "payload": payload_base,
                "submit_url": getattr(platform, "url", "")}


async def publish_all(entity: str, articles: list[dict], platforms: list[str] | None = None, credentials: dict | None = None) -> dict:
    """Publica todos os artigos em todas as plataformas configuradas."""
    if platforms is None:
        platforms = [k for k, v in PLATFORM_REGISTRY.items() if v.api and v.pricing == "free"]
    results = {}
    for article in articles:
        asset_type = article.get("asset_type", "unknown")
        text = article.get("article", "")
        seo = article.get("seo", {})
        for p in platforms:
            key = f"{asset_type}@{p}"
            try:
                result = await publish_to(p, entity, text, seo, credentials)
                results[key] = result
            except Exception as e:
                results[key] = {"status": "error", "message": str(e)}
    return {
        "entity": entity,
        "total_articles": len(articles),
        "total_publishes": len(results),
        "successful": sum(1 for v in results.values() if v.get("status") in ("published", "draft", "submitted")),
        "results": results,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Distribution Scorecards ──────────────────────────────────────────────────

def get_platform_scorecard(platform_key: str) -> dict:
    """Retorna scorecard completo de uma plataforma."""
    p = PLATFORM_REGISTRY.get(platform_key)
    if not p:
        return {"error": "Platform not found"}
    return {
        "name": p.name,
        "type": p.type,
        "region": p.region,
        "tier": p.tier,
        "scores": {
            "domain_authority": p.authority,
            "speed": p.speed,
            "permanence": p.permanence,
            "google_news": p.google_news,
            "api_available": p.api,
            "persistence": p.persistence,
            "ai_citation": p.ai_citation,
        },
        "outranking_potential": p.outranking_potential(),
        "pricing": p.pricing,
        "estimated_cost": p.estimated_cost,
        "notes": p.notes,
        "persistence": p.persistence,
        "ai_citation": p.ai_citation,
    }


def get_ranked_platforms(min_score: int = 0) -> list[dict]:
    """Retorna todas as plataformas ranqueadas por Outranking Potential."""
    scored = []
    for key, p in PLATFORM_REGISTRY.items():
        s = p.outranking_potential()
        if s >= min_score:
            scored.append({"key": key, **get_platform_scorecard(key)})
    scored.sort(key=lambda x: x["outranking_potential"], reverse=True)
    return scored


# ── Narrative Blast Campaign Workflow ───────────────────────────────────────

# Archetype → which Tier A "authority belt" profiles matter most
_AUTHORITY_BELT: dict[str, list[str]] = {
    "tech_executive":     ["google_business", "crunchbase", "angellist", "hackernoon", "github"],
    "corporate":          ["google_business", "crunchbase", "clutch", "glassdoor"],
    "startup_founder":    ["google_business", "crunchbase", "angellist", "hackernoon", "devto"],
    "financial":          ["google_business", "crunchbase", "clutch", "trustpilot"],
    "political":          ["google_business", "glassdoor"],
    "celebrity":          ["google_business", "trustpilot"],
    "institutional":      ["google_business", "crunchbase", "clutch"],
    "default":            ["google_business", "crunchbase"],
}

# Tier B content platforms for content blast (always free, have real APIs)
_CONTENT_BLAST_PLATFORMS: list[str] = ["linkedin", "medium", "youtube"]

# Archetype → extra content platforms
_ARCHETYPE_CONTENT_EXTRA: dict[str, list[str]] = {
    "tech_executive":     ["hackernoon", "devto", "github"],
    "startup_founder":    ["hackernoon", "devto", "github"],
    "financial":          ["substack"],
    "corporate":          ["substack"],
    "default":            [],
}

# Budget tiers: "minimal" (<€150/mês), "standard" (€150-300/mês), "premium" (>€300/mês)
_NEWSWIRE_BY_BUDGET: dict[str, list[str]] = {
    "minimal":  ["einpresswire", "24press"],
    "standard": ["einpresswire", "ereleases", "24press"],
    "premium":  ["globenewswire", "accesswire", "ereleases", "einpresswire"],
}


def build_narrative_blast(
    entity: str,
    archetype: str,
    budget: str = "standard",
    region: str = "BR",
    has_company: bool = True,
) -> dict:
    """
    Gera o workflow completo "Narrative Blast" — 30 dias estruturado.

    Retorna um dicionário com:
      - campaign_overview: resumo e prioridade
      - phases: lista de fases com dias, ações, plataformas e checklist
      - stack_mvp: stack mínima viável para o budget
      - warnings: riscos e itens que precisam de verificação humana
    """
    archetype_key = archetype if archetype in _AUTHORITY_BELT else "default"
    content_extra = _ARCHETYPE_CONTENT_EXTRA.get(archetype_key, [])
    authority_platforms = _AUTHORITY_BELT.get(archetype_key, _AUTHORITY_BELT["default"])
    if not has_company:
        authority_platforms = [p for p in authority_platforms if p != "google_business"]

    newswires = _NEWSWIRE_BY_BUDGET.get(budget, _NEWSWIRE_BY_BUDGET["standard"])
    content_platforms = _CONTENT_BLAST_PLATFORMS + [p for p in content_extra if p not in _CONTENT_BLAST_PLATFORMS]

    # Regional adjustment: add BR/PT-specific newswire if budget allows
    regional_extras = []
    if region == "BR" and budget in ("standard", "premium"):
        regional_extras = ["dino", "einpresswire_br"]
    elif region == "PT" and budget in ("standard", "premium"):
        regional_extras = ["einpresswire_br"]

    phases = [
        {
            "phase": "Dia 0 — Cinturão de Autoridade (setup único)",
            "days": "Dia 0",
            "priority": "alta",
            "description": "Criar ou atualizar perfis em plataformas de autoridade institucional. "
                           "Esses perfis alimentam o Knowledge Panel e são citados pelo Google AI Overview.",
            "actions": [
                {
                    "platform_key": pk,
                    "platform_name": PLATFORM_REGISTRY[pk].name if pk in PLATFORM_REGISTRY else pk,
                    "action": "Criar/atualizar perfil com bio completa, foto profissional e links para domínio principal",
                    "priority": "obrigatório" if pk in ("google_business", "crunchbase") else "recomendado",
                    "cost": PLATFORM_REGISTRY[pk].pricing if pk in PLATFORM_REGISTRY else "—",
                    "notes": PLATFORM_REGISTRY[pk].notes if pk in PLATFORM_REGISTRY else "",
                    "api": PLATFORM_REGISTRY[pk].api if pk in PLATFORM_REGISTRY else False,
                }
                for pk in authority_platforms if pk in PLATFORM_REGISTRY
            ],
            "checklist": [
                "Bio de 150-300 palavras (tom institucional, 3ª pessoa)",
                "Foto profissional alta resolução",
                "Link para domínio principal ou LinkedIn",
                "Palavras-chave do nome completo no campo de título/headline",
                "Verificar que perfil é público e indexável",
            ],
        },
        {
            "phase": "Dia 1 — Narrative Blast (sincronização simultânea)",
            "days": "Dia 1",
            "priority": "crítica",
            "description": "Publicar narrativa core em múltiplos canais no mesmo dia. "
                           "O Google detecta coocorrência de entidade em múltiplos domínios de alta autoridade "
                           "como sinal de relevância — isso é o que acelera displacement de SERP.",
            "actions": [
                {
                    "platform_key": "linkedin",
                    "platform_name": "LinkedIn Articles",
                    "action": "Publicar artigo principal (hub de narrativa). Este é o anchor — todos os outros vão linkar para ele.",
                    "priority": "obrigatório",
                    "cost": "free",
                    "notes": "Fixar no perfil após publicar. Adicionar 3-5 hashtags do setor.",
                    "api": True,
                },
            ] + [
                {
                    "platform_key": pk,
                    "platform_name": PLATFORM_REGISTRY[pk].name,
                    "action": f"Publicar versão adaptada para {PLATFORM_REGISTRY[pk].name} — formato {PLATFORM_REGISTRY[pk].type}",
                    "priority": "alta",
                    "cost": PLATFORM_REGISTRY[pk].pricing,
                    "estimated_cost": PLATFORM_REGISTRY[pk].estimated_cost,
                    "notes": PLATFORM_REGISTRY[pk].notes,
                    "api": PLATFORM_REGISTRY[pk].api,
                }
                for pk in newswires if pk in PLATFORM_REGISTRY and pk != "linkedin"
            ] + [
                {
                    "platform_key": pk,
                    "platform_name": PLATFORM_REGISTRY[pk].name,
                    "action": f"Publicar versão adaptada para {PLATFORM_REGISTRY[pk].name}",
                    "priority": "alta",
                    "cost": PLATFORM_REGISTRY[pk].pricing,
                    "notes": PLATFORM_REGISTRY[pk].notes,
                    "api": PLATFORM_REGISTRY[pk].api,
                }
                for pk in content_platforms if pk in PLATFORM_REGISTRY and pk != "linkedin"
            ],
            "checklist": [
                "Narrativa core idêntica em todas as versões (apenas formato muda, não mensagem)",
                "Todas as versões linkam para o artigo LinkedIn principal",
                "Press release inclui citação direta do executivo (1-2 frases)",
                "Vídeo usa os primeiros 60s para a mensagem core (YouTube)",
                "Solicitar indexação manual via Google Search Console para cada URL nova",
            ],
        },
        {
            "phase": "Dias 2-7 — Backfill e Amplificação",
            "days": "Dias 2-7",
            "priority": "média",
            "description": "Publicar conteúdo de suporte que reforça a narrativa core. "
                           "Releases de apoio com citações, decks, perfis atualizados com links para o novo conteúdo.",
            "actions": [
                {
                    "platform_key": pk,
                    "platform_name": PLATFORM_REGISTRY[pk].name,
                    "action": "Publicar release de apoio (citação ou dado adicional que reforça narrativa core)",
                    "priority": "recomendado",
                    "cost": PLATFORM_REGISTRY[pk].pricing,
                    "estimated_cost": PLATFORM_REGISTRY[pk].estimated_cost,
                    "notes": "Usar dados diferentes do release principal para evitar duplicate content",
                    "api": PLATFORM_REGISTRY[pk].api,
                }
                for pk in regional_extras if pk in PLATFORM_REGISTRY
            ] + [
                {
                    "platform_key": "substack",
                    "platform_name": "Substack",
                    "action": "Newsletter: resumo da semana com links para todos os conteúdos publicados",
                    "priority": "recomendado",
                    "cost": "free",
                    "notes": "Objeto de email: '[Nome] — [título do artigo principal]'. Evita newsletter genérica.",
                    "api": False,
                }
            ] + [
                {
                    "platform_key": pk,
                    "platform_name": PLATFORM_REGISTRY[pk].name,
                    "action": "Atualizar perfil com links para novo conteúdo publicado",
                    "priority": "complementar",
                    "cost": PLATFORM_REGISTRY[pk].pricing,
                    "notes": "Basta atualizar 'Recent work' ou bio com URL do artigo LinkedIn",
                    "api": PLATFORM_REGISTRY[pk].api,
                }
                for pk in authority_platforms if pk in PLATFORM_REGISTRY
            ],
            "checklist": [
                "Releases de apoio usam dados diferentes do principal (evitar penalidade de duplicate content)",
                "Atualizar bio em todos os perfis de autoridade com link para o artigo principal",
                "Responder comentários no LinkedIn artigo nas primeiras 48h (sinaliza engagement)",
            ],
        },
        {
            "phase": "Dias 8-30 — Monitoramento e Displacement Tracking",
            "days": "Dias 8-30",
            "priority": "operacional",
            "description": "Medir displacement: quantos resultados negativos foram empurrados para a página 2+ "
                           "pelos novos conteúdos positivos. Auditoria comparativa quinzenal.",
            "actions": [
                {
                    "platform_key": "—",
                    "platform_name": "SerpAPI",
                    "action": "Rodar nova auditoria CouncilIA no dia 15 e dia 30. Comparar NPA Score antes/depois.",
                    "priority": "obrigatório",
                    "cost": "~$0.01/auditoria",
                    "notes": "Focar nas posições dos novos URLs vs. posição original do conteúdo negativo",
                    "api": True,
                },
                {
                    "platform_key": "—",
                    "platform_name": "Google Search Console",
                    "action": "Solicitar indexação manual para cada URL nova publicada. Verificar indexação em 48-72h.",
                    "priority": "alta",
                    "cost": "free",
                    "notes": "URL Inspection Tool → Request Indexing. Até 10 URLs por dia por propriedade.",
                    "api": False,
                },
                {
                    "platform_key": "—",
                    "platform_name": "CouncilIA Monitor",
                    "action": f"Configurar alerta de monitoramento para '{entity}'. Trigger: variação NPA > 5 pontos.",
                    "priority": "recomendado",
                    "cost": "free",
                    "notes": "Rota /monitor/{slug}/check. Integrar com Windows Task Scheduler para execução diária.",
                    "api": True,
                },
            ],
            "checklist": [
                "NPA Score dia 1 vs. dia 15 vs. dia 30 documentado",
                "Print de SERP para query '[Nome] + [setor]' em cada checkpoint",
                "Listar quais URLs positivas estão indexadas (Search Console → Coverage)",
                "Identificar resultado negativo mais persistente → próximo release deve responder diretamente",
            ],
        },
    ]

    # Budget MVS (Minimum Viable Stack)
    if budget == "minimal":
        stack_mvp = [
            {"key": "linkedin",       "name": "LinkedIn Articles", "cost": "Free",      "role": "Hub de narrativa"},
            {"key": "medium",         "name": "Medium",            "cost": "Free",      "role": "Crosspost + indexação"},
            {"key": "youtube",        "name": "YouTube",           "cost": "Free",      "role": "Vídeo 3-5min do release"},
            {"key": "einpresswire",   "name": "EIN Presswire",     "cost": "$50-200",   "role": "Google News + syndication"},
            {"key": "crunchbase",     "name": "Crunchbase",        "cost": "Free",      "role": "Perfil de autoridade"},
            {"key": "google_business","name": "Google Business",   "cost": "Free",      "role": "Knowledge Panel anchor"},
        ]
        total_estimate = "€0-200/campanha"
    elif budget == "standard":
        stack_mvp = [
            {"key": "linkedin",        "name": "LinkedIn Articles",  "cost": "Free",       "role": "Hub de narrativa"},
            {"key": "medium",          "name": "Medium",             "cost": "Free",       "role": "Crosspost"},
            {"key": "youtube",         "name": "YouTube",            "cost": "Free",       "role": "Vídeo resumo"},
            {"key": "einpresswire",    "name": "EIN Presswire",      "cost": "$50-200",    "role": "Google News global"},
            {"key": "ereleases",       "name": "eReleases",          "cost": "$105-200",   "role": "Rede PR Newswire"},
            {"key": "hackernoon",      "name": "HackerNoon",         "cost": "Free",       "role": "Tech authority (se aplicável)"},
            {"key": "crunchbase",      "name": "Crunchbase",         "cost": "Free",       "role": "Perfil de autoridade"},
            {"key": "google_business", "name": "Google Business",    "cost": "Free",       "role": "Knowledge Panel anchor"},
            {"key": "dino" if region == "BR" else "einpresswire_br",
             "name": "Dino BR" if region == "BR" else "EIN BR",      "cost": "R$500-2000" if region == "BR" else "$50-200", "role": "Google News regional"},
        ]
        total_estimate = "€150-400/campanha"
    else:  # premium
        stack_mvp = [
            {"key": "linkedin",        "name": "LinkedIn Articles",  "cost": "Free",      "role": "Hub de narrativa"},
            {"key": "medium",          "name": "Medium",             "cost": "Free",      "role": "Crosspost"},
            {"key": "youtube",         "name": "YouTube",            "cost": "Free",      "role": "Vídeo resumo"},
            {"key": "globenewswire",   "name": "GlobeNewswire",      "cost": "$150-500",  "role": "Google News premium + AI Overview"},
            {"key": "accesswire",      "name": "Accesswire",         "cost": "$350",      "role": "Yahoo Finance + MarketWatch"},
            {"key": "ereleases",       "name": "eReleases",          "cost": "$105-200",  "role": "Rede PR Newswire"},
            {"key": "crunchbase",      "name": "Crunchbase",         "cost": "$29/mês",   "role": "Perfil pro"},
            {"key": "google_business", "name": "Google Business",    "cost": "Free",      "role": "Knowledge Panel anchor"},
            {"key": "hackernoon",      "name": "HackerNoon",         "cost": "Free",      "role": "Tech authority"},
        ]
        total_estimate = "€500-1200/campanha"

    # Warnings
    warnings = []
    if "issuewire" in newswires:
        warnings.append("IssueWire: Google News não garantido no plano básico. Verificar indexação manualmente antes de recomendar ao cliente.")
    if "24press" in newswires:
        warnings.append("24-7 Press Release: Google News só no plano pago ($249+). Plano $29 não distribui para Google News.")
    if "trustpilot" in authority_platforms:
        warnings.append("Trustpilot: alto risco de reviews negativos aparecerem no perfil. Usar apenas se reputação de produto é controlada.")
    if "glassdoor" in authority_platforms:
        warnings.append("Glassdoor: reviews de ex-funcionários podem amplificar narrativa negativa. Criar perfil apenas se monitoramento estiver ativo.")
    warnings.append("PR Underground ($74.99): Google News real, verificado. Plano US National ($419) inclui Yahoo Finance. Legítimo e custo agressivo.")
    warnings.append("RedPress: aggregator de syndication verificado. Usar plano Core ($219) ou superior para impacto real — plano Basic (DA 72) tem valor limitado.")
    warnings.append("Sitetrail (~$200/mês): NÃO incluído. 'Sites Google News-approved' é claim vago — risco de PBN. Investigar antes de recomendar.")
    warnings.append("Indexação manual no Google Search Console acelera resultados em 48-72h. Não pular este passo.")

    # ── Cross-Language Occupation ─────────────────────────────────────────
    # Mesmo conteúdo em EN/PT/ES ocupa Google global, AI models e SERPs multilíngues
    cross_language = {
        "enabled": region in ("GLOBAL", "PT", "ES"),
        "priority_languages": {
            "BR":     ["PT-BR", "EN", "ES"],
            "PT":     ["PT-PT", "EN", "ES"],
            "ES":     ["ES", "EN", "PT"],
            "GLOBAL": ["EN", "PT-BR", "ES"],
        }.get(region, ["PT-BR", "EN"]),
        "rationale": (
            "Publicar a mesma narrativa em PT+EN+ES multiplica pontos de entrada nos modelos de IA. "
            "ChatGPT/Gemini/Perplexity foram treinados majoritariamente em EN — "
            "ter conteúdo indexado em EN aumenta probabilidade de citação."
        ),
        "recommended_platforms": {
            "EN": ["medium", "linkedin", "hackernoon"],
            "PT-BR": ["linkedin", "medium", "substack"],
            "PT-PT": ["observador", "eco", "linkedin"],
            "ES": ["expansion", "linkedin", "medium"],
        },
        "effort": "alto — requer tradução profissional ou LLM com revisão humana",
        "impact": "muito alto para AI citation probability (+20-40pp estimado)",
    }

    # ── Narrative Saturation Detection ───────────────────────────────────
    # Detector de overposting: quando PARAR de publicar
    saturation_thresholds = {
        "releases_por_mes": {
            "verde": "1-2",
            "amarelo": "3-4",
            "vermelho": "5+",
            "nota": "Mais de 4 releases/mês com a mesma entidade → Google detecta footprint artificial",
        },
        "plataformas_mesmo_texto": {
            "verde": "1-2",
            "amarelo": "3",
            "vermelho": "4+",
            "nota": "Texto idêntico em 4+ domínios no mesmo dia → penalidade de duplicate content",
        },
        "sinais_de_saturacao": [
            "Novo conteúdo não aparece indexado em 72h (Google bloqueou crawl)",
            "Ranking do conteúdo positivo não sobe apesar de novos releases",
            "Domínio de newswire começa a ranquear em posição baixa (15+) para branded search",
            "Alertas do Google Search Console sobre duplicate content",
            "Novo artigo tem zero backlinks orgânicos após 30 dias",
        ],
        "acao_recomendada": (
            "Se detectar saturação: pausar novas publicações por 14 dias, "
            "focar em atualizar/expandir conteúdo já indexado, "
            "usar Motor de Variação Semântica para diferenciar próximas publicações."
        ),
    }

    return {
        "entity": entity,
        "archetype": archetype,
        "budget": budget,
        "region": region,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "campaign_overview": {
            "total_platforms": len(authority_platforms) + len(content_platforms) + len(newswires) + len(regional_extras),
            "newswires": [PLATFORM_REGISTRY[k].name for k in newswires if k in PLATFORM_REGISTRY],
            "content_platforms": [PLATFORM_REGISTRY[k].name for k in content_platforms if k in PLATFORM_REGISTRY],
            "authority_belt": [PLATFORM_REGISTRY[k].name for k in authority_platforms if k in PLATFORM_REGISTRY],
            "total_estimate": total_estimate,
            "duration_days": 30,
        },
        "phases": phases,
        "stack_mvp": stack_mvp,
        "warnings": warnings,
        "cross_language": cross_language,
        "saturation": saturation_thresholds,
    }
