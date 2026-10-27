"""PDF documents: monthly payslips and the dashboard summary (ReportLab).

Documents follow the request language. Khmer needs a Khmer font plus text shaping
(uharfbuzz) so that subscript consonants and vowels are placed correctly; the
Windows font 'Khmer UI' is used when available, otherwise the PDF falls back to English.
"""
import os
from datetime import datetime
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..core import i18n
from ..core.i18n import t
from ..core.logging import get_logger

log = get_logger("pdf")

INK = colors.HexColor("#0F172A")
MUTED = colors.HexColor("#64748B")
LINE = colors.HexColor("#E2E8F0")
SOFT = colors.HexColor("#F1F5F9")
TEAL = colors.HexColor("#0F766E")

SYMBOLS = {"USD": "$", "EUR": "€", "SGD": "S$", "KHR": "KHR "}
FONT_DIRS = [Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts", Path("/usr/share/fonts/truetype/khmeros")]
KHMER_FONTS = (("KhmerUI.ttf", "KhmerUIb.ttf"), ("KhmerOS.ttf", "KhmerOS.ttf"))


def money(value: float, currency: str = "USD") -> str:
    symbol = SYMBOLS.get(currency, currency + " ")
    text = f"{symbol}{abs(value):,.2f}"
    return "-" + text if value < 0 else text


def month_label(key: str) -> str:
    y, m = map(int, key.split("-"))
    return f"{i18n.month_name(m)} {y}"


@lru_cache
def _khmer_fonts() -> tuple[str, str] | None:
    """Register a Khmer font once; returns (regular, bold) font names or None."""
    for regular, bold in KHMER_FONTS:
        for folder in FONT_DIRS:
            if (folder / regular).exists():
                pdfmetrics.registerFont(TTFont("Khmer", str(folder / regular)))
                bold_path = folder / bold if (folder / bold).exists() else folder / regular
                pdfmetrics.registerFont(TTFont("Khmer-Bold", str(bold_path)))
                return "Khmer", "Khmer-Bold"
    log.warning("No Khmer font found - PDFs are generated in English")
    return None


class _Doc:
    """Fonts and paragraph styles for one document in the current language."""

    def __init__(self):
        fonts = _khmer_fonts() if i18n.language() == "km" else None
        if i18n.language() == "km" and fonts is None:
            i18n.set_language("en")  # no Khmer font on this server: fall back to English text
        self.regular, self.bold = fonts or ("Helvetica", "Helvetica-Bold")
        shaping = 1 if fonts else 0
        leading = 1.6 if fonts else 1.25  # Khmer needs room above and below the line

        def style(name: str, size: float, font: str | None = None, color: colors.Color = INK,
                  align: int = 0) -> ParagraphStyle:
            return ParagraphStyle(name, fontName=font or self.regular, fontSize=size, leading=size * leading,
                                  textColor=color, alignment=align, shaping=shaping)

        self.title = style("title", 18, self.bold)
        self.big = style("big", 15, self.bold)
        self.sub = style("sub", 9, color=MUTED)
        self.h = style("h", 11, self.bold)
        self.cell = style("cell", 9.5)
        self.cell_r = style("cell_r", 9.5, align=2)
        self.head = style("head", 8.5, self.bold, MUTED)
        self.head_r = style("head_r", 8.5, self.bold, MUTED, align=2)
        self.label = style("label", 8.5, self.bold, MUTED)
        self.net_label = style("net_label", 11, self.bold, TEAL)
        self.net_value = style("net_value", 18, self.bold, TEAL, align=2)

    def p(self, text: str, style: ParagraphStyle | None = None) -> Paragraph:
        return Paragraph(escape(str(text)), style or self.cell)

    def heading(self, story: list, text: str) -> None:
        story.append(Spacer(1, 3 * mm))
        story.append(self.p(text, self.h))
        story.append(Spacer(1, 1 * mm))

    def table(self, header: list[str], rows: list[list], widths: list[float], right_from: int = 1) -> Table:
        def row_cells(values: list, head: bool = False) -> list:
            return [self.p(v, (self.head_r if head else self.cell_r) if i >= right_from else
                           (self.head if head else self.cell)) for i, v in enumerate(values)]
        data = [row_cells(header, head=True)] + [row_cells(r) for r in rows]
        tbl = Table(data, colWidths=widths)
        style = [("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE), ("BACKGROUND", (0, 0), (-1, 0), SOFT),
                 ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                 ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
        for i in range(2, len(data), 2):
            style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FAFBFC")))
        tbl.setStyle(TableStyle(style))
        return tbl

    def header(self, story: list, settings: dict, title: str, subtitle: str) -> None:
        story.append(self.p(settings["company_name"], self.title))
        story.append(self.p(settings.get("domain", ""), self.sub))
        story.append(Spacer(1, 8 * mm))
        story.append(self.p(title, self.big))
        story.append(self.p(subtitle, self.sub))
        story.append(Spacer(1, 4 * mm))


def _new_document(buf: BytesIO, title: str, settings: dict):
    return SimpleDocTemplate(buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                             bottomMargin=18 * mm, title=title, author=settings["company_name"])


def payslip_pdf(p: dict, settings: dict) -> bytes:
    """p = serialized payroll row (see serializers.payroll_out)."""
    d = _Doc()
    cur = settings.get("currency", "USD")
    buf = BytesIO()
    doc = _new_document(buf, f"Payslip {p['code']} {p['month']}", settings)
    story = []
    d.header(story, settings, t("Monthly Payslip"),
             t("Pay period: {period}   •   Status: {status}", period=month_label(p["month"]), status=p["status"]))

    info = Table([[d.p(t("Employee"), d.label), d.p(p["employee"]), d.p(t("Employee ID"), d.label), d.p(p["code"])],
                  [d.p(t("Department"), d.label), d.p(p["department"]), d.p(t("Position"), d.label),
                   d.p(p["position"])]],
                 colWidths=[28 * mm, 57 * mm, 28 * mm, 57 * mm])
    info.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    story.append(info)

    adjustment = p.get("adjustment") or 0
    overtime = p.get("overtime_pay") or 0
    gross = p["base_salary"] + overtime + p["bonus"] + adjustment
    base_label = t("Base Salary")
    if p.get("paid_days"):  # joined or left during the month
        base_label = t("Base Salary ({days} of {total} days)", days=p["paid_days"], total=p["month_days"])
    earnings = [[base_label, money(p["base_salary"], cur)]]
    if overtime:
        earnings.append([t("Overtime ({hours} h)", hours=f"{p['overtime_hours']:g}"), money(overtime, cur)])
    earnings.append([t("Allowances / Bonus"), money(p["bonus"], cur)])
    if adjustment:
        earnings.append([t("Adjustment"), money(adjustment, cur)])
    earnings.append([t("Gross Earnings"), money(gross, cur)])
    d.heading(story, t("Earnings"))
    story.append(d.table([t("Description"), t("Amount")], earnings, [130 * mm, 40 * mm]))
    tax_label = (t("Income Tax (progressive)") if settings.get("tax_brackets")
                 else t("Income Tax ({rate}%)", rate=f"{settings.get('tax_rate', 0):g}"))
    deductions = [[tax_label, money(p["tax"], cur)],
                  [t("Pension ({rate}%)", rate=f"{settings.get('pension_rate', 0):g}"), money(p["pension"], cur)],
                  [t("Health Insurance"), money(p["insurance"], cur)]]
    if p.get("unpaid_deduction"):
        deductions.insert(0, [t("Unpaid Days ({days})", days=f"{p['unpaid_days']:g}"),
                              money(p["unpaid_deduction"], cur)])
    deductions.append([t("Total Deductions"), money(p["deductions"], cur)])
    d.heading(story, t("Deductions"))
    story.append(d.table([t("Description"), t("Amount")], deductions, [130 * mm, 40 * mm]))
    story.append(Spacer(1, 6 * mm))

    net = Table([[d.p(t("NET PAY"), d.net_label), d.p(money(p["net_salary"], cur), d.net_value)]],
                colWidths=[100 * mm, 70 * mm])
    net.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#CCFBF1")),
                             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                             ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                             ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12)]))
    story.append(net)
    if p.get("note"):
        story.append(Spacer(1, 4 * mm))
        story.append(d.p(t("Note: {note}", note=p["note"]), d.sub))
    story.append(Spacer(1, 10 * mm))
    story.append(d.p(t("Generated {when} • Pay day: {day} of the month. This is a computer-generated document.",
                       when=f"{datetime.now():%Y-%m-%d %H:%M}", day=settings.get("pay_day", "-")), d.sub))
    doc.build(story)
    return buf.getvalue()


def summary_pdf(stats: dict, settings: dict, generated_by: str) -> bytes:
    """Dashboard overview: key figures and headcount by department."""
    d = _Doc()
    cur = settings.get("currency", "USD")
    buf = BytesIO()
    doc = _new_document(buf, "Dashboard Summary", settings)
    story = []
    d.header(story, settings, t("Dashboard Summary"),
             t("Generated {when} by {user}", when=f"{datetime.now():%Y-%m-%d %H:%M}", user=generated_by))

    d.heading(story, t("Key Figures"))
    story.append(d.table([t("Figure"), t("Value")], [
        [t("Total employees"), str(stats["total_employees"])],
        [t("New hires this month"), str(stats["new_this_month"])],
        [t("On leave today"), str(stats["on_leave_today"])],
        [t("Present today"), f"{stats['present']} / {stats['expected']}"],
        [t("Attendance rate"), f"{stats['attendance_rate']:.1f}%"],
        [t("Late arrivals today"), str(stats["late"])],
        [t("Pending leave requests"), str(stats["pending_leaves"])],
        [t("Monthly base payroll"), money(stats["monthly_payroll"], cur)]], [120 * mm, 50 * mm]))

    depts = sorted(stats["departments"], key=lambda x: x["headcount"], reverse=True)
    total = sum(x["headcount"] for x in depts) or 1
    d.heading(story, t("Headcount by Department"))
    story.append(d.table(
        [t("Department"), t("Lead"), t("Headcount"), t("Share"), t("Monthly payroll")],
        [[x["name"], x["lead"], str(x["headcount"]), f"{x['headcount'] / total * 100:.0f}%", money(x["payroll"], cur)]
         for x in depts],
        [50 * mm, 40 * mm, 24 * mm, 18 * mm, 38 * mm], right_from=2))
    doc.build(story)
    return buf.getvalue()
