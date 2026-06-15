"""
Political Engine — Motor Central do Módulo Político-Eleitoral.

Gerencia entidades políticas, calendário eleitoral brasileiro,
janelas de compliance com a Lei 9504/97, e geração de queries
otimizadas para SERP político.

Eleições brasileiras 2026:
  1º turno: 4 de outubro de 2026
  2º turno: 25 de outubro de 2026
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal

# ── Storage ──────────────────────────────────────────────────────────────────
if os.environ.get("VERCEL"):
    POLITICAL_DIR = Path("/tmp/political")
else:
    POLITICAL_DIR = Path(__file__).parent.parent / "political"

POLITICAL_DIR.mkdir(parents=True, exist_ok=True)
POLITICIANS_INDEX = POLITICAL_DIR / "politicians.json"

# ── Calendário Eleitoral Brasileiro 2026 ─────────────────────────────────────
ELECTION_DATE_2026 = date(2026, 10, 4)
RUNOFF_DATE_2026   = date(2026, 10, 25)

ELECTORAL_WINDOWS: dict[str, dict] = {
    "construction": {
        "label":      "Construção de Imagem",
        "start":      date(2025, 1, 1),
        "end":        date(2026, 3, 31),
        "color":      "green",
        "allowed":    ["todos os tipos de conteúdo", "press releases", "artigos de opinião",
                       "conteúdo de mandato", "publicidade institucional"],
        "prohibited": [],
        "note":       "Fase mais livre. Máxima produção de conteúdo positivo.",
        "urgency":    "LOW",
    },
    "pre_campaign": {
        "label":      "Pré-Campanha",
        "start":      date(2026, 4, 1),
        "end":        date(2026, 5, 31),
        "color":      "yellow",
        "allowed":    ["conteúdo de mandato", "agenda pública", "prestação de contas",
                       "artigos editoriais (sem pedido de voto)"],
        "prohibited": ["pedido explícito de voto", "menção a adversários"],
        "note":       "Evitar pedido explícito de voto. Focar em realizações do mandato.",
        "urgency":    "MEDIUM",
    },
    "official_campaign": {
        "label":      "Campanha Oficial",
        "start":      date(2026, 6, 1),
        "end":        date(2026, 10, 1),
        "color":      "orange",
        "allowed":    ["propaganda eleitoral declarada com CNPJ registrado no TSE",
                       "horário eleitoral gratuito"],
        "prohibited": ["propaganda paga em veículos de comunicação", "outdoor",
                       "carro de som sem autorização", "fake news"],
        "note":       "Lei Eleitoral em vigor. Toda propaganda deve ser registrada no TSE.",
        "urgency":    "HIGH",
    },
    "silence": {
        "label":      "Silêncio Eleitoral",
        "start":      date(2026, 10, 2),
        "end":        date(2026, 10, 4),
        "color":      "red",
        "allowed":    ["manutenção de conteúdo já indexado"],
        "prohibited": ["qualquer nova propaganda eleitoral", "comícios", "carros de som",
                       "publicação em redes sociais com cunho eleitoral"],
        "note":       "PROIBIDO publicar nova propaganda. Manter apenas o que já está indexado.",
        "urgency":    "CRITICAL",
    },
    "runoff": {
        "label":      "2º Turno",
        "start":      date(2026, 10, 5),
        "end":        date(2026, 10, 25),
        "color":      "orange",
        "allowed":    ["propaganda eleitoral registrada no TSE"],
        "prohibited": ["propaganda não registrada"],
        "note":       "Mesmas regras da campanha oficial.",
        "urgency":    "HIGH",
    },
}

# ── Cargos Políticos Brasileiros ──────────────────────────────────────────────
POLITICAL_ROLES = [
    "Presidente da República",
    "Vice-Presidente da República",
    "Senador",
    "Deputado Federal",
    "Governador",
    "Vice-Governador",
    "Deputado Estadual",
    "Deputado Distrital",
    "Prefeito",
    "Vice-Prefeito",
    "Vereador",
]

# ── Partidos Brasileiros (ativos 2025) ─────────────────────────────────────
PARTIES = [
    "PT", "PL", "UNIÃO", "MDB", "REPUBLICANOS", "PP",
    "PSD", "PDT", "PSDB", "PSOL", "AVANTE", "PODE",
    "SOLIDARIEDADE", "PRD", "AGIR", "CIDADANIA", "PSB",
    "PCdoB", "DC", "REDE", "PMB", "UP", "PRTB",
]

# ── Estados Brasileiros ────────────────────────────────────────────────────
STATES = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
    "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
    "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
]


@dataclass
class PoliticalEntity:
    """Representa um político monitorado no sistema."""
    name:          str
    slug:          str
    role:          str                # Cargo atual
    party:         str                # Partido
    state:         str                # UF
    city:          str                # Município (para prefeitos/vereadores)
    target_role:   str                # Cargo disputado na próxima eleição
    election_year: int = 2026
    opponent:      str = ""           # Nome do principal adversário
    keywords:      list[str] = field(default_factory=list)   # Keywords políticas específicas
    created_at:    str = ""
    updated_at:    str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.slug:
            self.slug = _make_slug(self.name)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "PoliticalEntity":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def _make_slug(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s]", "", slug)
    slug = re.sub(r"\s+", "_", slug)
    return slug


# ── CRUD de Políticos ─────────────────────────────────────────────────────────

def _load_index() -> dict:
    if not POLITICIANS_INDEX.exists():
        return {}
    try:
        return json.loads(POLITICIANS_INDEX.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_index(index: dict) -> None:
    POLITICAL_DIR.mkdir(parents=True, exist_ok=True)
    text = json.dumps(index, indent=2, ensure_ascii=False)
    fd, tmp = tempfile.mkstemp(dir=POLITICAL_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, POLITICIANS_INDEX)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def register_politician(entity: PoliticalEntity) -> PoliticalEntity:
    """Cadastra ou atualiza um político no índice."""
    index = _load_index()
    entity.updated_at = datetime.now(timezone.utc).isoformat()
    index[entity.slug] = entity.to_dict()
    _save_index(index)
    return entity


def get_politician(slug: str) -> PoliticalEntity | None:
    """Recupera um político pelo slug."""
    index = _load_index()
    data = index.get(slug)
    if not data:
        return None
    return PoliticalEntity.from_dict(data)


def list_politicians() -> list[PoliticalEntity]:
    """Lista todos os políticos cadastrados."""
    index = _load_index()
    return [PoliticalEntity.from_dict(v) for v in index.values()]


def delete_politician(slug: str) -> bool:
    """Remove um político do índice."""
    index = _load_index()
    if slug not in index:
        return False
    del index[slug]
    _save_index(index)
    return True


# ── Calendário Eleitoral ──────────────────────────────────────────────────────

def get_electoral_window(target_date: date | None = None) -> dict:
    """
    Retorna a janela eleitoral atual (ou para uma data específica).
    Inclui todas as informações de compliance.
    """
    check = target_date or date.today()
    for window_key, window in ELECTORAL_WINDOWS.items():
        if window["start"] <= check <= window["end"]:
            days_remaining = (window["end"] - check).days
            return {
                "window":         window_key,
                "label":          window["label"],
                "color":          window["color"],
                "days_remaining": days_remaining,
                "urgency":        window["urgency"],
                "allowed":        window["allowed"],
                "prohibited":     window["prohibited"],
                "note":           window["note"],
                "election_countdown": (ELECTION_DATE_2026 - check).days,
            }

    # Pós-eleição
    if check > RUNOFF_DATE_2026:
        return {
            "window":         "post_election",
            "label":          "Pós-Eleição",
            "color":          "gray",
            "days_remaining": 0,
            "urgency":        "LOW",
            "allowed":        ["todos os tipos de conteúdo"],
            "prohibited":     [],
            "note":           "Eleição encerrada. Ciclo de construção reinicia.",
            "election_countdown": 0,
        }

    # Antes do calendário definido
    return {
        "window":         "pre_electoral",
        "label":          "Pré-Eleitoral",
        "color":          "green",
        "days_remaining": (ELECTORAL_WINDOWS["construction"]["start"] - check).days,
        "urgency":        "LOW",
        "allowed":        ["todos os tipos de conteúdo"],
        "prohibited":     [],
        "note":           "Fase livre. Iniciar construção de presença digital.",
        "election_countdown": (ELECTION_DATE_2026 - check).days,
    }


def electoral_calendar(entity: PoliticalEntity) -> dict:
    """Gera o calendário completo de ações para o político."""
    today = date.today()
    current_window = get_electoral_window(today)
    days_to_election = (ELECTION_DATE_2026 - today).days

    milestones = []
    for key, w in ELECTORAL_WINDOWS.items():
        days_away = (w["start"] - today).days
        status = "past" if w["end"] < today else "current" if w["start"] <= today <= w["end"] else "future"
        milestones.append({
            "window":    key,
            "label":     w["label"],
            "start":     w["start"].isoformat(),
            "end":       w["end"].isoformat(),
            "days_away": max(0, days_away),
            "status":    status,
            "urgency":   w["urgency"],
            "color":     w["color"],
        })

    return {
        "entity_name":      entity.name,
        "entity_slug":      entity.slug,
        "election_date":    ELECTION_DATE_2026.isoformat(),
        "runoff_date":      RUNOFF_DATE_2026.isoformat(),
        "days_to_election": max(0, days_to_election),
        "current_window":   current_window,
        "milestones":       milestones,
        "recommended_actions": _recommended_actions(current_window["window"], entity),
    }


def _recommended_actions(window: str, entity: PoliticalEntity) -> list[str]:
    """Recomendações de ação por janela eleitoral."""
    base = [
        f"Auditar SERP para '{entity.name}' (primeiras 10 páginas)",
        "Verificar o que o Google AI Overview diz sobre o político",
    ]
    if window == "construction":
        return base + [
            "Publicar prestação de contas do mandato (2+ vezes/semana)",
            "Criar/atualizar Wikipedia do político",
            "Publicar artigos de posicionamento em portais regionais",
            "Construir presença YouTube (inaugurações, eventos)",
            "Registrar Crunchbase/LinkedIn com histórico completo",
        ]
    elif window == "pre_campaign":
        return base + [
            "Intensificar publicação de realizações do mandato",
            "Distribuir releases em portais de notícia regionais",
            "Publicar agenda pública (sem pedido de voto)",
            "Criar perfil em portais municipais",
        ]
    elif window == "official_campaign":
        return base + [
            "ATENÇÃO: Registrar toda propaganda eleitoral no TSE",
            "Monitorar SERP diariamente",
            "Responder ataques negativos com conteúdo factual",
        ]
    elif window == "silence":
        return ["NÃO publicar nova propaganda eleitoral", "Apenas manutenção do que já está indexado"]
    else:
        return base


# ── Geração de Queries de Busca ───────────────────────────────────────────────

def political_queries(entity: PoliticalEntity) -> list[str]:
    """
    Gera as queries de busca mais estratégicas para auditar o político.
    Inclui variações de cargo + município + nome.
    """
    name = entity.name
    tokens = name.split()
    short = f"{tokens[0]} {tokens[-1]}" if len(tokens) >= 2 else name

    queries = [name]  # Query principal

    # Por cargo
    if entity.role:
        queries.append(f"{name} {entity.role}")
        queries.append(f"{short} {entity.role}")

    # Por município/estado
    if entity.city:
        queries.append(f"{name} {entity.city}")
        queries.append(f"{short} {entity.city}")
    if entity.state:
        queries.append(f"{name} {entity.state}")

    # Por partido
    if entity.party:
        queries.append(f"{name} {entity.party}")

    # Keywords personalizadas
    for kw in entity.keywords[:3]:
        queries.append(f"{name} {kw}")

    # Query de candidatura
    if entity.target_role:
        queries.append(f"{name} candidato {entity.target_role}")

    # Deduplicar e limitar
    seen = set()
    unique = []
    for q in queries:
        if q.lower() not in seen:
            seen.add(q.lower())
            unique.append(q)

    return unique[:8]


# ── Compliance Check ──────────────────────────────────────────────────────────

def compliance_check(content: str, window_key: str) -> dict:
    """
    Verifica se o conteúdo está conforme a Lei Eleitoral para a janela atual.

    Retorna: {"compliant": bool, "issues": list[str], "warning": str}
    """
    window = ELECTORAL_WINDOWS.get(window_key, {})
    prohibited = window.get("prohibited", [])
    content_lower = content.lower()

    issues = []
    warnings = []

    # Verificações específicas por janela
    if window_key in ("official_campaign", "silence"):
        VOTE_KW = ["vote em", "vote no", "vote na", "vote para", "vote pelo",
                   "meu voto", "nosso candidato", "#vota", "voto em"]
        for kw in VOTE_KW:
            if kw in content_lower:
                issues.append(f"Pedido implícito de voto detectado: '{kw}' — proibido sem registro no TSE")

    if window_key == "silence":
        warnings.append("SILÊNCIO ELEITORAL: Nenhum conteúdo eleitoral novo deve ser publicado")
        issues.append("Janela de silêncio eleitoral ativa — publicação proibida")

    ATTACK_KW = ["adversário corrupto", "bandido", "ladrão", "mentiroso",
                 "fake news sobre", "desonesto", "incompetente"]
    for kw in ATTACK_KW:
        if kw in content_lower:
            warnings.append(f"Possível ataque a adversário: '{kw}' — risco de ação por danos morais")

    return {
        "compliant": len(issues) == 0,
        "issues":    issues,
        "warnings":  warnings,
        "window":    window.get("label", window_key),
        "note":      window.get("note", ""),
    }
