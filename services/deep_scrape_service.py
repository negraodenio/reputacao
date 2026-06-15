import os
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

from services.serpapi_service import search
from services.firecrawl_service import scrape
from services.openrouter_service import call_openrouter

logger = logging.getLogger("councilia.deep_scrape")

TMP_DIR = Path("/tmp/political/deep_scan")
TMP_DIR.mkdir(parents=True, exist_ok=True)

def _generate_dossier(target_name: str, deep_texts: list[str]) -> str:
    texts_combined = "\n\n---\n\n".join(deep_texts)
    prompt = f"""
Você é um estrategista político e analista de inteligência militar-cibernética. Analise as seguintes transcrições brutas (markdown) de matérias jornalísticas vazadas e páginas web sobre o político adversário: {target_name}.

OBJETIVO: Criar um DOSSIÊ OPONENTE EXTREMAMENTE CIRÚRGICO baseado EXCLUSIVAMENTE nos textos fornecidos.

ESTRUTURA OBRIGATÓRIA:
1. RESUMO DOS ESCÂNDALOS: Identifique o cerne de todas as denúncias relatadas nas reportagens.
2. ALVOS E VALORES: Extraia e liste em formato de tópicos (bullet points) os nomes de empreiteiras, empresas, laranjas, valores desviados ou envolvidos citados nos textos.
3. FRAQUEZAS NARRATIVAS (O CHIFRE DE AQUILES): Aponte falhas nas explicações dadas por {target_name} nas matérias, que possam ser ridicularizadas ou expostas pela campanha do nosso cliente.
4. SUGESTÃO DE ATAQUE: Indique uma linha de frente agressiva a ser usada nos debates e redes sociais para desestabilizar o oponente.

TEXTOS BRUTOS COLETADOS:
{texts_combined[:40000]}
"""
    
    res = call_openrouter(
        prompt=prompt,
        system_prompt="Você é um expert implacável em inteligência competitiva e análise de vulnerabilidades políticas. Responda em Português do Brasil com formatação HTML limpa (use tags <h3>, <ul>, <li>, <p> para estruturar a resposta, sem usar markdown como ** ou ##). O texto deve ser retornando pronto para renderização web.",
        temperature=0.3
    )
    return res["choices"][0]["message"]["content"]

def _generate_defense(target_name: str, deep_texts: list[str]) -> str:
    texts_combined = "\n\n---\n\n".join(deep_texts)
    prompt = f"""
Você é um Gerente de Crise sênior (Fixer). Nosso cliente, o político {target_name}, está sofrendo fortes ataques difamatórios baseados nas matérias jornalísticas abaixo. Analise os textos brutos transcritos.

OBJETIVO: Criar um ESCUDO NARRATIVO (Defesa Profunda) para blindar o cliente contra acusações maliciosas. Baseie-se EXCLUSIVAMENTE nos textos fornecidos para prever a bala de prata do inimigo.

ESTRUTURA OBRIGATÓRIA:
1. RAIOS-X DO ATAQUE: Liste as acusações exatas feitas pela mídia (qual é o argumento central dos jornalistas ou oponentes nas matérias).
2. LINHA DE DEFESA IRREFUTÁVEL: Crie um argumento lógico, jurídico ou social para cada ponto de ataque que desmonte a acusação. Ache o buraco na reportagem.
3. NOTA DE ESCLARECIMENTO: Escreva uma nota oficial à imprensa (pronta para uso), cirúrgica, imponente e protetora, projetada para encerrar o assunto imediatamente, passando confiança ao eleitor.

TEXTOS BRUTOS COLETADOS:
{texts_combined[:40000]}
"""
    
    res = call_openrouter(
        prompt=prompt,
        system_prompt="Você é o maior especialista em contenção de crise e relações públicas estratégicas da América Latina. Responda em Português do Brasil com formatação HTML limpa (use tags <h3>, <ul>, <li>, <p> para estruturar a resposta, sem usar markdown como ** ou ##). O texto deve ser retornando pronto para renderização web.",
        temperature=0.3
    )
    return res["choices"][0]["message"]["content"]

def run_deep_scan_async(slug: str, target_name: str, scan_type: str):
    """
    Roda a extração pesada em background.
    scan_type: 'dossier' (oponente) ou 'defense' (cliente).
    """
    status_file = TMP_DIR / f"{slug}_{scan_type}_status.json"
    
    def worker():
        try:
            status_data = {"status": "running", "step": "Infiltrando na SERP e varrendo links...", "result": None}
            status_file.write_text(json.dumps(status_data))
            
            # 1. SerpAPI (pegar links com palavras associadas a denúncias/crises)
            query = f'"{target_name}" (escândalo OR crime OR denúncia OR polícia OR investigação OR polêmica OR fraude)'
            results = search(query, num=5)
            
            links = []
            for r in results:
                link = r.get("link", "")
                if "youtube.com" not in link and "instagram.com" not in link and "facebook.com" not in link:
                    links.append(link)
            
            links = links[:3] # Máximo 3 portais profundos
            
            if not links:
                status_data["status"] = "completed"
                status_data["result"] = "<p>Nenhuma matéria incriminatória ou notícia estruturada foi encontrada para este alvo nas buscas profundas da SERP.</p>"
                status_file.write_text(json.dumps(status_data))
                return

            status_data["step"] = f"Extraindo dados brutos (Deep Scrape) de {len(links)} domínios com Firecrawl..."
            status_file.write_text(json.dumps(status_data))
            
            # 2. Firecrawl
            deep_texts = []
            for link in links:
                try:
                    text = scrape(link)
                    if text and len(text) > 300: # IGNORA SCRAPE VAZIO OU COM ERRO
                        deep_texts.append(f"ORIGEM DA INFORMAÇÃO: {link}\n{text}")
                except Exception as e:
                    logger.warning(f"Erro no scrape do link {link}: {e}")
                    
            if not deep_texts:
                status_data["status"] = "completed"
                status_data["result"] = "<p>Os links encontrados bloquearam a raspagem profunda ou não retornaram conteúdo útil suficiente.</p>"
                status_file.write_text(json.dumps(status_data))
                return
                
            status_data["step"] = "Destilando inteligência narrativa com LLM Estratégico..."
            status_file.write_text(json.dumps(status_data))
            
            # 3. LLM
            if scan_type == 'dossier':
                report = _generate_dossier(target_name, deep_texts)
            else:
                report = _generate_defense(target_name, deep_texts)
                
            status_data["status"] = "completed"
            status_data["result"] = report
            status_data["sources"] = links
            status_file.write_text(json.dumps(status_data))
            
        except Exception as e:
            logger.error(f"Erro crítico no Deep Scan: {e}")
            status_data = {"status": "error", "message": str(e)}
            status_file.write_text(json.dumps(status_data))
            
    thread = threading.Thread(target=worker)
    thread.start()
    return {"status": "started"}

def check_deep_scan_status(slug: str, scan_type: str) -> dict:
    status_file = TMP_DIR / f"{slug}_{scan_type}_status.json"
    if not status_file.exists():
        return {"status": "not_found"}
    try:
        return json.loads(status_file.read_text())
    except Exception as e:
        return {"status": "error", "message": f"Erro de leitura: {str(e)}"}
