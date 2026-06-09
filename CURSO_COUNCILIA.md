# COUNCILIA — Curso de Formação Operacional

## `Domínio Completo do Software de Inteligência Reputacional`

---

**Público-alvo**: Operador do sistema (você) que vai vender, conduzir auditorias e executar estratégias para clientes.

**Pré-requisito**: Nenhum. O curso parte do zero conceitual e constrói até o domínio operacional completo.

**Formato**: Assíncrono, autoinstrucional. Cada módulo tem: conceito → demonstração → exercício → verificação.

**Carga horária total estimada**: 24 horas (8 módulos × 3 horas cada)

---

# MÓDULO 0 — FUNDAÇÃO CONCEITUAL

## O que é Reputação Digital (e por que ela é mensurável)

### 0.1 A Equação Fundamental

```
Reputação Digital ≠ Imagem
Reputação Digital = O que o Google diz que você é
```

Reputação tradicional é o que as pessoas pensam de você. Reputação digital é o que a **primeira página do Google** mostra quando pesquisam seu nome. São duas coisas diferentes.

Uma pessoa pode ter uma imagem positiva no mundo real e uma reputação digital destruída — porque o Google indexou um processo, uma notícia negativa, um blog de denúncia. E vice-versa.

**CouncilIA trabalha com a reputação digital mensurável.** Não com opinião, não com percepção — com SERP (Search Engine Results Page), que é um fato objetivo.

### 0.2 O Google como Campo de Batalha

Toda busca por um nome próprio produz uma página de resultados. Esses resultados são:

| Tipo | Exemplo | Autoridade (1-10) | Controlável? |
|---|---|---|---|
| Jurídico | JusBrasil, Conjur, STF | 8-10 | NÃO |
| Mainstream | Folha, Globo, Veja, UOL | 7-10 | NÃO |
| Redes sociais | LinkedIn, Instagram, Twitter | 8-9 | PARCIAL |
| Blogs setoriais | Portais de notícias locais | 3-6 | PARCIAL |
| Controlado | Site próprio, LinkedIn Articles | 5-9 | SIM |

A guerra de reputação é sobre **qual tipo de resultado domina a primeira página**. Um resultado jurídico (JusBrasil) tem autoridade altíssima e é quase impossível de remover. O jogo é **ocupar as outras posições com conteúdo controlado** para diluir o impacto.

### 0.3 O Conceito de Vácuo de Autoridade

```
Vácuo de Autoridade = a soma de espaços na página 1 que a entidade
                       não controla e que terceiros ocupam
```

Se seu cliente não tem site, não tem LinkedIn ativo, não tem artigo publicado — o Google vai preencher a página 1 com o que encontrar. E o que encontra geralmente é: processos, notícias negativas, blogs de reclamação.

**O vácuo é o principal problema.** Não a existência de resultados negativos — mas a ausência de resultados positivos para contrabalançá-los.

### 0.4 Métricas Essenciais

| Métrica | O que significa | Fórmula |
|---|---|---|
| **NPA** (Nível de Pressão Agregado) | Pressão reputacional geral (0-100) | Soma ponderada de negative share, autoridade negativa, momentum, domínios jurídicos |
| **Negative Share** | % de resultados negativos na página 1 | Posições negativas ÷ 10 × 100 |
| **Controlled Assets** | Quantos resultados a entidade controla | Posições com domínio controlado |
| **Tier-1 Dominance** | Quantos Tier-1 negativos | Veículos de elite com conteúdo negativo |
| **Legal Domain Count** | Quantos domínios jurídicos | JusBrasil, STF, etc. |
| **Narrative Saturation** | % de cobertura negativa por domínio | Artigos negativos ÷ total no domínio |
| **YouTube Toxicity** | Pressão de vídeos negativos no YouTube (0-100) | Posições YouTube negativas (30pts) + posição média (25pts) + saturação (25pts) + severidade (20pts) |
| **YouTube NPA Boost** | Multiplicador 1.2× sobre o impacto de vídeos negativos no NPA | `base_npa_impact × 1.2` — vídeos têm CTR 2-5× maior que texto |
| **Knowledge Panel Score** | Probabilidade de ter Knowledge Panel no Google (0-100) | Consistência nome (15) + Wikipedia (25) + schema.org (20) + NAP (15) + LinkedIn (15) + Crunchbase (10) |
| **Crisis Stage** | Estágio atual da crise reputacional | BREAKING / ESCALATING / SATURATED / DECAYING / ARCHIVED / STABLE |
| **Recovery Probability** | Chance de recuperar página 1 em 90 dias (0-98%) | 9 fatores ponderados: dominância tier-1 (18%) + saturação (15%) + permanência legal (14%) + Wikipedia (12%) + YouTube (12%) + ativos (10%) + momentum (8%) + persistência (6%) + autoridade (5%) |
| **News Occupation Score** | % de controle sobre o ecossistema Google News (0-100) | Cobertura positiva (30pts) + releases controlados (25pts) + autoridade dos portais (20pts) + velocidade de indexação (15pts) + saturação de portais (10pts) |

---

**EXERCÍCIO 0.1**: Pesquise seu próprio nome no Google em janela anônima. Classifique cada resultado da página 1 nos tipos acima. Calcule seu Negative Share. Quantos resultados você controla?

---

# MÓDULO 1 — ARQUITETURA DO SISTEMA

## O Que Cada Peça Faz e Como Elas se Conectam

### 1.1 Mapa da Arquitetura

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              COUNCILIA SYSTEM                                   │
│                                                                                 │
│  ENTRADAS                     PROCESSAMENTO                           SAÍDAS   │
│  ───────                     ─────────────                           ──────   │
│                                                                                 │
│  SERPAPI (Google) ──┐                                                        │
│  GNews          ────┤                                                        │
│  Firecrawl      ────┤──→ audit_service.py ──→ snapshot (JSON)                │
│  OpenRouter     ────┤                                                        │
│  Expansion      ────┘                                                        │
│                                                                                 │
│  ┌──────── SNAPSHOT ────────┐                                                  │
│  │                         │                                                  │
│  │  serp_dominance.py ─────┤──→ Toxicity Gauge + Position War Map            │
│  │  battle_planner.py ─────┤──→ War Room + YouTube + KP + LinkedIn          │
│  │  crisis_stage.py ───────┤──→ Stage Classification (BREAKING→STABLE)       │
│  │  recovery_probability.py─┤──→ 9-Factor Recovery Score                     │
│  │  response_service.py ───┤──→ Playbook do Arquétipo                        │
│  │  occupation_service.py ──┤──→ Asset Strategy Timeline                     │
│  │  knowledge_panel.py ────┤──→ KP Score + Wikidata + Schema.org             │
│  │  youtube_warfare.py ────┤──→ YouTube Toxicity + Scripts + Ads             │
│  │  news_distribution.py ──┤──→ Portal Selection + Release Payload           │
│  │  linkedin_targeting.py ─┤──→ LinkedIn Ads + Stakeholder Matrix            │
│  │  content_producer.py ───┤──→ 7 Article Types                              │
│  │  site_builder.py ───────┤──→ Static Site (HTML)                           │
│  │  monitoring_engine.py ──┤──→ SERP/News Watcher + Alerts (file-based)      │
│  └─────────────────────────┘                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 As 5 APIs Externas

| API | Função | Custo por chamada | Limitação |
|---|---|---|---|
| **SERPAPI** | Busca no Google (top 20 orgânicos) | ~$0.01 | 100 buscas/mês no plano grátis |
| **GNews** | Notícias recentes | Grátis | 100 requisições/dia |
| **Firecrawl** | Scrape de página (conteúdo do #1) | ~$0.01 | 500 páginas/mês grátis |
| **OpenRouter** | LLM (DeepSeek R1) | ~$0.10-0.30 | Pago por token |
| **Expansion** | GNews + SERPAPI internos | Custo das chamadas internas | N/A |

### 1.3 O Snapshot — O Coração do Sistema

O snapshot é um arquivo JSON salvo em `snapshots/{entidade}/{data}.json`. Ele contém:

```json
{
  "entity": "Nome da Entidade",
  "threat_level": "CRITICAL",
  "threat_archetype": "criminal",
  "crisis_state": "active_crisis",
  "npa_score": 78.5,
  "page_1_negative_ratio": 0.7,
  "top_3_negative_count": 2,
  "legal_domain_count": 3,
  "dominated_domain": "jusbrasil.com.br",
  "source_concentration": "legal",
  "serp": [ ... resultados enriquecidos com is_video ... ],
  "narrative_pressure": { "momentum": "Escalating", "count_7d": 12 },
  "negative_domains": [ ... ],
  "associations": { "entities": [ ... ] },
  "youtube_toxicity": 65,          // 0-100, presente se há vídeos na SERP
  "video_npa_boost": 1.5,          // multiplicador se vídeos negativos presentes
  "video_count": 3,                // quantos resultados YouTube na SERP
  "kp_score": 42,                  // 0-100, inferido da SERP
  "generated_at": "2026-05-17T..."
}
```

Além do JSON, a cada auditoria o sistema gera um **screenshot automático** da SERP em `snapshots/{slug}/serp_{data}.png` — uma página estilizada como Google com os resultados reais, capturada via Playwright (sem CAPTCHA).

**TODO** módulo downstream lê **deste mesmo snapshot**. Eles não refazem chamadas externas. A consistência dos dados é garantida.

### 1.4 Os Serviços Downstream — 20 Módulos no Total

| # | Serviço | Arquivo | O que faz |
|---|---|---|---|
| 1 | SERP Dominance | `serp_dominance.py` | Gauge de toxidade, war map de posições, clusters |
| 2 | Battle Planner | `battle_planner.py` | Plano de guerra com 14 seções (orgânico + pago + YouTube + KP + LinkedIn) |
| 3 | Crisis Stage | `crisis_stage.py` | Classifica crise em 6 estágios + configura estratégia por estágio |
| 4 | Recovery Probability | `recovery_probability.py` | 9 fatores → 0–98% de chance de recuperação |
| 5 | Response Strategy | `response_service.py` | Playbook de 8 seções por arquétipo |
| 6 | Occupation Strategy | `occupation_service.py` | Fases de ocupação por arquétipo |
| 7 | Knowledge Panel | `knowledge_panel.py` | Score KP, Wikidata, schema.org JSON-LD |
| 8 | YouTube Warfare | `youtube_warfare.py` | Toxidade YouTube, scripts de vídeo, campanhas de ads |
| 9 | News Distribution | `news_distribution.py` | Seleção de portais, release payload, news occupation score |
| 10 | LinkedIn Targeting | `linkedin_targeting.py` | Segmentação por arquétipo, plano de campanhas, matriz de stakeholders |
| 11 | Content Producer | `content_producer.py` | Geração de 7 tipos de artigo + Motor de Variação Semântica (6 enquadramentos) |
| 12 | Asset Service | `asset_service.py` | Tipos de ativo, campanhas de amplificação |
| 13 | Site Builder | `site_builder.py` | Site estático a partir do cache de artigos |
| 14 | Monitoring Engine | `monitoring_engine.py` | Background asyncio loop (5min), atomic writes, SMTP email, auto-reaudit, pruning |
| 15 | Distribution Engine | `distribution_engine.py` | **75 plataformas** + Persistence Score + AI Citation + Narrative Blast + Quick Publish + Publish Assist (39 guias) + newswire wrappers |
| 16 | PDF Service | `pdf_service.py` | Geração de PDF (relatório + comparação) via fpdf2 |
| 17 | SERP Screenshot | `serp_screenshot.py` | Renderização sintética da SERP + captura via Playwright |
| 18 | Post-Audit Pipeline | `post_audit_pipeline.py` | Geração automática de conteúdo por threat_level |
| 19 | Health & Status | `api/routes/automation.py` | `/health`, `/status`, `/api/credentials/check` |
| 20 | Retry & Resilience | SerpAPI/OpenRouter/Firecrawl | Exponential backoff 2-8s |

### 1.5 O Cache de Artigos

`saves/` e `articles_cache/{slug}/{asset_type}.json`

Quando você gera artigos, eles ficam em cache. O site builder lê do cache. **Gerar tudo uma vez → build site instantâneo depois.**

### 1.6 O Que é Automático vs. O Que é Manual

Nem tudo o que o sistema faz é publicação. Aqui está o mapa exato do que é automático e o que exige ação humana.

#### O que o sistema faz sozinho

| Ação | Como |
|---|---|---|
| Medir SERP (quem está na página 1, posição, sentimento) | `/dominance` |
| Analisar crise (stage, archetype, recovery probability) | `/battle-plan`, `/recovery` |
| Recomendar o que produzir e em que ordem | Battle Plan — seções orgânica + paga |
| Gerar o texto completo de cada ativo | `/content` — botão "Gerar" |
| Gerar press release formatado para cada portal | `/news-distribution` |
| Gerar roteiro de vídeo YouTube | `/content/generate-video` |
| Gerar conteúdo automaticamente por threat level | Post-Audit Pipeline (MEDIUM=2, HIGH/CRITICAL=7+YouTube) |
| Formatar o payload de envio por portal (email, API, formulário) | `/news-distribution/{slug}/send` |
| Publicar via API (Medium, LinkedIn, WordPress, EIN Presswire) | `/quick-publish/{slug}` — com dry-run |
| Comparar SERP antes vs depois | `/snapshots` — compare |
| Gerar PDF do relatório | `/pdf` — botão no relatório |
| Gerar PDF de comparação | `/snapshots/{slug}/compare/pdf` |
| Capturar screenshot da SERP | Automático a cada auditoria |
| Monitorar SERP em background (5min) | Asyncio loop — sem cron |
| Enviar email de alerta | SMTP real (Gmail configurável) |
| Reauditar automaticamente em CRÍTICO | Monitoring Engine |
| Verificar status do sistema | `/health`, `/status`, `/api/credentials/check` |
| Guias de publicação manual (39 plataformas) | `/publish-assist/{slug}` |

#### O que você faz manualmente

| Ação | Por quê não é automático |
|---|---|---|
| Publicar LinkedIn Articles completo | API só suporta UGC feed posts, não Articles |
| Publicar no Medium (status=draft) | API só cria rascunho — clicar Publish no painel |
| Publicar em portais editoriais (ConJur, Migalhas, Valor) | Editorial independente — email manual |
| Enviar o release por email | Email parte de você, não do sistema |
| Chamar a API paga (EIN Presswire, MaxPress, PRWeb) | Requer API key paga do cliente |
| Gravar o vídeo YouTube | O sistema gera o roteiro, a câmera é sua |
| Criar o Google Ads / LinkedIn Ads | Requer acesso à conta de anúncios do cliente |
| Subir o site no Netlify | Arrastar a pasta, 2 minutos |
| Criar Wikidata / implementar schema.org | Requer acesso ao site e wiki do cliente |
| Indexar URLs no Google Search Console | Login Google do cliente necessário |

#### O fluxo real com um cliente

```
SISTEMA FAZ:                          VOCÊ FAZ:
─────────────                         ─────────
1. Auditar → snapshot                 
2. Analisar → battle plan             
3. Gerar artigos automaticamente      (se MEDIUM+) pelo Post-Audit Pipeline
4. Gerar artigo LinkedIn    →         5. Revisar e publicar no LinkedIn
6. Gerar press release      →         7. Enviar email para ConJur/Migalhas
8. Gerar roteiro YouTube    →         9. Gravar e publicar o vídeo
10. Build site              →         11. Subir no Netlify
12. Gerar 6 variações semânticas →    13. Publicar variações em canais diferentes
14. Quick Publish via API   →         15. Configurar .env + revisar dry-run
16. Publish Assist (39 guias) →       17. Seguir passo a passo para plataformas manuais
18. Narrative Blast 30d     →         19. Executar as ações na sequência correta
20. Monitorar em background  →        21. Verificar alertas (email automático)
22. Reauditar em CRÍTICO    →         23. Revisar nova auditoria gerada
24. Nova auditoria em 30d   →         25. Ver screenshots antes/depois na comparação
26. Baixar PDF do relatório  →        27. Enviar PDF ao cliente
```

#### Sobre "novas notícias para cada ação"

O sistema gera **um release por ação recomendada** — isso é real. O que ele não faz é garantir que o portal vai publicar. Você envia, o portal decide.

Para garantir indexação no Google News você precisa:

1. **Portais gratuitos** (Migalhas, ConJur, Segs): enviar email manualmente com o texto gerado pelo sistema
2. **Portais pagos** (MaxPress, PRWeb): pagar pelo plano, depois o sistema gera o JSON de envio pronto

**O sistema resolve 80% do trabalho intelectual** — diagnóstico, estratégia, texto, formatação. Os 20% restantes são execução humana nos canais externos.

---

**EXERCÍCIO 1.1**: Abra o snapshot mais recente do `tiago_schiettini_batista`. Identifique: threat_level, threat_archetype, crisis_state, npa_score, negative_ratio. Compare com o que você vê na interface.

---

# MÓDULO 2 — OPERAÇÃO: AUDITORIA

## Como Conduzir uma Auditoria do Zero

### 2.1 Fluxo de Auditoria

```
1. ACESSAR
   http://localhost:8000/
   
2. DIGITAR
   Nome completo da entidade (ex: "João Silva")
   
3. AGUARDAR
   30-60 segundos (SERPAPI + GNews + Firecrawl + OpenRouter + Expansion)
   
   4. RECEBER
   Relatório completo com:
   - Sumário Executivo (LLM)
   - Sinais Negativos (domínios, threat level)
   - Ativos Positivos
   - NPA Score + decomposição
   - Associacões Descobertas (Expansion)
   - Mapa de Domínios
   - Diretrizes Operacionais
   
5. BAIXAR PDF
   Botão "PDF" no canto do relatório → relatório profissional
   
6. SCREENSHOT
   Automático — salvo em snapshots/{slug}/serp_{data}.png
   Visível na comparação antes/depois
```

### 2.2 O Que Acontece nos Bastidores (Ordem Exata)

```python
# audit_service.py — sequência real de chamadas:
1. serpapi_service.search(entity, num=20)      # Google → 20 resultados
2. firecrawl_service.scrape(serp[0].url)       # Conteúdo do #1
3. gnews_service.search(entity)                 # Até 10 notícias
4. enrichment: nomes alternativos + top-4 associações
5. gnews_service.search(compound_query)         # Busca enriquecida
6. serpapi_service.search(compound_query, num=10) # SERP enriquecida
7. expansion_service: descobre entidades ocultas (12h TTL cache)
8. openrouter_service.call(prompt_analise)      # LLM analisa tudo
9. snapshot_service.save()                      # Persiste
```

### 2.3 O Que Ler no Relatório

#### a) Threat Level (CRITICAL / HIGH / MEDIUM / LOW)

| Nível | Quando | Negative Share | Ação |
|---|---|---|---|
| CRITICAL | ≥50% negativos OU ≥2 jurídicos + escalada | ≥50% | Emergência. Responder em dias. |
| HIGH | ≥30% negativos OU ≥1 jurídico | 30-50% | Prioridade. Ocupação necessária. |
| MEDIUM | Entre 10-30% negativos, sem jurídico crítico | 10-30% | Prevenção. Construir autoridade. |
| LOW | <10% negativos, sem ameaça real | <10% | Manutenção. Reforço de ativos. |

#### b) Threat Archetype

**ESTA É A INFORMAÇÃO MAIS IMPORTANTE DO RELATÓRIO.**

O arquétipo determina o playbook operacional. Não confunda:

- **Criminal**: investigação, processo criminal, operação policial → silêncio estratégico, jurídico primeiro
- **Reputacional**: escândalo corporativo, crise de marca → ocupação narrativa, branding
- **Político**: agente público, figura política → coalizão, imprensa, guerra narrativa
- **Mídia**: veículo de comunicação → gestão de pauta, correção editorial
- **Administrativo**: órgão público, servidor → transparência, documentos, procedimentos
- **Associativo**: risco por vínculo com terceiro → desassociação documentada, blindagem

#### c) Crisis Stage — O Novo Padrão (6 Estágios)

O snapshot antigo usava `crisis_state` com 3 valores. O sistema atual classifica em **6 estágios determinísticos**:

| Estágio | Gatilho | Estratégia |
|---|---|---|
| **BREAKING** | 1+ artigo nos últimos 7d + momentum escalando + CRITICAL | Defensivo máximo. Silêncio + jurídico |
| **ESCALATING** | 3+ artigos em 7d + escalando + neg_ratio ≥0.3 | Containment ativo. Produzir notas + FAQ |
| **SATURATED** | 5+ artigos em 7d + escalando + neg_ratio ≥0.5 | SEO amplification. Ocupar todas as frentes |
| **DECAYING** | Momentum declinando + neg_ratio ≥0.3 | Manutenção. Monitorar + sustentar ativos |
| **ARCHIVED** | Sem artigos recentes + neg_ratio <0.3 | Vigilância. Prevenir reativação |
| **STABLE** | Nenhum dos acima | Construção de autoridade. Reforço contínuo |

**O Crisis Stage drive todas as decisões downstream**: tipo de anúncio, tom da comunicação, visibilidade, prioridade de stakeholders, cadência de produção.

#### d) YouTube Toxicity Score

Se a entidade tem vídeos do YouTube nos resultados da página 1, o sistema calcula:

- **YouTube Toxicity (0-100)**: 4 componentes — contagem de vídeos negativos (30pts), posição média (25pts), saturação negativa (25pts), severidade de posição (20pts)
- **NPA Boost**: Se há vídeos negativos, o NPA recebe um multiplicador de **1.2×** sobre o impacto desses vídeos — porque vídeos têm CTR 2-5× maior que resultados de texto e thumbnail visual

O YouTube é tratado como um campo de batalha separado dentro da guerra de SERP.

#### e) Knowledge Panel Score

Score inferido da SERP (0-100) que estima a probabilidade de a entidade ter ou poder ter um Knowledge Panel no Google. Baseado em 6 componentes: consistência do nome (15pts), presença Wikipedia (25pts), schema.org readiness (20pts), consistência NAP (15pts), LinkedIn (15pts), Crunchbase (10pts).

#### f) NPA Score

```
0-20:   Verde  — pressão mínima
20-40:  Amarelo — atenção
40-60:  Laranja — pressão moderada
60-80:  Vermelho — pressão alta
80-100: Preto — pressão crítica
```

### 2.4 O Segredo #1: Vácuo é Pior que Ameaça

Um cliente com NPA 40 mas controlled_assets = 0 (zero ativos próprios na página 1) está **mais vulnerável** que um cliente com NPA 60 mas controlled_assets = 3.

Por quê? Porque o vácuo significa que QUALQUER novo resultado negativo vai ocupar espaço desocupado. O cliente sem ativos próprios não tem "amortecedor".

**Na venda**: não foque só na crise. Foque no vácuo. "O senhor não tem NADA na primeira página do Google. Se amanhã surgir uma notícia negativa, ela vai ocupar posição #1 sem concorrência."

---

**EXERCÍCIO 2.1**: Faça auditoria de uma entidade real (pode ser você, um amigo, um cliente potencial). Anote: threat_level, threat_archetype, crisis_state, NPA, negative_share, controlled_assets. Escreva um parágrafo de diagnóstico.

---

# MÓDULO 3 — OPERAÇÃO: DOMINÂNCIA E BATTLE PLAN

## Lendo o Campo de Batalha e Planejando a Guerra

### 3.1 SERP Dominance — Leitura do Gauge

`GET /dominance/{slug}`

A página de dominância mostra:

1. **SERP Toxicity Gauge (0-100)**: Ringue SVG verde → amarelo → vermelho. Não é o NPA — é a **toxidade específica da SERP**, ponderada por authority dos domínios negativos.

2. **Domain Clusters**: Quem está ocupando o quê.
   ```
   jusbrasil.com.br:    4 posições (1, 3, 5, 7) — peso 40%
   folha.uol.com.br:    2 posições (2, 4)       — peso 25%
   linkedin.com:        1 posição (8)            — peso 12%
   ```
   O peso considera: posição + authority + negative/positive.

3. **Position War Map**: Ranking #1 a #20. Cada resultado com:
   - Posição
   - Domínio + authority score
   - Sentimento (positivo / negativo / neutro)
   - Tipo (mainstream / jurídico / controlado / social / blog)
   - Se é controlado pela entidade

### 3.2 Battle Plan — As 14 Seções da Guerra

`GET /battle-plan/{slug}`

O battle plan agora tem 14 seções. As seções 1-10 são do núcleo original; as seções 11-14 são as novas frentes de batalha.

#### Seção 1: Dificuldade de Deslocamento

Cada resultado da página 1 recebe uma classificação:

| Dificuldade | O que significa | Tempo estimado | Recuperável? |
|---|---|---|---|
| **EASY** | Blog, site de baixa autoridade, resultado antigo | 15-30 dias | SIM — outranking com SEO |
| **MEDIUM** | Portal setorial, LinkedIn de terceiros | 30-60 dias | SIM — requer conteúdo + backlinks |
| **HARD** | Veículo mainstream, rede social de alto DA | 60-90 dias | SIM — requer ads + conteúdo sustentado |
| **VERY_HARD** | JusBrasil, STF, CGU, Wikipedia | Permanente | **NÃO** — estratégia é supressão, não remoção |

**O SEGREDO #2**: VERY_HARD não se remove. Se o cliente pergunta "consegue tirar do JusBrasil?", a resposta honesta é não. O que se faz é:
1. Não tentar remover (impossível)
2. Ocupar as posições 2-10 com conteúdo controlado
3. O resultado VERY_HARD vira uma "ilha" cercada de conteúdo positivo
4. Com o tempo, o CTR do VERY_HARD cai porque as pessoas veem opções melhores

#### Seção 2-3: Guerra Orgânica vs Defesa Paga

```
GUERRA ORGÂNICA                    DEFESA PAGA
─────────────────                  ────────────
SEO de longo prazo                 Google Ads imediato
Custa: tempo + conteúdo            Custa: R$/clique
Autoridade permanente              Visibilidade temporária
Ideal para: EASY + MEDIUM          Ideal para: HARD + VERY_HARD
Resultado em 30-90 dias            Resultado em horas
```

**Nunca venda apenas um dos dois.** A guerra orgânica SEM defesa paga = demora demais. A defesa paga SEM guerra orgânica = para quando o orçamento acaba.

#### Seção 4: Search Intent

Cada termo de busca tem uma intenção. O battle plan classifica:

| Intent | Exemplo | Landing page ideal |
|---|---|---|
| **branded** | "João Silva", "João Silva empresa" | Perfil institucional / LinkedIn |
| **hostile** | "João Silva fraude", "João Silva processo" | FAQ / Esclarecimento Jurídico |
| **institutional** | "João Silva site oficial" | Site institucional |
| **crisis** | "João Silva escândalo" | Nota oficial / Press release |
| **professional** | "João Silva currículo", "João Silva cargo" | LinkedIn / Biografia |

#### Seção 5-6: Saturation e Asset Gap

**Saturação**: quantos artigos negativos cada domínio publicou. Domínio com saturação ALTA = campanha coordenada contra a entidade.

**Asset Gap**: o que existe vs o que precisaria existir.
```
Ativos necessários: 6 (artigo, bio, perfil, release, FAQ, jurídico)
Ativos existentes:  2 (LinkedIn, site)
GAP: 4 ativos → prioridade: FAQ > Perfil > Artigo > Bio
```

#### Seção 7: Recovery Probability (Nova Fórmula de 9 Fatores)

```
RecProb = 0.90 — penalidade ponderada + bônus de ativos controlados

Fatores e pesos:
  Tier-1 Dominance (neg):     18%  — veículos Tier-1 com conteúdo negativo
  Saturation (neg):           15%  — saturação narrativa
  Legal Permanence (neg):     14%  — domínios jurídicos permanentes
  Wikipedia Contamination:    12%  — presença negativa na Wikipedia
  Video Toxicity:             12%  — YouTube toxity (1.5x NPA)
  Controlled Assets (bônus):  10%  — cada ativo controlado recupera pontos
  Momentum (neg):              8%  — escalando vs declinando
  Indexed Persistence (neg):   6%  — quanto tempo os negativos estão indexados
  Domain Authority (neg):      5%  — autoridade média dos domínios negativos

Saída:
  probability_pct: 0-98% (nunca 100% — sempre há risco residual)
  level: VERY_HIGH / HIGH / MEDIUM / LOW / VERY_LOW
  estimated_time: "30-60 dias" / "60-90 dias" / "90-180 dias" / "+180 dias"
  estimated_budget: faixa de investimento em R$
  difficulty: resolvível / desafiador / muito difícil / crítico
  banda_de_confiança: ±8pp (VERY_HIGH) / ±15pp (MEDIUM) / ±20pp (VERY_LOW)

Exemplo: CRITICAL + 4 VERY_HARD + 1 controlled + HIGH saturation + YouTube videos negativos
  = 42% de probabilidade de recuperação em 90 dias
  ±15pp de banda de confiança
  Breakeven estimado: 60 dias
```

**O SEGREDO #3**: Recovery Probability é a ferramenta de venda mais poderosa. "O senhor tem 42% de chance de recuperar a página 1 em 90 dias. Com o plano que estou propondo, isso sobe para 68%."

#### Seção 8: Crisis Stage Strategy

O crisis stage detectado na auditoria drive as configurações do battle plan:

| Stage | Ads Mode | Tom | Visibilidade | Ativo Principal | Cadência |
|---|---|---|---|---|---|
| BREAKING | DEFENSIVO MÁXIMO | Silêncio jurídico | Baixíssima | Nota jurídica | Imediata (horas) |
| ESCALATING | CONTAINMENT | Defensivo | Baixa | Esclarecimento | Diária |
| SATURATED | SEO AMPLIFICATION | Neutro-institucional | Média | FAQ / Artigo | Semanal |
| DECAYING | MAINTENANCE | Neutro | Média-alta | Release positivo | Quinzenal |
| ARCHIVED | VIGILÂNCIA | Neutro | Alta | Biografia | Mensal |
| STABLE | BUILD AUTHORITY | Proativo | Alta | Perfil completo | Mensal |

**Isso significa que o mesmo cliente com NPA 60 em estágio ESCALATING recebe um tratamento COMPLETAMENTE DIFERENTE de um cliente com NPA 60 em estágio DECAYING.**

#### Seção 9: Timeline 30/60/90

| Fase | Orgânico | Pago | Marco |
|---|---|---|---|
| 0-30 dias | Produzir 6 artigos + 1 roteiro YouTube, publicar site, SEO on-page | Google Ads brand defense + LinkedIn Ads | 2 ativos na página 1 |
| 30-60 dias | Guest posts, Medium cross-pub, backlinks, distribuir release | LinkedIn Ads profissional, expandir termos | 4 ativos na página 1 |
| 60-90 dias | SEO continuado, FAQ rich snippets, newsletter, YouTube ads | Manter ads, otimizar landing pages | 6 ativos, negative share <40% |

#### Seção 10: KPIs

| KPI | Início | 30 dias | 60 dias | 90 dias |
|---|---|---|---|---|
| Negative Share | 70% | 55% | 40% | 30% |
| Controlled Assets | 1 | 3 | 5 | 6 |
| SERP Toxicity | 82 | 65 | 48 | 35 |
| YouTube Toxicity | 65 | 50 | 35 | 20 |
| News Occupation Score | 15 | 35 | 55 | 70 |
| Authority Score | 2.1 | 3.4 | 4.8 | 6.0 |
| Top-3 Negativos | 3 | 2 | 1 | 1 |

#### Seção 11: YouTube Warfare — O Campo de Batalha dos Vídeos

`GET /youtube/{slug}`

YouTube é um campo de batalha separado porque:
- **CTR 2-5× maior** que texto — thumbnail visual ocupa mais espaço
- **Domain Authority 100** — youtube.com é o segundo maior site do mundo
- **Featured no Google** — vídeos aparecem em carrossel e posição #0
- **Dwell time maior** — usuário passa minutos no YouTube vs segundos no texto

O sistema detecta automaticamente resultados do YouTube na SERP e calcula:

```
YouTube Toxicity (0-100):
  Contagem de vídeos negativos:  30pts  — cada vídeo negativo soma
  Posição média negativa:         25pts  — weighted por posição
  Saturação negativa:             25pts  — % negativos entre todos vídeos
  Severidade de posição:          20pts  — top-3 penalizado extra

NPA Boost: 1.5× sobre o impacto dos vídeos negativos no NPA total
```

**4 tipos de roteiro de vídeo** que o sistema gera:

| Tipo | Quando usar | Duração | Estrutura |
|---|---|---|---|
| **Posicionamento Institucional** | Crise ativa, precisa de declaração pública | 5 min | Hook → Contexto → Resposta → Autoridade → CTA |
| **Esclarecimento** | Narrativa negativa precisa ser corrigida publicamente | 5 min | Hook → Contexto → Resposta → Autoridade → CTA |
| **Trajetória** | Sem crise ativa, construir autoridade | 5 min | Hook → Contexto → Resposta → Autoridade → CTA |
| **FAQ** | Responder perguntas frequentes (otimizado para featured snippet) | 5 min | Hook → Contexto → Resposta → Autoridade → CTA |

**Campanhas de YouTube Ads** geradas automaticamente:

| Tipo | Formato | Duração | CPM Estimado |
|---|---|---|---|
| TrueView In-Stream | Skipável após 5s | 15-30s | R$ 15-30 |
| Discovery Ads | Na busca e relacionados | Título + descrição | R$ 12-25 |
| Bumper Ads | Não-skipável | 6s | R$ 20-40 |

**Asset template**: `asset_templates/roteiro_youtube.md` — estrutura completa com SEO (título, descrição 500+ palavras, tags, timestamps, thumbnail) e equipamento mínimo.

#### Seção 12: Knowledge Panel Engineering — O Perfil Oficial do Google

`GET /knowledge-panel/{slug}`

O Knowledge Panel é a "caixa" que aparece no lado direito do Google quando você pesquisa uma entidade. Ter um Knowledge Panel bem construído significa que o Google **reconhece oficialmente** a entidade e mostra informações controladas.

O sistema infere da SERP o **Knowledge Panel Score (0-100)**:

| Componente | Peso | O que verifica |
|---|---|---|
| Consistência do Nome | 15pts | O nome aparece igual em todos os resultados |
| Wikipedia | 25pts | Entidade tem artigo na Wikipedia |
| Schema.org Readiness | 20pts | Site da entidade tem schema.org/Person |
| NAP Consistency | 15pts | Nome, Endereço, Telefone consistentes |
| LinkedIn | 15pts | Perfil LinkedIn verificado/institucional |
| Crunchbase | 10pts | Perfil no Crunchbase |

**Setup Guide (6 passos gerados pelo sistema):**

```
1. Wikidata → Criar perfil WikiData → links oficiais → fontes
   [STATUS: ausente / criado / revisado]

2. Wikipedia → Redigir artigo → cumprir WP:Notability → revisão
   [STATUS: ausente / em rascunho / publicado]

3. NAP → Padronizar nome/telefone/endereço em todos os canais
   [STATUS: inconsistente / parcial / consistente]

4. Schema.org → Inserir JSON-LD schema.org/Person no <head>
   [STATUS: ausente / implementado]

5. Search Console → Reivindicar Knowledge Panel → enviar documentação
   [STATUS: pendente / reivindicado]

6. Foto + Redes → Foto oficial consistente → links de redes sociais
   [STATUS: fotos inconsistentes / parcial / completo]
```

O sistema também gera:
- **Wikidata Profile**: texto Wikidata-ready com label, description, aliases, statements, references
- **Schema.org JSON-LD**: código para colar no `<head>` do site institucional
- **FAQ Schema**: FAQPage JSON-LD para featured snippets

#### Seção 13: LinkedIn Ads Targeting — Segmentação por Arquétipo

`GET /linkedin-ads/{slug}`

Diferente de Google Ads (que defende termos de busca), o LinkedIn Ads **atinge pessoas específicas** — cargos, empresas, setores. A segmentação é derivada do **arquétipo da ameaça**, não do threat level.

| Arquétipo | Funções-alvo | Senioridade | Indústrias | CPM Estimado |
|---|---|---|---|---|
| Criminal | Sócios, jurídico, compliance, risco | Director+ | Legal, financeiro, seguros | R$ 55-85 |
| Reputacional | CEO, VP Marketing, PR, RI | VP+ | Todos os setores relevantes | R$ 45-75 |
| Político | Chief of Staff, comunicação, jurídico | Gerente+ | Público, político, ONGs | R$ 50-80 |
| Mídia | Editor, pauta, ombudsman, chefe de redação | Coordenador+ | Mídia, jornalismo | R$ 35-65 |
| Administrativo | Procurador, controlador, auditor, secretário | Diretor+ | Público, jurídico | R$ 45-70 |
| Associativo | Sócio, diretor jurídico, relações institucionais | Gerente+ | Todos (dependente do caso) | R$ 40-70 |

**Campanhas geradas pelo sistema:**

1. **Brand Awareness** (reach objective) — visibilidade ampla para o perfil institucional
2. **Engagement** (engagement objective) — conteúdo patrocinado com artigo de posicionamento
3. **Account-Based** (se houver target_companies) — segmentação por empresa específica

**Matriz de Exposição por Stakeholder**: 4 grupos por arquétipo com relevância (1-10), descrição de cobertura e mensagem sugerida.

#### Seção 14: News Distribution — Ocupação do Google News

`GET /news-distribution/{slug}`

Google News tem mecânicas de ranking diferentes do Google orgânico: **frescor** (notícias recentes), **autoridade do portal** (domínio), **volume de sindicação** (quantos portais republicam).

O sistema mantém um banco de **10 portais brasileiros** categorizados por setor e arquétipo:

| Portal | Setor | Método | Velocidade | Autoridade |
|---|---|---|---|---|
| Segs | Jurídico/Administrativo | Free | 24h | 6/10 |
| Mercado & Consumidor | Economia/Negócios | Free | 24-48h | 7/10 |
| MaxPress | Geral | Paid API | 2-4h | 7/10 |
| AION | Jurídico | Free | 24h | 5/10 |
| Migalhas | Jurídico | Free | 24h | 8/10 |
| ConJur | Jurídico | Free | 24h | 9/10 |
| Brasil 247 | Política/Geral | Free | 12-24h | 6/10 |
| PRWeb | Geral | Paid API | 2-4h | 7/10 |
| StartupBase | Startup/Tech | Email | 48-72h | 4/10 |

**Seleção determinística**: o sistema seleciona portais por matching de arquétipo (+3pts), setor (+2pts), autoridade (+1pt/10).

**News Occupation Score (0-100)**: métrica paralela ao SERP Occupation Score, avaliando:
| Componente | Peso | Descrição |
|---|---|---|
| Cobertura positiva | 30pts | % de notícias positivas no Google News |
| Releases controlados | 25pts | Quantos portais publicaram o release |
| Autoridade dos portais | 20pts | Média de authority dos portais que publicaram |
| Velocidade de indexação | 15pts | Tempo médio entre envio e publicação |
| Saturação de portais | 10pts | Diversidade de portais vs repetição do mesmo |

**Release Payload**: para cada portal, o sistema gera o formato correto (JSON para API, corpo de email para free, formulário para web).

---

**EXERCÍCIO 3.1**: Abra o battle plan do Tiago Schiettini. Identifique: quantos VERY_HARD, qual a recovery probability, qual o asset gap, qual o crisis stage. Depois abra o /youtube/tiago-schiettini — há vídeos negativos? Qual o YouTube Toxicity? E o /knowledge-panel/tiago-schiettini — qual o KP Score? Qual o primeiro passo do setup guide?

---

# MÓDULO 4 — OPERAÇÃO: RESPOSTA E OCUPAÇÃO

## O Playbook do Arquétipo — A Peça Central

### 4.1 Response Strategy — 8 Seções Operacionais (Ajustadas por Crisis Stage)

`GET /response` → formulário → POST → 8 seções

O formulário pergunta:
- Entidade, threat level, narrative state, dominant themes
- Source concentration, legal exposure, authority vacuum, associations
- **Arquétipo** (dropdown ou automático do snapshot)
- **Crisis Stage** (automático do snapshot — mas pode ser sobrescrito manualmente)

O sistema resolve **tudo deterministicamente** (sem LLM) antes de gerar:

```python
# O LLM só redige — as decisões são aritméticas E influenciadas pelo crisis stage:
posture       = f(archetype, threat, concentration, legal, crisis_stage)
visibility    = f(archetype, threat, legal, crisis_stage)
temperature   = f(archetype, threat, crisis_stage)
stakeholders  = f(archetype, threat, legal, crisis_stage)
asset_order   = f(archetype, threat, crisis_stage)
escalation    = f(archetype, concentration, threat, crisis_stage)
redirection   = f(archetype, dominant_themes, crisis_stage)
```

**Exemplo**: Um cliente criminal em BREAKING recebe `silêncio absoluto + jurídico exclusivo`. O mesmo cliente criminal em DECAYING recebe `construção de autoridade setorial`. Mesmo arquétipo, mesma ameaça — estágio diferente, resposta diferente.

#### As 8 Seções:

| # | Seção | O que contém |
|---|---|---|
| 1 | Postura Recomendada | O que fazer, o que NÃO fazer, por quê |
| 2 | Estratégia Imediata 0-7d | Ações ordenadas por prioridade |
| 3 | Mapa de Redirecionamento | Tema atual → Tema desejado → Mecanismo |
| 4 | Linguagem Segura | Para entrevista, imprensa, stakeholders internos |
| 5 | Defesa Narrativa | Evitar / Negar / Reforçar / Redirecionar |
| 6 | Mensagens por Stakeholder | Mensagem + canal + timing para cada público |
| 7 | Alertas de Escalonamento | Gatilhos + sinais + ações |
| 8 | Sequência de Deploy de Ativos | Ordem + janela + objetivo |

### 4.2 Os 6 Playbooks de Arquétipo — O CONHECIMENTO SECRETO

Abaixo está o que **nenhum concorrente tem**. O que diferencia um relatório genérico de uma engine operacional.

#### Playbook 1: CRIMINAL

```
Princípio: "Conter vazamento narrativo. Toda comunicação passa 
            pelo jurídico. Zero reatividade."
            
CRITICAL + legal + mainstream → contencao-juridica-absoluta
Visibilidade: BAIXISSIMA
Temperatura: FRIA

O que significa:
- SILÊNCIO ESTRATÉGICO. Porta-voz ÚNICO (advogado externo).
- Nenhuma declaração pública sem aprovação do jurídico.
- Nota jurídica breve, sem admissão de culpa.
- Reafirmar cooperação com autoridades.
- Produzir conteúdo TÉCNICO setorial (não sobre o caso).
- FAQ de transparência SEM menção ao caso criminal.

Sequência de ativos:
  1. Manifestação Jurídica Oficial (Dia 1)
  2. Nota de Esclarecimento Jurídico (Dia 1-2)
  3. FAQ de Transparência (Dia 2-4)
  4. Perfil Institucional Enxuto (Dia 3-5)
  5. Roteiro de Porta-Voz Jurídico (Dia 5-7)
  6. Press Release pós-posição jurídica (Semana 3)

Stakeholders (ordem):
  Jurídico Criminal → Advogados Externos → Sócios
  → Assessoria Jurídica → Imprensa (via jurídico)

Gatilhos de escalonamento:
  - Entrada de inquérito/operação policial
  - Condução coercitiva ou busca e apreensão
  - Prisão de pessoa ligada à entidade
  - Matéria de capa em Tier-1
  - Repercussão em CPI

Erro fatal: falar com a imprensa sem o jurídico.
```

#### Playbook 2: REPUTACIONAL (Corporativo)

```
Princípio: "Ocupar espaço narrativo. Silêncio é derrota. 
            Produzir, distribuir, amplificar."

CRITICAL + mainstream + sem jurídico → ocupacao-narrativa-agressiva
Visibilidade: ALTA
Temperatura: AGRESIVA

O que significa:
- PRODUZIR E DISTRIBUIR. Silêncio não é opção.
- Artigo de posicionamento imediato no LinkedIn.
- Press release distribuído em 24h.
- Campanha de Google Ads brand defense no DIA 1.
- Entrevistas proativas com veículos simpáticos.

Sequência de ativos:
  1. Artigo LinkedIn — Posicionamento (Dia 1)
  2. Press Release Oficial (Dia 1-2)
  3. Perfil Institucional Atualizado (Dia 2-3)
  4. FAQ de Transparência (Dia 3-5)
  5. Roteiro de Entrevista para CEO (Dia 3-5)
  6. Google Ads brand defense (Dia 1-3)

Erro fatal: ficar em silêncio esperando a crise passar.
```

#### Playbook 3: POLÍTICO

```
Princípio: "Base política e coalizão em primeiro lugar. 
            Imprensa é campo de batalha, não auditório."

CRITICAL + mainstream + sem jurídico → guerra-narrativa
Visibilidade: ALTA
Temperatura: AGRESIVA

O que significa:
- MOBILIZAR BASE. Ativar rede de apoiadores.
- Produzir contra-narrativa imediatamente.
- Ocupar todos os canais — redes, imprensa, rua.
- Silêncio é rendição política.

Sequência de ativos:
  1. Nota Política Oficial (Horas)
  2. Artigo de Posicionamento (Dia 1)
  3. Roteiro de Entrevista (Dia 1-2)
  4. Mobilização de Base (Dia 1-2)
  5. Perfil Institucional Atualizado (Dia 2-4)
  6. Press Release para Veículos Simpáticos (Semana 1)

Erro fatal: tentar agradar a todos. Política exige lados.
```

#### Playbook 4: MÍDIA (Veículo de Comunicação)

```
Princípio: "Gestão de pauta é a chave. A crise de um veículo 
            é sua própria pauta virada contra ele."

O que significa:
- CONTROLAR A NARRATIVA SOBRE O VEÍCULO.
- Não deixar concorrentes pautarem sua crise.
- Transparência sobre o erro (quando aplicável).
- Correção pública quando necessário.

Erro fatal: tratar a crise como se fosse com outro veículo.
```

#### Playbook 5: ADMINISTRATIVO

```
Princípio: "Transparência e procedimento. A crise administrativa 
            se combate com documentos, não com versões."

O que significa:
- DOCUMENTOS ACIMA DE VERSÕES.
- Publicar editais, contratos, pareceres.
- A verdade administrativa está nos arquivos.
- Posicionamento público com dados, não com opiniões.

Erro fatal: dar versão política para crise administrativa.
```

#### Playbook 6: ASSOCIATIVO

```
Princípio: "Desassociação documentada em primeiro lugar. O risco 
            não é da entidade — é da associação indevida a terceiros."

O que significa:
- PROVAR A AUSÊNCIA DE VÍNCULO.
- Documentos, contratos, distratos, atas.
- A verdade está nos papéis, não nas versões.
- Reforçar identidade própria.
- Revisar contratos para blindagem futura.

Este é o playbook do Tiago Schiettini (association_based).
Seu risco não é por ação própria — é por associação a terceiros.

Erro fatal: agir como se a crise fosse reputacional (playbook 2)
quando na verdade é associativa. Ocupação narrativa agressiva
num caso associativo pode chamar MAIS atenção para o vínculo.
```

### 4.3 Occupation Strategy — Fases por Arquétipo

`GET /occupation/{slug}`

A estratégia de ocupação é dividida em 3 fases que MUDAM por arquétipo:

| Arquétipo | Fase 1 | Fase 2 | Fase 3 |
|---|---|---|---|
| Criminal | Contenção Jurídica | Estabilização | Reocupação |
| Reputacional | Defesa de Marca | Ocupação | Autoridade |
| Político | Blindagem de Base | Estabilização | Projeção |
| Mídia | Gestão de Pauta | Correção | Credibilidade |
| Administrativo | Transparência | Regularização | Conformidade |
| Associativo | Desassociação | Blindagem Contratual | Compliance |

Cada fase tem ativos específicos, timing e métricas de sucesso.

---

**EXERCÍCIO 4.1**: Pegue o snapshot do Tiago Schiettini (association_based). Agora finja que você mudou o arquétipo para "reputacional" manualmente no formulário de response. O que muda na postura? Na sequência de ativos? Nos stakeholders? Simule e anote as diferenças.

---

# MÓDULO 5 — OPERAÇÃO: PRODUÇÃO E PUBLICAÇÃO

## Do Artigo ao Site no Ar

### 5.1 Content Studio — 7 Tipos de Ativo

`GET /content/{slug}`

Grade com **7 ativos** (6 originais + 1 novo). Cada um tem:

| Ativo | Tipo | Plataforma |
|---|---|---|
| Artigo LinkedIn | Posicionamento Profissional | LinkedIn Articles |
| Perfil Institucional | Institucional | Site próprio |
| Biografia | Profissional | Site / Wikipedia |
| Esclarecimento Jurídico | Jurídico | Site |
| FAQ de Transparência | FAQ | Site (schema.org) |
| Press Release | Crise | Distribuição para portais |
| **Roteiro YouTube** | **Vídeo** | **YouTube (produção externa)** |

O ativo **Roteiro YouTube** gera um script completo de 5 minutos com:
- Hook (0-30s): abertura que prende atenção
- Contexto (30s-2min): cenário e motivação
- Resposta (2-4min): posicionamento ou esclarecimento
- Autoridade (4-5min): credenciais e facts
- CTA (5min): chamada para ação

Além do script, o sistema gera SEO completo (título, descrição 500+ palavras, tags, timestamps, thumbnail specs) e instruções de equipamento mínimo.

### 5.2 O Que um Artigo Contém

Quando você gera um artigo, recebe:

```json
{
  "asset_type": "artigo_linkedin",
  "entity_name": "Entidade",
  "label": "Artigo LinkedIn — Posicionamento Profissional",
  "article": "texto completo do artigo em markdown...",
  "body_md": "versão limpa do markdown para APIs...",
  "seo": {
    "title": "Título SEO (máx 70 chars)",
    "meta_description": "Descrição (máx 160 chars) com nome completo",
    "slug": "entidade-artigo-linkedin",
    "tags": ["nome-completo-em-ascii", "tag2", "tag3"],
    "suggested_filename": "entidade-artigo_linkedin.html"
  },
  "platform": {
    "platform": "LinkedIn Articles",
    "url": "linkedin.com/pulse",
    "type": "social_professional",
    "setup_time": "5 min (conta existente)",
    "steps": [...]
  },
  "amplification": { ... }
}
```

**Garantias de qualidade do conteúdo gerado:**
- **System Prompt em PT-BR** — separado do template, garante output em português independente do idioma do contexto
- **Nome completo 5× no corpo** — densidade de marca validada automaticamente
- **H1/H2 structure** — headings semânticos em todos os templates
- **JSON-LD** — Person ou FAQPage inserido no artigo quando aplicável
- **body_md** — campo extra para APIs que exigem markdown puro (Medium, WordPress)
- **Tags SEO**: nome completo em ASCII (sem acentos) para indexação no Google
- **Conteúdo non-commodity** — POV único, exemplos específicos, dados verificáveis

### 5.3 O Segredo #4: O Artigo é Sobre o Contexto, Não Sobre a Entidade

A qualidade do artigo gerado depende do **contexto estratégico** alimentado para o LLM. O `produce_article()` constrói um contexto rico a partir do battle plan:

```python
def _build_rich_context(entity_name, asset_type, plan):
    # Injeta no prompt:
    # - Nível de ameaça
    # - SERP toxicity
    # - Negative share
    # - Domínios negativos dominantes
    # - Domínios controlados existentes
    # - Displacement difficulty
    # - Search intent mapping
    # - Asset gap
    # - Archetype do playbook
```

**Quanto melhor o snapshot, melhor o artigo.** Se o audit foi pobre, o artigo será genérico.

### 5.4 Build Site — Instantâneo

`POST /content/{slug}/build-site`

Após gerar os artigos (uma vez), o build-site é INSTANTÂNEO:

```
1. Lê todos os artigos do cache
2. Gera homepage (grid com todos)
3. Gera página individual para cada artigo
4. Gera _deploy_instructions.txt
5. Salva em content_sites/{slug}/
6. Retorna preview
```

**O site é estático.** Zero backend. Zero banco. Zero manutenção. Só HTML.

### 5.5 News Distribution — Colocar nos Portais

`GET /news-distribution/{slug}`

Após gerar o Press Release no Content Studio:

1. Acesse o dashboard de News Distribution
2. Veja os **portais selecionados** automaticamente por arquétipo + setor
3. Escolha um portal no dropdown
4. Cole o release (máx 3000 caracteres)
5. Clique "Gerar Payload" → o sistema formata o conteúdo para o método do portal
6. **Execute manualmente** o envio (API, email ou formulário) — o sistema não envia automaticamente

**Workflow completo de distribuição:**

```
1. Content Studio → Gerar Press Release
2. News Distribution → Gerar Payload para cada portal
3. Enviar manualmente (API key / email / formulário web)
4. Monitorar → /monitor/{slug} → News Watcher detecta novas publicações
5. News Occupation Score aumenta conforme portais publicam
```

### 5.6 Publicação via API — Quick Publish

`GET /quick-publish/{slug}`

Após gerar os artigos no Content Studio:

1. Acesse o dashboard de Quick Publish
2. Veja o **status das credenciais** configuradas no .env:
   - Medium token → status "ok" ou "setup_required"
   - LinkedIn token → status "ok" ou "setup_required"
   - WordPress credentials → status "ok" ou "setup_required"
   - EIN Presswire API key → status "ok" ou "setup_required"
3. Selecione um artigo em cache + uma plataforma compatível
4. Clique **"Preview"** para ver o conteúdo formatado (dry-run)
5. Revise o preview — especialmente para newswires pagas (EIN Presswire cobra por envio)
6. Clique **"Publicar"** para enviar via API

**Resultados possíveis:**
- **Medium**: rascunho criado — "Aceder ao painel e clicar Publish"
- **LinkedIn**: feed post publicado (UGC Post, não Article completo)
- **WordPress**: draft criado — publicar manualmente no painel
- **EIN Presswire**: release submetido para distribuição (requer `EIN_CONTACT_EMAIL`)

### 5.7 Publicação Manual — Publish Assist

`GET /publish-assist/{slug}`

Para plataformas sem API (portais editoriais, YouTube, Substack, etc.):

1. Acesse o dashboard de Publish Assist
2. O sistema detecta a **região** automaticamente (BR/PT/ES) pelo snapshot
3. Filtra **plataformas prioritárias** pelo arquétipo da entidade
4. Para cada plataforma, o sistema mostra:
   - Guia passo a passo com links diretos
   - Conteúdo formatado para copiar e colar
   - SEO impact estimado (ALTO/MÉDIO/BAIXO)
   - Advertências importantes
5. Siga as instruções em cada guia para publicar manualmente

**39 guias de publicação** cobrindo todos os tipos de plataforma — de LinkedIn Articles a ConJur, Migalhas, Valor Econômico, YouTube, Substack, HackerNoon, etc.

### 5.8 LinkedIn Ads — Campanhas para o Perfil

`GET /linkedin-ads/{slug}`

1. Abra o dashboard de LinkedIn Ads Targeting
2. Verifique a **segmentação gerada** (job functions, titles, seniorities, industries, interests)
3. Confira o **CPM estimado** e o **tamanho de audiência**
4. Revise a **estrutura de campanhas** (Brand Awareness + Engagement + Account-Based)
5. Crie as campanhas manualmente no LinkedIn Campaign Manager
6. Use a **Matriz de Exposição por Stakeholder** para definir mensagens por público

### 5.12 YouTube — Produção do Vídeo

Após gerar o roteiro no Content Studio (`/content/{slug}/generate-video`):

1. Siga o template em `asset_templates/roteiro_youtube.md`
2. Grave seguindo a estrutura: Hook → Contexto → Resposta → Autoridade → CTA
3. Edite com thumbnail e timestamps (especificações no template)
4. Publish no YouTube (não listado ou público, conforme estratégia)
5. Cross-publish: YouTube → Medium Article (embed) → Site (embed) → LinkedIn
6. Ative YouTube Ads (TrueView / Discovery / Bumper) conforme campanha gerada

**Automação**: se `threat_level ≥ HIGH`, o roteiro YouTube é gerado **automaticamente** pela Post-Audit Pipeline — sem precisar clicar em "Gerar". Basta revisar e gravar.

---

**EXERCÍCIO 5.1**: Gere um artigo e um roteiro de vídeo para o Tiago Schiettini. Depois abra o News Distribution e veja quais portais foram selecionados. Qual a diferença entre o release para o Segs e para o ConJur?

---

# MÓDULO 6 — ANÁLISE E INTERPRETAÇÃO

## Como Ler os Resultados e Tomar Decisões

### 6.1 O Ciclo de Medição

```
1. DIA 0: Auditar → snapshot → baseline
2. DIA 30: Auditar de novo → comparar + verificar monitoramento
3. DIA 60: Auditar de novo → comparar + verificar monitoramento
4. DIA 90: Auditar de novo → comparar + verificar monitoramento
```

O sistema tem `compare_snapshots()` que mostra a diferença entre duas auditorias:
- NPA aumentou ou diminuiu?
- Negative share mudou?
- Controlled assets aumentaram?
- Novo domínio jurídico apareceu?
- Algum VERY_HARD foi deslocado?
- YouTube Toxicity mudou?
- News Occupation Score evoluiu?
- **SERP screenshot antes vs depois** — evidência visual lado a lado
- **PDF de comparação** disponível para download

### 6.2 Continuous Monitoring — Background Asyncio Loop

`O monitoramento roda automaticamente em background — sem necessidade de cron.`

O módulo de monitoramento contínuo **inicia com o servidor** via asyncio loop e verifica cada entidade monitorada a cada 5 minutos.

**Estado salvo em**: `monitoring/{slug}/state.json` — com atomic writes (`os.replace()`) para evitar corrupção.

**6 triggers de alerta**:

| Trigger | Nível | Condição |
|---|---|---|
| Novo domínio negativo na SERP | CRÍTICO | Domínio nunca visto antes aparece na página 1 |
| Domínio jurídico detectado | CRÍTICO | Domínio .jus.br ou similar aparece |
| Mudança no top-3 | ALTO | Posições 1-3 mudaram de sentimento |
| Novo artigo no Google News | MÉDIO | GNews retorna artigo novo para a entidade |
| Cobertura positiva detectada | INFO | Artigo com sentimento positivo no GNews |
| Salto de NPA | ALTO | Delta ≥10 pontos desde último check |

**O que o monitoramento verifica em cada check**:

```
check_serp():   SERPAPI → novos domínios negativos, jurídicos, top-3 contaminado
check_news():   GNews → artigos novos, cobertura positiva  
check_npa_delta(): calcula diferença do NPA atual vs último snapshot
```

**Quando um trigger dispara**, o sistema pode:
1. Registrar o alerta no state.json (sempre)
2. Enviar email via SMTP real (Gmail configurável — `COUNCILIA_SMTP_USER` / `COUNCILIA_SMTP_PASS`)
3. Reauditar automaticamente se o alerta for CRÍTICO
4. Pruning automático: estado limpo após 90 dias
5. Disparar webhook Slack (se configurado)

**Configuração** (via dashboard):

```
Configure Monitoring:
  - Entidade a monitorar
  - Email para alertas
▼ Configuração automática:
  - Frequência: 5 minutos em background (asyncio loop)
  - Sem necessidade de cron / Task Scheduler
  - Alerta CRÍTICO → reauditoria automática
  - Pruning automático após 90 dias
```

**Para usar**: basta acessar `/status` ou `/health` para verificar se o monitor está ativo. O loop começa automaticamente com o servidor.

### 6.3 O Que Monitorar Semanalmente

| O que | Como | Frequência |
|---|---|---|
| SERP toxicity gauge | `/dominance/{slug}` | Semanal |
| Posições dos ativos controlados | Verificar no Google manualmente | Semanal |
| Alertas do monitoramento | Email automático + `/status` | Contínuo (background 5min) |
| YouTube Toxicity | `/youtube/{slug}` | Semanal |
| News Occupation Score | `/news-distribution/{slug}` | Semanal |
| Knowledge Panel | `/knowledge-panel/{slug}` | Quinzenal |
| Novos resultados negativos | `/snapshots` → comparar | Quinzenal |
| CTR dos anúncios | Google Ads dashboard | Semanal |
| Cliques orgânicos | Google Search Console | Mensal |
| Status do servidor | `/health` | Diário |
| Credenciais das APIs | `/api/credentials/check` | Semanal |

### 6.4 O Segredo #5: A Queda do Gauge é o Argumento de Venda

Quando você faz uma nova auditoria após 30 dias de trabalho e o NPA caiu de 72 para 58, isso é **prova mensurável de resultado**. Print do gauge antes/depois é o melhor material de venda que existe.

Guarde o snapshot inicial como "baseline" e use a comparação como relatório de evolução para o cliente.

### 6.5 Quando Escalonar

Os gatilhos de escalation do response strategy dizem **quando mudar de estratégia**:

- Saiu matéria Tier-1? → Ativar protocolo de crise
- Novo domínio jurídico? → Revisar FAQ + notificação ao jurídico
- Novo vídeo negativo no YouTube? → Ativar YouTube Ads + produzir roteiro de resposta
- Alerta CRÍTICO no monitoramento? → Revisar estratégia imediatamente
- Cliente deu declaração não autorizada? → Conter + alinhar porta-voz
- Viralizou nas redes? → Ativar defesa paga + mobilização

---

**EXERCÍCIO 6.1**: Configure o monitoramento para o Tiago Schiettini: acesse `/monitor/tiago-schiettini`, execute um check, veja os triggers. Depois simule 30 dias de trabalho: que métricas você esperaria ver mudar (NPA, YouTube Toxicity, News Occupation, KP Score)? Quais NÃO mudariam (por quê)?

---

# MÓDULO 7 — VENDA DO SERVIÇO

## Como Posicionar, Precificar e Fechar

### 7.1 O Discurso de Venda

#### O Problema (abrir a porta)

> "O senhor já pesquisou o próprio nome no Google hoje?"

Esta pergunta abre 100% das conversas. A resposta é quase sempre "não" ou "faz tempo".

> "Pesquise agora. O que aparece na primeira página?"

A partir daí, o Google está aberto na frente de vocês dois. Não tem argumento contra o que está na tela.

#### O Diagnóstico (gratuito, 30 segundos)

Na primeira reunião, você abre o sistema e faz uma auditoria ao vivo:

> "Vou rodar uma análise aqui. Em 30 segundos temos um diagnóstico."

Enquanto o sistema processa, você explica o que está acontecendo:

> "Estou consultando 5 fontes diferentes: o Google, as notícias, o conteúdo do primeiro resultado, a deep web de associações, e uma inteligência artificial que cruza tudo."

Quando o relatório aparece:

> "Aqui está. O Nível de Pressão Agregado do senhor é 72 — isso é pressão alta. A página 1 do Google tem 70% de resultados negativos. Três domínios jurídicos. E o senhor controla ZERO resultados."

#### A Solução (o plano)

> "Existe um processo para reverter isso. Não é milagre — é engenharia. Ocupar a página 1 com conteúdo controlado, na sequência certa, no timing certo, com amplificação certa."

Mostre o battle plan:

> "Aqui está o plano: 30/60/90 dias. Quanto tempo para ocupar cada posição. Quanto investimento em conteúdo orgânico. Quanto em anúncios. Qual a probabilidade de recuperação. Quais os KPIs em cada fase."

#### O Fechamento

> "O investimento é X. O resultado projetado é reduzir o negative share de 70% para 30% em 90 dias. A cada mês, fazemos uma nova auditoria para medir. Se não mudar, paramos e revisamos. Mas muda."

### 7.2 Precificação Sugerida

| Item | Custo mensal sugerido |
|---|---|---|
| Auditoria única (diagnóstico) | R$ 1.500 - 3.000 |
| Mensalidade operação + monitoramento | R$ 5.000 - 15.000 |
| Produção de conteúdo (6 artigos/mês) | R$ 3.000 - 8.000 |
| **Produção de roteiro YouTube + vídeo** (1 vídeo/mês) | **R$ 3.000 - 8.000** |
| **Distribuição em portais Google News** (até 5 portais) | **R$ 2.000 - 5.000** |
| **LinkedIn Ads gestão** (criação + otimização) | **R$ 1.500 - 4.000 + verba de mídia** |
| Site jornalístico + deploy | R$ 2.000 - 5.000 (one-time) |
| Gestão de Google Ads (brand defense) | R$ 1.000 - 3.000 + verba de mídia |
| **Continuous Monitoring setup + alertas** | **R$ 1.000 - 3.000 (one-time) + R$ 500/mês** |
| Consultoria estratégica (playbook) | R$ 3.000 - 8.000/mês |
| **Pacote completo premium (recomendado)** | **R$ 15.000 - 35.000/mês** |

### 7.3 Os 9 Argumentos que Fecham Venda

| # | Argumento | Contra o quê |
|---|---|---|---|
| 1 | "A primeira página do Google é seu currículo público" | "Não preciso disso" |
| 2 | "Seu concorrente já está ocupando esse espaço" | "Vou pensar" |
| 3 | "Vacuo é pior que ameaça — não ter nada é ter a página 1 à disposição de quem quiser" | "Não tenho crise" |
| 4 | "Crise não avisa. Quando chegar, a página 1 já está ocupada por conteúdo controlado" | "Não tenho crise agora" |
| 5 | "O sistema mede antes e depois — não é achismo, é dado" | "Isso funciona?" |
| 6 | "90 dias. Se em 90 dias o NPA não caiu, paramos" | "E se não der certo?" |
| 7 | **"Seu nome tem vídeo negativo no YouTube — vídeo tem 3× mais chance de ser visto que texto"** | **"YouTube não é problema"** |
| 8 | **"O Google News pode ser ocupado com releases — seus concorrentes já estão lá"** | **"Não preciso de notícia"** |
| 9 | **"Monitoramento contínuo detecta crise em horas, não em semanas"** | **"Eu fico de olho"** |

### 7.4 Perfil de Cliente Ideal

| B2B | B2C |
|---|---|
| Empresas com reputação sensível | Executivos C-Level |
| Escritórios de advocacia | Políticos e candidatos |
| Clínicas e hospitais | Profissionais liberais de alto escalão |
| Instituições financeiras | Pessoas com exposição pública |
| Órgãos públicos | Influenciadores |
| Startups em crescimento acelerado | Empresários com busca ativa |

**O cliente ideal tem**: NPA > 40 + controlled_assets < 3 + orçamento para investir 3+ meses.

### 7.5 O Segredo #6: O Diagnóstico é a Venda

Nunca feche uma venda sem mostrar o sistema AO VIVO. A auditoria ao vivo (30 segundos) é o melhor fechador. Quando o cliente vê o próprio nome no relatório com NPA, negative share, domínios jurídicos — a decisão está tomada.

**O sistema é o vendedor.** Você só opera.

---

**EXERCÍCIO 7.1**: Prepare um script de 5 minutos para uma reunião de venda. Inclua: abertura (pergunta do Google), diagnóstico ao vivo, solução (o plano), fechamento (preço + prazo). Grave-se apresentando.

---

# MÓDULO 8 — OPERAÇÃO AVANÇADA

## Técnicas, Truques e Casos de Borda

### 8.1 Limpeza de Cache Forçada

Às vezes o OpenRouter retorna um artigo ruim. Para regenerar:

```bash
# Deletar o cache do artigo específico
Remove-Item articles_cache/{slug}/{asset_type}.json

# Ou deletar tudo e regenerar
Remove-Item articles_cache/{slug} -Recurse
```

Depois: gere novamente no Content Studio.

### 8.2 Mudança Manual de Arquétipo

Se a classificação automática errou o arquétipo, você pode forçar manualmente no formulário de Response. Basta selecionar o arquétipo correto no dropdown.

**Quando fazer isso:**
- O snapshot classificou como "criminal" mas é claramente "reputacional" (sem investigação criminal real)
- O snapshot classificou como "reputacional" mas há risco associativo não detectado
- O cliente tem múltiplos arquétipos (ex: político com risco criminal)

### 8.3 Execução Offline (Sem APIs)

Se as APIs estiverem indisponíveis, o sistema ainda funciona para leitura:

- `/dominance/{slug}` — lê do snapshot
- `/battle-plan/{slug}` — lê do snapshot
- `/content/{slug}/build-site` — lê do cache de artigos

Apenas auditoria nova e geração de artigos exigem APIs.

### 8.4 O Segredo #7: O Site é Isca, Não Destino

O site jornalístico gerado NÃO é o destino final. É **isca**. Você publica no site para ter um link controlado para indexar. Mas o tráfego mesmo vem de:

1. **Google Ads**: cliques pagos → landing page do site
2. **LinkedIn Articles**: publicação cruzada com link para o site
3. **Medium**: cross-publication com canonical link para o site
4. **Release**: distribuído com link para o site
5. **FAQ**: schema.org/FAQPage → featured snippet → clique

O site é o hub central, mas a distribuição é o que gera resultado.

### 8.5 Crisis Stage Override Manual

Se a classificação automática do crisis stage errou, você pode forçar manualmente:

- **BREAKING → ESCALATING**: se a crise perdeu o fator surpresa
- **ESCALATING → SATURATED**: quando a produção de ativos já está em andamento
- **SATURATED → DECAYING**: quando o momentum claramente caiu

O crisis stage drive toda a configuração downstream (ads, tom, visibilidade). Mudar manualmente o estágio muda automaticamente a estratégia.

### 8.6 Monitoramento — Reset e Reconfiguração

Se o estado do monitoramento ficar corrompido:

```
POST /monitor/{slug}/reset
→ Deleta monitoring/{slug}/state.json
→ Próximo check recria do zero
```

Para mudar a configuração (webhook Slack, frequências), chame `configure_monitoring()` novamente com os novos parâmetros. O state.json é atualizado na próxima verificação.

### 8.7 Integração com YouTube Ads

O battle plan gera a estratégia de YouTube Ads. Para executar:

1. Abrir Google Ads
2. Criar campanha "Video"
3. Escolher tipo: TrueView In-Stream / Discovery / Bumper
4. Usar o roteiro gerado como script do anúncio
5. Segmentação: conforme o YouTube Ads campaign gerado
6. Orçamento: sugerido no battle plan
7. Ativar

**Não use YouTube Ads para vender — use para DEFENDER.** A campanha de brand defense no YouTube existe para garantir que quando alguém pesquisar o nome do cliente no YouTube, o primeiro vídeo seja o controlado, não o negativo.

### 8.8 Integração com Google Ads

O battle plan gera a estratégia de ads. Para executar:

1. Abrir Google Ads
2. Criar campanha "Search"
3. Termos: conforme o battle plan (brand defense + termos hostis)
4. Landing page: o artigo gerado no site
5. Orçamento: sugerido no battle plan
6. Ativar

**Não use o Google Ads para vender — use para DEFENDER.** A campanha de brand defense existe para garantir que quando alguém pesquisar o nome do cliente, o primeiro anúncio leve ao conteúdo controlado, não ao JusBrasil.

### 8.9 Retry e Resiliência

Todas as chamadas externas (SERPAPI, GNews, Firecrawl, OpenRouter) têm **retry com exponential backoff**:

```
Tentativa 1: 0s
Tentativa 2: 2s
Tentativa 3: 4s
Tentativa 4: 8s (máximo)
```

Isso significa que timeouts temporários (comuns em APIs de IA) não quebram o fluxo de auditoria. Se após 4 tentativas a chamada falhar, o sistema registra o erro e continua com o que tem — nunca deixa uma auditoria incompleta por causa de uma API lenta.

### 8.10 Integração com LinkedIn Ads

O LinkedIn Ads é configurado no LinkedIn Campaign Manager:

1. Criar campanha com objetivo "Brand Awareness" ou "Engagement"
2. Segmentação: copiar do dashboard `/linkedin-ads/{slug}`
3. Criar audiência matched por lista de empresas (se disponível)
4. Criar Creative: Single Image Ad ou Sponsored Content
5. Orçamento: sugerido no plano (CPM × impressões estimadas)
6. Ativar

### 8.11 Tratamento de Erros Comuns

| Problema | Causa | Solução |
|---|---|---|
| "Nenhum snapshot encontrado" | Entidade nunca auditada | Fazer auditoria |
| OpenRouter timeout (60s) | LLM lento | Tentar de novo |
| GNews retorna 0 artigos | API quota excedida | Esperar 1h |
| SERPAPI quota excedida | 100 buscas/mês grátis | Upgrade de plano |
| Artigo genérico/demasiado curto | Contexto ruim | Verificar battle plan |
| Build site retorna poucos artigos | Cache incompleto | Rodar generate-all |
| 422 Unprocessable Entity | Route conflict | Verificar se slug não tem caracteres especiais |
| Monitoring state corrompido | JSON mal formatado | `POST /monitor/{slug}/reset` |
| NPA não aparece no monitoring | Snapshot mais recente não tem NPA | Rodar nova auditoria |
| YouTube Toxicity = 0 sem vídeos | Entidade não tem YouTube na SERP | Normal — só aparece quando há vídeos negativos |
| News Occupation Score baixo | Nenhum release enviado ainda | Enviar release para portais selecionados |
| KP Score baixo | Entidade sem Wikipedia/schema.org | Seguir o setup guide de 6 passos |
| **500 Internal Server Error** | pipeline_log.json no cache | Gerar artigos novamente (cache limpo) |
| **Medium retorna "published" mas é draft** | API sempre cria draft | Aceder ao painel Medium e clicar Publish |
| **LinkedIn Article não aparece** | API UGC Post = feed post, não Article | LinkedIn Articles = manual via web |
| **EIN Presswire falha** | contact_email ausente | Configurar `EIN_CONTACT_EMAIL` no .env |
| **WordPress retorna erro** | Application Password incorreta | Regenerar no painel WordPress |

### 8.12 O Segredo #8: O Maior Risco é o Cliente Falar

O cliente contrata, você faz o plano, produz os artigos, sobe o site. Aí o cliente dá uma entrevista ao jornal local e fala o que não devia.

**O playbook do arquétipo já prevê isso.** Os gatilhos de escalation incluem "declaração pública não autorizada de porta-voz secundário". A linguagem segura para porta-vozes é treinamento obrigatório.

Inclua no contrato: cláusula de silêncio estratégico. O cliente só fala com imprensa APÓS aprovação do roteiro.

### 8.13 Métricas de Sucesso para o Cliente

| Cliente feliz quando | Métrica |
|---|---|---|
| "Meu nome não aparece mais no JusBrasil" | Não é sobre REMOVER, é sobre OCUPAR. O JusBrasil continua lá, mas na posição #7 em vez de #1 |
| "Recebi uma proposta depois que me pesquisaram" | CTR dos anúncios + cliques orgânicos no perfil |
| "Um jornalista me ligou e eu estava preparado" | Roteiro de entrevista foi usado |
| "O Google mudou" | SERP toxicity gauge caiu |
| "O YouTube não mostra mais vídeo negativo" | YouTube Toxicity caiu de 65 para 20 |
| "Meu release saiu em 3 portais" | News Occupation Score subiu |
| "Contratei porque vi o relatório do concorrente" | Diagnóstico é a venda |

---

**EXERCÍCIO FINAL**: Simule um cliente real. Escolha uma entidade (pode ser fictícia). Passe por TODO o fluxo:

1. Auditoria → snapshot
2. Analisar arquétipo + threat level + crisis stage
3. Abrir dominância → interpretar gauge
4. Abrir battle plan → identificar ações prioritárias (incluindo YouTube, KP, LinkedIn, News)
5. Gerar response strategy → ler o playbook (ajustado pelo crisis stage)
6. Produzir 6 artigos + 1 roteiro de vídeo
7. Gerar 6 variações semânticas do artigo LinkedIn (Módulo 10)
8. Abrir YouTube Warfare → ver toxicity, gerar script de vídeo
9. Abrir Knowledge Panel → ver KP Score, seguir setup guide
10. Abrir LinkedIn Ads → ver segmentação, planejar campanhas
11. Abrir News Distribution → selecionar portais, gerar payloads
12. Build site → verificar no disco
13. Abrir Distribution Engine → identificar top 5 plataformas por AI Citation Probability
14. Abrir Quick Publish → verificar status das credenciais
15. Abrir Publish Assist → escolher 3 plataformas manuais e seguir os guias
16. Abrir Narrative Blast → configurar budget e região, ler as 4 fases
17. Configurar monitoramento → verificar background loop ativo
18. Escrever proposta comercial para o cliente (3 parágrafos: problema, solução, investimento)

Isso é a certificação CouncilIA. Se você fizer isso completo, você domina o sistema.

---

# MÓDULO 9 — DISTRIBUTION ENGINE E NARRATIVE BLAST

## Como Distribuir Narrativa de Forma Coordenada

### 9.1 O Problema que o Distribution Engine Resolve

Publicar conteúdo em uma plataforma não move o Google. Publicar o mesmo conteúdo em 20 plataformas no mesmo dia gera penalidade de duplicate content e pode ser detectado como manipulação.

O Distribution Engine resolve isso com três camadas:

```
CAMADA 1 — Seleção inteligente de plataformas
  75 plataformas ranqueadas por 7 dimensões
  Você não publica em tudo — publica nas certas

CAMADA 2 — Variação Semântica (anti-duplicate)
  Mesma narrativa, 6 enquadramentos diferentes
  Cada plataforma recebe um formato diferente

CAMADA 3 — Sequenciamento temporal (Narrative Blast)
  Publicação coordenada em 4 fases ao longo de 30 dias
  Google detecta cluster de autoridade, não spam
```

### 9.2 As 7 Dimensões de Avaliação de Plataformas

| Dimensão | Peso | O que mede |
|---|---|---|
| Autoridade de Domínio (DA) | 30% | Peso do domínio no Google |
| Velocidade de Indexação | 15% | Em quanto tempo o conteúdo aparece no Google |
| Permanência | 10% | Por quanto tempo o conteúdo fica indexado |
| Google News | 10% | Se o domínio alimenta o Google News |
| API disponível | 5% | Automação possível |
| **Persistence Score** | **15%** | Quão duradouro é o conteúdo (5 níveis: Very Low / Low / Medium / High / Very High) |
| **AI Citation Probability** | **15%** | Probabilidade de ser citado por ChatGPT/Gemini/Perplexity (0–100) |

**Por que AI Citation Probability importa**: 30-40% das buscas em 2026 passam por algum modelo de IA. Se a plataforma onde você publicou é citada pelo ChatGPT, ela tem impacto direto nas respostas sobre o cliente — independentemente do ranking orgânico do Google.

**Top 5 por score composto:**

| Plataforma | Score | AI Citation | Persist. |
|---|---|---|---|
| LinkedIn | 98 | 92 | Muito Alta |
| Google Business | 98 | 90 | Muito Alta |
| YouTube | 97 | 85 | Muito Alta |
| Medium | 92 | 88 | Alta |
| GlobeNewswire | 91 | 82 | Alta |

### 9.3 O Protocolo Narrative Blast (30 dias)

O Narrative Blast divide a distribuição em 4 fases com objetivos distintos:

**Dia 0 — Cinturão de Autoridade**

Antes de publicar qualquer conteúdo, crie ou atualize os perfis de autoridade institucional. Esses perfis:
- Alimentam o Knowledge Panel do Google
- São citados por LLMs como fontes de referência
- Criam "entidade reconhecível" para o Google antes do blast de conteúdo

Perfis obrigatórios: Google Business Profile, Crunchbase. Recomendados por arquétipo: AngelList (founders), HackerNoon (tech), GitHub (técnicos).

**Dia 1 — Narrative Blast (sincronização simultânea)**

Publicar a narrativa core em múltiplos canais no mesmo dia. O Google detecta:
- Co-citação de entidade em múltiplos domínios de alta autoridade
- Cluster temporal (mesmo período) como sinal de relevância
- Diversidade de fontes como sinal de autoridade genuína

Sequência típica: LinkedIn (hub) → Newswire (Google News) → Medium (crosspost) → YouTube (vídeo)

**Dias 2–7 — Backfill**

Releases de apoio com dados diferentes (evitar duplicate content). Atualizar perfis de autoridade com links para o conteúdo do Dia 1. Newsletter Substack com links para tudo.

**Dias 8–30 — Monitoramento**

Nova auditoria CouncilIA no Dia 15 e Dia 30. Indexação manual no Google Search Console para cada URL nova. Displacement tracking: medir quais resultados positivos subiram.

### 9.4 Detecção de Saturação — Quando Parar

O maior risco de uma estratégia de distribuição agressiva é o overposting:

| Métrica | Verde | Amarelo | Vermelho |
|---|---|---|---|
| Releases/mês | 1–2 | 3–4 | 5+ |
| Texto idêntico em plataformas/dia | 1–2 | 3 | 4+ |

**Sinais de que você foi longe demais:**
- Novo conteúdo não indexa em 72h (Google bloqueou crawl)
- Ranking dos conteúdos positivos não sobe apesar de novos releases
- Alerta de duplicate content no Google Search Console
- Novo artigo com zero backlinks orgânicos após 30 dias

**Ação**: pausar 14 dias, atualizar/expandir conteúdo já indexado, usar Variação Semântica nos próximos releases.

### 9.5 Cross-Language Occupation

Para clientes com presença internacional ou exposição em buscas em inglês:

Publicar a mesma narrativa em PT + EN + ES multiplica pontos de entrada nos modelos de IA. ChatGPT e Gemini foram treinados majoritariamente em inglês — ter conteúdo indexado em EN aumenta AI citation probability em 20–40pp estimado.

**Plataformas por idioma:**
- PT-BR: LinkedIn, Medium, Substack
- EN: Medium, LinkedIn, HackerNoon
- ES: Expansión, LinkedIn, Medium

**Quando usar**: clientes tech com exposição global, fundadores com audiência internacional, executivos de empresas multinacionais.

---

**EXERCÍCIO 9.1**: Abra `/distribution/{slug}` para um cliente. Identifique as 5 plataformas com maior AI Citation Probability. Para qual budget (minimal/standard/premium) a estratégia muda? Acesse `/narrative-blast/{slug}` e veja como a stack muda por nível. Depois abra `/quick-publish/{slug}` e verifique o status das credenciais — quais APIs estão prontas para usar?

---

# MÓDULO 10 — MOTOR DE VARIAÇÃO SEMÂNTICA

## Como Evitar Penalidade de Duplicate Content

### 10.1 O Problema

Você gerou o artigo. É bom. Você quer publicar em LinkedIn, Medium, HackerNoon e enviar para uma newswire no mesmo dia.

Se você publica o mesmo texto em 4 lugares no mesmo dia, o Google detecta:
1. Mesmo texto idêntico em múltiplos domínios
2. Mesmo período de publicação
3. Mesmas keywords, mesmas entidades, mesmo enquadramento

Resultado: nenhum dos 4 ranqueia bem. O Google não sabe qual é o "original" e desvaloriza todos.

### 10.2 A Solução — 6 Enquadramentos Narrativos

O Motor de Variação Semântica mantém a **narrativa central idêntica** mas muda perspectiva, tom, estrutura e ênfase:

| Enquadramento | Tom | Ênfase | Ideal para |
|---|---|---|---|
| **Declaração Institucional** | Corporativo, impessoal | Posição de mercado, compliance | Newswires, boilerplate |
| **Opinião Técnica** | Especialista, analítico | Metodologia, conclusões não-óbvias | LinkedIn, Medium, HackerNoon |
| **Comentário de Compliance** | Cauteloso, orientado a risco | Regulatório, due diligence | Substack, WordPress |
| **Análise de Mercado** | Setorial, comparativo | Tendências, cenários, peers | Substack, GlobeNewswire |
| **Nota do Fundador** | Direto, reflexivo | Decisões pessoais, contexto | LinkedIn, Medium, Substack |
| **Insight Operacional** | Prático, de bastidores | Processos reais, métricas concretas | HackerNoon, Dev.to |

**Por que funciona**: o Google não penaliza conteúdo que é semanticamente coerente com ângulos diferentes. Penaliza texto idêntico. LLMs citam fontes diferentes quando o mesmo tema é abordado com perspectivas diferentes.

### 10.3 Como Usar

1. Abrir `/semantic-variations/{slug}`
2. Selecionar o artigo em cache (gerado pelo Content Studio)
3. Marcar os enquadramentos desejados (todos por padrão)
4. Clicar "Gerar Variações"
5. Aguardar 20–30 segundos (1 chamada LLM por enquadramento)
6. Copiar cada variação para a plataforma correspondente

**Regra operacional**: nunca use o mesmo enquadramento em mais de uma plataforma no mesmo dia.

### 10.4 Distribuição por Enquadramento

```
ARTIGO BASE (gerado no Content Studio)
├── Declaração Institucional → EIN Presswire ou GlobeNewswire
├── Opinião Técnica         → LinkedIn Articles
├── Análise de Mercado      → Medium
├── Nota do Fundador        → Substack
├── Comentário de Compliance → WordPress (site do cliente)
└── Insight Operacional     → HackerNoon (se tech) ou Dev.to
```

**Timing**: publicar em 2–3 dias, não tudo no mesmo dia. LinkedIn + Newswire no Dia 1. Medium + Substack no Dia 2–3. Site do cliente no Dia 4–5.

### 10.5 O que a Variação NÃO muda

- Os **fatos centrais** (datas, números, eventos)
- As **afirmações verificáveis** (cargos, conquistas específicas)
- O **posicionamento narrativo** (o que o cliente quer transmitir)
- As **keywords estratégicas** (nome completo, nome da empresa)

**Mudar fatos entre variações é o erro mais grave.** Se o artigo diz que o cliente fundou a empresa em 2018 e a variação diz 2019, você criou inconsistência que alimenta desconfiança.

---

**EXERCÍCIO 10.1**: Gere todas as 6 variações para o artigo `artigo_linkedin` de um cliente. Compare os primeiros parágrafos. Identifique: o que mudou (tom, perspectiva, estrutura) e o que permaneceu (fatos, afirmações centrais). Associe cada variação a uma plataforma e justifique a escolha.

---

## GLOSSÁRIO

| Termo | Definição |
|---|---|
| **NPA** | Nível de Pressão Agregado. Score 0-100 que resume a pressão reputacional |
| **SERP** | Search Engine Results Page — página de resultados do Google |
| **Negative Share** | % de resultados negativos na página 1 |
| **Controlled Asset** | Resultado que a entidade controla (site próprio, LinkedIn, Medium) |
| **Tier-1** | Veículo de elite (Folha, Globo, Estadão, Veja, UOL) |
| **Domain Authority** | Peso 1-10 de um domínio no Google |
| **Vácuo de Autoridade** | Espaços na página 1 que a entidade não ocupa |
| **Asset Gap** | Diferença entre ativos necessários e existentes |
| **Recovery Probability** | Chance de recuperar a página 1 em 90 dias (0-98%), calculada por 9 fatores |
| **Crisis Stage** | Estágio da crise: BREAKING, ESCALATING, SATURATED, DECAYING, ARCHIVED, STABLE |
| **YouTube Toxicity** | Pressão de vídeos negativos no YouTube (0-100), 4 componentes |
| **YouTube NPA Boost** | Multiplicador 1.2× sobre impacto de vídeos negativos no NPA |
| **Knowledge Panel Score** | Probabilidade de ter Knowledge Panel (0-100), 6 componentes |
| **News Occupation Score** | % de controle sobre Google News (0-100), 5 componentes |
| **Arquétipo** | Natureza da ameaça: criminal, reputacional, político, mídia, administrativo, associativo |
| **Playbook** | Conjunto de regras operacionais para um arquétipo |
| **Deslocamento** | Estratégia de mover um resultado negativo de posição |
| **Brand Defense** | Campanha de Google Ads para proteger o nome da entidade |
| **Featured Snippet** | Caixa de resposta no topo do Google (posição #0) |
| **Schema.org** | Marcação HTML que ajuda o Google a entender o conteúdo |
| **Canonical Link** | Link que diz ao Google qual é a versão original do conteúdo |
| **TrueView** | Formato de anúncio YouTube skipável após 5 segundos |
| **Bumper Ads** | Anúncio YouTube não-skipável de 6 segundos |
| **Distribution Engine** | Módulo que ranqueia **75 plataformas** por 7 dimensões para distribuição estratégica |
| **Persistence Score** | Score 0–100 (5 níveis: Very Low / Low / Medium / High / Very High) de quanto tempo o conteúdo de uma plataforma permanece indexado |
| **AI Citation Probability** | Score 0–100 da probabilidade de uma plataforma ser citada por LLMs (ChatGPT, Gemini, Perplexity) |
| **Narrative Blast** | Protocolo de distribuição narrativa coordenada em 4 fases / 30 dias |
| **Variação Semântica** | Versão de um artigo com enquadramento diferente — mesmo fatos, perspectiva distinta |
| **Duplicate Content** | Texto idêntico em múltiplos domínios — penalizado pelo Google |
| **Saturação Narrativa** | Overposting: número excessivo de releases com a mesma entidade em curto período |
| **Cross-Language Occupation** | Estratégia de publicar em PT + EN + ES para multiplicar pontos de entrada em LLMs |
| **Cinturão de Autoridade** | Conjunto de perfis institucionais (Crunchbase, Google Business, AngelList) que constroem entidade reconhecível |
| **Outranking Potential** | Score composto 0–100 que mede a capacidade de uma plataforma de ranquear acima de resultados negativos |
| **Discovery Ads** | Anúncio YouTube que aparece na busca e em vídeos relacionados |
| **Stakeholder Exposure Matrix** | Mapa de quem precisa ver cada mensagem, por arquétipo |
| **Quick Publish** | Dashboard de publicação via API (Medium, LinkedIn, WordPress, EIN Presswire) com dry-run |
| **Publish Assist** | 39 guias manuais de publicação passo a passo com conteúdo formatado |
| **Post-Audit Pipeline** | Geração automática de conteúdo baseada no threat_level da auditoria |
| **Dry-Run** | Preview do payload antes de publicar — evita cobranças acidentais em newswires pagas |
| **Atomic Write** | `os.replace()` para salvar JSON sem corrupção em caso de crash |
| **Background Monitoring** | Asyncio loop que verifica SERP a cada 5 min — sem cron externo |
