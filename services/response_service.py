"""
Response Strategy Generation Layer — Archetype-Driven.

Decisões estratégicas são resolvidas deterministicamente em Python.
O archetype (criminal/reputacional/politico/media/administrativo/associativo)
é o eixo primário. Threat level é o eixo secundário.
O LLM apenas redige o texto a partir de parâmetros já decididos.
"""
from pathlib import Path
from services.openrouter_service import call_openrouter
import re

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# ── Archetype Playbooks ─────────────────────────────────────────────────────────
# Cada archetype tem sua própria lógica de: postura, visibilidade, temperatura,
# stakeholders, asset sequence, gatilhos e redirecionamento narrativo.

ARCHETYPE_PLAYBOOKS: dict[str, dict] = {

    # ── CRIMINAL ─────────────────────────────────────────────────────
    # Prioridade: jurídico → esclarecimento → contenção → estabilização → autoridade
    # Regra de ouro: baixíssima visibilidade, falar APENAS via jurídico.
    "criminal": {
        "label": "Criminal / Investigação",
        "principio": "Conter vazamento narrativo. Toda comunicação passa pelo jurídico. Zero reatividade.",
        "posture": {
            ("CRITICAL", "legal",  True):  "contencao-juridica-absoluta",
            ("CRITICAL", "legal",  False): "esclarecimento-juridico-controlado",
            ("CRITICAL", "mainstream", True):  "contencao-juridica-absoluta",
            ("CRITICAL", "mainstream", False): "baixa-visibilidade-estabilizacao",
            ("CRITICAL", "blog",   True):  "contencao-juridica-absoluta",
            ("CRITICAL", "blog",   False): "deslocamento-narrativo-tecnico",
            ("CRITICAL", "social", True):  "contencao-juridica-absoluta",
            ("CRITICAL", "social", False): "reforco-canal-proprio-juridico",
            ("HIGH",     "legal",  True):  "tecnico-juridico",
            ("HIGH",     "legal",  False): "tecnico-juridico",
            ("HIGH",     "mainstream", True):  "institucional-defensivo",
            ("HIGH",     "mainstream", False): "construcao-autoridade-cautelosa",
            ("HIGH",     "blog",   True):  "institucional-defensivo",
            ("HIGH",     "blog",   False): "deslocamento-narrativo",
            ("HIGH",     "social", True):  "baixa-visibilidade-estabilizacao",
            ("HIGH",     "social", False): "reforco-canal-proprio",
            ("MEDIUM",   "legal",  True):  "tecnico-juridico",
            ("MEDIUM",   "legal",  False): "baixa-visibilidade-estabilizacao",
            ("MEDIUM",   "mainstream", True):  "institucional-defensivo",
            ("MEDIUM",   "mainstream", False): "construcao-autoridade",
            ("MEDIUM",   "blog",   True):  "deslocamento-narrativo",
            ("MEDIUM",   "blog",   False): "deslocamento-narrativo",
            ("MEDIUM",   "social", True):  "reforco-canal-proprio",
            ("MEDIUM",   "social", False): "reforco-canal-proprio",
            ("LOW",      "legal",  True):  "tecnico-juridico",
            ("LOW",      "legal",  False): "consolidacao-autoridade",
            ("LOW",      "mainstream", True):  "construcao-autoridade",
            ("LOW",      "mainstream", False): "consolidacao-autoridade",
            ("LOW",      "blog",   True):  "consolidacao-autoridade",
            ("LOW",      "blog",   False): "consolidacao-autoridade",
            ("LOW",      "social", True):  "reforco-canal-proprio",
            ("LOW",      "social", False): "consolidacao-autoridade",
        },
        "visibility": {
            ("CRITICAL", True):  "BAIXISSIMA",
            ("CRITICAL", False): "BAIXA",
            ("HIGH",     True):  "BAIXA",
            ("HIGH",     False): "MODERADA",
            ("MEDIUM",   True):  "MODERADA",
            ("MEDIUM",   False): "MODERADA",
            ("LOW",      True):  "MODERADA",
            ("LOW",      False): "ALTA",
        },
        "temperature": {
            "CRITICAL": "FRIA", "HIGH": "FRIA", "MEDIUM": "MODERADA", "LOW": "AGRESSIVA",
        },
        "stakeholders": {
            ("CRITICAL", True):  ["Jurídico Criminal", "Advogados Externos", "Sócios", "Assessoria Jurídica", "Imprensa (via jurídico)"],
            ("CRITICAL", False): ["Jurídico", "Sócios", "Advogados Externos", "Assessoria de Imprensa", "Público Geral"],
            ("HIGH",     True):  ["Jurídico Criminal", "Advogados Externos", "Sócios", "Imprensa", "Público Geral"],
            ("HIGH",     False): ["Jurídico", "Sócios", "Assessoria de Imprensa", "Parceiros", "Público Geral"],
            ("MEDIUM",   True):  ["Jurídico", "Sócios", "Parceiros", "Imprensa", "Público Geral"],
            ("MEDIUM",   False): ["Sócios", "Jurídico", "Imprensa", "Parceiros", "Público Geral"],
            ("LOW",      True):  ["Jurídico", "Sócios", "Público Geral", "Imprensa", "Parceiros"],
            ("LOW",      False): ["Sócios", "Imprensa", "Público Geral", "Parceiros", "Jurídico"],
        },
        "assets": {
            "CRITICAL": [
                {"ativo": "Manifestação Jurídica Oficial",        "janela": "Dia 1",    "objetivo": "Estabelecer versão jurídica antes da versão jornalística"},
                {"ativo": "Nota de Esclarecimento Jurídico",      "janela": "Dia 1-2",  "objetivo": "Documento formal com posição oficial restrita ao jurídico"},
                {"ativo": "FAQ de Transparência",                 "janela": "Dia 2-4",  "objetivo": "Antecipar perguntas da imprensa e público em canal controlado"},
                {"ativo": "Perfil Institucional Enxuto",          "janela": "Dia 3-5",  "objetivo": "Ocupar #1 da busca com biografia controlada e sem menção ao caso"},
                {"ativo": "Roteiro de Porta-Voz Jurídico",        "janela": "Dia 5-7",  "objetivo": "Preparar linguagem segura para eventual contato com imprensa"},
                {"ativo": "Press Release (após posição jurídica)","janela": "Semana 3", "objetivo": "Comunicado oficial quando houver decisão ou evolução processual"},
            ],
            "HIGH": [
                {"ativo": "Nota de Esclarecimento Jurídico",      "janela": "Dia 1-3",  "objetivo": "Documento formal posicionando a entidade no espectro jurídico"},
                {"ativo": "Biografia Executiva",                  "janela": "Dia 2-4",  "objetivo": "Controlar resultado #1 com narrativa autorizada e blindada"},
                {"ativo": "FAQ de Transparência",                 "janela": "Dia 3-7",  "objetivo": "FAQ com perguntas duras respondidas institucionalmente"},
                {"ativo": "Perfil Institucional",                 "janela": "Semana 2", "objetivo": "Diversificar ativos controlados na página 1"},
                {"ativo": "Roteiro de Entrevista",                "janela": "Semana 2", "objetivo": "Preparar porta-voz técnica para abordagem de imprensa"},
            ],
            "MEDIUM": [
                {"ativo": "Artigo LinkedIn",                      "janela": "Dia 1-5",  "objetivo": "Iniciar produção de conteúdo de posicionamento"},
                {"ativo": "Biografia Executiva",                  "janela": "Dia 3-7",  "objetivo": "Consolidar narrativa oficial"},
                {"ativo": "Perfil Institucional",                 "janela": "Semana 2", "objetivo": "Diversificar presença online"},
                {"ativo": "Press Release",                        "janela": "Semana 2", "objetivo": "Gerar menções neutras em veículos setoriais"},
            ],
            "LOW": [
                {"ativo": "Artigo LinkedIn",                      "janela": "Dia 1-7",  "objetivo": "Fortalecer presença editorial"},
                {"ativo": "Perfil Institucional",                 "janela": "Semana 1", "objetivo": "Consolidar ativos de autoridade"},
                {"ativo": "Biografia Executiva",                  "janela": "Semana 2", "objetivo": "Atualizar e otimizar narrativa"},
                {"ativo": "Press Release",                        "janela": "Semana 2", "objetivo": "Distribuir posicionamentos proativamente"},
            ],
        },
        "escalation": {
            ("legal",       "CRITICAL"): [
                "Entrada de inquérito ou operação policial com nome da entidade",
                "Vazamento seletivo para imprensa de peças processuais",
                "Condução coercitiva ou busca e apreensão",
                "Prisão (temporária ou preventiva) de pessoa ligada à entidade",
                "Matéria de capa em veículo Tier-1 (Globo, Estadão, Folha, Veja)",
                "Repercussão em CPI ou comissão parlamentar",
            ],
            ("legal",       "HIGH"): [
                "Entrada de veículo Tier-1 com cobertura do caso",
                "Nova peça processual com menção direta à entidade",
                "Reação pública de autoridade (juiz, promotor, delegado)",
                "Vazamento de documentos para imprensa",
            ],
            ("mainstream",  "CRITICAL"): [
                "Segunda cobertura negativa no mesmo veículo em menos de 7 dias",
                "Entrada de agências internacionais",
                "Repercussão em perfis de grande alcance",
                "Reação pública de autoridade",
            ],
            ("mainstream",  "HIGH"): [
                "Segunda cobertura negativa no mesmo veículo",
                "Menção em editorial ou coluna de opinião",
                "Pickup por veículo de TV aberta",
            ],
        },
        "redirection_overrides": {
            "crime":    "rigor juridico e presuncao de inocencia",
            "inquérito":"cooperacao com autoridades e devido processo legal",
            "operação": "transparencia processual e respeito as instituicoes",
            "prisão":   "presuncao de inocencia e garantias constitucionais",
        },
        "descricao_postura": {
            "contencao-juridica-absoluta":      "SILÊNCIO ESTRATÉGICO. Toda comunicação via jurídico externo. Porta-voz único. Nenhuma declaração pública sem aprovação do departamento jurídico.",
            "esclarecimento-juridico-controlado":"Nota jurídica breve, sem admission de culpa. Reafirmar cooperação com autoridades. Sem entrevistas.",
            "deslocamento-narrativo-tecnico":   "Produzir conteúdo técnico setorial para deslocar termos associados ao caso criminal para segunda página.",
            "reforco-canal-proprio-juridico":   "Canal próprio com posicionamento jurídico claro. FAQ de transparência sobre o caso.",
            "construcao-autoridade-cautelosa":  "Conteúdo de autoridade SEM menção ao caso. Posicionamento técnico setorial.",
        },
    },

    # ── REPUTACIONAL (corporate) ─────────────────────────────────────
    # Prioridade: ocupação → branding → mídia → distribuição
    # Regra de ouro: ocupar espaço. Silêncio = derrota.
    "reputacional": {
        "label": "Reputacional / Corporativo",
        "principio": "Ocupar espaço narrativo. Silêncio é derrota. Produzir, distribuir, Amplificar.",
        "posture": {
            ("CRITICAL", "legal",  True):  "institucional-defensivo",
            ("CRITICAL", "legal",  False): "ocupacao-narrativa-agressiva",
            ("CRITICAL", "mainstream", True):  "conciliatorio-com-clarificacao",
            ("CRITICAL", "mainstream", False): "ocupacao-narrativa-agressiva",
            ("CRITICAL", "blog",   True):  "institucional-defensivo",
            ("CRITICAL", "blog",   False): "deslocamento-narrativo",
            ("CRITICAL", "social", True):  "reforco-canal-proprio",
            ("CRITICAL", "social", False): "reforco-canal-proprio",
            ("HIGH",     "legal",  True):  "institucional-defensivo",
            ("HIGH",     "legal",  False): "construcao-autoridade",
            ("HIGH",     "mainstream", True):  "institucional-defensivo",
            ("HIGH",     "mainstream", False): "construcao-autoridade-ativista",
            ("HIGH",     "blog",   True):  "institucional-defensivo",
            ("HIGH",     "blog",   False): "deslocamento-narrativo",
            ("HIGH",     "social", True):  "reforco-canal-proprio",
            ("HIGH",     "social", False): "reforco-canal-proprio",
            ("MEDIUM",   "legal",  True):  "tecnico-juridico",
            ("MEDIUM",   "legal",  False): "construcao-autoridade",
            ("MEDIUM",   "mainstream", True):  "institucional-defensivo",
            ("MEDIUM",   "mainstream", False): "construcao-autoridade",
            ("MEDIUM",   "blog",   True):  "deslocamento-narrativo",
            ("MEDIUM",   "blog",   False): "deslocamento-narrativo",
            ("MEDIUM",   "social", True):  "reforco-canal-proprio",
            ("MEDIUM",   "social", False): "reforco-canal-proprio",
            ("LOW",      "legal",  True):  "tecnico-juridico",
            ("LOW",      "legal",  False): "consolidacao-autoridade",
            ("LOW",      "mainstream", True):  "construcao-autoridade",
            ("LOW",      "mainstream", False): "consolidacao-autoridade",
            ("LOW",      "blog",   True):  "consolidacao-autoridade",
            ("LOW",      "blog",   False): "consolidacao-autoridade",
            ("LOW",      "social", True):  "reforco-canal-proprio",
            ("LOW",      "social", False): "consolidacao-autoridade",
        },
        "visibility": {
            ("CRITICAL", True):  "MODERADA", ("CRITICAL", False): "ALTA",
            ("HIGH",     True):  "MODERADA", ("HIGH",     False): "ALTA",
            ("MEDIUM",   True):  "MODERADA", ("MEDIUM",   False): "ALTA",
            ("LOW",      True):  "ALTA",     ("LOW",      False): "ALTA",
        },
        "temperature": {
            "CRITICAL": "MODERADA", "HIGH": "AGRESIVA", "MEDIUM": "AGRESIVA", "LOW": "AGRESIVA",
        },
        "stakeholders": {
            ("CRITICAL", True):  ["Jurídico", "CEO", "Conselho", "Assessoria de Imprensa", "Investidores"],
            ("CRITICAL", False): ["CEO", "Assessoria de Imprensa", "Conselho", "Investidores", "Clientes"],
            ("HIGH",     True):  ["Jurídico", "CEO", "Assessoria de Imprensa", "Conselho", "Colaboradores"],
            ("HIGH",     False): ["CEO", "Assessoria de Imprensa", "Colaboradores", "Clientes", "Investidores"],
            ("MEDIUM",   True):  ["Jurídico", "Assessoria de Imprensa", "CEO", "Colaboradores", "Clientes"],
            ("MEDIUM",   False): ["CEO", "Assessoria de Imprensa", "Colaboradores", "Parceiros", "Clientes"],
            ("LOW",      True):  ["Jurídico", "CEO", "Colaboradores", "Clientes", "Parceiros"],
            ("LOW",      False): ["CEO", "Colaboradores", "Assessoria de Imprensa", "Clientes", "Parceiros"],
        },
        "assets": {
            "CRITICAL": [
                {"ativo": "Artigo LinkedIn — Posicionamento",     "janela": "Dia 1",    "objetivo": "Ocupar espaço narrativo imediatamente com posicionamento público"},
                {"ativo": "Press Release Oficial",                "janela": "Dia 1-2",  "objetivo": "Versão oficial distribuída para veículos cadastrados"},
                {"ativo": "Perfil Institucional Atualizado",      "janela": "Dia 2-3",  "objetivo": "Reforçar ativos controlados na página 1"},
                {"ativo": "FAQ de Transparência",                 "janela": "Dia 3-5",  "objetivo": "Antecipar perguntas da imprensa em canal controlado"},
                {"ativo": "Roteiro de Entrevista para CEO",       "janela": "Dia 3-5",  "objetivo": "Preparar porta-voz principal para contato com imprensa"},
                {"ativo": "Campanha de Google Ads (brand defense)","janela": "Dia 1-3",  "objetivo": "Garantir CTR em buscas de marca mesmo durante crise"},
            ],
            "HIGH": [
                {"ativo": "Artigo LinkedIn",                      "janela": "Dia 1-3",  "objetivo": "Posicionamento público em canal de alta autoridade"},
                {"ativo": "Press Release",                        "janela": "Dia 2-4",  "objetivo": "Distribuir versão oficial para imprensa setorial"},
                {"ativo": "Perfil Institucional",                 "janela": "Dia 3-7",  "objetivo": "Reforçar presença controlada na página 1"},
                {"ativo": "Roteiro de Entrevista",                "janela": "Semana 2", "objetivo": "Preparar porta-voz para imprensa"},
                {"ativo": "FAQ de Transparência",                 "janela": "Semana 2", "objetivo": "Antecipar perguntas frequentes do público"},
            ],
            "MEDIUM": [
                {"ativo": "Artigo LinkedIn",                      "janela": "Dia 1-5",  "objetivo": "Conteúdo de posicionamento e autoridade"},
                {"ativo": "Biografia Executiva",                  "janela": "Dia 3-7",  "objetivo": "Consolidar narrativa oficial"},
                {"ativo": "Perfil Institucional",                 "janela": "Semana 2", "objetivo": "Diversificar presença online"},
                {"ativo": "Press Release",                        "janela": "Semana 2", "objetivo": "Gerar menções neutras em veículos setoriais"},
            ],
            "LOW": [
                {"ativo": "Artigo LinkedIn",                      "janela": "Dia 1-7",  "objetivo": "Fortalecer presença editorial"},
                {"ativo": "Perfil Institucional",                 "janela": "Semana 1", "objetivo": "Consolidar ativos de autoridade"},
                {"ativo": "Biografia Executiva",                  "janela": "Semana 2", "objetivo": "Atualizar e otimizar narrativa"},
                {"ativo": "Press Release",                        "janela": "Semana 2", "objetivo": "Distribuir posicionamentos proativamente"},
            ],
        },
        "escalation": {
            ("mainstream", "CRITICAL"): [
                "Matéria de capa em Tier-1",
                "Queda de ação em bolsa ou repercussão financeira relevante",
                "Reação pública de cliente ou parceiro estratégico",
                "Entrada de órgão regulador",
            ],
            ("mainstream", "HIGH"): [
                "Segunda cobertura negativa no mesmo veículo",
                "Menção em coluna de opinião ou editorial",
                "Pickup por veículo setorial de grande alcance",
            ],
        },
        "redirection_overrides": {
            "escândalo": "modernizacao de processos e governanca corporativa",
            "crise":     "resiliencia organizacional e gestao de risco",
            "demissão":  "reestruturacao e renovacao de lideranca",
            "prejuízo":  "eficiencia operacional e disciplina financeira",
        },
        "descricao_postura": {
            "ocupacao-narrativa-agressiva":  "PRODUZIR E DISTRIBUIR. Silêncio não é opção. Publicar artigo de posicionamento, press release, campanha de ads. Ocupar antes que terceiros ocupem.",
            "construcao-autoridade-ativista": "Conteúdo de autoridade COM tom propositivo. Não apenas defender — avançar pauta positiva.",
        },
    },

    # ── POLÍTICO ─────────────────────────────────────────────────────
    # Prioridade: coalizão → imprensa → stakeholders → guerra narrativa
    # Regra de ouro: base política primeiro, imprensa depois.
    "politico": {
        "label": "Político / Agente Público",
        "principio": "Base política e coalizão em primeiro lugar. Imprensa é campo de batalha, não auditório.",
        "posture": {
            ("CRITICAL", "legal",  True):  "contencao-juridica-absoluta",
            ("CRITICAL", "legal",  False): "guerra-narrativa",
            ("CRITICAL", "mainstream", True):  "conciliatorio-com-clarificacao",
            ("CRITICAL", "mainstream", False): "guerra-narrativa",
            ("CRITICAL", "blog",   True):  "institucional-defensivo",
            ("CRITICAL", "blog",   False): "deslocamento-narrativo-agressivo",
            ("CRITICAL", "social", True):  "mobilizacao-de-base",
            ("CRITICAL", "social", False): "mobilizacao-de-base",
            ("HIGH",     "legal",  True):  "tecnico-juridico",
            ("HIGH",     "legal",  False): "posicionamento-propositivo",
            ("HIGH",     "mainstream", True):  "institucional-defensivo",
            ("HIGH",     "mainstream", False): "posicionamento-propositivo",
            ("HIGH",     "blog",   True):  "institucional-defensivo",
            ("HIGH",     "blog",   False): "deslocamento-narrativo",
            ("HIGH",     "social", True):  "mobilizacao-de-base",
            ("HIGH",     "social", False): "mobilizacao-de-base",
            ("MEDIUM",   "legal",  True):  "tecnico-juridico",
            ("MEDIUM",   "legal",  False): "posicionamento-propositivo",
            ("MEDIUM",   "mainstream", True):  "institucional-defensivo",
            ("MEDIUM",   "mainstream", False): "construcao-autoridade",
            ("MEDIUM",   "blog",   True):  "deslocamento-narrativo",
            ("MEDIUM",   "blog",   False): "deslocamento-narrativo",
            ("MEDIUM",   "social", True):  "mobilizacao-de-base",
            ("MEDIUM",   "social", False): "mobilizacao-de-base",
            ("LOW",      "legal",  True):  "tecnico-juridico",
            ("LOW",      "legal",  False): "consolidacao-autoridade",
            ("LOW",      "mainstream", True):  "construcao-autoridade",
            ("LOW",      "mainstream", False): "consolidacao-autoridade",
            ("LOW",      "blog",   True):  "consolidacao-autoridade",
            ("LOW",      "blog",   False): "consolidacao-autoridade",
            ("LOW",      "social", True):  "mobilizacao-de-base",
            ("LOW",      "social", False): "mobilizacao-de-base",
        },
        "visibility": {
            ("CRITICAL", True):  "BAIXA",  ("CRITICAL", False): "ALTA",
            ("HIGH",     True):  "MODERADA", ("HIGH",     False): "ALTA",
            ("MEDIUM",   True):  "MODERADA", ("MEDIUM",   False): "ALTA",
            ("LOW",      True):  "ALTA",     ("LOW",      False): "ALTA",
        },
        "temperature": {
            "CRITICAL": "AGRESIVA", "HIGH": "AGRESIVA", "MEDIUM": "MODERADA", "LOW": "AGRESIVA",
        },
        "stakeholders": {
            ("CRITICAL", True):  ["Jurídico", "Coalizão Política", "Base Parlamentar", "Lideranças Partidárias", "Imprensa"],
            ("CRITICAL", False): ["Coalizão Política", "Base Parlamentar", "Lideranças Partidárias", "Imprensa", "Eleitores"],
            ("HIGH",     True):  ["Jurídico", "Coalizão Política", "Assessoria de Imprensa", "Base Parlamentar", "Eleitores"],
            ("HIGH",     False): ["Coalizão Política", "Assessoria de Imprensa", "Base Parlamentar", "Lideranças Partidárias", "Imprensa"],
            ("MEDIUM",   True):  ["Jurídico", "Assessoria de Imprensa", "Coalizão Política", "Base Parlamentar", "Eleitores"],
            ("MEDIUM",   False): ["Assessoria de Imprensa", "Coalizão Política", "Eleitores", "Base Parlamentar", "Jurídico"],
            ("LOW",      True):  ["Jurídico", "Assessoria de Imprensa", "Eleitores", "Base Parlamentar", "Coalizão Política"],
            ("LOW",      False): ["Assessoria de Imprensa", "Eleitores", "Coalizão Política", "Base Parlamentar", "Imprensa"],
        },
        "assets": {
            "CRITICAL": [
                {"ativo": "Nota Política Oficial",                "janela": "Horas",   "objetivo": "Posicionamento público imediato para base e imprensa"},
                {"ativo": "Artigo de Posicionamento",             "janela": "Dia 1",    "objetivo": "Versão pública da narrativa em veículo de grande alcance"},
                {"ativo": "Roteiro de Entrevista para Imprensa",  "janela": "Dia 1-2",  "objetivo": "Preparar linguagem segura e mensagens-chave para mídia"},
                {"ativo": "Mobilização de Base (redes sociais)",  "janela": "Dia 1-2",  "objetivo": "Ativar base de apoiadores para defesa pública coordenada"},
                {"ativo": "Perfil Institucional Atualizado",      "janela": "Dia 2-4",  "objetivo": "Reforçar biografia e realizações na página 1 do Google"},
                {"ativo": "Press Release para Veículos Simpáticos","janela": "Semana 1","objetivo": "Distribuir narrativa favorável em veículos alinhados"},
            ],
            "HIGH": [
                {"ativo": "Nota Política",                        "janela": "Dia 1-2",  "objetivo": "Posicionamento público antes que a versão adversária se fixe"},
                {"ativo": "Artigo de Imprensa",                   "janela": "Dia 2-4",  "objetivo": "Artigo assinado em veículo de grande circulação"},
                {"ativo": "Roteiro de Entrevista",                "janela": "Dia 3-5",  "objetivo": "Preparar porta-voz para abordagem de imprensa"},
                {"ativo": "Perfil Institucional",                 "janela": "Semana 1", "objetivo": "Reforçar biografia e realizações"},
            ],
            "MEDIUM": [
                {"ativo": "Artigo LinkedIn",                      "janela": "Dia 1-5",  "objetivo": "Conteúdo de posicionamento político"},
                {"ativo": "Press Release",                        "janela": "Semana 1", "objetivo": "Distribuir realizações e pautas positivas"},
                {"ativo": "Biografia Política",                   "janela": "Semana 2", "objetivo": "Consolidar trajetória e realizações"},
            ],
            "LOW": [
                {"ativo": "Artigo LinkedIn",                      "janela": "Dia 1-7",  "objetivo": "Fortalecer presença digital e engajamento"},
                {"ativo": "Press Release Proativo",               "janela": "Semana 2", "objetivo": "Distribuir pautas positivas"},
            ],
        },
        "escalation": {
            ("mainstream", "CRITICAL"): [
                "Matéria de capa em Tier-1 com tom de denúncia",
                "Entrada de veículo internacional",
                "Repercussão em redes sociais com mais de 100 mil compartilhamentos",
                "Pronunciamento de adversário político de alto nível",
                "Abertura de CPI ou comissão parlamentar de inquérito",
                "Reação do governo ou de órgão de controle",
            ],
            ("mainstream", "HIGH"): [
                "Segunda matéria negativa no mesmo veículo",
                "Pickup por veículo de rádio ou TV aberta",
                "Menção em editorial de jornal de grande circulação",
            ],
            ("social", "CRITICAL"): [
                "Trending topics nacional com hashtag negativa",
                "Vídeo viral com mais de 1 milhão de visualizações",
                "Repercussão em perfil de influenciador político com mais de 500 mil seguidores",
            ],
        },
        "redirection_overrides": {
            "corrupção":    "combate a corrupcao e transparencia na gestao publica",
            "escândalo":    "prestacao de contas e compromisso com a verdade",
            "CPI":          "colaboracao com o parlamento e defesa da gestao",
            "impeachment":  "defesa do mandato e legitimidade democratica",
            "renúncia":     "responsabilidade institucional e projeto politico",
        },
        "descricao_postura": {
            "guerra-narrativa":                "Mobilizar base. Produzir contra-narrativa. Ocupar todos os canais. Silêncio não é estratégia — é rendição.",
            "deslocamento-narrativo-agressivo": "Produzir conteúdo em volume e velocidade superiores. Múltiplos artigos, releases, posts. Sobrepor narrativa adversária.",
            "mobilizacao-de-base":             "Ativar rede de apoiadores. Coordenação de mensagens. Produção de conteúdo de rua e digital.",
            "posicionamento-propositivo":       "Avançar pauta positiva. Falar de futuro, projeto, entregas. Não apenas se defender — propor.",
        },
    },

    # ── MÍDIA ────────────────────────────────────────────────────────
    # Prioridade: gestão de pauta → imprensa → opinião pública → correção de rota
    "media": {
        "label": "Mídia / Veículo de Comunicação",
        "principio": "Gestão de pauta é a chave. A crise de um veículo é sua própria pauta virada contra ele.",
        "posture": {
            ("CRITICAL", "legal",  True):  "contencao-juridica-absoluta",
            ("CRITICAL", "legal",  False): "gestao-de-pauta",
            ("CRITICAL", "mainstream", True):  "conciliatorio-com-clarificacao",
            ("CRITICAL", "mainstream", False): "gestao-de-pauta",
            ("CRITICAL", "blog",   True):  "institucional-defensivo",
            ("CRITICAL", "blog",   False): "deslocamento-de-pauta",
            ("CRITICAL", "social", True):  "reforco-canal-proprio",
            ("CRITICAL", "social", False): "reforco-canal-proprio",
            ("HIGH",     "legal",  True):  "tecnico-juridico",
            ("HIGH",     "legal",  False): "correcao-de-rota-editorial",
            ("HIGH",     "mainstream", True):  "institucional-defensivo",
            ("HIGH",     "mainstream", False): "correcao-de-rota-editorial",
            ("HIGH",     "blog",   True):  "institucional-defensivo",
            ("HIGH",     "blog",   False): "deslocamento-narrativo",
            ("HIGH",     "social", True):  "reforco-canal-proprio",
            ("HIGH",     "social", False): "reforco-canal-proprio",
            ("MEDIUM",   "legal",  True):  "tecnico-juridico",
            ("MEDIUM",   "legal",  False): "alinhamento-editorial",
            ("MEDIUM",   "mainstream", True):  "institucional-defensivo",
            ("MEDIUM",   "mainstream", False): "alinhamento-editorial",
            ("MEDIUM",   "blog",   True):  "deslocamento-narrativo",
            ("MEDIUM",   "blog",   False): "deslocamento-narrativo",
            ("MEDIUM",   "social", True):  "reforco-canal-proprio",
            ("MEDIUM",   "social", False): "reforco-canal-proprio",
            ("LOW",      "legal",  True):  "tecnico-juridico",
            ("LOW",      "legal",  False): "consolidacao-autoridade",
            ("LOW",      "mainstream", True):  "construcao-autoridade",
            ("LOW",      "mainstream", False): "consolidacao-autoridade",
            ("LOW",      "blog",   True):  "consolidacao-autoridade",
            ("LOW",      "blog",   False): "consolidacao-autoridade",
            ("LOW",      "social", True):  "reforco-canal-proprio",
            ("LOW",      "social", False): "consolidacao-autoridade",
        },
        "visibility": {
            ("CRITICAL", True):  "BAIXA",  ("CRITICAL", False): "MODERADA",
            ("HIGH",     True):  "MODERADA", ("HIGH",     False): "MODERADA",
            ("MEDIUM",   True):  "MODERADA", ("MEDIUM",   False): "ALTA",
            ("LOW",      True):  "ALTA",     ("LOW",      False): "ALTA",
        },
        "temperature": {
            "CRITICAL": "FRIA", "HIGH": "MODERADA", "MEDIUM": "MODERADA", "LOW": "AGRESIVA",
        },
        "stakeholders": {
            ("CRITICAL", True):  ["Jurídico", "Conselho Editorial", "Diretoria de Jornalismo", "Assessoria Jurídica", "Acionistas"],
            ("CRITICAL", False): ["Conselho Editorial", "Diretoria de Jornalismo", "Assessoria de Imprensa", "Colaboradores", "Leitores"],
            ("HIGH",     True):  ["Jurídico", "Conselho Editorial", "Diretoria de Jornalismo", "Colaboradores", "Leitores"],
            ("HIGH",     False): ["Conselho Editorial", "Diretoria de Jornalismo", "Colaboradores", "Assessoria de Imprensa", "Leitores"],
            ("MEDIUM",   True):  ["Jurídico", "Conselho Editorial", "Colaboradores", "Leitores", "Anunciantes"],
            ("MEDIUM",   False): ["Conselho Editorial", "Colaboradores", "Leitores", "Anunciantes", "Assessoria de Imprensa"],
            ("LOW",      True):  ["Jurídico", "Conselho Editorial", "Leitores", "Colaboradores", "Anunciantes"],
            ("LOW",      False): ["Conselho Editorial", "Leitores", "Colaboradores", "Anunciantes", "Assessoria de Imprensa"],
        },
        "assets": {
            "CRITICAL": [
                {"ativo": "Nota à Audiência/Leitores",            "janela": "Horas",   "objetivo": "Comunicado direto ao público sobre o ocorrido e providências"},
                {"ativo": "Nota de Esclarecimento Jurídico",      "janela": "Dia 1",    "objetivo": "Versão jurídica dos fatos para proteger o veículo"},
                {"ativo": "Artigo Editorial de Correção de Rota", "janela": "Dia 1-3",  "objetivo": "Posicionamento editorial sobre o caso — transparência e compromisso"},
                {"ativo": "FAQ para Leitores",                    "janela": "Dia 2-4",  "objetivo": "Antecipar perguntas do público em formato controlado"},
                {"ativo": "Roteiro de Porta-Voz",                 "janela": "Dia 2-4",  "objetivo": "Preparar diretoria para entrevistas sobre o caso"},
                {"ativo": "Campanha de Reconexão com Audiência",  "janela": "Semana 1", "objetivo": "Produzir conteúdo que reafirme o compromisso editorial do veículo"},
            ],
            "HIGH": [
                {"ativo": "Nota à Audiência",                     "janela": "Dia 1-2",  "objetivo": "Posicionamento público sobre o caso"},
                {"ativo": "Artigo de Correção de Rota",           "janela": "Dia 2-4",  "objetivo": "Editorial ou artigo assinado sobre as lições do caso"},
                {"ativo": "FAQ para Leitores",                    "janela": "Semana 1", "objetivo": "Transparência sobre o ocorrido"},
            ],
            "MEDIUM": [
                {"ativo": "Artigo de Posicionamento Editorial",   "janela": "Dia 1-7",  "objetivo": "Reforçar linha editorial e compromisso com a audiência"},
                {"ativo": "Press Release Setorial",               "janela": "Semana 2", "objetivo": "Comunicado para o mercado de comunicação"},
            ],
            "LOW": [
                {"ativo": "Conteúdo de Reforço de Marca",         "janela": "Semana 1", "objetivo": "Fortalecer presença e autoridade do veículo"},
                {"ativo": "Press Release Proativo",               "janela": "Semana 2", "objetivo": "Distribuir pautas positivas sobre o veículo"},
            ],
        },
        "escalation": {
            ("mainstream", "CRITICAL"): [
                "Matéria de capa em OUTRO veículo sobre o caso",
                "Entrada de agências internacionais",
                "Repercussão em redes sociais questionando a credibilidade do veículo",
                "Manifestação de associação de imprensa ou órgão de classe",
                "Queda de assinaturas ou anunciantes",
            ],
            ("mainstream", "HIGH"): [
                "Pickup do caso por veículo concorrente",
                "Repercussão em colunas de mídia e opinião pública",
                "Manifestação de leitores organizados",
            ],
        },
        "redirection_overrides": {
            "plágio":       "compromisso com a integridade editorial e revisao de processos",
            "fake news":    "compromisso com a verificacao factual e fontes confiaveis",
            "parcialidade": "independencia editorial e pluralidade de fontes",
            "erro":         "transparencia na correcao e compromisso com a verdade",
        },
        "descricao_postura": {
            "gestao-de-pauta":            "CONTROLAR A NARRATIVA SOBRE O VEÍCULO. Não deixar que concorrentes pautem a crise do seu veículo. Produzir sua própria versão primeiro.",
            "deslocamento-de-pauta":      "Mudar o foco da discussão. Produzir conteúdo sobre temas onde o veículo tem autoridade incontestável.",
            "correcao-de-rota-editorial": "Admitir erros quando aplicável. Transparência gera credibilidade. Correção pública quando necessário.",
            "alinhamento-editorial":      "Reunir equipe editorial para alinhar discurso e próxima pauta. Evitar contradições internas.",
        },
    },

    # ── ADMINISTRATIVO ───────────────────────────────────────────────
    # Prioridade: transparência → procedimentos → stakeholders → regularização
    "administrativo": {
        "label": "Administrativo / Órgão Público",
        "principio": "Transparência e procedimento. A crise administrativa se combate com documentos, não com versões.",
        "posture": {
            ("CRITICAL", "legal",  True):  "transparencia-processual",
            ("CRITICAL", "legal",  False): "transparencia-processual",
            ("CRITICAL", "mainstream", True):  "institucional-defensivo",
            ("CRITICAL", "mainstream", False): "prestacao-de-contas",
            ("CRITICAL", "blog",   True):  "institucional-defensivo",
            ("CRITICAL", "blog",   False): "prestacao-de-contas",
            ("CRITICAL", "social", True):  "transparencia-processual",
            ("CRITICAL", "social", False): "prestacao-de-contas",
            ("HIGH",     "legal",  True):  "tecnico-juridico",
            ("HIGH",     "legal",  False): "regularizacao-procedimental",
            ("HIGH",     "mainstream", True):  "institucional-defensivo",
            ("HIGH",     "mainstream", False): "regularizacao-procedimental",
            ("HIGH",     "blog",   True):  "institucional-defensivo",
            ("HIGH",     "blog",   False): "regularizacao-procedimental",
            ("HIGH",     "social", True):  "regularizacao-procedimental",
            ("HIGH",     "social", False): "regularizacao-procedimental",
            ("MEDIUM",   "legal",  True):  "tecnico-juridico",
            ("MEDIUM",   "legal",  False): "conformidade-procedimental",
            ("MEDIUM",   "mainstream", True):  "institucional-defensivo",
            ("MEDIUM",   "mainstream", False): "conformidade-procedimental",
            ("MEDIUM",   "blog",   True):  "conformidade-procedimental",
            ("MEDIUM",   "blog",   False): "conformidade-procedimental",
            ("MEDIUM",   "social", True):  "conformidade-procedimental",
            ("MEDIUM",   "social", False): "conformidade-procedimental",
            ("LOW",      "legal",  True):  "tecnico-juridico",
            ("LOW",      "legal",  False): "consolidacao-procedimental",
            ("LOW",      "mainstream", True):  "consolidacao-procedimental",
            ("LOW",      "mainstream", False): "consolidacao-procedimental",
            ("LOW",      "blog",   True):  "consolidacao-procedimental",
            ("LOW",      "blog",   False): "consolidacao-procedimental",
            ("LOW",      "social", True):  "consolidacao-procedimental",
            ("LOW",      "social", False): "consolidacao-procedimental",
        },
        "visibility": {
            ("CRITICAL", True):  "MODERADA", ("CRITICAL", False): "ALTA",
            ("HIGH",     True):  "MODERADA", ("HIGH",     False): "ALTA",
            ("MEDIUM",   True):  "ALTA",     ("MEDIUM",   False): "ALTA",
            ("LOW",      True):  "ALTA",     ("LOW",      False): "ALTA",
        },
        "temperature": {
            "CRITICAL": "MODERADA", "HIGH": "MODERADA", "MEDIUM": "FRIA", "LOW": "MODERADA",
        },
        "stakeholders": {
            ("CRITICAL", True):  ["Jurídico", "Tribunal de Contas", "Órgão Regulador", "Imprensa", "Cidadãos"],
            ("CRITICAL", False): ["Cidadãos", "Imprensa", "Órgão Regulador", "Jurídico", "Tribunal de Contas"],
            ("HIGH",     True):  ["Jurídico", "Órgão Regulador", "Tribunal de Contas", "Imprensa", "Cidadãos"],
            ("HIGH",     False): ["Cidadãos", "Imprensa", "Órgão Regulador", "Jurídico", "Tribunal de Contas"],
            ("MEDIUM",   True):  ["Jurídico", "Órgão Regulador", "Cidadãos", "Imprensa", "Tribunal de Contas"],
            ("MEDIUM",   False): ["Cidadãos", "Órgão Regulador", "Jurídico", "Imprensa", "Tribunal de Contas"],
            ("LOW",      True):  ["Jurídico", "Cidadãos", "Órgão Regulador", "Imprensa", "Tribunal de Contas"],
            ("LOW",      False): ["Cidadãos", "Jurídico", "Órgão Regulador", "Imprensa", "Tribunal de Contas"],
        },
        "assets": {
            "CRITICAL": [
                {"ativo": "Nota Oficial com Documentação",         "janela": "Horas",   "objetivo": "Comunicado oficial com referência a documentos, leis e procedimentos"},
                {"ativo": "Dossiê de Regularidade",               "janela": "Dia 1-2",  "objetivo": "Compilado de documentos que comprovam regularidade do ato questionado"},
                {"ativo": "FAQ de Transparência",                 "janela": "Dia 2-4",  "objetivo": "Perguntas e respostas baseadas em legislação e procedimentos"},
                {"ativo": "Página de Transparência Dedicada",     "janela": "Dia 2-5",  "objetivo": "Microsite ou página com toda a documentação do caso"},
                {"ativo": "Press Release Institucional",          "janela": "Semana 1", "objetivo": "Comunicado oficial distribuído para imprensa"},
                {"ativo": "Campanha de Prestação de Contas",      "janela": "Semana 2", "objetivo": "Conteúdo explicativo sobre o procedimento administrativo correto"},
            ],
            "HIGH": [
                {"ativo": "Nota Oficial",                          "janela": "Dia 1-2",  "objetivo": "Posicionamento oficial baseado em documentos"},
                {"ativo": "FAQ de Transparência",                 "janela": "Dia 2-5",  "objetivo": "Antecipar perguntas da imprensa e cidadãos"},
                {"ativo": "Dossiê de Regularidade",               "janela": "Semana 1", "objetivo": "Documentação comprobatória da regularidade"},
                {"ativo": "Press Release",                        "janela": "Semana 2", "objetivo": "Comunicado oficial distribuído para imprensa"},
            ],
            "MEDIUM": [
                {"ativo": "Nota de Esclarecimento",               "janela": "Dia 1-5",  "objetivo": "Esclarecimento baseado em procedimentos vigentes"},
                {"ativo": "Página de Transparência",              "janela": "Semana 2", "objetivo": "Documentar o procedimento correto para consulta pública"},
            ],
            "LOW": [
                {"ativo": "Conteúdo de Transparência Proativa",   "janela": "Semana 1", "objetivo": "Publicar procedimentos e boas práticas do órgão"},
                {"ativo": "Press Release de Gestão",              "janela": "Semana 2", "objetivo": "Divulgar resultados e eficiência administrativa"},
            ],
        },
        "escalation": {
            ("legal", "CRITICAL"): [
                "Decisão judicial desfavorável com repercussão",
                "Notificação de tribunal de contas",
                "Abertura de procedimento disciplinar",
                "Recomendação do Ministério Público",
            ],
            ("mainstream", "CRITICAL"): [
                "Matéria de capa em Tier-1",
                "Reação de associação de servidores ou classe",
                "Manifestação de órgão de controle externo",
                "Repercussão em redes sociais com questionamentos à gestão",
            ],
            ("mainstream", "HIGH"): [
                "Segunda matéria negativa no mesmo veículo",
                "Pickup por veículo de rádio ou TV",
                "Nota de órgão regulador ou de classe",
            ],
        },
        "redirection_overrides": {
            "licitação":    "transparencia em licitacoes e cumprimento da lei 8666",
            "contrato":     "gestao contratual transparente e fiscalizacao rigorosa",
            "concurso":     "meritocracia e legalidade em concursos publicos",
            "desvio":       "auditoria e controle interno rigorosos",
            "fraude":       "mecanismos de controle e prevencao a fraude",
        },
        "descricao_postura": {
            "transparencia-processual":     "DOCUMENTOS ACIMA DE VERSÕES. Publicar editais, contratos, pareceres. A verdade administrativa está nos arquivos.",
            "prestacao-de-contas":          "Posicionamento público com dados, números e documentos. Transparência radical.",
            "regularizacao-procedimental":  "Identificar o desvio de procedimento e demonstrar a correção. Documentar o passo a passo da regularização.",
            "conformidade-procedimental":   "Alinhar todos os procedimentos aos marcos legais e regulatórios vigentes. Demonstrar conformidade.",
            "consolidacao-procedimental":   "Sistematizar e publicar procedimentos como referência de boas práticas administrativas.",
        },
    },

    # ── ASSOCIATIVO (association_based) ──────────────────────────────
    # Prioridade: desassociação → esclarecimento jurídico → blindagem contratual → compliance
    "associativo": {
        "label": "Associativo / Risco por Vínculo",
        "principio": "Desassociação documentada em primeiro lugar. O risco não é da entidade — é da associação indevida a terceiros.",
        "posture": {
            ("CRITICAL", "legal",  True):  "desassociacao-documentada",
            ("CRITICAL", "legal",  False): "desassociacao-documentada",
            ("CRITICAL", "mainstream", True):  "esclarecimento-institucional",
            ("CRITICAL", "mainstream", False): "desassociacao-documentada",
            ("CRITICAL", "blog",   True):  "esclarecimento-institucional",
            ("CRITICAL", "blog",   False): "desassociacao-narrativa",
            ("CRITICAL", "social", True):  "esclarecimento-institucional",
            ("CRITICAL", "social", False): "desassociacao-narrativa",
            ("HIGH",     "legal",  True):  "blindagem-contratual",
            ("HIGH",     "legal",  False): "desassociacao-narrativa",
            ("HIGH",     "mainstream", True):  "esclarecimento-institucional",
            ("HIGH",     "mainstream", False): "desassociacao-narrativa",
            ("HIGH",     "blog",   True):  "esclarecimento-institucional",
            ("HIGH",     "blog",   False): "desassociacao-narrativa",
            ("HIGH",     "social", True):  "esclarecimento-institucional",
            ("HIGH",     "social", False): "desassociacao-narrativa",
            ("MEDIUM",   "legal",  True):  "blindagem-contratual",
            ("MEDIUM",   "legal",  False): "reforco-compliance",
            ("MEDIUM",   "mainstream", True):  "esclarecimento-institucional",
            ("MEDIUM",   "mainstream", False): "reforco-compliance",
            ("MEDIUM",   "blog",   True):  "reforco-compliance",
            ("MEDIUM",   "blog",   False): "reforco-compliance",
            ("MEDIUM",   "social", True):  "reforco-compliance",
            ("MEDIUM",   "social", False): "reforco-compliance",
            ("LOW",      "legal",  True):  "blindagem-contratual",
            ("LOW",      "legal",  False): "consolidacao-compliance",
            ("LOW",      "mainstream", True):  "consolidacao-compliance",
            ("LOW",      "mainstream", False): "consolidacao-compliance",
            ("LOW",      "blog",   True):  "consolidacao-compliance",
            ("LOW",      "blog",   False): "consolidacao-compliance",
            ("LOW",      "social", True):  "consolidacao-compliance",
            ("LOW",      "social", False): "consolidacao-compliance",
        },
        "visibility": {
            ("CRITICAL", True):  "BAIXA",  ("CRITICAL", False): "MODERADA",
            ("HIGH",     True):  "BAIXA",  ("HIGH",     False): "MODERADA",
            ("MEDIUM",   True):  "MODERADA", ("MEDIUM",   False): "MODERADA",
            ("LOW",      True):  "MODERADA", ("LOW",      False): "ALTA",
        },
        "temperature": {
            "CRITICAL": "FRIA", "HIGH": "FRIA", "MEDIUM": "MODERADA", "LOW": "AGRESIVA",
        },
        "stakeholders": {
            ("CRITICAL", True):  ["Jurídico", "Sócios", "Contratantes", "Órgão Regulador", "Imprensa (via jurídico)"],
            ("CRITICAL", False): ["Jurídico", "Sócios", "Contratantes", "Imprensa", "Cidadãos"],
            ("HIGH",     True):  ["Jurídico", "Sócios", "Contratantes", "Órgão Regulador", "Imprensa"],
            ("HIGH",     False): ["Jurídico", "Sócios", "Contratantes", "Imprensa", "Cidadãos"],
            ("MEDIUM",   True):  ["Jurídico", "Sócios", "Contratantes", "Órgão Regulador", "Cidadãos"],
            ("MEDIUM",   False): ["Sócios", "Jurídico", "Contratantes", "Imprensa", "Cidadãos"],
            ("LOW",      True):  ["Jurídico", "Sócios", "Contratantes", "Órgão Regulador", "Cidadãos"],
            ("LOW",      False): ["Sócios", "Contratantes", "Jurídico", "Cidadãos", "Imprensa"],
        },
        "assets": {
            "CRITICAL": [
                {"ativo": "Nota de Desassociação Jurídica",       "janela": "Dia 1",    "objetivo": "Documento formal comprovando a ausência de vínculo com o terceiro envolvido"},
                {"ativo": "Dossiê de Desassociação Documentada",  "janela": "Dia 1-3",  "objetivo": "Compilado de documentos (contratos, distratos, atas) que comprovam o desligamento"},
                {"ativo": "Esclarecimento Institucional",         "janela": "Dia 2-4",  "objetivo": "Posicionamento público explicando a natureza do vínculo (ou ausência dele)"},
                {"ativo": "FAQ de Transparência",                 "janela": "Dia 3-5",  "objetivo": "Antecipar perguntas sobre o vínculo e as providências tomadas"},
                {"ativo": "Perfil Institucional Atualizado",      "janela": "Dia 3-7",  "objetivo": "Reforçar identidade própria e desvincular da associação indevida"},
                {"ativo": "Roteiro de Porta-Voz",                 "janela": "Semana 1", "objetivo": "Preparar discurso de desassociação para oportunidades de imprensa"},
            ],
            "HIGH": [
                {"ativo": "Nota de Desassociação",                "janela": "Dia 1-2",  "objetivo": "Documento formal comprovando a desassociação"},
                {"ativo": "Esclarecimento Institucional",         "janela": "Dia 2-4",  "objetivo": "Posicionamento público sobre o vínculo"},
                {"ativo": "FAQ de Transparência",                 "janela": "Dia 3-7",  "objetivo": "Antecipar perguntas da imprensa e contratantes"},
                {"ativo": "Blindagem Contratual (revisão)",       "janela": "Semana 2", "objetivo": "Revisar contratos para evitar associações futuras"},
            ],
            "MEDIUM": [
                {"ativo": "Nota de Esclarecimento",               "janela": "Dia 1-5",  "objetivo": "Posicionamento público sobre a natureza do vínculo"},
                {"ativo": "Política de Compliance",               "janela": "Semana 2", "objetivo": "Publicar ou reforçar política de compliance e due diligence"},
                {"ativo": "Perfil Institucional",                 "janela": "Semana 2", "objetivo": "Reforçar identidade e valores da entidade"},
            ],
            "LOW": [
                {"ativo": "Conteúdo de Compliance",               "janela": "Semana 1", "objetivo": "Publicar políticas de compliance e due diligence"},
                {"ativo": "Perfil Institucional",                 "janela": "Semana 2", "objetivo": "Fortalecer identidade própria e autoridade de marca"},
            ],
        },
        "escalation": {
            ("legal", "CRITICAL"): [
                "Citação direta da entidade em processo judicial de terceiro",
                "Determinação judicial que atinja direta ou indiretamente a entidade",
                "Notificação extrajudicial envolvendo o nome da entidade",
                "Bloqueio de contratos ou contas por associação ao terceiro",
            ],
            ("mainstream", "CRITICAL"): [
                "Matéria Tier-1 associando a entidade ao terceiro investigado",
                "Reação de contratantes ou parceiros comerciais",
                "Queda de contrato ou negócio por receio de associação",
                "Manifestação de órgão regulador ou de classe sobre o vínculo",
            ],
            ("mainstream", "HIGH"): [
                "Segunda matéria associando a entidade ao terceiro",
                "Pickup do caso por veículo setorial",
                "Questionamento de contratante sobre o vínculo",
            ],
        },
        "redirection_overrides": {
            "associação": "independencia juridica e autonomia institucional",
            "vínculo":    "relacoes contratuais formais e documentadas",
            "ligação":    "independencia operacional e governance",
            "sócio":      "estrutura societaria transparente e compliance",
        },
        "descricao_postura": {
            "desassociacao-documentada":     "PROVAR A AUSÊNCIA DE VÍNCULO. Documentos, contratos, distratos, atas. A verdade está nos papéis, não nas versões.",
            "desassociacao-narrativa":       "Construir narrativa de identidade própria. Reforçar quem a entidade É, não apenas quem ela NÃO É.",
            "esclarecimento-institucional":  "Posicionamento público claro sobre a natureza do vínculo. Sem defensividade — fato.",
            "blindagem-contratual":          "Revisar contratos, políticas de compliance e due diligence. Blindar a entidade contra futuras associações.",
            "reforco-compliance":            "Fortalecer políticas de compliance, due diligence e governança. Publicar como diferencial competitivo.",
            "consolidacao-compliance":       "Sistematizar e publicar práticas de compliance como referência setorial.",
        },
    },
}


# ── Resolução determinística com archetype ────────────────────────

def _resolve_posture(threat_level: str, source_concentration: str, legal_exposure: bool, archetype: str = "") -> str:
    """Resolve postura consultando o playbook do archetype, com fallback para matriz genérica."""
    if archetype and archetype in ARCHETYPE_PLAYBOOKS:
        pb = ARCHETYPE_PLAYBOOKS[archetype]
        key = (threat_level, source_concentration, legal_exposure)
        if key in pb["posture"]:
            return pb["posture"][key]
    return POSTURE_MATRIX.get((threat_level, source_concentration, legal_exposure), "consolidacao-autoridade")


def _resolve_visibility(threat_level: str, legal_exposure: bool, archetype: str = "") -> str:
    if archetype and archetype in ARCHETYPE_PLAYBOOKS:
        pb = ARCHETYPE_PLAYBOOKS[archetype]
        key = (threat_level, legal_exposure)
        if key in pb["visibility"]:
            return pb["visibility"][key]
    return VISIBILITY_MATRIX.get((threat_level, legal_exposure), "MODERADA")


def _resolve_temperature(threat_level: str, archetype: str = "") -> str:
    if archetype and archetype in ARCHETYPE_PLAYBOOKS:
        pb = ARCHETYPE_PLAYBOOKS[archetype]
        if threat_level in pb["temperature"]:
            return pb["temperature"][threat_level]
    return TEMPERATURE_MATRIX.get(threat_level, "MODERADA")


def _resolve_stakeholder_priority(threat_level: str, legal_exposure: bool, archetype: str = "") -> list[str]:
    if archetype and archetype in ARCHETYPE_PLAYBOOKS:
        pb = ARCHETYPE_PLAYBOOKS[archetype]
        key = (threat_level, legal_exposure)
        if key in pb["stakeholders"]:
            return pb["stakeholders"][key]
    return STAKEHOLDER_PRIORITY.get((threat_level, legal_exposure),
        ["Jurídico", "Parceiros", "Imprensa", "Investidores", "Público Geral"])


def _resolve_escalation_triggers(source_concentration: str, threat_level: str, archetype: str = "") -> list[str]:
    if archetype and archetype in ARCHETYPE_PLAYBOOKS:
        pb = ARCHETYPE_PLAYBOOKS[archetype]
        key = (source_concentration, threat_level)
        if key in pb.get("escalation", {}):
            return pb["escalation"][key]
    return ESCALATION_TRIGGERS.get((source_concentration, threat_level), [
        "Entrada de veículo de grande alcance nacional",
        "Novo resultado negativo indexado nos três primeiros resultados de busca",
        "Reação pública de stakeholder institucional",
        "Declaração não coordenada de porta-voz",
    ])


def _build_redirection_map(dominant_themes: str, archetype: str = "") -> str:
    themes_lower = dominant_themes.lower()
    # Base map
    matches = []
    for trigger, destination in REDIRECTION_MAP.items():
        if trigger in themes_lower:
            matches.append(f"{trigger} → {destination}")
    # Archetype overrides
    if archetype and archetype in ARCHETYPE_PLAYBOOKS:
        overrides = ARCHETYPE_PLAYBOOKS[archetype].get("redirection_overrides", {})
        for trigger, destination in overrides.items():
            if trigger in themes_lower:
                # Replace base match if exists
                matches = [m for m in matches if not m.startswith(trigger)]
                matches.append(f"{trigger} → {destination}")
    if not matches:
        return "Nenhum tema de alto risco identificado. Mapa de redirecionamento não aplicável no momento."
    return "\n".join(f"  • {m}" for m in matches)


def _resolve_asset_sequence(threat_level: str, archetype: str = "") -> list[dict]:
    if archetype and archetype in ARCHETYPE_PLAYBOOKS:
        pb = ARCHETYPE_PLAYBOOKS[archetype]
        if threat_level in pb.get("assets", {}):
            return pb["assets"][threat_level]
    return ASSET_SEQUENCE.get(threat_level, ASSET_SEQUENCE["MEDIUM"])


def _get_archetype_principio(archetype: str) -> str:
    if archetype in ARCHETYPE_PLAYBOOKS:
        return ARCHETYPE_PLAYBOOKS[archetype].get("principio", "")
    return ""


def _get_archetype_label(archetype: str) -> str:
    if archetype in ARCHETYPE_PLAYBOOKS:
        return ARCHETYPE_PLAYBOOKS[archetype].get("label", archetype)
    return archetype


def _get_posture_description(posture: str, archetype: str) -> str:
    if archetype and archetype in ARCHETYPE_PLAYBOOKS:
        desc = ARCHETYPE_PLAYBOOKS[archetype].get("descricao_postura", {})
        if posture in desc:
            return desc[posture]
    return ""


def _clean(text: str) -> str:
    text = re.sub(r"[^\x00-\x7F\u00C0-\u024F\u1E00-\u1EFF\n]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── Matrizes genéricas (fallback) ──────────────────────────────────

POSTURE_MATRIX: dict[tuple, str] = {
    ("CRITICAL", "legal",        True):  "institucional-defensivo",
    ("CRITICAL", "legal",        False): "baixa-visibilidade-estabilizacao",
    ("CRITICAL", "mainstream",   True):  "conciliatorio-com-clarificacao",
    ("CRITICAL", "mainstream",   False): "baixa-visibilidade-estabilizacao",
    ("CRITICAL", "blog",         True):  "institucional-defensivo",
    ("CRITICAL", "blog",         False): "deslocamento-narrativo",
    ("CRITICAL", "social",       True):  "baixa-visibilidade-estabilizacao",
    ("CRITICAL", "social",       False): "reforco-canal-proprio",
    ("HIGH",     "legal",        True):  "tecnico-juridico",
    ("HIGH",     "legal",        False): "tecnico-juridico",
    ("HIGH",     "mainstream",   True):  "institucional-defensivo",
    ("HIGH",     "mainstream",   False): "construcao-autoridade",
    ("HIGH",     "blog",         True):  "institucional-defensivo",
    ("HIGH",     "blog",         False): "deslocamento-narrativo",
    ("HIGH",     "social",       True):  "baixa-visibilidade-estabilizacao",
    ("HIGH",     "social",       False): "reforco-canal-proprio",
    ("MEDIUM",   "legal",        True):  "tecnico-juridico",
    ("MEDIUM",   "legal",        False): "baixa-visibilidade-estabilizacao",
    ("MEDIUM",   "mainstream",   True):  "institucional-defensivo",
    ("MEDIUM",   "mainstream",   False): "construcao-autoridade",
    ("MEDIUM",   "blog",         True):  "deslocamento-narrativo",
    ("MEDIUM",   "blog",         False): "deslocamento-narrativo",
    ("MEDIUM",   "social",       True):  "reforco-canal-proprio",
    ("MEDIUM",   "social",       False): "reforco-canal-proprio",
    ("LOW",      "legal",        True):  "tecnico-juridico",
    ("LOW",      "legal",        False): "consolidacao-autoridade",
    ("LOW",      "mainstream",   True):  "construcao-autoridade",
    ("LOW",      "mainstream",   False): "consolidacao-autoridade",
    ("LOW",      "blog",         True):  "consolidacao-autoridade",
    ("LOW",      "blog",         False): "consolidacao-autoridade",
    ("LOW",      "social",       True):  "reforco-canal-proprio",
    ("LOW",      "social",       False): "consolidacao-autoridade",
}

VISIBILITY_MATRIX: dict[tuple, str] = {
    ("CRITICAL", True):  "LOW",     ("CRITICAL", False): "LOW",
    ("HIGH",     True):  "LOW",     ("HIGH",     False): "MODERATE",
    ("MEDIUM",   True):  "MODERATE", ("MEDIUM",   False): "MODERATE",
    ("LOW",      True):  "MODERATE", ("LOW",      False): "HIGH",
}

TEMPERATURE_MATRIX: dict[str, str] = {
    "CRITICAL": "LOW", "HIGH": "MODERATE", "MEDIUM": "MODERATE", "LOW": "AGGRESSIVE",
}

STAKEHOLDER_PRIORITY: dict[tuple, list[str]] = {
    ("CRITICAL", True):  ["Jurídico", "Parceiros", "Investidores", "Imprensa", "Público Geral"],
    ("CRITICAL", False): ["Parceiros", "Jurídico", "Imprensa", "Investidores", "Público Geral"],
    ("HIGH",     True):  ["Jurídico", "Parceiros", "Imprensa", "Investidores", "Público Geral"],
    ("HIGH",     False): ["Parceiros", "Imprensa", "Investidores", "Jurídico", "Público Geral"],
    ("MEDIUM",   True):  ["Jurídico", "Parceiros", "Investidores", "Imprensa", "Público Geral"],
    ("MEDIUM",   False): ["Parceiros", "Imprensa", "Público Geral", "Investidores", "Jurídico"],
    ("LOW",      True):  ["Jurídico", "Parceiros", "Público Geral", "Imprensa", "Investidores"],
    ("LOW",      False): ["Imprensa", "Público Geral", "Parceiros", "Investidores", "Jurídico"],
}

ESCALATION_TRIGGERS: dict[tuple, list[str]] = {
    ("legal",       "CRITICAL"): [
        "Entrada de veículo Tier-1 (Folha, Globo, Estadão, Veja)",
        "Novo domínio jurídico indexado na página 1 do Google",
        "Aumento da razão negativa no top-3 de resultados",
        "Declaração pública não autorizada de porta-voz secundário",
    ],
    ("legal",       "HIGH"): [
        "Entrada de veículo Tier-1",
        "Novo domínio jurídico indexado na página 1",
        "Cobertura de TV ou rádio nacional",
    ],
    ("mainstream",  "CRITICAL"): [
        "Segunda cobertura negativa no mesmo veículo em menos de 7 dias",
        "Entrada de agências internacionais (Reuters, AP, Bloomberg)",
        "Repercussão em perfis de grande alcance nas redes sociais",
        "Reação pública de stakeholder institucional (órgão regulador, associação setorial)",
    ],
    ("mainstream",  "HIGH"): [
        "Segunda cobertura negativa no mesmo veículo",
        "Entrada de agências internacionais",
        "Menção em editorial ou coluna de opinião",
    ],
    ("blog",        "MEDIUM"): [
        "Pickup por veículo mainstream de publicação originalmente em blog",
        "Aumento de frequência: mais de 3 novos artigos em 7 dias",
        "Entrada em resultado de pesquisa de imagem ou vídeo",
    ],
    ("social",      "MEDIUM"): [
        "Viral orgânico acima de 10 mil compartilhamentos",
        "Pickup por jornalista verificado com mais de 50 mil seguidores",
        "Entrada em trending topics nacional ou setorial",
    ],
}

REDIRECTION_MAP: dict[str, str] = {
    "fraude":          "conformidade e governança",
    "corrupção":       "governança institucional",
    "investigação":    "cooperação institucional e transparência",
    "escândalo":       "modernização de processos e accountability",
    "processo":        "resolução jurídica e compromisso institucional",
    "crise":           "gestão de risco e resiliência organizacional",
    "polêmica":        "debate técnico e posicionamento fundamentado",
    "acusação":        "presunção de inocência e devido processo",
    "denúncia":        "apuração responsável e resposta institucional",
    "crime":           "rigor jurídico e separação de instâncias",
    "desvio":          "auditoria e controle interno",
    "superfaturamento":"eficiência e transparência orçamentária",
    "nepotismo":       "meritocracia e critérios objetivos de seleção",
    "lobby":           "representação institucional legítima",
}

ASSET_SEQUENCE: dict[str, list[dict]] = {
    "CRITICAL": [
        {"ativo": "Nota de Esclarecimento Jurídico", "janela": "Dia 1-2",  "objetivo": "Estabelecer posição factual antes que o vácuo seja preenchido por terceiros"},
        {"ativo": "Biografia Executiva",             "janela": "Dia 2-3",  "objetivo": "Controlar o resultado #1 da busca pelo nome com narrativa autorizada"},
        {"ativo": "Perfil Institucional",            "janela": "Dia 3-5",  "objetivo": "Ampliar ativos controlados na página 1 para deslocar resultados negativos"},
        {"ativo": "Roteiro de Entrevista",           "janela": "Dia 5-7",  "objetivo": "Preparar porta-voz para interações de imprensa inevitáveis"},
        {"ativo": "Artigo LinkedIn",                 "janela": "Semana 2", "objetivo": "Introduzir narrativa de posicionamento em canal próprio de alta autoridade"},
        {"ativo": "Press Release",                   "janela": "Semana 3", "objetivo": "Gerar cobertura neutra ou positiva para contrabalancear narrativa dominante"},
    ],
    "HIGH": [
        {"ativo": "Biografia Executiva",             "janela": "Dia 1-3",  "objetivo": "Fixar narrativa autorizada no topo da busca pelo nome"},
        {"ativo": "Artigo LinkedIn",                 "janela": "Dia 3-5",  "objetivo": "Criar ativo indexável de posicionamento em canal próprio"},
        {"ativo": "Perfil Institucional",            "janela": "Dia 4-7",  "objetivo": "Diversificar ativos controlados e reduzir vácuo de autoridade"},
        {"ativo": "Roteiro de Entrevista",           "janela": "Semana 2", "objetivo": "Preparar linguagem segura para contato com imprensa"},
        {"ativo": "Press Release",                   "janela": "Semana 2", "objetivo": "Distribuir narrativa positiva em canais de terceiros"},
        {"ativo": "Nota de Esclarecimento Jurídico", "janela": "Sob demanda", "objetivo": "Ativar apenas se exposição jurídica se materializar publicamente"},
    ],
    "MEDIUM": [
        {"ativo": "Artigo LinkedIn",                 "janela": "Dia 1-5",  "objetivo": "Iniciar produção de conteúdo de posicionamento em canal de alta autoridade"},
        {"ativo": "Biografia Executiva",             "janela": "Dia 3-7",  "objetivo": "Consolidar narrativa oficial em resultado de busca direta"},
        {"ativo": "Perfil Institucional",            "janela": "Semana 2", "objetivo": "Diversificar presença online com ativo indexável e controlado"},
        {"ativo": "Press Release",                   "janela": "Semana 2", "objetivo": "Gerar menções neutras em veículos setoriais"},
        {"ativo": "Roteiro de Entrevista",           "janela": "Semana 3", "objetivo": "Preparar linguagem para oportunidades de imprensa proativas"},
    ],
    "LOW": [
        {"ativo": "Artigo LinkedIn",                 "janela": "Dia 1-7",  "objetivo": "Fortalecer presença editorial em canal próprio de alta autoridade"},
        {"ativo": "Perfil Institucional",            "janela": "Semana 1", "objetivo": "Consolidar ativos de autoridade em buscas diretas"},
        {"ativo": "Biografia Executiva",             "janela": "Semana 2", "objetivo": "Atualizar e otimizar narrativa para buscas de nome"},
        {"ativo": "Press Release",                   "janela": "Semana 2", "objetivo": "Distribuir conquistas ou posicionamentos relevantes proativamente"},
    ],
}


# ── Função pública ─────────────────────────────────────────────────

def generate_response(
    entity_name: str,
    threat_level: str,
    narrative_state: str,
    dominant_themes: str,
    source_concentration: str,
    legal_exposure: bool,
    authority_vacuum: str,
    discovered_associations: str,
    threat_archetype: str = "",
) -> dict:
    """
    Resolve todas as decisões estratégicas deterministicamente,
    usando archetype como eixo primário e threat level como secundário.
    Depois chama o LLM apenas para redigir as 8 seções.
    """
    posture       = _resolve_posture(threat_level, source_concentration, legal_exposure, threat_archetype)
    visibility    = _resolve_visibility(threat_level, legal_exposure, threat_archetype)
    temperature   = _resolve_temperature(threat_level, threat_archetype)
    stakeholder_order = _resolve_stakeholder_priority(threat_level, legal_exposure, threat_archetype)
    triggers      = _resolve_escalation_triggers(source_concentration, threat_level, threat_archetype)
    redirection   = _build_redirection_map(dominant_themes, threat_archetype)
    asset_sequence = _resolve_asset_sequence(threat_level, threat_archetype)

    archetype_label = _get_archetype_label(threat_archetype)
    archetype_principio = _get_archetype_principio(threat_archetype)
    posture_desc = _get_posture_description(posture, threat_archetype)

    prompt_template = (PROMPTS_DIR / "response_strategy.txt").read_text(encoding="utf-8")
    prompt = prompt_template.format(
        entity_name            = entity_name,
        threat_level           = threat_level,
        narrative_state        = narrative_state,
        dominant_themes        = dominant_themes,
        source_concentration   = source_concentration,
        legal_exposure         = "Sim" if legal_exposure else "Não",
        authority_vacuum       = authority_vacuum,
        discovered_associations = discovered_associations or "Nenhuma associação crítica identificada.",
        recommended_posture    = posture,
        visibility_level       = visibility,
        response_temperature   = temperature,
        stakeholder_priority_order = " → ".join(stakeholder_order),
        escalation_triggers    = "\n".join(f"  • {t}" for t in triggers),
        redirection_map        = redirection,
        threat_archetype       = archetype_label,
        archetype_principio    = archetype_principio,
        posture_desc           = posture_desc,
    )

    response = call_openrouter(prompt, temperature=0.3)
    raw = response["choices"][0]["message"]["content"]
    text = _clean(raw)

    return {
        "text":                 text,
        "threat_archetype":     threat_archetype,
        "archetype_label":      archetype_label,
        "archetype_principio":  archetype_principio,
        "posture":              posture,
        "posture_desc":         posture_desc,
        "visibility":           visibility,
        "response_temperature": temperature,
        "stakeholder_order":    stakeholder_order,
        "escalation_triggers":  triggers,
        "redirection_map":      redirection,
        "asset_sequence":       asset_sequence,
    }


# ── Parser de seções ───────────────────────────────────────────────

RESPONSE_SECTION_PATTERNS = [
    ("postura_recomendada",    r"1\.\s+\**\s*POSTURA DE RESPOSTA RECOMENDADA\**"),
    ("estrategia_imediata",    r"2\.\s+\**\s*ESTRAT[EÉ]GIA DE RESPOSTA IMEDIATA\**"),
    ("mapa_redirecionamento",  r"3\.\s+\**\s*MAPA DE REDIRECIONAMENTO NARRATIVO\**"),
    ("linguagem_segura",       r"4\.\s+\**\s*LINGUAGEM SEGURA PARA PORTA-VOZES\**"),
    ("defesa_narrativa",       r"5\.\s+\**\s*ORIENTA[CÇ][AÃ]O DE DEFESA NARRATIVA\**"),
    ("mensagens_stakeholder",  r"6\.\s+\**\s*MENSAGENS POR STAKEHOLDER\**"),
    ("alertas_escalonamento",  r"7\.\s+\**\s*ALERTAS DE ESCALONAMENTO\**"),
    ("sequencia_ativos",       r"8\.\s+\**\s*SEQU[EÊ]NCIA DE DEPLOY DE ATIVOS\**"),
]


def parse_response_sections(text: str) -> dict:
    boundaries = []
    for key, pattern in RESPONSE_SECTION_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            boundaries.append((m.start(), m.end(), key))
    boundaries.sort()

    sections = {key: "" for key, _ in RESPONSE_SECTION_PATTERNS}
    for i, (start, end, key) in enumerate(boundaries):
        next_start = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
        body = text[end:next_start].strip()
        body = re.sub(r"^#+\s*", "", body, flags=re.MULTILINE)
        body = re.sub(r"^\*\*.*?\*\*\s*$", "", body, flags=re.MULTILINE)
        body = re.sub(r"^---+\s*$", "", body, flags=re.MULTILINE)
        sections[key] = body.strip()
    return sections
