# CouncilIA — Fluxo Operacional Completo

## Da Busca ao Impulsionamento

```
BUSCA              ANÁLISE              PLANO              PRODUÇÃO           DISTRIBUIÇÃO          IMPULSIONAMENTO        FRENTES ADICIONAIS
─────              ───────              ─────              ────────           ────────────          ────────────────        ─────────────────

SERPAPI       ──→  Audit Service  ──→  SERP Dominance ──→ Content Studio ──→ Distribution     ──→  Google Ads         ──→  YouTube Warfare
 top 20              │                  │                   │                  Engine              (brand defense)          toxicity+scripts+ads
                      │                  │                   │                  75 plataformas
GNews         ──→   │             ──→  Battle Plan    ──→   │             ──→  Narrative Blast  ──→  LinkedIn Ads        ──→  Knowledge Panel
 notícias           │                  │                   │                  30d workflow          (profissional)           score+wikidata+schema
                     │                  │                   │
Firecrawl     ──→   │             ──→  Occupation     ──→   │             ──→  Semantic         ──→  News Distribution   ──→  Monitoring Engine
 scrape              │                  │                   │                  Variations            portais+payload          asyncio 5min + email
                     │                  │                   │                  6 frames
OpenRouter    ──→   │             ──→  Response       ──→   │             ──→  Site Jornalístico ──→  Release Distributors ──→  Recovery Probability
 DeepSeek R1        │                  │                   │                  (deploy Netlify)      EIN+eReleases+etc        9 fatores
                     │                  │                   │
 Expansion     ──→   │             ──→  Post-Audit      ──→   │
 entidades           │                  Pipeline             │
 ocultas             ▼                  (gera artigos        ▼
                                      por threat level)
                 Snapshot          Estratégia          Artigos Prontos
                 (JSON)            (determinística)    (7 tipos + variações)
```

---

## Passo a Passo Operacional

### 1. AUDIT — `GET /` (form) → `POST /` (processa)

O operador digita o nome de uma entidade. O sistema faz **automaticamente**:

| # | Chamada | O que busca | Custo |
|---|---|---|---|
| 1 | `SERPAPI` | Top 20 resultados do Google | ~$0.01 |
| 2–4 | `Firecrawl` ×3 | Conteúdo das 3 URLs selecionadas (até 15k chars cada) | ~$0.01 cada |
| 5 | `GNews` | Até 10 notícias recentes | grátis |
| 6–12 | `GNews` ×7 | Variações de nome + top-4 associações semânticas | grátis |
| 13 | `OpenRouter` | Análise estratégica completa (DeepSeek R1) | ~$0.10–0.30 |

**Resultado automático em `snapshots/{slug}/{data}.json`:**

- Arquétipo (criminal / reputacional / político / mídia / administrativo / associativo)
- Crisis stage (BREAKING / ESCALATING / SATURATED / DECAYING / ARCHIVED / STABLE)
- NPA Score 0–100 + Negative Share + Momentum
- Threat level (CRITICAL / HIGH / MEDIUM / LOW)
- YouTube Toxicity (0–100) + NPA Boost 1.2×
- KP Score (0–100) — probabilidade de Knowledge Panel
- Associações descobertas com nível de risco
- Screenshot automático em `snapshots/{slug}/serp_{data}.png`

---

### 2. DOMINÂNCIA SERP — `GET /dominance/{entity}`

Zero chamadas externas — lê do snapshot.

- **Gauge de Toxicidade SERP** 0–100 com breakdown de 5 componentes
- **Clusters por Domínio** com peso de dominância ponderado
- **Position War Map** — mapa #1 a #20 com sentimento, tipo, autoridade, controlado

---

### 3. BATTLE PLAN — `GET /battle-plan/{entity}`

Zero chamadas externas. **14 seções operacionais:**

| Seção | O que define |
|---|---|
| **Deslocamento** | EASY / MEDIUM / HARD / VERY_HARD por resultado + tempo estimado |
| **Guerra Orgânica** | Quais posições atacar com SEO + conteúdo controlado |
| **Defesa Paga** | Termos Google Ads, landing pages, orçamento mínimo/máximo |
| **Intent Matrix** | branded / hostile / institutional / crisis / professional |
| **Asset-to-Keyword** | Qual ativo responde qual termo de busca |
| **Saturação Narrativa** | HIGH / MEDIUM / LOW por domínio |
| **Asset Gap** | Ativos necessários vs existentes |
| **Recovery Probability** | 0–98% + breakeven + dificuldade |
| **Timeline 30/60/90d** | Fases com ações orgânicas + pagas |
| **KPIs** | Projeções de toxicity, negative share, controlled assets |
| **YouTube Warfare** | Toxicity + roteiros + campanhas TrueView/Discovery/Bumper |
| **Knowledge Panel** | KP Score + guide 6 passos + Wikidata + schema.org |
| **LinkedIn Ads** | Segmentação por arquétipo + 3 campanhas + matriz de stakeholders |
| **News Distribution** | Portais selecionados + payloads prontos + news occupation score |

---

### 4. RESPOSTA OPERACIONAL — `GET /response` → `POST /response`

Playbook de 8 seções ditado pelo arquétipo:

| Arquétipo | Princípio | Postura em CRITICAL+legal |
|---|---|---|
| Criminal | Conter vazamento. Jurídico primeiro. | contenção-jurídica-absoluta |
| Reputacional | Ocupar espaço. Silêncio = derrota. | conciliatório-com-clarificação |
| Político | Base, depois imprensa. | guerra-narrativa |
| Mídia | Gestão de pauta. | gestão-de-pauta |
| Administrativo | Documentos > versões. | transparência-processual |
| Associativo | Desassociação documentada. | desassociação-documentada |

---

### 5. OCUPAÇÃO SERP — `GET /occupation/{entity}`

Estratégia de ocupação faseada por arquétipo — três fases com ativos específicos por fase.

---

### 6. PRODUÇÃO DE CONTEÚDO — `GET /content/{entity}`

**Automático**: gera texto completo com SEO metadata, instruções de publicação e amplificação.

| Asset | Plataforma principal | SEO Boost |
|---|---|---|
| `artigo_linkedin` | LinkedIn Articles (DA 98) | ALTO |
| `biografia_executiva` | Site + LinkedIn | CRÍTICO |
| `perfil_institucional` | Site Institucional | ALTO |
| `comunicado_imprensa` | Newswires + Site | ALTO |
| `esclarecimento_juridico` | Site + FAQ | MÉDIO |
| `faq_transparencia` | Site (FAQPage schema) | ALTO |
| `roteiro_youtube` | YouTube (DA 100) | ALTO |

**Gerar Tudo** = 7 artigos em lote → `articles_cache/{slug}/`

Cada artigo gerado vem com:
1. Texto completo em PT-BR (non-commodity, ponto de vista único)
2. SEO metadata (title, meta_description, slug, tags)
3. Fan-out queries (8 queries relacionadas que o Google pode gerar)
4. JSON-LD estruturado (Person ou FAQPage) quando aplicável
5. Passo a passo de publicação por plataforma
6. Estratégia de amplificação (Google Ads, LinkedIn Ads, SEO)

---

### 7. MOTOR DE VARIAÇÃO SEMÂNTICA — `GET /semantic-variations/{entity}`

**Novo.** Anti-mass-posting: gera 6 versões do mesmo artigo com enquadramentos diferentes.

| Enquadramento | Tom | Plataformas ideais |
|---|---|---|
| Declaração Institucional | Corporativo, impessoal | EIN Presswire, GlobeNewswire |
| Opinião Técnica | Especialista, analítico | LinkedIn, Medium, HackerNoon |
| Comentário de Compliance | Cauteloso, orientado a riscos | Substack, WordPress |
| Análise de Mercado | Setorial, comparativo | Substack, Medium |
| Nota do Fundador / Executivo | Direto, reflexivo | LinkedIn, Medium, Substack |
| Insight Operacional | Prático, de bastidores | HackerNoon, Dev.to |

**Por que existe**: Google penaliza texto idêntico em múltiplos domínios no mesmo dia. As variações mantêm a narrativa core, mudam perspectiva e estrutura — coerência semântica sem footprint artificial.

---

### 8. DISTRIBUTION ENGINE — `GET /distribution/{entity}`

**75 plataformas** em 4 tiers, avaliadas por 7 dimensões:

| Dimensão | Peso na fórmula |
|---|---|
| Autoridade de Domínio (DA) | 30% |
| Velocidade de Indexação | 15% |
| Permanência | 10% |
| Google News | 10% |
| API disponível | 5% |
| **Persistence Score** | 15% |
| **AI Citation Probability** | 15% |

**Persistence Score**: 5 níveis (Very Low / Low / Medium / High / Very High). Quão duradouro é o conteúdo publicado. YouTube, LinkedIn, Forbes = "Very High". Farms de syndication = "Low".

**AI Citation Probability**: probabilidade de a plataforma ser citada por LLMs (ChatGPT, Gemini, Perplexity). Top: LinkedIn 92, Google Business 90, Forbes 90, Medium 88, GlobeNewswire 82.

### 8a. PUBLISH ASSIST — `GET /publish-assist/{slug}`

**39 guias manuais** com passo a passo, URL de publicação, impacto SEO e advertências para plataformas sem API automatizável (portais editoriais, YouTube, LinkedIn Articles completos, Substack, HackerNoon, etc.). Detecta região automaticamente (BR/PT/ES) e filtra plataformas por arquétipo.

### 8b. QUICK PUBLISH — `GET /quick-publish/{slug}`

Dashboard de publicação automatizada via API:
- **Status das credenciais** (Medium token, LinkedIn token, WordPress, EIN Presswire)
- **Seleção de artigo + plataforma** com preview formatado
- **Dry-run** antes de publicar para evitar cobranças acidentais em newswires pagas
- **Trigger de publicação** via `POST /quick-publish/{slug}/trigger`

### 8c. POST-AUDIT PIPELINE

Após cada auditoria, se `threat_level >= MEDIUM`, o sistema gera automaticamente:
- **MEDIUM**: 2 artigos (artigo_linkedin + comunicado_imprensa)
- **HIGH / CRITICAL**: 7 artigos + 1 roteiro YouTube
- Salvos em cache via `save_article()` — prontos para revisão e publicação imediata

Top 5 plataformas pelo score composto:

| Plataforma | Score | Persist. | Cit. IA |
|---|---|---|---|
| LinkedIn | 98 | Muito Alta | 92 |
| Google Business Profile | 98 | Muito Alta | 90 |
| YouTube | 97 | Muito Alta | 85 |
| Medium | 92 | Alta | 88 |
| GlobeNewswire | 91 | Alta | 82 |

---

### 9. NARRATIVE BLAST — `GET /narrative-blast/{entity}?budget=standard&region=BR`

Workflow de campanha de 30 dias estruturado, adaptado por `budget` (minimal / standard / premium) e `região` (BR / PT / GLOBAL).

**4 fases:**

| Fase | Dias | Ações |
|---|---|---|
| **Cinturão de Autoridade** | Dia 0 | Criar/atualizar perfis: Google Business, Crunchbase, AngelList, HackerNoon |
| **Narrative Blast** | Dia 1 | Publicar narrativa core simultânea: LinkedIn + Newswire + Medium + YouTube |
| **Backfill** | Dias 2–7 | Releases de apoio regionais, atualizar perfis com links, newsletter Substack |
| **Monitoramento** | Dias 8–30 | Nova auditoria D15 e D30, indexação manual Google Search Console, CouncilIA Monitor |

**Inclui:**
- Stack Mínima Viável por nível de budget com custo estimado
- **Cross-Language Occupation** — PT-BR + EN + ES com plataformas por idioma (+20-40pp estimado em AI citation)
- **Narrative Saturation Detection** — thresholds de quando parar: ≤2 releases/mês = verde, 5+ = vermelho
- 5 sinais de saturação a monitorar
- Avisos operacionais sobre plataformas de risco

---

### 10. SITE JORNALÍSTICO — `/content/{entity}/build-site`

Gera site HTML estático completo a partir do cache de artigos — zero LLM.

```
content_sites/{slug}/
├── index.html                          (homepage com grid de artigos)
├── {slug}-artigo_linkedin.html
├── {slug}-biografia_executiva.html
├── {slug}-comunicado_imprensa.html
├── {slug}-esclarecimento_juridico.html
├── {slug}-faq_transparencia.html
├── {slug}-perfil_institucional.html
└── _deploy_instructions.txt
```

Deploy: arrastar pasta no Netlify → 2 minutos.

---

### 11. YOUTUBE WARFARE — `GET /youtube/{slug}`

**Automático**: YouTube Toxicity Score (0–100) com 4 componentes. NPA Boost 1.2× para vídeos negativos. 4 tipos de roteiro (Posicionamento Institucional, Esclarecimento, Trajetória, FAQ). Campanhas TrueView / Discovery / Bumper.

**Pipeline automático**: se `threat_level ≥ HIGH`, roteiro YouTube é gerado automaticamente na post-audit pipeline.

**Manual**: gravar o vídeo, publicar, criar campanhas no Google Ads.

---

### 12. KNOWLEDGE PANEL — `GET /knowledge-panel/{slug}`

**Automático**: KP Score (0–100) com 6 componentes. Wikidata profile completo. Schema.org Person JSON-LD. FAQ Schema. Setup guide de 6 passos.

**Manual**: criar Wikidata, implementar schema.org, reivindicar KP no Search Console.

---

### 13. NEWS DISTRIBUTION — `GET /news-distribution/{slug}`

**Automático**: seleção de portais por arquétipo + autoridade. Release payload formatado por portal. News Occupation Score (0–100).

**Manual**: enviar por email (ConJur, Migalhas, Segs) ou via API paga (MaxPress, PRWeb).

---

### 14. LINKEDIN ADS — `GET /linkedin-ads/{slug}`

**Automático**: segmentação por arquétipo (6 perfis), estimativa de audiência, CPM, 3 campanhas, Matriz de Stakeholders 4×4.

**Manual**: criar campanhas no LinkedIn Campaign Manager.

---

### 15. MONITORING

**Automático em background**: asyncio loop interno verifica a cada 5 minutos — sem necessidade de cron externo ou Windows Task Scheduler.

**Funcionalidades:**
- **Asyncio loop**: inicia com o servidor, verifica cada entidade monitorada a cada 5 min
- **Atomic writes**: `os.replace()` previne corrupção de JSON em caso de crash
- **SMTP email alerts**: alertas reais via Gmail configurável (`COUNCILIA_SMTP_USER` / `COUNCILIA_SMTP_PASS`)
- **Auto-reaudit em CRITICAL**: se um alerta CRÍTICO dispara, o sistema reaudita automaticamente
- **Pruning automático**: estado de monitoramento limpo após 90 dias
- **6 triggers**: CRÍTICO (novo domínio negativo, jurídico) / ALTO (top-3 mudou, salto NPA ≥10) / MÉDIO (GNews) / INFO (cobertura positiva)
- **Estado salvo em**: `monitoring/{slug}/state.json`

**Health endpoints:**
- `GET /health` — status do sistema + monitor ativo
- `GET /status` — dashboard de entidades monitoradas
- `GET /api/credentials/check` — validação de credenciais (.env)

---

## O Ciclo Completo — Sistema vs. Operador

```
SISTEMA FAZ                                           VOCÊ FAZ
───────────                                           ────────

1.  Auditar → snapshot completo                       —
2.  Calcular arquétipo, crisis stage, NPA             —
3.  Capturar screenshot da SERP                       —
4.  Mapear dominância → gauge + war map               —
5.  Gerar battle plan com 14 seções                   —
6.  Calcular recovery probability                     —
7.  Gerar playbook de resposta por arquétipo          —
8.  Produzir 7 artigos em PT-BR (non-commodity)       Revisar e aprovar antes de publicar
9.  Gerar 6 variações semânticas por artigo           Escolher qual variação vai para qual canal
10. Gerar payload de release por portal               Enviar email / ativar API paga
11. Calcular segmentação LinkedIn Ads                 Criar campanhas no LinkedIn Campaign Mgr
12. Gerar roteiro YouTube (4 tipos)                   Gravar e publicar o vídeo
13. Gerar KP Score + Wikidata + schema.org            Criar perfil Wikidata, implementar no site
14. Build site HTML → content_sites/                  Arrastar pasta no Netlify (2 min)
15. Gerar plano Narrative Blast 30d                   Executar as ações na sequência correta
16. Ranquear 75 plataformas por AI Citation + Persist. Escolher plataformas pelo budget do cliente
17. Formatar conteúdo por plataforma                  Publicar com login na conta do cliente
18. Publicar via API (Medium, LinkedIn, WordPress)    Configurar credenciais no .env
19. Dry-run antes de publicar                         Revisar preview antes de confirmar
20. Monitorar SERP + News em background (5min)        Agir se alerta CRÍTICO (email automático)
21. Reauditar automaticamente em CRÍTICO              Revisar nova auditoria gerada
22. Comparar snapshots → Movement Report              Mostrar evolução ao cliente
23. Gerar PDF do relatório + comparação               Enviar ao cliente
```

---

## Estado de Automação — Resumo

| Módulo | Grau | O que é manual |
|---|---|---|---|
| Auditoria (POST /) | **100% automático** | — |
| Screenshot SERP | **100% automático** | — |
| SERP Dominance | **100% automático** | — |
| Battle Plan | **100% automático** | — |
| Recovery Probability | **100% automático** | — |
| YouTube Warfare (análise) | **100% automático** | Gravar e publicar vídeo |
| Knowledge Panel (score + conteúdo) | **100% automático** | Criar Wikidata, implementar schema |
| LinkedIn Ads (plano) | **100% automático** | Criar campanhas no Campaign Mgr |
| News Distribution (seleção + payload) | **100% automático** | Enviar email / ativar API |
| Produção de conteúdo | **100% automático** | Revisão humana antes de publicar |
| Post-Audit Pipeline (conteúdo automático) | **100% automático** | — |
| Variação Semântica | Trigger manual, execução automática | Escolher canais por variação |
| Distribution Engine (ranqueamento) | **100% automático** | — |
| Narrative Blast (plano) | **100% automático** | Executar as ações manualmente |
| Publicação via API (Medium, LinkedIn, WordPress) | **Payload pronto, publicar com credenciais** | Configurar .env + revisar dry-run |
| Publicação manual (39 guias) | **Payload pronto, passo a passo gerado** | Login na conta do cliente |
| Site builder | Geração automática, deploy manual | Arrastar pasta no Netlify |
| Monitoring | **Background loop 5min** + email automático + auto-reaudit | Agir se alerta CRÍTICO |
| Health / Status / Credentials | **100% automático** | — |

**Regra prática**: tudo que exige acesso a conta de terceiros (LinkedIn, Google Ads, email do cliente, Search Console) é manual. Tudo que depende só das APIs do sistema é automático.

---

## Diferença Antes vs Agora

| Antes | Agora |
|---|---|---|
| Relatório genérico em inglês | **Sistema 100% em PT-BR** — templates, UI e conteúdo gerado |
| 46 plataformas sem critério de IA | **75 plataformas** com Persistence Score + AI Citation Probability |
| Fórmula de Outranking sem IA | **Fórmula v2**: authority(30%) + speed(15%) + perm(10%) + GN(10%) + api(5%) + persist(15%) + ai_citation(15%) |
| Sem variação semântica | **Motor de Variação Semântica** — 6 enquadramentos |
| Distribuição sem workflow | **Narrative Blast** — 4 fases em 30 dias |
| Sem detecção de saturação | **Saturation Detection** — thresholds de overposting |
| Sem ocupação multilíngue | **Cross-Language Occupation** — PT+EN+ES |
| Asset templates em inglês | **Templates em PT-BR** — LLM gera conteúdo em português |
| distribution.html sem scores de IA | **Dashboard atualizado** com Persist. e Cit. IA |
| Monitoring sem integração de distribuição | Distribution + Blast + Semantic **integrados** |
| Sem press release próprio | **PRESS_RELEASE_COUNCILIA.md** gerado |
| Monitor externo (cron / Task Scheduler) | **Background asyncio loop** — 5min automático sem dependência externa |
| Sem email automático | **SMTP alerts** — real via Gmail |
| Sem auto-reaudit | **Reauditoria automática em CRÍTICO** |
| Sem validação de conteúdo | **Nome 5x / H1+H2 / JSON-LD / body_md** validados |
| Sem publicação via API | **Quick Publish** — Medium, LinkedIn, WordPress, EIN Presswire |
| Sem guias de publicação | **Publish Assist** — 39 guias manuais passo a passo |
| Sem ativação por threat level | **Post-Audit Pipeline** — gera conteúdo automaticamente |
| Sem retry em chamadas externas | **Exponential backoff** — SerpAPI, OpenRouter, Firecrawl |
| Sem atomic writes | **os.replace()** em monitoring, cost_tracker, snapshot |
| NPA sem Metrópoles/CNN | **Authority-weighted NPA** — mainstream portals rankeiam corretamente |

---

## Resumo: 90% Automático, 10% Manual

O sistema cobre **todo o trabalho intelectual** — diagnóstico, classificação, estratégia, redação, formatação para cada canal, payloads prontos, plano de distribuição de 30 dias, publicação via API, tracking de evolução e monitoramento contínuo em background.

O que não é automatizado:

| Ação | Motivo |
|---|---|
| Publicar no LinkedIn Articles completo | API não suporta Articles — apenas UGC feed posts |
| Publicar no Medium (status=draft) | API só cria rascunho — clicar Publish no painel |
| Publicar em portais editoriais (ConJur, Migalhas) | Editorial independente — email manual com release |
| Enviar release por email (ConJur, Migalhas, Valor) | Email parte de você, não do sistema |
| Ativar API paga (EIN Presswire, MaxPress, PRWeb) | Requer pagamento e credencial do cliente |
| Gravar vídeo YouTube | O sistema gera o roteiro — a câmera é sua |
| Criar campanhas Google Ads / LinkedIn Ads | Requer acesso à conta de anúncios do cliente |
| Criar Wikidata / implementar schema.org | Requer acesso ao site e wiki do cliente |
| Deploy do site no Netlify | Arrastar pasta, 2 minutos — puramente operacional |
| Indexação manual no Google Search Console | Login do Google do cliente necessário |
