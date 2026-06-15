"""
Continuous Monitoring Engine — SERP Watcher, News Watcher, NPA Delta Monitor,
Alert Dispatcher.

State stored in JSON files under monitoring/{slug}/ for zero-database operation.
Watches compare latest snapshot against fresh API data and triggers alerts.

Background scheduler runs automatically via asyncio loop started in app/main.py.
No external cron or Task Scheduler required.
"""
import json
import os
import tempfile
import smtplib
import asyncio
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from urllib.parse import urlparse
from services.constants import classify_domain

import os
if os.environ.get("VERCEL"):
    MONITOR_DIR = Path("/tmp/monitoring")
else:
    MONITOR_DIR = Path(__file__).parent.parent / "monitoring"

# Alertas mais antigos que N dias são removidos do estado (pruning)
ALERT_RETENTION_DAYS = 90


# ── TRIGGER DEFINITIONS ────────────────────────────────────────────────────

TRIGGERS = {
    "new_negative_domain": {
        "label": "Novo Domínio Negativo",
        "level": "CRÍTICO",
        "condition": "Novo domínio com sentimento negativo entra no top-10 SERP",
        "action": "Notificação imediata + sugestão de resposta pelo arquétipo",
    },
    "legal_domain_detected": {
        "label": "Domínio Jurídico Detectado",
        "level": "CRÍTICO",
        "condition": "Domínio do tipo 'jurídico' (JusBrasil, TJ, STF, MP) entra na SERP",
        "action": "Alerta + ativar playbook criminal/administrativo automaticamente",
    },
    "npa_delta_10": {
        "label": "NPA +10 em uma Run",
        "level": "ALTO",
        "condition": "NPA sobe 10+ pontos entre dois snapshots consecutivos",
        "action": "Notificação + relatório de diff + sugestão de conteúdo urgente",
    },
    "top3_contaminated": {
        "label": "Top-3 Contaminado",
        "level": "ALTO",
        "condition": "Posições 1, 2 ou 3 passam a ter resultado negativo",
        "action": "Notificação + Google Ads brand defense sugerido imediatamente",
    },
    "new_news_article": {
        "label": "Nova Matéria Detectada",
        "level": "MÉDIO",
        "condition": "Nova matéria no GNews sobre a entidade",
        "action": "Notificação com sentimento + link para review do operador",
    },
    "positive_coverage": {
        "label": "Cobertura Positiva Detectada",
        "level": "INFO",
        "condition": "Nova cobertura positiva detectada (após ação do operador)",
        "action": "Notificação positiva + atualização do NPA para baixo",
    },
    "auto_reaudit_triggered": {
        "label": "Reauditoria Automática Disparada",
        "level": "INFO",
        "condition": "Alerta CRÍTICO detectado → reauditoria automática iniciada",
        "action": "Nova auditoria completa para capturar estado atual",
    },
}


# ── FILE I/O — ATOMIC WRITES ───────────────────────────────────────────────

def _ensure_monitor_dir(slug: str) -> Path:
    d = MONITOR_DIR / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def _atomic_write(path: Path, data: dict) -> None:
    """Escrita atômica: escreve em arquivo temporário → renomeia.
    Elimina risco de corrupção se o processo for interrompido durante a escrita.
    """
    text = json.dumps(data, indent=2, ensure_ascii=False)
    # Cria temp no mesmo diretório para garantir que rename é atômico (mesmo filesystem)
    dir_ = path.parent
    fd, tmp_path = tempfile.mkstemp(dir=dir_, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_path, path)  # atômico em Windows e Unix
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _load_monitor_state(slug: str) -> dict:
    path = _ensure_monitor_dir(slug) / "state.json"
    if not path.exists():
        return _blank_state(slug)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        # Arquivo corrompido — retorna estado limpo sem apagar o original
        # (o original fica como .bak para diagnóstico)
        bak = path.with_suffix(".bak")
        try:
            path.rename(bak)
        except OSError:
            pass
        return _blank_state(slug)


def _save_monitor_state(slug: str, state: dict) -> None:
    path = _ensure_monitor_dir(slug) / "state.json"
    _atomic_write(path, state)


def _blank_state(slug: str) -> dict:
    return {
        "slug": slug,
        "watchers": {},
        "alerts": [],
        "last_check": None,
        "mode": "vigilance",
        "config": {},
    }


# ── PRUNING ────────────────────────────────────────────────────────────────

def _prune_alerts(alerts: list[dict]) -> list[dict]:
    """Remove alertas mais antigos que ALERT_RETENTION_DAYS."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=ALERT_RETENTION_DAYS)).isoformat()
    return [a for a in alerts if a.get("timestamp", "9999") >= cutoff]


# ── EMAIL ──────────────────────────────────────────────────────────────────

def _send_email_alert(alert: dict, email_to: str, config: dict) -> dict:
    """
    Envia alerta por email via SMTP.

    Configuração via variáveis de ambiente (ou config dict):
      COUNCILIA_SMTP_HOST    (padrão: smtp.gmail.com)
      COUNCILIA_SMTP_PORT    (padrão: 587)
      COUNCILIA_SMTP_USER    (endereço Gmail)
      COUNCILIA_SMTP_PASS    (senha de app Gmail — não a senha normal)

    Para Gmail:
      1. Ativar verificação em dois passos na conta Google
      2. Acessar myaccount.google.com/apppasswords
      3. Criar senha de app "CouncilIA"
      4. Usar essa senha em COUNCILIA_SMTP_PASS
    """
    smtp_host = config.get("smtp_host") or os.environ.get("COUNCILIA_SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(config.get("smtp_port") or os.environ.get("COUNCILIA_SMTP_PORT", 587))
    smtp_user = config.get("smtp_user") or os.environ.get("COUNCILIA_SMTP_USER", "")
    smtp_pass = config.get("smtp_pass") or os.environ.get("COUNCILIA_SMTP_PASS", "")

    if not smtp_user or not smtp_pass:
        return {"ok": False, "error": "SMTP não configurado. Definir COUNCILIA_SMTP_USER e COUNCILIA_SMTP_PASS."}

    level = alert.get("level", "INFO")
    detail = alert.get("detail", "")
    trigger = alert.get("trigger", "")
    entity = alert.get("entity", "")
    ts = alert.get("timestamp", "")[:19].replace("T", " ")

    subject = f"[CouncilIA {level}] {entity} — {TRIGGERS.get(trigger, {}).get('label', trigger)}"

    body_html = f"""
<html><body style="font-family:monospace;background:#0a0a0a;color:#e8e8e8;padding:24px;">
<div style="max-width:600px;margin:0 auto;">
  <div style="border-bottom:1px solid #333;padding-bottom:16px;margin-bottom:24px;">
    <span style="color:#c8a96e;font-size:11px;letter-spacing:0.2em;text-transform:uppercase;">CouncilIA — Alerta de Monitoramento</span>
  </div>
  <div style="font-size:24px;font-weight:600;margin-bottom:8px;color:{'#c0392b' if level == 'CRÍTICO' else '#d35400' if level == 'ALTO' else '#d4a017' if level == 'MÉDIO' else '#27ae60'};">{level}</div>
  <div style="font-size:16px;margin-bottom:24px;">{entity}</div>
  <div style="background:#111;border:1px solid #222;padding:16px;margin-bottom:16px;">
    <div style="font-size:11px;color:#666;margin-bottom:8px;text-transform:uppercase;letter-spacing:0.1em;">Detalhe</div>
    <div style="font-size:14px;">{detail}</div>
  </div>
  <div style="font-size:10px;color:#444;margin-top:24px;">
    Trigger: {trigger} &nbsp;|&nbsp; {ts} UTC
  </div>
  <div style="margin-top:16px;">
    <a href="http://localhost:8000/monitor/{entity.lower().replace(' ', '_')}"
       style="color:#c8a96e;font-size:11px;">Ver painel de monitoramento →</a>
  </div>
</div>
</body></html>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = email_to
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [email_to], msg.as_string())
        return {"ok": True}
    except smtplib.SMTPAuthenticationError:
        return {"ok": False, "error": "Autenticação SMTP falhou. Verificar COUNCILIA_SMTP_USER e COUNCILIA_SMTP_PASS."}
    except smtplib.SMTPException as e:
        return {"ok": False, "error": f"Erro SMTP: {e}"}
    except Exception as e:
        return {"ok": False, "error": f"Erro de conexão: {e}"}


# ── CONFIGURATION ──────────────────────────────────────────────────────────

def configure_monitoring(slug: str,
                          serp_freq_h: int = 6,
                          news_freq_m: int = 120,
                          crisis_serp_freq_h: int = 1,
                          crisis_news_freq_m: int = 30,
                          slack_webhook: str = "",
                          email_to: str = "",
                          smtp_host: str = "",
                          smtp_port: int = 587,
                          smtp_user: str = "",
                          smtp_pass: str = "") -> dict:
    """Configura frequência e canais de alerta para uma entidade."""
    config = {
        "serp_freq_hours": serp_freq_h,
        "news_freq_minutes": news_freq_m,
        "crisis_serp_freq_hours": crisis_serp_freq_h,
        "crisis_news_freq_minutes": crisis_news_freq_m,
        "slack_webhook": slack_webhook,
        "email_to": email_to,
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "smtp_user": smtp_user,
        "smtp_pass": smtp_pass,
    }
    state = _load_monitor_state(slug)
    state["config"] = config
    _save_monitor_state(slug, state)
    return config


# ── ALERT DISPATCH ─────────────────────────────────────────────────────────

def dispatch_alert(alert: dict, slack_webhook: str = "", email_to: str = "",
                   config: dict | None = None) -> dict:
    """Despacha alerta para Slack e/ou email."""
    results = {"dispatched": [], "failed": []}
    cfg = config or {}

    if slack_webhook:
        try:
            import httpx
            level = alert.get("level", "INFO")
            emoji = {"CRÍTICO": "🔴", "ALTO": "🟠", "MÉDIO": "🟡", "INFO": "🟢"}.get(level, "⚪")
            payload = {
                "text": (
                    f"{emoji} *[{level}] CouncilIA Monitor*\n"
                    f"*Entidade:* {alert.get('entity', '')}\n"
                    f"{alert.get('detail', '')}\n"
                    f"_Trigger: {alert.get('trigger', '')} | {alert.get('timestamp', '')[:19]} UTC_"
                ),
            }
            r = httpx.post(slack_webhook, json=payload, timeout=10)
            if r.status_code == 200:
                results["dispatched"].append("slack")
            else:
                results["failed"].append(f"slack: HTTP {r.status_code}")
        except Exception as e:
            results["failed"].append(f"slack: {e}")

    if email_to:
        result = _send_email_alert(alert, email_to, cfg)
        if result.get("ok"):
            results["dispatched"].append(f"email:{email_to}")
        else:
            results["failed"].append(f"email: {result.get('error', 'erro desconhecido')}")

    return results


def _dispatch_new_alerts(slug: str, entity: str, new_alerts: list[dict]) -> None:
    """Despacha alertas novos para todos os canais configurados."""
    if not new_alerts:
        return
    state = _load_monitor_state(slug)
    cfg = state.get("config", {})
    slack = cfg.get("slack_webhook", "")
    email = cfg.get("email_to", "")
    if not slack and not email:
        return
    for alert in new_alerts:
        alert_with_entity = {**alert, "entity": entity}
        dispatch_alert(alert_with_entity, slack_webhook=slack, email_to=email, config=cfg)


# ── CHECK FUNCTIONS ────────────────────────────────────────────────────────

def check_serp(slug: str, old_serp: list[dict], new_serp: list[dict]) -> list[dict]:
    state = _load_monitor_state(slug)
    state.setdefault("watchers", {})
    state["watchers"]["serp"] = {"last_check": datetime.now(timezone.utc).isoformat()}

    alerts = []
    old_domains = {r.get("domain", "") for r in old_serp}
    old_neg_top3 = {r.get("domain", "") for r in old_serp
                    if r.get("position", 99) <= 3 and r.get("sentiment") == "negative"}
    new_neg_top3 = {r.get("domain", "") for r in new_serp
                    if r.get("position", 99) <= 3 and r.get("sentiment") == "negative"}

    for r in new_serp:
        domain = r.get("domain", "")
        sentiment = r.get("sentiment", "neutral")

        if domain not in old_domains and sentiment == "negative":
            alerts.append({
                "trigger": "new_negative_domain",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "detail": f"Novo domínio negativo: {domain} na posição #{r.get('position')}",
                "level": TRIGGERS["new_negative_domain"]["level"],
                "domain": domain,
                "position": r.get("position"),
            })

        if classify_domain(domain) == "legal" and domain not in old_domains:
            alerts.append({
                "trigger": "legal_domain_detected",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "detail": f"Domínio jurídico detectado: {domain}",
                "level": TRIGGERS["legal_domain_detected"]["level"],
                "domain": domain,
            })

    if new_neg_top3 and not old_neg_top3:
        alerts.append({
            "trigger": "top3_contaminated",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": f"Top-3 contaminado: {', '.join(new_neg_top3)}",
            "level": TRIGGERS["top3_contaminated"]["level"],
            "domains": list(new_neg_top3),
        })

    state["watchers"]["serp"]["last_alerts"] = len(alerts)
    state["alerts"].extend(alerts)
    state["alerts"] = _prune_alerts(state["alerts"])
    state["last_check"] = datetime.now(timezone.utc).isoformat()
    _save_monitor_state(slug, state)
    return alerts


def check_news(slug: str, old_news: list[dict], new_news: list[dict]) -> list[dict]:
    state = _load_monitor_state(slug)
    state.setdefault("watchers", {})
    state["watchers"]["news"] = {"last_check": datetime.now(timezone.utc).isoformat()}

    old_urls = {a.get("url", "") for a in old_news}
    old_domains = {urlparse(a.get("url", "")).netloc.replace("www.", "") for a in old_news}

    alerts = []
    for a in new_news:
        if a.get("url", "") in old_urls:
            continue
        domain = urlparse(a.get("url", "")).netloc.replace("www.", "")
        sentiment = _classify_article_sentiment(a)

        alerts.append({
            "trigger": "new_news_article",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": f"Nova matéria: {a.get('title', '')[:80]} — {domain}",
            "level": TRIGGERS["new_news_article"]["level"],
            "url": a.get("url", ""),
            "domain": domain,
            "sentiment": sentiment,
        })

        if sentiment == "positive" and domain not in old_domains:
            alerts.append({
                "trigger": "positive_coverage",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "detail": f"Cobertura positiva em {domain}: {a.get('title', '')[:80]}",
                "level": TRIGGERS["positive_coverage"]["level"],
                "url": a.get("url", ""),
                "domain": domain,
            })

    state["watchers"]["news"]["last_alerts"] = len(alerts)
    state["alerts"].extend(alerts)
    state["alerts"] = _prune_alerts(state["alerts"])
    state["last_check"] = datetime.now(timezone.utc).isoformat()
    _save_monitor_state(slug, state)
    return alerts


def check_npa_delta(slug: str, old_npa: dict, new_npa: dict, threshold: int = 10) -> list[dict]:
    state = _load_monitor_state(slug)

    old_count = old_npa.get("count_7d", 0)
    new_count = new_npa.get("count_7d", 0)
    delta = new_count - old_count

    alerts = []
    if delta >= threshold:
        alerts.append({
            "trigger": "npa_delta_10",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": f"NPA saltou {delta} pontos: {old_count} → {new_count} artigos nos últimos 7 dias",
            "level": TRIGGERS["npa_delta_10"]["level"],
            "delta": delta,
            "old_count": old_count,
            "new_count": new_count,
        })

    if alerts:
        state["alerts"].extend(alerts)
        state["alerts"] = _prune_alerts(state["alerts"])
        state["last_check"] = datetime.now(timezone.utc).isoformat()
        _save_monitor_state(slug, state)

    return alerts


def _classify_article_sentiment(article: dict) -> str:
    title = (article.get("title", "") or "").lower()
    pos = {"sucesso", "recuperação", "crescimento", "resultado positivo", "prêmio",
           "reconhecimento", "inauguração", "expansão", "parceria", "investimento"}
    neg = {"investigação", "processo", "condenação", "crise", "escândalo", "fraude",
           "demissão", "falência", "dívida", "polêmica", "denúncia", "prisão"}
    if any(w in title for w in neg):
        return "negative"
    if any(w in title for w in pos):
        return "positive"
    return "neutral"


# ── SUMMARY & RESET ────────────────────────────────────────────────────────

def get_monitor_summary(slug: str) -> dict:
    state = _load_monitor_state(slug)
    alerts = state.get("alerts", [])
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    recent_alerts = [a for a in alerts if a.get("timestamp", "") >= cutoff]
    crisis_alerts = [a for a in recent_alerts if a.get("level") in ("CRÍTICO", "ALTO")]
    return {
        "slug": slug,
        "mode": state.get("mode", "vigilance"),
        "config": state.get("config", {}),
        "total_alerts_7d": len(recent_alerts),
        "crisis_alerts_7d": len(crisis_alerts),
        "last_check": state.get("last_check"),
        "recent_alerts": recent_alerts[-10:],
        "watchers": state.get("watchers", {}),
    }


def reset_monitoring(slug: str) -> dict:
    state = _blank_state(slug)
    _save_monitor_state(slug, state)
    return state


# ── BACKGROUND SCHEDULER ───────────────────────────────────────────────────

def get_monitored_slugs() -> list[str]:
    """Retorna todos os slugs que têm um state.json configurado."""
    if not MONITOR_DIR.exists():
        return []
    return [
        d.name for d in MONITOR_DIR.iterdir()
        if d.is_dir() and (d / "state.json").exists()
    ]


def _should_run_check(slug: str) -> bool:
    """Verifica se é hora de rodar o check para este slug, baseado na frequência configurada."""
    state = _load_monitor_state(slug)
    last_check = state.get("last_check")
    if not last_check:
        return True
    cfg = state.get("config", {})
    # Usar frequência de crise se mode == crise_ativa
    mode = state.get("mode", "vigilance")
    if mode == "crise_ativa":
        freq_hours = cfg.get("crisis_serp_freq_hours", 1)
    else:
        freq_hours = cfg.get("serp_freq_hours", 6)

    last_dt = datetime.fromisoformat(last_check)
    if last_dt.tzinfo is None:
        last_dt = last_dt.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
    return elapsed >= freq_hours


async def run_background_monitoring():
    """
    Loop assíncrono que roda em segundo plano enquanto o servidor estiver ativo.

    A cada 5 minutos verifica todos os slugs monitorados.
    Para cada slug, checa se é hora de rodar o check baseado na frequência configurada.
    Se alerta CRÍTICO for detectado, dispara reauditoria automática.
    """
    import logging
    logger = logging.getLogger("councilia.monitor")

    # Aguarda 30s para o servidor inicializar completamente
    await asyncio.sleep(30)
    logger.info("CouncilIA Background Monitor iniciado.")

    while True:
        try:
            slugs = get_monitored_slugs()
            for slug in slugs:
                if not _should_run_check(slug):
                    continue
                try:
                    await _auto_check_slug(slug, logger)
                except Exception as e:
                    logger.error(f"Erro no check automático de {slug}: {e}")
        except Exception as e:
            logger.error(f"Erro no loop de monitoramento: {e}")

        # Checa a cada 5 minutos se algum slug precisa de check
        await asyncio.sleep(300)


async def _auto_check_slug(slug: str, logger) -> None:
    """Executa check completo de um slug e dispara ações automáticas."""
    from services.snapshot_service import get_two_latest_snapshots
    from services.gnews_service import fetch_news

    snaps = get_two_latest_snapshots(slug)
    if not snaps or len(snaps) < 2:
        return

    old_snap, new_snap = snaps[0], snaps[1]
    entity = new_snap.get("entity", slug)

    old_serp = old_snap.get("serp", [])
    new_serp = new_snap.get("serp", [])
    old_news = old_snap.get("news", [])

    # Busca notícias frescas
    try:
        fresh_news = fetch_news(entity)
    except Exception:
        fresh_news = []

    # Roda os checks
    serp_alerts = check_serp(slug, old_serp, new_serp)
    news_alerts = check_news(slug, old_news, fresh_news)
    old_npa = old_snap.get("narrative_pressure", {})
    new_npa = new_snap.get("narrative_pressure", {})
    npa_alerts = check_npa_delta(slug, old_npa, new_npa)

    all_new_alerts = serp_alerts + news_alerts + npa_alerts

    if all_new_alerts:
        logger.info(f"[{slug}] {len(all_new_alerts)} alertas novos: "
                    f"{[a['trigger'] for a in all_new_alerts]}")
        # Despacha para Slack/email
        _dispatch_new_alerts(slug, entity, all_new_alerts)

    # Reauditoria automática se alerta CRÍTICO
    critical = [a for a in all_new_alerts if a.get("level") == "CRÍTICO"]
    if critical:
        logger.warning(f"[{slug}] Alerta CRÍTICO → disparando reauditoria automática")
        await _trigger_reaudit(slug, entity, critical, logger)


async def _trigger_reaudit(slug: str, entity: str, critical_alerts: list[dict],
                           logger) -> None:
    """
    Dispara reauditoria completa quando alerta CRÍTICO é detectado.
    Registra o evento no estado de monitoramento.
    Roda em thread separada para não bloquear o loop asyncio.
    """
    import concurrent.futures

    def _run_audit_sync():
        from services.audit_service import run_audit
        # Tenta extrair country/industry do snapshot mais recente
        from services.snapshot_service import get_latest_snapshot
        snap = get_latest_snapshot(slug)
        country = snap.get("country", "Brasil") if snap else "Brasil"
        industry = snap.get("industry", "") if snap else ""
        return run_audit(entity, country=country, industry=industry)

    loop = asyncio.get_event_loop()
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            await loop.run_in_executor(pool, _run_audit_sync)

        # Registra evento de reauditoria no estado
        state = _load_monitor_state(slug)
        state["alerts"].append({
            "trigger": "auto_reaudit_triggered",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "detail": f"Reauditoria automática concluída após {len(critical_alerts)} alerta(s) CRÍTICO(s): "
                      f"{critical_alerts[0].get('detail', '')[:80]}",
            "level": "INFO",
        })
        state["alerts"] = _prune_alerts(state["alerts"])
        _save_monitor_state(slug, state)
        logger.info(f"[{slug}] Reauditoria automática concluída.")

    except Exception as e:
        logger.error(f"[{slug}] Reauditoria automática falhou: {e}")
