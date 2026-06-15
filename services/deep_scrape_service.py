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
4. ANTECEDENTES JURÍDICOS E GOVERNAMENTAIS: Liste inquéritos, processos no Jusbrasil, Escavador ou irregularidades no TCU encontrados contra o alvo, informando a gravidade.
5. SUGESTÃO DE ATAQUE: Indique uma linha de frente agressiva a ser usada nos debates e redes sociais para desestabilizar o oponente.

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
3. DEFESA JURÍDICA E GOVERNAMENTAL: Se houver processos (Jusbrasil/Escavador) ou apontamentos do TCU, crie a narrativa de mitigação para desqualificar a importância desses passivos judiciais.
4. NOTA DE ESCLARECIMENTO: Escreva uma nota oficial à imprensa (pronta para uso), cirúrgica, imponente e protetora, projetada para encerrar o assunto imediatamente, passando confiança ao eleitor.

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
            
            # 1. SerpAPI (pesquisas simultâneas: mídia, justiça e governo)
            import concurrent.futures
            
            q_media = f'"{target_name}" (escândalo OR crime OR denúncia OR polícia OR investigação OR polêmica OR fraude)'
            q_legal = f'site:jusbrasil.com.br OR site:escavador.com "{target_name}"'
            q_gov = f'site:tcu.gov.br OR site:transparencia.gov.br "{target_name}"'
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                f_media = executor.submit(search, q_media, 5)
                f_legal = executor.submit(search, q_legal, 3)
                f_gov = executor.submit(search, q_gov, 3)
                
                res_media = f_media.result()
                res_legal = f_legal.result()
                res_gov = f_gov.result()
            
            links = []
            def _add_links(results, max_count):
                added = 0
                for r in results:
                    link = r.get("link", "")
                    if "youtube.com" not in link and "instagram.com" not in link and "facebook.com" not in link:
                        links.append(link)
                        added += 1
                        if added >= max_count:
                            break
                            
            _add_links(res_media, 2)
            _add_links(res_legal, 2)
            _add_links(res_gov, 1)
            
            if not links:
                status_data["status"] = "completed"
                status_data["result"] = "<p>Nenhuma matéria incriminatória ou notícia estruturada foi encontrada para este alvo nas buscas profundas da SERP.</p>"
                status_file.write_text(json.dumps(status_data))
                return

            status_data["step"] = f"Araponga ativado: Raspando e baixando {len(links)} portais/tribunais na íntegra..."
            status_file.write_text(json.dumps(status_data))
            
            # 2. Firecrawl Paralelo (Muito mais rápido e bypassa limites de tempo)
            deep_texts = []
            
            def _fetch_link(l):
                try:
                    txt = scrape(l)
                    if txt and len(txt) > 300:
                        return f"ORIGEM DA INFORMAÇÃO: {l}\n{txt}"
                except Exception as e:
                    logger.warning(f"Erro no scrape do link {l}: {e}")
                return None
                
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(links)) as executor:
                future_to_url = {executor.submit(_fetch_link, l): l for l in links}
                for future in concurrent.futures.as_completed(future_to_url):
                    data = future.result()
                    if data:
                        deep_texts.append(data)
                    
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
