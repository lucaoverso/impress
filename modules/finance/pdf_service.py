import io
from datetime import datetime
from html import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .config import SCHOOL_NAME


BRAND = colors.HexColor("#0f766e")
INK = colors.HexColor("#1f2a37")
MUTED = colors.HexColor("#4b5563")
LINE = colors.HexColor("#d8dee8")
SOFT = colors.HexColor("#f8fbff")


def _currency(cents: int) -> str:
    value = int(cents or 0) / 100
    text = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {text}"


def _date_br(value: str) -> str:
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return str(value or "-")


def _month_label(month: str) -> str:
    names = (
        "janeiro", "fevereiro", "marco", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
    )
    year, month_number = month.split("-")
    return f"{names[int(month_number) - 1]} de {year}".replace("marco", "março")


def generate_month_report_pdf(report: dict) -> bytes:
    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        title=f"Prestação de contas - {report['month']}",
        author=SCHOOL_NAME,
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "FinanceTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=19, leading=23, textColor=INK, spaceAfter=5,
    )
    subtitle = ParagraphStyle(
        "FinanceSubtitle", parent=styles["BodyText"], fontSize=10,
        leading=14, textColor=MUTED, spaceAfter=12,
    )
    heading = ParagraphStyle(
        "FinanceHeading", parent=styles["Heading2"], fontName="Helvetica-Bold",
        fontSize=12, leading=15, textColor=INK, spaceBefore=12, spaceAfter=7,
    )
    body = ParagraphStyle(
        "FinanceBody", parent=styles["BodyText"], fontSize=8.5,
        leading=11, textColor=INK,
    )
    body_right = ParagraphStyle("FinanceBodyRight", parent=body, alignment=TA_RIGHT)
    summary = report["summary"]
    story = [
        Paragraph(escape(SCHOOL_NAME), subtitle),
        Paragraph("Prestação de contas mensal", title),
        Paragraph(
            f"Periodo: {_month_label(report['month'])}. Emitido em "
            f"{datetime.now().strftime('%d/%m/%Y às %H:%M')}.",
            subtitle,
        ),
    ]

    summary_data = [
        ["Entradas", "Gastos", "Saldo do periodo"],
        [
            _currency(summary["income_cents"]),
            _currency(summary["expense_cents"]),
            _currency(summary["balance_cents"]),
        ],
    ]
    summary_table = Table(summary_data, colWidths=[58 * mm] * 3)
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), SOFT),
                ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
                ("TEXTCOLOR", (0, 1), (-1, 1), INK),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("FONTSIZE", (0, 1), (-1, 1), 12),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend([summary_table, Spacer(1, 4 * mm)])

    categories = summary.get("categories") or []
    story.append(Paragraph("Resumo por categoria", heading))
    if categories:
        category_rows = [["Tipo", "Categoria", "Lançamentos", "Total"]]
        for item in categories:
            category_rows.append(
                [
                    "Entrada" if item["transaction_type"] == "INCOME" else "Gasto",
                    Paragraph(escape(item["category"]), body),
                    str(item["transaction_count"]),
                    _currency(item["total_cents"]),
                ]
            )
        category_table = Table(category_rows, colWidths=[26 * mm, 82 * mm, 28 * mm, 38 * mm], repeatRows=1)
        category_table.setStyle(_table_style())
        story.append(category_table)
    else:
        story.append(Paragraph("Nenhum lancamento ativo neste mes.", body))

    story.append(Paragraph("Movimentações do período", heading))
    transactions = report.get("transactions") or []
    if transactions:
        rows = [["Data", "Tipo", "Descricao", "Categoria", "Valor"]]
        for item in transactions:
            details = escape(item["description"])
            if item.get("counterparty"):
                details += f"<br/><font color='#4b5563'>{escape(item['counterparty'])}</font>"
            rows.append(
                [
                    _date_br(item["occurred_on"]),
                    "Entrada" if item["transaction_type"] == "INCOME" else "Gasto",
                    Paragraph(details, body),
                    Paragraph(escape(item["category"]), body),
                    Paragraph(_currency(item["amount_cents"]), body_right),
                ]
            )
        transaction_table = Table(
            rows, colWidths=[20 * mm, 22 * mm, 62 * mm, 36 * mm, 34 * mm], repeatRows=1
        )
        transaction_table.setStyle(_table_style())
        story.append(transaction_table)
    else:
        story.append(Paragraph("Nenhuma movimentação para apresentar.", body))

    story.extend(
        [
            Spacer(1, 14 * mm),
            KeepTogether(
                [
                    Table([[""], ["Responsável pela prestação de contas"]], colWidths=[75 * mm], style=[
                        ("LINEABOVE", (0, 0), (-1, 0), 0.6, INK),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("TEXTCOLOR", (0, 1), (-1, 1), MUTED),
                        ("FONTSIZE", (0, 1), (-1, 1), 8),
                    ])
                ]
            ),
        ]
    )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.line(18 * mm, 13 * mm, 192 * mm, 13 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 8 * mm, "Documento gerado pelo sistema de gestão escolar")
        canvas.drawRightString(192 * mm, 8 * mm, f"Página {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()


def _table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), BRAND),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.35, LINE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]
    )
