"""
YouTube Warfare Engine — Detecção, Scoring, Asset Generation,
TrueView Campaigns, e Battle Plan Integration.

YouTube is the highest CTR, highest-authority (DA 100) channel on SERP.
A single negative video at position 1-3 has 2-5x the CTR of text links
and can persist for years without organic decay.
"""
import re
from datetime import datetime, timezone
from services.constants import domain_authority


YOUTUBE_DA = 100  # YouTube domain authority = max


def extract_youtube_results(serp: list[dict]) -> list[dict]:
    """Filter & enrich YouTube/video results from a SERP array.

    Each returned video has:
      - title, channel, url, video_id, position, sentiment,
        views (if available), is_negative, thumbnail_url
    """
    videos = []
    for r in serp:
        url = r.get("url", "") or ""
        domain = r.get("domain", "") or ""
        is_youtube = "youtube.com" in domain or "youtu.be" in url
        is_video_type = r.get("type") == "video"
        if not (is_youtube or is_video_type):
            continue

        video_id = _extract_video_id(url)
        sentiment = r.get("sentiment", "neutral")
        position = r.get("position", 99)

        videos.append({
            "title": (r.get("title", "") or "")[:120],
            "channel": _extract_channel(r.get("title", ""), url),
            "url": url,
            "video_id": video_id,
            "position": position,
            "sentiment": sentiment,
            "is_negative": sentiment == "negative",
            "domain": domain,
            "authority": YOUTUBE_DA,
            "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg" if video_id else "",
        })
    return videos


def _extract_video_id(url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|/shorts/)([a-zA-Z0-9_-]{11})", url)
    return m.group(1) if m else ""


def _extract_channel(title: str, url: str) -> str:
    """Best-effort channel extraction from URL or fallback."""
    m = re.search(r"(?:@|channel/)([\w-]+)", url)
    if m:
        return m.group(1)
    return "YouTube"


def compute_youtube_toxicity(videos: list[dict]) -> dict:
    """YouTube Toxicity Score (0-100) with decomposition.

    Components:
      - Video negative count (30 pts): raw number of negative videos found
      - Average position penalty (25 pts): how high negative videos rank
      - Negative saturation (25 pts): ratio of negative to total videos
      - Position-weighted severity (20 pts): combined position × negativity
    """
    total = len(videos) or 1
    neg_videos = [v for v in videos if v["is_negative"]]
    neg_count = len(neg_videos)

    # Video Negative Count (30 pts)
    neg_count_score = min(neg_count * 6, 30)

    # Average position penalty (25 pts)
    if neg_videos:
        avg_pos = sum(v["position"] for v in neg_videos) / len(neg_videos)
        # Lower position (closer to #1) = worse. Normalize: (10 - avg_pos) / 9 * 25
        pos_penalty = round(max(0, (10 - min(avg_pos, 10)) / 9) * 25, 1)
    else:
        pos_penalty = 0

    # Negative saturation (25 pts)
    neg_saturation = neg_count / total
    sat_score = round(neg_saturation * 25, 1)

    # Position-weighted severity (20 pts)
    if neg_videos:
        severity = sum(
            (11 - v["position"]) * 2 for v in neg_videos
        )
        severity_score = min(severity, 20)
    else:
        severity_score = 0

    total_score = round(neg_count_score + pos_penalty + sat_score + severity_score, 1)

    return {
        "total": total_score,
        "breakdown": {
            "video_negative_count": {"score": neg_count_score, "max": 30, "raw": neg_count},
            "avg_position_penalty": {"score": pos_penalty, "max": 25, "raw": round(sum(v["position"] for v in neg_videos) / max(len(neg_videos), 1), 1) if neg_videos else 0},
            "negative_saturation":  {"score": sat_score,     "max": 25, "raw": round(neg_saturation * 100, 1)},
            "position_severity":    {"score": severity_score, "max": 20, "raw": round(severity, 1) if neg_videos else 0},
        },
        "videos_detected": total,
        "negative_videos": neg_count,
        "videos": videos,
        "label": _toxicity_label(total_score),
    }


def _toxicity_label(score: float) -> str:
    if score >= 70:
        return "CRÍTICO — Domínio visual negativo consolidado"
    if score >= 40:
        return "ALTO — Presença negativa significativa no YouTube"
    if score >= 15:
        return "MODERADO — Sinais de contaminação visual"
    return "BAIXO — Sem contaminação significativa no YouTube"


def compute_video_npa_boost(youtube_toxicity: dict) -> dict:
    """Computes NPA boost factor from YouTube data.

    YouTube videos recebem peso adicional no NPA porque ocupam
    mais espaço visual na SERP (thumbnail) e têm CTR superior a texto.

    Boost escolhido: 1.2x (conservador).
    Razão: sem dados de CTR por entidade, qualquer número acima de 1.2x
    é especulativo. Revisar quando tivermos ≥30 cases com vídeos indexados.
    """
    BOOST = 1.2  # conservador até termos dados de CTR reais
    score = youtube_toxicity["total"]
    base_npa_impact = score / 100 * 50  # 0-50 scaled
    boosted = round(base_npa_impact * BOOST, 1)
    return {
        "youtube_score": score,
        "base_npa_impact": base_npa_impact,
        "boosted_npa_impact": boosted,
        "boost_multiplier": BOOST,
        "boost_note": "Conservador (1.2x) — sem dados de CTR calibrados por entidade",
        "npa_additional_points": round(boosted - base_npa_impact, 1),
    }


def generate_video_script(
    entity: str,
    asset_subtype: str,
    context: str = "",
) -> str:
    """Generate a 5-minute YouTube video script using the roteiro_youtube template.

    Asset subtypes:
      - posicionamento_institucional: general institutional positioning
      - esclarecimento: clarification/response to crisis
      - trajetoria: career/life trajectory (bio-style)
      - faq: FAQ / transparency about the situation
    """
    template = _get_video_template(asset_subtype)
    filled = template.format(entity=entity, context=context or "")
    return filled


def _get_video_template(subtype: str) -> str:
    """Return the template string for the requested subtype."""
    templates = {
        "posicionamento_institucional": """\
ROTEIRO — Posicionamento Institucional ({entity})
Duração: 4:30 — 5:00
Tom: Sério, institucional, confiável

[HOOK — 0:00 a 0:30]
Quadro: Plano médio, fundo institucional (escritório/biblioteca/neutro)
"Meu nome é {entity} e neste vídeo vou responder diretamente às perguntas que muitos de vocês têm feito."

[CONTEXTO — 0:30 a 2:00]
"Nos últimos dias, circularam informações sobre [contexto]. Quero esclarecer pessoalmente o que está acontecendo."
— Explicação factual do contexto em 3 frases máximas
— Sem defensividade, sem atacar terceiros
— Mostrar documentos/telas se relevante (corte para tela compartilhada)

[POSICIONAMENTO — 2:00 a 4:00]
"Minha posição é clara: [mensagem-chave]."
— 3 pilares do posicionamento (cada um com exemplo concreto)
— O que está sendo feito para resolver/endereçar
— Medidas já tomadas (factual, verificável)

[CTA INSTITUCIONAL — 4:00 a 4:45]
"Para mais informações, visite [site]. Lá você encontra documentos, FAQ e comunicados oficiais."
— Inscreva-se no canal para acompanhar atualizações
— Link para site institucional na descrição
— Deixe seu comentário — responderei pessoalmente

[ENCERRAMENTO — 4:45 a 5:00]
"Obrigado pela confiança. Sigo à disposição."
— Tela preta com contatos: site, LinkedIn, email
""",

        "esclarecimento": """\
ROTEIRO — Esclarecimento ({entity})
Duração: 4:00 — 5:00
Tom: Direto, factual, sem rodeios

[HOOK — 0:00 a 0:30]
Quadro: Primeiro plano, contato visual direto
"Vou ser direto: [mentira/boato/notícia incorreta]. Isso não é verdade. Aqui estão os fatos."

[CONTEXTO — 0:30 a 2:00]
"Deixa eu explicar exatamente o que aconteceu."
— Linha do tempo dos eventos (15s cada marco)
— Sem julgamentos, apenas fatos com datas
— Documentos como evidência (mostrar na tela)

[REFUTAÇÃO — 2:00 a 3:30]
"A informação que circulou está incorreta porque: [razão 1], [razão 2], [razão 3]."
— Cada refutação com fonte verificável
— Evitar linguagem emocional
— Se aplicável: mencionar medida judicial já tomada

[CTA — 3:30 a 4:30]
"Todo o material está disponível em [site/esclarecimento]. Compartilhe este vídeo com quem precisa saber a verdade."
— Link para FAQ completo na descrição
— Oferecer entrevistas para veículos sérios

[ENCERRAMENTO]
— Tela preta com contato jurídico/institucional
""",

        "trajetoria": """\
ROTEIRO — Trajetória Profissional ({entity})
Duração: 4:00 — 5:00
Tom: Inspirador, profissional, humano

[HOOK — 0:00 a 0:40]
"Meu nome é {entity} e esta é a história de como cheguei até aqui."
— Imagens de abertura: fotos de arquivo, momentos marcantes

[JORNADA — 0:40 a 3:00]
— Formação: onde estudou, o que formou
— Carreira: principais marcos (empresas, cargos, conquistas)
— Realizações relevantes (prêmios, cases, projetos)
— Momento de virada ou desafio superado

[VALORES — 3:00 a 4:00]
"O que me guia profissionalmente: [princípio 1], [princípio 2], [princípio 3]."
— Como esses valores se aplicam ao trabalho atual
— Exemplo concreto de decisão difícil baseada em valores

[CTA — 4:00 a 4:45]
"Se você quer saber mais sobre meu trabalho, me siga no LinkedIn e acompanhe meu site."
— Inscreva-se no canal

[ENCERRAMENTO]
— Tela final com redes sociais e site
""",

        "faq": """\
ROTEIRO — FAQ / Perguntas Frequentes ({entity})
Duração: 5:00 — 6:00
Tom: Didático, paciente, transparente

[HOOK — 0:00 a 0:30]
"Recebi muitas perguntas sobre [tema]. Vou responder as principais aqui."

[PERGUNTAS — 0:30 a 5:00]
— PERGUNTA 1: [pergunta mais comum] → Resposta direta (30-45s)
— PERGUNTA 2: [segunda mais comum] → Resposta (30-45s)
— PERGUNTA 3: [terceira] → Resposta (30-45s)
— PERGUNTA 4: [quarta] → Resposta (30-45s)
— PERGUNTA 5: [quinta] → Resposta (30-45s)

[CTA — 5:00 a 5:30]
"Todas as respostas estão também no FAQ do meu site: [site/faq]."
— Deixe sua pergunta nos comentários
— Inscreva-se para novos vídeos
""",
    }
    return templates.get(subtype, templates["posicionamento_institucional"])


def youtube_ads_campaign(entity: str, threat_level: str, archetype: str) -> dict:
    """Generate YouTube Ads campaign structure for the battle plan."""
    is_critical = threat_level.upper() == "CRITICAL"

    campaigns = []
    if is_critical:
        campaigns.append({
            "name": "Brand Defense — TrueView In-Stream",
            "objective": "Defender CTR de marca contra resultados negativos",
            "format": "TrueView In-Stream (pular após 5s)",
            "budget_daily_min": 80,
            "budget_daily_max": 150,
            "targeting": f"Pesquisa de nome + '{entity}'",
            "video_asset": "Posicionamento Institucional ou Esclarecimento",
            "bid_strategy": "CPV (custo por visualização) — máximo R$0,30",
            "landing_page": "Site institucional / página de esclarecimento",
        })
        campaigns.append({
            "name": "Hostile Terms — Discovery Ads",
            "objective": "Ocupar descoberta para termos de crise antes do usuário buscar",
            "format": "Discovery Ads (YouTube Home + Watch Next)",
            "budget_daily_min": 50,
            "budget_daily_max": 100,
            "targeting": f"Termos: '{entity}' + termos hostis do arquétipo {archetype}",
            "video_asset": "FAQ ou Trajetória",
            "bid_strategy": "CPM — máximo R$25",
            "landing_page": "FAQ no site / artigo completo",
        })

    campaigns.append({
        "name": "Institutional Presence — Bumper Ads",
        "objective": "Manutenção de presença institucional com remarketing",
        "format": "Bumper Ads (6s, não pulável)",
        "budget_daily_min": 30,
        "budget_daily_max": 60,
        "targeting": "Remarketing: visitantes do site + público de busca de nome",
        "video_asset": "Cápsula de 6s com posicionamento",
        "bid_strategy": "CPM — máximo R$40",
        "landing_page": "Site institucional",
    })

    total_min = sum(c["budget_daily_min"] for c in campaigns)
    total_max = sum(c["budget_daily_max"] for c in campaigns)

    return {
        "campaigns": campaigns,
        "total_daily_budget_min": total_min,
        "total_daily_budget_max": total_max,
        "total_monthly_budget_min": total_min * 30,
        "total_monthly_budget_max": total_max * 30,
        "strategy_note": "YouTube Ads operating as visual brand defense layer. "
            "In crisis, TrueView blocks negative CTR at the top of SERP. "
            "In vigilance, Bumper Ads maintain institutional recall.",
    }


def youtube_battle_section(serp: list[dict]) -> dict:
    """Generate the 'Guerra YouTube' section for the battle plan."""
    videos = extract_youtube_results(serp)
    toxicity = compute_youtube_toxicity(videos)
    neg_videos = [v for v in videos if v["is_negative"]]

    section = {
        "present": len(videos) > 0,
        "total_videos": len(videos),
        "negative_videos": len(neg_videos),
        "youtube_toxicity": toxicity,
        "recommended_actions": [],
        "negative_video_list": [
            {
                "title": v["title"],
                "channel": v["channel"],
                "position": v["position"],
                "url": v["url"],
                "urgency": "CRÍTICO" if v["position"] <= 3 else "ALTO" if v["position"] <= 5 else "MODERADO",
                "strategy": _video_strategy(v["position"]),
            }
            for v in neg_videos
        ],
    }

    if neg_videos:
        section["recommended_actions"].extend([
            "Criar canal oficial da entidade no YouTube (se não existir)",
            "Produzir vídeo de posicionamento institucional como primeiro asset",
            "Publicar FAQ em vídeo para capturar tráfego de busca",
            "Configurar YouTube Ads (TrueView) para termos de marca",
        ])
        if any(v["position"] <= 3 for v in neg_videos):
            section["recommended_actions"].insert(0,
                "URGENTE: Vídeo negativo na posição 1-3 — produzir contra-vídeo nas próximas 48h"
            )

    section["channel_strategy"] = {
        "own_channel": {
            "priority": "CRÍTICO" if toxicity["total"] >= 40 else "RECOMENDADO",
            "videos_to_produce": _recommended_videos(toxicity["total"]),
            "cadence": "1 vídeo/semana nas primeiras 4 semanas, depois 1-2/mês",
        },
        "partner_channels": {
            "strategy": "Identificar podcasts e canais do setor para entrevistas",
            "search_terms": f"entrevista + [setor], podcast + [setor], canal do [setor]",
        },
    }

    return section


def _video_strategy(position: int) -> str:
    if position == 1:
        return "Produzir vídeo próprio e impulsionar com TrueView para ocupar #1"
    if position <= 3:
        return "Produzir conteúdo de autoridade + SEO YouTube + TrueView para deslocar"
    if position <= 5:
        return "Produzir FAQ em vídeo + otimizar para busca de nome"
    return "Produzir conteúdo institucional contínuo para empurrar para página 2+"


def _recommended_videos(toxicity_score: float) -> list[str]:
    if toxicity_score >= 70:
        return ["esclarecimento", "posicionamento_institucional", "faq", "trajetoria"]
    if toxicity_score >= 40:
        return ["posicionamento_institucional", "faq", "trajetoria"]
    if toxicity_score >= 15:
        return ["posicionamento_institucional", "trajetoria"]
    return ["trajetoria"]
