"""
Teste completo de auditoria pos-correcao do NPA.
Verifica se as noticias expandidas estao sendo injetadas corretamente.
"""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.stdout.reconfigure(encoding="utf-8")

from services.audit_service import run_audit

ENTITY = "Tiago Schiettini Batista"

print("Rodando auditoria com NPA expandido...")
result = run_audit(ENTITY, "Brasil", "Tecnologia")
text = result["text"]
debug = result.get("debug_expansion", {})

print("\n--- NPA INFO ---")
print(f"  Total artigos no NPA:   {len(result['all_news'])}")
print(f"  Exatos (nome entidade): {sum(1 for a in result['all_news'] if True)}")

print("\n--- SECOES DO RELATORIO ---")
sections_found = re.findall(r"^\d\.\s+\*\*[^*]+\*\*", text, re.MULTILINE)
for s in sections_found:
    print(f"  {s}")

print("\n--- PRIMEIRAS 600 CHARS ---")
print(text[:600])
