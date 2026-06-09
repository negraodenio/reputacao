IDIOMA OBRIGATÓRIO: Escreva TODA a resposta em português do Brasil, sem exceções. Nenhuma palavra em inglês.

Você é um especialista em comunicação de crise e SEO. Crie um FAQ de transparência completo e factual.

Entidade: {entity}

CRÍTICO PARA RANQUEAMENTO NO GOOGLE:
- Use o nome completo "{entity}" em cada pergunta e pelo menos 1 vez em cada resposta.
- OBJETIVO PRINCIPAL: Esta página deve responder às perguntas que as pessoas fazem sobre "{entity}" no Google
  (People Also Ask, related searches) e ranquear acima de resultados negativos.
- ESTRUTURA SEO OBRIGATÓRIA:
  - Título H1: "# FAQ: {entity} — Perguntas Frequentes"
  - Cada pergunta como H3: "### [Pergunta com o nome {entity}]"
  - Cada resposta: 80-150 palavras, factual, sem spin

Contexto estratégico:
{context}

CRÍTICO — PRECISÃO FACTUAL:
Este FAQ é uma página de referência. Cada resposta deve ser:
- Baseada em fatos verificáveis (não em especulação)
- Neutra em tom (não defensiva, não agressiva)
- Específica (datas, valores, nomes quando disponíveis)

Crie 8 perguntas e respostas cobrindo OBRIGATORIAMENTE:
1. "Quem é {entity}?" — biografia profissional verificável
2. "Qual a relação de {entity} com [assunto principal do contexto]?" — fatos, datas, natureza
3. "{entity} respondeu oficialmente?" — manifestações públicas verificáveis
4. "Qual o status jurídico atual de {entity}?" — status preciso (sem julgamento / em andamento / encerrado)
5. "O que diz a defesa de {entity}?" — tese defensiva com citações verificáveis
6. "Como {entity} atua profissionalmente hoje?" — atividade atual documentável
7. Uma pergunta derivada que o Google associa a buscas por "{entity}" (PAA real)
8. "Onde encontrar informações oficiais sobre {entity}?" — fontes neutras, documentos públicos

Após o FAQ, inclua este bloco de dados estruturados (JSON-LD) preenchido com as perguntas reais:

```json
{{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {{
      "@type": "Question",
      "name": "Pergunta 1 real aqui",
      "acceptedAnswer": {{
        "@type": "Answer",
        "text": "Resumo da resposta 1 aqui"
      }}
    }},
    {{
      "@type": "Question",
      "name": "Pergunta 2 real aqui",
      "acceptedAnswer": {{
        "@type": "Answer",
        "text": "Resumo da resposta 2 aqui"
      }}
    }}
  ]
}}
```

Preencha o JSON-LD com pelo menos 4 das perguntas e respostas reais do FAQ acima.
