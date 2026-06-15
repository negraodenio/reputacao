"""
Political Content Producer — Gerador de Conteúdo Político Especializado.

Gera conteúdo indexável e sem violações da Lei Eleitoral para políticos:
  - mandato_realizacoes:        prestação de contas de obras/ações
  - posicionamento_legislativo: projetos de lei e votações
  - perfil_eleitoral:           biografia política
  - agenda_publica:             cobertura de eventos e inaugurações
  - contraposicao_narrativa:    resposta factual a narrativas negativas

Cada tipo de conteúdo é calibrado para indexação no Google News:
  - Título com SEO político
  - Lead jornalístico (5W1H)
  - Corpo com estrutura HTML semântica
  - Dados factuais (datas, valores, locais)
  - Sem linguagem eleitoral ilegal
"""
from __future__ import annotations
import logging
import json
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("councilia.political_content")

# ── Storage ────────────────────────────────────────────────────────────────────
if os.environ.get("VERCEL"):
    POLITICAL_CONTENT_DIR = Path("/tmp/political_content")
else:
    POLITICAL_CONTENT_DIR = Path(__file__).parent.parent / "political_content"

POLITICAL_CONTENT_DIR.mkdir(parents=True, exist_ok=True)

# ── Tipos de conteúdo e seus prompts ─────────────────────────────────────────
POLITICAL_CONTENT_TYPES = {
    "mandato_realizacoes": {
        "label":       "Prestação de Contas — Realizações do Mandato",
        "description": "Artigo jornalístico listando obras, projetos e ações do mandato",
        "serp_target": "Aparecer no top 5 quando buscam '{nome} realizações', '{nome} obras'",
        "window_ok":   ["construction", "pre_campaign", "pre_electoral"],
    },
    "posicionamento_legislativo": {
        "label":       "Posicionamento Legislativo",
        "description": "Artigo sobre projetos de lei, votações e posições públicas",
        "serp_target": "Aparecer quando buscam '{nome} projeto de lei', '{nome} votação'",
        "window_ok":   ["construction", "pre_campaign", "pre_electoral"],
    },
    "perfil_eleitoral": {
        "label":       "Perfil Político",
        "description": "Biografia política completa e indexável",
        "serp_target": "Aparecer no top 3 para busca pelo nome do político",
        "window_ok":   ["construction", "pre_campaign", "official_campaign", "pre_electoral"],
    },
    "agenda_publica": {
        "label":       "Agenda Pública",
        "description": "Cobertura de evento, inauguração ou participação pública",
        "serp_target": "Ocupar Google News com notícias recentes e positivas",
        "window_ok":   ["construction", "pre_campaign", "official_campaign", "pre_electoral"],
    },
    "contraposicao_narrativa": {
        "label":       "Contraposição Narrativa",
        "description": "Resposta factual a narrativas negativas circulando no Google",
        "serp_target": "Deslocar resultados negativos com conteúdo factual equivalente",
        "window_ok":   ["construction", "pre_campaign", "official_campaign", "pre_electoral"],
    },
    "release_conquista": {
        "label":       "Release — Conquista/Aprovação",
        "description": "Press release sobre aprovação de projeto, investimento ou reconhecimento",
        "serp_target": "Google News Top Stories com título de conquista positiva",
        "window_ok":   ["construction", "pre_campaign", "official_campaign", "pre_electoral"],
    },
}


def produce_political_content(
    entity_name:    str,
    content_type:   str,
    context:        dict | None = None,
    electoral_window: str = "construction",
) -> dict:
    """
    Gera conteúdo político especializado.

    Args:
        entity_name:      Nome do político
        content_type:     Tipo de conteúdo (ver POLITICAL_CONTENT_TYPES)
        context:          Contexto adicional (realizações, projetos, cargo, cidade, etc.)
        electoral_window: Janela eleitoral atual (para compliance)

    Returns:
        {
          "content_type": str,
          "title": str,
          "lead": str,
          "body": str,
          "seo_tags": list,
          "word_count": int,
          "compliance_check": dict,
          "generated_at": str,
        }
    """
    if content_type not in POLITICAL_CONTENT_TYPES:
        raise ValueError(f"Tipo inválido: {content_type}. Válidos: {list(POLITICAL_CONTENT_TYPES)}")

    ctx = context or {}
    type_config = POLITICAL_CONTENT_TYPES[content_type]

    # Check compliance
    from services.political_engine import compliance_check
    window_ok = electoral_window in type_config.get("window_ok", [])
    if not window_ok and electoral_window == "silence":
        return {
            "error": "PUBLICAÇÃO BLOQUEADA — Silêncio eleitoral ativo. Nenhum conteúdo pode ser publicado.",
            "content_type": content_type,
            "electoral_window": electoral_window,
        }

    # Montar prompt
    prompt = _build_prompt(content_type, entity_name, ctx, electoral_window)

    try:
        from services.openrouter_service import call_openrouter
        response = call_openrouter(prompt, max_tokens=1200)
        raw = response["choices"][0]["message"]["content"]

        # Parsear o retorno estruturado
        parsed = _parse_political_content(raw, entity_name, content_type)

        # Compliance check no conteúdo gerado
        full_text = f"{parsed.get('title', '')} {parsed.get('body', '')}"
        compliance = compliance_check(full_text, electoral_window)

        parsed.update({
            "content_type":    content_type,
            "type_label":      type_config["label"],
            "entity_name":     entity_name,
            "electoral_window": electoral_window,
            "compliance":      compliance,
            "generated_at":    datetime.now(timezone.utc).isoformat(),
            "word_count":      len(parsed.get("body", "").split()),
        })

        return parsed

    except Exception as e:
        logger.error(f"Erro gerando conteúdo político ({content_type}): {e}")
        return {
            "error":        str(e),
            "content_type": content_type,
            "entity_name":  entity_name,
        }


def _build_prompt(
    content_type:     str,
    entity_name:      str,
    context:          dict,
    electoral_window: str,
) -> str:
    """Monta o prompt LLM para cada tipo de conteúdo político."""

    cargo    = context.get("role", "político")
    partido  = context.get("party", "")
    cidade   = context.get("city", "")
    estado   = context.get("state", "")
    detalhes = context.get("details", "")
    mandato_info = context.get("mandate_info", "")

    loc = f"{cidade}/{estado}" if cidade and estado else (cidade or estado or "Brasil")
    party_str = f" pelo {partido}" if partido else ""

    compliance_note = ""
    if electoral_window == "official_campaign":
        compliance_note = "\n⚠️ COMPLIANCE: NÃO inclua pedido de voto, número eleitoral ou propaganda eleitoral. Foque em fatos do mandato."
    elif electoral_window == "pre_campaign":
        compliance_note = "\n⚠️ COMPLIANCE: NÃO inclua pedido de voto. Foque em realizações factuais."

    base_persona = f"""Você é um jornalista político especializado em coberturas regionais brasileiras.
Escreva para a versão online de um portal de notícias de {estado or 'Brasil'}.
O texto deve ser indexável pelo Google News: linguagem jornalística, fatos, dados, datas.
NÃO use linguagem de propaganda ou adjetivos excessivos.{compliance_note}

POLÍTICO: {entity_name}, {cargo}{party_str} — {loc}
{f'Informações do mandato: {mandato_info}' if mandato_info else ''}
{f'Contexto adicional: {detalhes}' if detalhes else ''}
"""

    prompts = {
        "mandato_realizacoes": base_persona + f"""
Escreva um artigo jornalístico de prestação de contas do mandato de {entity_name}.

ESTRUTURA OBRIGATÓRIA (retorne EXATAMENTE assim):
---TÍTULO---
[Título factual com nome, cargo e realização principal — máx 80 chars]
---LEAD---
[Parágrafo de abertura jornalístico com 5W1H — máx 60 palavras]
---CORPO---
[Corpo do artigo com 400-600 palavras. Incluir:
- Lista de realizações concretas (obras, projetos, investimentos com valores/datas quando possível)
- Impacto para a população local
- Declarações atribuídas ao político ou à assessoria
- Citação de fonte oficial (câmara, prefeitura, assembleia)
- Perspectivas futuras
Linguagem jornalística factual. NÃO use adjetivos políticos.]
---TAGS---
[5 tags SEO separadas por vírgula, incluindo nome do político, cargo e cidade]
""",

        "posicionamento_legislativo": base_persona + f"""
Escreva um artigo sobre o posicionamento legislativo de {entity_name}.

ESTRUTURA OBRIGATÓRIA:
---TÍTULO---
[Título sobre projeto de lei, votação ou posição pública — máx 80 chars]
---LEAD---
[Lead jornalístico sobre a iniciativa legislativa — máx 60 palavras]
---CORPO---
[400-600 palavras sobre:
- Projeto(s) de lei apresentado(s) ou votações relevantes
- Posição em temas importantes para o estado/município
- Impacto para os cidadãos
- Como o projeto tramita/tramitou
- Declaração do político sobre o tema
Linguagem técnica-jornalística. Citar número do projeto quando aplicável.]
---TAGS---
[5 tags SEO]
""",

        "perfil_eleitoral": base_persona + f"""
Escreva uma biografia política completa e indexável de {entity_name}.

ESTRUTURA OBRIGATÓRIA:
---TÍTULO---
["{entity_name}: Quem é o {cargo}?" ou similar — máx 80 chars]
---LEAD---
[Lead de apresentação do político — máx 60 palavras]
---CORPO---
[600-800 palavras cobrindo:
- Trajetória política (cronológica)
- Cargos exercidos anteriormente
- Principais realizações documentadas
- Posição política e valores declarados
- Atuação no {loc}
- Projetos em andamento
Texto neutro e informativo. Sem elogios políticos. Como Wikipedia.]
---TAGS---
[5 tags SEO incluindo nome completo, cargo, cidade/estado, partido]
""",

        "agenda_publica": base_persona + f"""
Escreva uma cobertura jornalística de evento/inauguração/atividade de {entity_name}.

ESTRUTURA OBRIGATÓRIA:
---TÍTULO---
[Título sobre a atividade pública — máx 80 chars]
---LEAD---
[Lead com o evento e seu impacto — máx 60 palavras]
---CORPO---
[300-500 palavras sobre:
- O evento ou inauguração (data, local, quem participou)
- O que foi inaugurado/anunciado/entregue
- Dados de investimento ou alcance
- Depoimento de beneficiário ou autoridade
- Próximos passos
Tom jornalístico, factual.]
---TAGS---
[5 tags SEO]
""",

        "contraposicao_narrativa": base_persona + f"""
Escreva um artigo de esclarecimento factual sobre {entity_name}.

CONTEXTO DA NARRATIVA NEGATIVA: {detalhes or 'Acusações genéricas sem comprovação'}

ESTRUTURA OBRIGATÓRIA:
---TÍTULO---
[Título factual que apresente a versão do político — ex: "{entity_name} esclarece acusações sobre X"]
---LEAD---
[Lead com posicionamento factual — máx 60 palavras]
---CORPO---
[400-600 palavras com:
- Contexto factual do assunto
- Posicionamento oficial do político/assessoria
- Documentos, decisões ou dados que embasem a posição
- Cronologia dos fatos
- Status atual da situação
Tom jornalístico. Não atacar adversários. Focar em fatos comprovados.]
---TAGS---
[5 tags SEO]
""",

        "release_conquista": base_persona + f"""
Escreva um press release sobre conquista/aprovação de {entity_name}.

ESTRUTURA OBRIGATÓRIA:
---TÍTULO---
[Título sobre a conquista — ex: "Câmara aprova projeto de {entity_name}..."]
---LEAD---
[Lead com a conquista e impacto — máx 60 palavras]
---CORPO---
[300-500 palavras sobre:
- A conquista (aprovação, investimento, reconhecimento, obra)
- O que isso significa para a população
- Citação do político
- Dados e números
- Próximos passos
Formato press release jornalístico.]
---TAGS---
[5 tags SEO]
""",
    }

    return prompts.get(content_type, prompts["agenda_publica"])


def _parse_political_content(raw: str, entity_name: str, content_type: str) -> dict:
    """Parseia o retorno estruturado do LLM."""
    import re

    def extract(tag: str) -> str:
        pattern = rf"---{tag}---\s*(.*?)(?=---|\Z)"
        m = re.search(pattern, raw, re.DOTALL | re.IGNORECASE)
        return m.group(1).strip() if m else ""

    title = extract("TÍTULO") or extract("TITULO") or f"Nota sobre {entity_name}"
    lead  = extract("LEAD") or ""
    body  = extract("CORPO") or raw.strip()
    tags_raw = extract("TAGS") or entity_name
    tags  = [t.strip() for t in tags_raw.split(",") if t.strip()]

    # Texto completo para publicação
    full_text = f"{title}\n\n{lead}\n\n{body}" if lead else f"{title}\n\n{body}"

    return {
        "title":     title,
        "lead":      lead,
        "body":      body,
        "full_text": full_text,
        "seo_tags":  tags,
    }


def save_political_content(
    entity_slug: str,
    content_type: str,
    content: dict,
) -> Path:
    """Salva conteúdo político gerado em disco."""
    import tempfile
    slug_dir = POLITICAL_CONTENT_DIR / entity_slug
    slug_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{content_type}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    out_path = slug_dir / filename

    text = json.dumps(content, indent=2, ensure_ascii=False)
    fd, tmp = tempfile.mkstemp(dir=slug_dir, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, out_path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise

    return out_path


def load_political_content(entity_slug: str, content_type: str) -> dict | None:
    """Carrega o conteúdo político mais recente de um tipo."""
    slug_dir = POLITICAL_CONTENT_DIR / entity_slug
    if not slug_dir.exists():
        return None

    files = sorted(slug_dir.glob(f"{content_type}_*.json"), reverse=True)
    if not files:
        return None

    try:
        return json.loads(files[0].read_text(encoding="utf-8"))
    except Exception:
        return None


def list_political_content(entity_slug: str) -> list[dict]:
    """Lista todos os conteúdos políticos gerados para um político."""
    slug_dir = POLITICAL_CONTENT_DIR / entity_slug
    if not slug_dir.exists():
        return []

    results = []
    for f in sorted(slug_dir.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            results.append({
                "filename":     f.name,
                "content_type": data.get("content_type"),
                "type_label":   data.get("type_label"),
                "title":        data.get("title"),
                "word_count":   data.get("word_count", 0),
                "generated_at": data.get("generated_at"),
                "compliance":   data.get("compliance", {}).get("compliant", True),
            })
        except Exception:
            continue

    return results
