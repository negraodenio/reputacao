"""PDF generation for audit reports and comparisons using fpdf2."""
from datetime import datetime
from fpdf import FPDF

_ASCII = str.maketrans({
    "\u2014": "-", "\u2013": "-", "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"', "\u2026": "...", "\u00e0": "a",
    "\u00e1": "a", "\u00e2": "a", "\u00e3": "a", "\u00e4": "a",
    "\u00e7": "c", "\u00e8": "e", "\u00e9": "e", "\u00ea": "e",
    "\u00eb": "e", "\u00ec": "i", "\u00ed": "i", "\u00ee": "i",
    "\u00ef": "i", "\u00f1": "n", "\u00f2": "o", "\u00f3": "o",
    "\u00f4": "o", "\u00f5": "o", "\u00f6": "o", "\u00f9": "u",
    "\u00fa": "u", "\u00fb": "u", "\u00fc": "u", "\u00c0": "A",
    "\u00c1": "A", "\u00c2": "A", "\u00c3": "A", "\u00c4": "A",
    "\u00c7": "C", "\u00c9": "E", "\u00ca": "E", "\u00cd": "I",
    "\u00d3": "O", "\u00d4": "O", "\u00d5": "O", "\u00d6": "O",
    "\u00da": "U", "\u00dc": "U", "\u00f0": "d",
})


def _ascii(text: str) -> str:
    return text.translate(_ASCII) if text else ""

WIDTH = 210
MARGIN = 20
BODY_W = WIDTH - 2 * MARGIN
CO1 = (192, 192, 192)
CO2 = (80, 80, 80)
CRED = (192, 57, 43)
CGREEN = (39, 174, 96)
CBLACK = (30, 30, 30)


class ReportPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "", 7)
            self.set_text_color(*CO1)
            self.cell(0, 6, "CouncilIA  |  Reputation Intelligence", align="L")
            self.cell(0, 6, _ascii(f"p. {self.page_no()}"), align="R", new_x="LMARGIN", new_y="NEXT")
            self.line(MARGIN, 14, WIDTH - MARGIN, 14)
            self.ln(4)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 6)
        self.set_text_color(*CO1)
        self.cell(0, 6, "CONFIDENTIAL", align="C")

    def section_title(self, num: str, label: str):
        self.add_page_if_full(20)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*CRED)
        self.cell(0, 7, _ascii(f"{num}  {label}"), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*CO1)
        self.line(MARGIN, self.get_y(), WIDTH - MARGIN, self.get_y())
        self.ln(3)

    def add_page_if_full(self, needed: int = 30):
        if self.get_y() + needed > self.h - 16:
            self.add_page()

    def body_text(self, text: str):
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*CBLACK)
        self.add_page_if_full()
        self.multi_cell(0, 4.2, _ascii(text))
        self.ln(2)

    def metric_grid(self, items: list[tuple[str, str, tuple | None]]):
        n_rows = (len(items) + 1) // 2
        self.add_page_if_full(n_rows * 18 + 10)
        x0 = self.get_x()
        y0 = self.get_y()
        col_w = BODY_W / 2
        for i, (label, value, color) in enumerate(items):
            x = x0 + (i % 2) * col_w
            y = y0 + (i // 2) * 18
            self.set_xy(x, y)
            self.set_fill_color(245, 245, 245)
            self.set_draw_color(*CO1)
            self.rect(x, y, col_w - 1, 17, style="F")
            self.set_font("Helvetica", "", 6)
            self.set_text_color(*CO2)
            self.set_xy(x + 4, y + 2)
            self.cell(col_w - 8, 4, _ascii(label))
            self.set_font("Helvetica", "B", 16)
            if color:
                self.set_text_color(*color)
            else:
                self.set_text_color(*CBLACK)
            self.set_xy(x + 4, y + 7)
            self.cell(col_w - 8, 8, _ascii(str(value)))
        self.set_y(y0 + n_rows * 18)


def generate_audit_pdf(entity_name: str, threat_level: str, generated_at: str,
                       sections: dict, npa: dict) -> bytes:
    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    # Title block
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*CBLACK)
    pdf.cell(0, 10, _ascii(entity_name), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*CO2)
    pdf.cell(0, 5, _ascii(f"Relatorio de Auditoria  |  {generated_at}"), new_x="LMARGIN", new_y="NEXT")
    colors = {"CRITICAL": (192, 57, 43), "HIGH": (211, 84, 0), "MEDIUM": (201, 162, 39), "LOW": (39, 174, 96)}
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*colors.get(threat_level, CO2))
    pdf.cell(0, 7, _ascii(f"Nivel de Ameaca: {threat_level}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Narrative Pressure
    pdf.section_title("02", "Pressao Narrativa")
    pdf.metric_grid([
        ("Artigos - 7 dias", str(npa.get("count_7d", 0)), None),
        ("Artigos - 30 dias", str(npa.get("count_30d", 0)), None),
        ("Momentum", npa.get("momentum", ""), None),
        ("Concentracao", npa.get("concentration", ""), None),
    ])
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*CO2)
    pdf.cell(0, 5, _ascii(f"Fonte Mais Agressiva: {npa.get('most_aggressive', '-')}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    for domain, count, dtype in npa.get("top_domains", []):
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*CBLACK)
        pdf.cell(0, 4, _ascii(f"   {domain}  ({count})  [{dtype}]"),
                 new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.body_text(sections.get("npa_interpretation", ""))

    # Sections 01, 03-07
    mapping = [
        ("01", "Sumario Executivo", "reputation_summary"),
        ("03", "Ativos Positivos", "positive_assets"),
        ("04", "Analise Narrativa", "narrative_analysis"),
        ("05", "Sinais Negativos", "negative_signals"),
        ("06", "Associacoes Descobertas", "associations"),
        ("07", "Posicionamento Recomendado", "recommended_positioning"),
    ]
    for num, label, key in mapping:
        text = sections.get(key, "")
        if text.strip():
            pdf.add_page_if_full()
            pdf.section_title(num, label)
            pdf.body_text(text)

    return pdf.output()


def generate_compare_pdf(entity_name: str, generated_at: str,
                         old_snap: dict, new_snap: dict, diff: dict) -> bytes:
    pdf = ReportPDF()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*CBLACK)
    pdf.cell(0, 10, _ascii(entity_name), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*CO2)
    pdf.cell(0, 5, _ascii(f"Relatorio de Evolucao  |  {generated_at}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Before / After side by side
    pdf.set_font("Helvetica", "B", 8)
    col_w = BODY_W / 2
    for title, snap, c in [
        ("ANTES - " + diff.get("period", {}).get("from", ""), old_snap, CRED),
        ("DEPOIS - " + diff.get("period", {}).get("to", ""), new_snap, CGREEN),
    ]:
        x = MARGIN + (0 if c == CRED else col_w)
        pdf.set_xy(x, pdf.get_y())
        pdf.set_fill_color(*c)
        pdf.set_text_color(255, 255, 255)
        pdf.rect(x, pdf.get_y(), col_w - 1, 6, style="F")
        pdf.cell(col_w - 1, 6, _ascii(f"  {title}"), align="L")
        pdf.set_xy(x, pdf.get_y() + 7)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*CBLACK)
        metrics = [
            f"NPA:          {snap.get('npa_score', '-')}",
            f"Neg. Share:   {snap.get('page_1_negative_ratio', 0):.0%}",
            f"Top-3 Neg.:   {snap.get('top_3_negative_count', 0)}",
            f"Ativos:       {snap.get('controlled_assets', 0)}",
            f"Dominios Jur.: {snap.get('legal_domain_count', 0)}",
        ]
        for m in metrics:
            pdf.set_x(x + 4)
            pdf.cell(col_w - 8, 4, _ascii(m))
    pdf.ln(40)

    # Deltas
    pdf.section_title("", "Evolucao")
    pdf.metric_grid([
        ("Deslocamento Negativo", _ascii(f"-{diff.get('negative_displacement', 0)} pos."), CGREEN),
        ("Crescimento Ativos", _ascii(f"+{diff.get('asset_penetration_growth', 0)}"), CGREEN),
        ("Top-3 Negativos", _ascii(str(diff.get("top_3_negative_delta", 0))), CRED if diff.get("top_3_negative_delta", 0) > 0 else CGREEN),
    ])
    pdf.ln(4)

    # Ranking movement
    rm = diff.get("ranking_movement", {})
    pdf.section_title("", "Movimentacao de Ranking")
    y0 = pdf.get_y()
    for idx, (header, items) in enumerate([
        ("SUBIRAM", rm.get("moved_up", [])),
        ("CAIRAM", rm.get("moved_down", [])),
        ("ENTRARAM", rm.get("entered", [])),
    ]):
        x = MARGIN + idx * (col_w + 2)
        pdf.set_xy(x, y0)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*CO2)
        pdf.cell(col_w, 5, header)
        pdf.set_font("Helvetica", "", 6.5)
        pdf.set_text_color(*CBLACK)
        for item in items[:6]:
            pdf.set_x(x + 2)
            if "from" in item:
                pdf.cell(col_w - 2, 3.5, _ascii(f"{item['domain']}  #{item['from']} -> #{item['to']}"))
            else:
                pdf.cell(col_w - 2, 3.5, _ascii(f"{item['domain']}  #{item['position']}"))

    # New negative entrants
    if rm.get("new_negative_entrants"):
        pdf.ln(8)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*CRED)
        pdf.cell(0, 6, "NOVOS ENTRANTES NEGATIVOS", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*CBLACK)
        for m in rm["new_negative_entrants"]:
            pdf.cell(0, 4, _ascii(f"  {m['domain']} na posicao #{m['position']}"), new_x="LMARGIN", new_y="NEXT")

    return pdf.output()


def serve_pdf(pdf_bytes: bytes, filename: str = "report.pdf"):
    from fastapi.responses import Response
    if isinstance(pdf_bytes, bytearray):
        pdf_bytes = bytes(pdf_bytes)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
