"""
Knowledge Panel Engineering — Wikidata, Schema.org, KP Score, NAP Consistency.

The Knowledge Panel is the highest-visibility real estate on brand-name SERP:
up to 40% of desktop screen, nearly 100% on mobile above the fold.
It operates on completely different logic from organic SERP — sources
are Wikidata, Wikipedia, schema.org, and verified Google Search Console claims.
"""
import json
from datetime import datetime, timezone


def compute_knowledge_panel_score(snapshot: dict) -> dict:
    """Knowledge Panel Score (0-100) — how well-optimized the entity is for KP.

    Components:
      - Entity name match (15 pts): entity name appears consistently in SERP
      - Wikipedia presence (25 pts): wikipedia.org in SERP results
      - Schema readiness (20 pts): institutional/social domains controlled
      - NAP consistency (15 pts): name/title consistent across results
      - LinkedIn presence (15 pts): linkedin.com in SERP as controlled
      - CRUNCHBASE presence (10 pts): crunchbase.com in SERP as controlled

    Each component is inferred from snapshot SERP data (no external API calls).
    """
    serp = snapshot.get("serp", [])
    entity = snapshot.get("entity", "")
    entity_lower = entity.lower()

    # Entity name match (15 pts) — entity appears in titles
    title_matches = sum(1 for r in serp if entity_lower in (r.get("title", "") or "").lower())
    name_score = min(title_matches * 3, 15)

    # Wikipedia presence (25 pts)
    wiki_results = [r for r in serp if "wikipedia.org" in (r.get("domain", "") or "")]
    wiki_score = 25 if wiki_results else 0
    wiki_url = wiki_results[0].get("url", "") if wiki_results else ""

    # Schema readiness — controlled institutional/social domains (20 pts)
    controlled = [r for r in serp if r.get("controlled")]
    schema_ready = [r for r in controlled
                    if r.get("type") in ("institutional", "social")]
    schema_score = min(len(schema_ready) * 4, 20)

    # NAP consistency (15 pts) — same name appears in top results
    top5 = [r for r in serp if r.get("position", 99) <= 5]
    consistent = sum(1 for r in top5 if entity_lower in (r.get("title", "") or "").lower())
    nap_score = min(consistent * 3, 15)

    # LinkedIn presence (15 pts)
    linkedin = [r for r in serp if "linkedin.com" in (r.get("domain", "") or "")]
    linkedin_score = 15 if linkedin else 0
    linkedin_url = linkedin[0].get("url", "") if linkedin else ""

    # Crunchbase presence (10 pts)
    crunchbase = [r for r in serp if "crunchbase.com" in (r.get("domain", "") or "")]
    cb_score = 10 if crunchbase else 0

    total = min(name_score + wiki_score + schema_score + nap_score + linkedin_score + cb_score, 100)

    return {
        "total": total,
        "breakdown": {
            "entity_name_consistency": {"score": name_score, "max": 15, "raw": title_matches},
            "wikipedia_presence":      {"score": wiki_score, "max": 25, "raw": bool(wiki_results)},
            "schema_readiness":        {"score": schema_score, "max": 20, "raw": len(schema_ready)},
            "nap_consistency":         {"score": nap_score, "max": 15, "raw": consistent},
            "linkedin_presence":       {"score": linkedin_score, "max": 15, "raw": bool(linkedin)},
            "crunchbase_presence":     {"score": cb_score, "max": 10, "raw": bool(crunchbase)},
        },
        "label": _kp_label(total),
        "has_kp": wiki_score >= 25,
        "wikipedia_url": wiki_url,
        "linkedin_url": linkedin_url,
        "needs_wikidata": wiki_score == 0,
        "needs_wikipedia": wiki_score == 0,
        "needs_search_console_claim": wiki_score >= 25 and linkedin_score >= 15,
    }


def _kp_label(score: float) -> str:
    if score >= 80:
        return "OTIMIZADO — Knowledge Panel elegível, reivindicar via Search Console"
    if score >= 50:
        return "PARCIAL — Presença básica estabelecida, criar Wikidata/Wikipedia"
    if score >= 25:
        return "INICIAL — Presença mínima, precisa de Wikipedia + schema.org"
    return "AUSENTE — Sem condições de gerar Knowledge Panel"


def generate_wikidata_profile(entity: str, title: str = "", company: str = "") -> str:
    """Generate a Wikidata-ready profile text for copy-paste submission.

    Wikidata fields:
      - Label (obrigatório): nome completo
      - Description (obrigatório): breve descrição (cargo + área)
      - Aliases: variações do nome
      - Instance of (P31): human (Q5)
      - Employer (P108): empresa/organização
      - Position held (P39): cargo
      - Official website (P856): URL oficial
      - LinkedIn profile (P2034): URL do LinkedIn
    """
    parts = []
    parts.append("=== WIKIDATA — PROFILE READY TO SUBMIT ===")
    parts.append("")
    parts.append(f"Label (en): {entity}")
    parts.append(f"Label (pt): {entity}")
    parts.append("")
    desc = f"{title} at {company}" if title and company else title or company or "Professional"
    parts.append(f"Description (en): {desc}")
    parts.append(f"Description (pt): {desc}")
    parts.append("")
    parts.append("Aliases: " + ", ".join(_generate_aliases(entity)))
    parts.append("")
    parts.append("Statements:")
    parts.append("  Instance of (P31): human (Q5) — always applies")
    if company:
        parts.append(f"  Employer (P108): {company}")
    if title:
        parts.append(f"  Position held (P39): {title}")
    parts.append("")
    parts.append("REQUIRED REFERENCES:")
    parts.append("- At least 2 independent reliable sources (news articles, LinkedIn, company website)")
    parts.append("- LinkedIn profile link")
    parts.append("- Company/Institutional profile link")
    parts.append("")
    parts.append("SUBMIT AT: https://www.wikidata.org/wiki/Special:NewItem")
    return "\n".join(parts)


def _generate_aliases(entity: str) -> list[str]:
    """Name variations for Wikidata aliases."""
    parts = entity.strip().split()
    aliases = []
    if len(parts) >= 2:
        aliases.append(f"{parts[0]} {parts[-1]}")
        aliases.append(f"{parts[-1]}, {parts[0]}")
        if len(parts) >= 3:
            aliases.append(" ".join(parts[:2]))
            aliases.append(" ".join([parts[0]] + parts[2:]))
    return aliases


def generate_schema_org(entity: str, title: str = "", company: str = "",
                         site_url: str = "", linkedin_url: str = "") -> str:
    """Generate schema.org/Person JSON-LD ready to embed in site <head>."""
    schema = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": entity,
        "jobTitle": title or "",
        "worksFor": {
            "@type": "Organization",
            "name": company or "",
        } if company else None,
        "url": site_url or "",
        "sameAs": [
            linkedin_url or "",
        ],
    }
    if not schema["worksFor"]:
        del schema["worksFor"]

    html = '<script type="application/ld+json">\n'
    html += json.dumps(schema, indent=2, ensure_ascii=False)
    html += '\n</script>'
    return html


def generate_faq_schema(questions: list[dict]) -> str:
    """Generate schema.org/FAQPage JSON-LD.

    questions: list of {"question": str, "answer": str}
    """
    main_entity = []
    for q in questions:
        main_entity.append({
            "@type": "Question",
            "name": q.get("question", ""),
            "acceptedAnswer": {
                "@type": "Answer",
                "text": q.get("answer", ""),
            },
        })

    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": main_entity,
    }

    html = '<script type="application/ld+json">\n'
    html += json.dumps(schema, indent=2, ensure_ascii=False)
    html += '\n</script>'
    return html


def wikipedia_elegibility_checklist(entity: str) -> list[dict]:
    """Generate Wikipedia eligibility checklist based on entity type."""
    return [
        {"criterion": "Notoriedade comprovada por cobertura significativa em fontes confiáveis e independentes",
         "status": "Verificar",
         "note": "Mínimo 3 fontes independentes (veículos de imprensa, livros, publicações acadêmicas)"},
        {"criterion": "Múltiplas fontes (não apenas uma) e independentes da entidade",
         "status": "Verificar",
         "note": "LinkedIn e site próprio NÃO contam como fontes independentes"},
        {"criterion": "Conteúdo verificável — cada afirmação com referência inline",
         "status": "Verificar",
         "note": "Artigos sem fontes são marcados para eliminação"},
        {"criterion": "Tom neutro, sem auto-promoção ou linguagem de marketing",
         "status": "Verificar",
         "note": "Wikipedia não é LinkedIn — linguagem deve ser enciclopédica"},
        {"criterion": "Artigo mínimo de 300-500 palavras com seções claras",
         "status": "Verificar",
         "note": "Carreira, biografia, principais realizações com referências"},
    ]


def kp_setup_guide(entity: str, snapshot: dict) -> dict:
    """Complete Knowledge Panel setup guide with steps for the operator."""
    kp = compute_knowledge_panel_score(snapshot)
    serp = snapshot.get("serp", [])

    steps = []
    if kp["needs_wikidata"]:
        steps.append({
            "order": 1,
            "action": "Criar perfil no Wikidata",
            "detail": "Acessar wikidata.org → Special:NewItem. Preencher label, description, aliases.",
            "template": "Usar gerador automático do CouncilIA (aba Wikidata Profile)",
            "time": "1-3 dias",
            "done": False,
        })
    if kp["needs_wikipedia"]:
        steps.append({
            "order": 2,
            "action": "Criar artigo na Wikipedia (se elegível)",
            "detail": "Seguir o checklist de elegibilidade. Mínimo 500 palavras, 3+ fontes.",
            "template": "Usar checklist do CouncilIA",
            "time": "1-4 semanas",
            "done": False,
        })
    steps.append({
        "order": 3,
        "action": "Padronizar NAP em todos os assets",
        "detail": "Usar exatamente o mesmo nome, cargo, descrição em LinkedIn, site, artigos, releases.",
        "template": "CouncilIA já gera assets padronizados",
        "time": "Imediato",
        "done": True,
    })
    steps.append({
        "order": 4,
        "action": "Adicionar schema.org no site gerado",
        "detail": "Inserir JSON-LD schema.org/Person no <head> do site institucional.",
        "template": "CouncilIA gera schema.org automaticamente no Site Builder",
        "time": "1-2 dias",
        "done": True,
    })
    steps.append({
        "order": 5,
        "action": "Reivindicar Knowledge Panel no Google Search Console",
        "detail": "Acessar Search Console → Knowledge Panel → Reivindicar. Requer site verificado.",
        "template": "Link: https://search.google.com/search-console/knowledge-panel",
        "time": "1-7 dias",
        "done": False,
    })
    steps.append({
        "order": 6,
        "action": "Após reivindicação: atualizar foto oficial e links sociais",
        "detail": "Adicionar foto profissional, LinkedIn, site oficial, Twitter/X.",
        "template": "Direto no Search Console após aprovação",
        "time": "Imediato após aprovação",
        "done": False,
    })

    return {
        "knowledge_panel_score": kp,
        "steps": steps,
        "completed_count": sum(1 for s in steps if s["done"]),
        "total_steps": len(steps),
        "summary": f"KP Score: {kp['total']}/100 — {kp['label']}. "
                   f"{sum(1 for s in steps if s['done'])}/{len(steps)} steps completed.",
    }
