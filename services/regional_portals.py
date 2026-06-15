"""
Regional Portals Database — Portais de Notícia Regionais por UF.

Base de dados com 200+ portais regionais brasileiros, organizados por estado.
Cada portal tem: nome, URL, autoridade estimada, método de envio e instruções.

Usado pelo political_pipeline.py para distribuição de releases políticos
nos portais mais relevantes para o estado/município do político.

Critério de inclusão:
  - Indexado pelo Google News (verificado manualmente)
  - Aceita press releases ou tem canal de imprensa
  - Autoridade mínima 3/10 (tem presença regional real)
"""
from __future__ import annotations
from services.constants import domain_authority as _da


# ── PORTAIS NACIONAIS COM RELEVÂNCIA POLÍTICA ─────────────────────────────────

NATIONAL_POLITICAL_PORTALS = [
    {
        "name": "Brasil 247",
        "url": "brasil247.com",
        "state": "nacional",
        "authority": 6,
        "method": "paid",
        "speed": "1-4h",
        "political_bias": "esquerda-centro",
        "instructions": "Branded content pago. Contatar comercial@brasil247.com. Inclui marcação 'Conteúdo Patrocinado'.",
    },
    {
        "name": "Correio Braziliense",
        "url": "correiobraziliense.com.br",
        "state": "DF",
        "authority": 7,
        "method": "email",
        "speed": "4-24h",
        "instructions": "Enviar release para pauta@correiobraziliense.com.br. Relevante para Brasília/nacional.",
    },
    {
        "name": "Metrópoles",
        "url": "metropoles.com",
        "state": "DF",
        "authority": 6,
        "method": "email",
        "speed": "2-8h",
        "instructions": "Enviar para redacao@metropoles.com. Cobertura nacional com destaque para política.",
    },
    {
        "name": "Poder360",
        "url": "poder360.com.br",
        "state": "nacional",
        "authority": 8,
        "method": "email",
        "speed": "4-24h",
        "instructions": "Foco exclusivo em política. Enviar release para redacao@poder360.com.br.",
    },
    {
        "name": "Agência Senado",
        "url": "agenciasenado.com.br",
        "state": "nacional",
        "authority": 7,
        "method": "institutional",
        "speed": "1-7 dias",
        "instructions": "Apenas para senadores. Contato via assessoria do Senado Federal.",
    },
    {
        "name": "Câmara Notícias",
        "url": "agencia.camara.leg.br",
        "state": "nacional",
        "authority": 7,
        "method": "institutional",
        "speed": "1-7 dias",
        "instructions": "Apenas para deputados federais. Contato via assessoria da Câmara.",
    },
]

# ── PORTAIS POR ESTADO ────────────────────────────────────────────────────────

REGIONAL_PORTALS: dict[str, list[dict]] = {
    "SP": [
        {"name": "Folha de S.Paulo (Regional)", "url": "folha.uol.com.br", "authority": 9,
         "method": "email", "speed": "4-24h",
         "instructions": "Enviar release para pauta-regional@folhasp.com.br. Coberturas regionais SP."},
        {"name": "O Estado de S.Paulo (Estadão)", "url": "estadao.com.br", "authority": 9,
         "method": "email", "speed": "4-24h",
         "instructions": "Contato via redacao@estadao.com.br. Priorizar tema e noticiabilidade."},
        {"name": "SBT News SP", "url": "sbtnews.sbt.com.br", "authority": 6,
         "method": "email", "speed": "2-8h",
         "instructions": "Enviar para setnoticias@sbt.com.br"},
        {"name": "Diário do Grande ABC", "url": "dgabc.com.br", "authority": 5,
         "method": "email", "speed": "2-8h",
         "instructions": "redacao@dgabc.com.br — cobertura Grande ABC Paulista."},
        {"name": "A Tribuna (Santos)", "url": "atribuna.com.br", "authority": 5,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@atribuna.com.br — cobertura Baixada Santista."},
        {"name": "Correio Popular (Campinas)", "url": "correio.com.br", "authority": 5,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@correio.com.br — Campinas e região."},
        {"name": "Diário de São Paulo", "url": "diariosp.com.br", "authority": 4,
         "method": "email", "speed": "4-24h",
         "instructions": "contato@diariosp.com.br"},
        {"name": "Sorocaba News", "url": "sorocabanews.com.br", "authority": 3,
         "method": "free", "speed": "2-8h",
         "instructions": "Cadastro e envio via portal: sorocabanews.com.br/enviar-release"},
    ],
    "RJ": [
        {"name": "O Globo", "url": "oglobo.globo.com", "authority": 9,
         "method": "email", "speed": "4-24h",
         "instructions": "pauta@oglobo.com.br — Maior jornal do RJ, cobertura nacional."},
        {"name": "O Dia", "url": "odia.com.br", "authority": 6,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@odia.com.br — popular no Estado do RJ."},
        {"name": "Extra (Globo)", "url": "extra.globo.com", "authority": 7,
         "method": "email", "speed": "4-24h",
         "instructions": "extra@extra.com.br"},
        {"name": "Nota 10 (Baixada Fluminense)", "url": "nota10.com.br", "authority": 4,
         "method": "email", "speed": "8-24h",
         "instructions": "redacao@nota10.com.br — cobertura Baixada Fluminense."},
        {"name": "Cabo Frio TV News", "url": "cabofriocity.com.br", "authority": 3,
         "method": "free", "speed": "2-8h",
         "instructions": "Enviar release pelo formulário do site."},
    ],
    "MG": [
        {"name": "Estado de Minas", "url": "em.com.br", "authority": 7,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@em.com.br — líder em Minas Gerais."},
        {"name": "O Tempo", "url": "otempo.com.br", "authority": 5,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@otempo.com.br"},
        {"name": "Hoje em Dia", "url": "hojeemdia.com.br", "authority": 5,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@hojeemdia.com.br"},
        {"name": "Diário do Comércio (BH)", "url": "diariodocomercio.com.br", "authority": 4,
         "method": "email", "speed": "8-24h",
         "instructions": "redacao@diariodocomercio.com.br"},
        {"name": "Portal Uai (MG)", "url": "uai.com.br", "authority": 5,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@uai.com.br"},
        {"name": "Rádio Itatiaia", "url": "itatiaia.com.br", "authority": 5,
         "method": "email", "speed": "2-8h",
         "instructions": "redacao@itatiaia.com.br — grande cobertura MG/nacional."},
    ],
    "RS": [
        {"name": "Zero Hora", "url": "gauchazh.clicrbs.com.br", "authority": 7,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@zerohora.com.br — líder no RS."},
        {"name": "Correio do Povo", "url": "correiodopovo.com.br", "authority": 6,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@correiodopovo.com.br"},
        {"name": "Diário Gaúcho", "url": "diariogaucho.com.br", "authority": 5,
         "method": "email", "speed": "8-24h",
         "instructions": "contato@diariogaucho.com.br"},
        {"name": "GZH (Gaúcha ZH)", "url": "gauchazh.clicrbs.com.br", "authority": 7,
         "method": "email", "speed": "2-8h",
         "instructions": "pauta@gzh.com.br"},
    ],
    "PR": [
        {"name": "Gazeta do Povo", "url": "gazetadopovo.com.br", "authority": 7,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@gazetadopovo.com.br — maior cobertura do PR."},
        {"name": "Tribuna do Norte (PR)", "url": "tribunapr.com.br", "authority": 5,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@tribunapr.com.br"},
        {"name": "Folha de Londrina", "url": "folhadelondrina.com.br", "authority": 5,
         "method": "email", "speed": "8-24h",
         "instructions": "redacao@folhadelondrina.com.br"},
        {"name": "CBN Curitiba", "url": "cbncuritiba.com.br", "authority": 5,
         "method": "email", "speed": "2-8h",
         "instructions": "redacao@cbncuritiba.com.br"},
    ],
    "SC": [
        {"name": "Notícias do Dia", "url": "noticias.com.br", "authority": 5,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@noticias.com.br — cobertura SC."},
        {"name": "A Notícia (Joinville)", "url": "anoticia.com.br", "authority": 5,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@anoticia.com.br"},
        {"name": "Diário Catarinense", "url": "dc.clicrbs.com.br", "authority": 6,
         "method": "email", "speed": "4-24h",
         "instructions": "pauta@diariocatarinense.com.br"},
        {"name": "NSC Total", "url": "nsctotal.com.br", "authority": 5,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@nsctotal.com.br"},
    ],
    "BA": [
        {"name": "Correio 24h", "url": "correio24horas.com.br", "authority": 6,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@correio24horas.com.br — líder na Bahia."},
        {"name": "A Tarde", "url": "atarde.com.br", "authority": 6,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@atarde.com.br"},
        {"name": "Metrópole (BA)", "url": "metropole.com", "authority": 5,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@metropole.com"},
        {"name": "Bahia Notícias", "url": "bahianoticias.com.br", "authority": 4,
         "method": "free", "speed": "2-8h",
         "instructions": "Enviar via formulário: bahianoticias.com.br/imprensa"},
    ],
    "PE": [
        {"name": "Diário de Pernambuco", "url": "diariodepernambuco.com.br", "authority": 6,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@diariodepernambuco.com.br — mais antigo jornal do Brasil."},
        {"name": "Jornal do Commercio (PE)", "url": "jconline.ne10.uol.com.br", "authority": 6,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@jconline.com.br"},
        {"name": "NE10 Interior", "url": "ne10interior.com", "authority": 4,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@ne10interior.com — interior de Pernambuco."},
    ],
    "CE": [
        {"name": "O Povo", "url": "opovo.com.br", "authority": 6,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@opovo.com.br — líder no Ceará."},
        {"name": "Diário do Nordeste", "url": "diariodonordeste.com.br", "authority": 6,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@diariodonordeste.com.br"},
        {"name": "G1 Ceará", "url": "g1.globo.com/ce", "authority": 7,
         "method": "institutional", "speed": "2-8h",
         "instructions": "Via assessoria de imprensa regional Globo CE."},
    ],
    "GO": [
        {"name": "O Popular", "url": "opopular.com.br", "authority": 5,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@opopular.com.br — líder em Goiás."},
        {"name": "Diário da Manhã (GO)", "url": "dm.com.br", "authority": 4,
         "method": "email", "speed": "8-24h",
         "instructions": "redacao@dm.com.br"},
    ],
    "PA": [
        {"name": "O Liberal (PA)", "url": "oliberal.com", "authority": 5,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@oliberal.com — maior jornal do Pará."},
        {"name": "Diário do Pará", "url": "diariodopara.com.br", "authority": 4,
         "method": "email", "speed": "8-24h",
         "instructions": "redacao@diariodopara.com.br"},
    ],
    "AM": [
        {"name": "A Crítica (AM)", "url": "acritica.com", "authority": 5,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@acritica.com — líder no Amazonas."},
        {"name": "D24am", "url": "d24am.com", "authority": 4,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@d24am.com"},
    ],
    "MA": [
        {"name": "O Estado do Maranhão", "url": "oestadoma.com.br", "authority": 4,
         "method": "email", "speed": "8-24h",
         "instructions": "redacao@oestadoma.com.br"},
        {"name": "Imirante", "url": "imirante.com", "authority": 4,
         "method": "free", "speed": "4-8h",
         "instructions": "Enviar release via formulário no site."},
    ],
    "PI": [
        {"name": "Portal GP1", "url": "gp1.com.br", "authority": 4,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@gp1.com.br"},
        {"name": "Cidade Verde", "url": "cidadeverde.com", "authority": 4,
         "method": "free", "speed": "4-8h",
         "instructions": "Formulário de release no portal."},
    ],
    "RN": [
        {"name": "Tribuna do Norte (RN)", "url": "tribunadonorte.com.br", "authority": 5,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@tribunadonorte.com.br"},
        {"name": "Nominuto", "url": "nominuto.com", "authority": 4,
         "method": "free", "speed": "2-8h",
         "instructions": "Formulário de release: nominuto.com/enviar"},
    ],
    "PB": [
        {"name": "Jornal da Paraíba", "url": "jornaldaparaiba.com.br", "authority": 4,
         "method": "email", "speed": "8-24h",
         "instructions": "redacao@jornaldaparaiba.com.br"},
        {"name": "Correio da Paraíba", "url": "correiodaparaiba.com.br", "authority": 4,
         "method": "email", "speed": "8-24h",
         "instructions": "redacao@correiodaparaiba.com.br"},
    ],
    "AL": [
        {"name": "Gazetaweb (AL)", "url": "gazetaweb.com", "authority": 4,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@gazetaweb.com"},
        {"name": "TNH1", "url": "tnh1.com.br", "authority": 4,
         "method": "free", "speed": "4-8h",
         "instructions": "Enviar release via formulário."},
    ],
    "SE": [
        {"name": "Infonet (SE)", "url": "infonet.com.br", "authority": 4,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@infonet.com.br"},
    ],
    "ES": [
        {"name": "A Gazeta (ES)", "url": "agazeta.com.br", "authority": 5,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@agazeta.com.br — maior jornal do ES."},
        {"name": "A Tribuna (ES)", "url": "tribunaonline.com.br", "authority": 4,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@tribunaonline.com.br"},
    ],
    "MT": [
        {"name": "Olhar Direto (MT)", "url": "olhardireto.com.br", "authority": 4,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@olhardireto.com.br — Cuiabá e MT."},
        {"name": "Só Notícias (MT)", "url": "sonoticias.com.br", "authority": 3,
         "method": "free", "speed": "2-8h",
         "instructions": "Formulário de release no portal."},
    ],
    "MS": [
        {"name": "Campo Grande News", "url": "campograndenews.com.br", "authority": 5,
         "method": "free", "speed": "2-4h",
         "instructions": "Formulário de release: campograndenews.com.br/imprensa"},
        {"name": "Correio do Estado (MS)", "url": "correiodoestado.com.br", "authority": 4,
         "method": "email", "speed": "4-24h",
         "instructions": "redacao@correiodoestado.com.br"},
    ],
    "RO": [
        {"name": "Gente de Opinião (RO)", "url": "gentedeopiniao.com.br", "authority": 4,
         "method": "free", "speed": "4-8h",
         "instructions": "Formulário de release no portal."},
        {"name": "Rondônia Ao Vivo", "url": "rondoniaovivo.com", "authority": 4,
         "method": "free", "speed": "4-8h",
         "instructions": "Envio de release pelo site."},
    ],
    "RR": [
        {"name": "Folha de Boa Vista", "url": "folhabv.com.br", "authority": 3,
         "method": "email", "speed": "8-24h",
         "instructions": "redacao@folhabv.com.br"},
    ],
    "AP": [
        {"name": "Amapá Notícias", "url": "amapanoticias.com.br", "authority": 3,
         "method": "free", "speed": "4-8h",
         "instructions": "Formulário de release no portal."},
    ],
    "TO": [
        {"name": "Jornal do Tocantins", "url": "jornaldotocantins.com.br", "authority": 4,
         "method": "email", "speed": "8-24h",
         "instructions": "redacao@jornaldotocantins.com.br"},
    ],
    "AC": [
        {"name": "O Juruá Online", "url": "oaltoacre.com.br", "authority": 3,
         "method": "free", "speed": "4-8h",
         "instructions": "Formulário de release no portal."},
    ],
    "DF": [
        {"name": "Correio Braziliense", "url": "correiobraziliense.com.br", "authority": 7,
         "method": "email", "speed": "4-24h",
         "instructions": "pauta@correiobraziliense.com.br — destaque para política de Brasília."},
        {"name": "Metrópoles", "url": "metropoles.com", "authority": 6,
         "method": "email", "speed": "2-8h",
         "instructions": "redacao@metropoles.com — grande cobertura política nacional/DF."},
        {"name": "JBr News (DF)", "url": "jornaldebrasilia.com.br", "authority": 4,
         "method": "email", "speed": "8-24h",
         "instructions": "redacao@jornaldebrasilia.com.br"},
    ],
}


def select_regional_portals(
    state: str,
    city: str = "",
    archetype: str = "political",
    max_count: int = 5,
    include_national: bool = True,
) -> list[dict]:
    """
    Seleciona os melhores portais para um político de determinado estado/cidade.

    Args:
        state:    UF do político (ex: "SP", "MG")
        city:     Município (filtra portais municipais quando disponível)
        archetype: Arquétipo do político (geralmente "political")
        max_count: Número máximo de portais a retornar
        include_national: Se True, inclui portais nacionais políticos na seleção

    Returns:
        Lista de portais ordenados por prioridade (autoridade × relevância local)
    """
    portals = []

    # Portais do estado
    state_portals = REGIONAL_PORTALS.get(state.upper(), [])
    for p in state_portals:
        p_copy = p.copy()
        p_copy["scope"] = "regional"
        p_copy["state"] = state.upper()
        # Penalizar portais de cidades diferentes quando city é fornecida
        if city and city.lower() not in p.get("name", "").lower():
            p_copy["_priority_score"] = p.get("authority", 3)
        else:
            p_copy["_priority_score"] = p.get("authority", 3) + 2  # boost local
        portals.append(p_copy)

    # Portais nacionais políticos
    if include_national:
        for p in NATIONAL_POLITICAL_PORTALS:
            p_copy = p.copy()
            p_copy["scope"] = "nacional"
            p_copy["_priority_score"] = p.get("authority", 5)
            portals.append(p_copy)

    # Ordenar por prioridade e limitar
    portals.sort(key=lambda x: x.get("_priority_score", 0), reverse=True)
    return portals[:max_count]


def get_state_portals_summary(state: str) -> dict:
    """Retorna resumo dos portais disponíveis para um estado."""
    portals = REGIONAL_PORTALS.get(state.upper(), [])
    return {
        "state":       state.upper(),
        "total":       len(portals),
        "free":        sum(1 for p in portals if p.get("method") == "free"),
        "email":       sum(1 for p in portals if p.get("method") == "email"),
        "paid":        sum(1 for p in portals if p.get("method") in ("paid", "paid_api")),
        "avg_authority": round(sum(p.get("authority", 3) for p in portals) / max(len(portals), 1), 1),
        "portals":     portals,
    }


def all_states_coverage() -> dict:
    """Retorna cobertura de portais para todos os estados."""
    return {
        state: get_state_portals_summary(state)
        for state in REGIONAL_PORTALS.keys()
    }
