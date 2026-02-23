"""
Report Generator — PDF and Excel report output.
"""
import os
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment


class ReportGenerator:
    def __init__(self, template: dict):
        self.template = template

    def generate_pdf(self, metrics: dict, labels: list[dict], project_dir: Path) -> Path:
        """Generate PDF report with KPIs, timeline, waste patterns, and ergo info."""
        pdf_path = project_dir / "report.pdf"
        doc = SimpleDocTemplate(str(pdf_path), pagesize=A4,
                                leftMargin=15*mm, rightMargin=15*mm,
                                topMargin=15*mm, bottomMargin=15*mm)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("title_custom", parent=styles["Heading1"], fontSize=16)
        h2_style = ParagraphStyle("h2_custom", parent=styles["Heading2"], fontSize=12)
        body_style = styles["BodyText"]

        elements = []

        # Title
        elements.append(Paragraph("WorkStudy AI Analysis Report", title_style))
        elements.append(Paragraph(f"Template: {self.template.get('label', 'N/A')}", body_style))
        elements.append(Spacer(1, 10*mm))

        # KPI Table
        elements.append(Paragraph("KPI Summary", h2_style))
        kpi = metrics.get("kpi", {})
        focus = self.template.get("focus_kpi", [])
        kpi_data = [["KPI", "Value"]]
        for k in focus:
            val = kpi.get(k, "N/A")
            if isinstance(val, float):
                val = f"{val:.3f}"
            kpi_data.append([k, str(val)])

        t = Table(kpi_data, colWidths=[70*mm, 50*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 8*mm))

        # Waste Patterns
        waste = metrics.get("waste_fired", [])
        if waste:
            elements.append(Paragraph("Waste Patterns Triggered", h2_style))
            for w in waste:
                elements.append(Paragraph(
                    f"  {w['description']} ({w['metric']}={w['actual_value']} > {w['threshold']})",
                    body_style))
                elements.append(Paragraph(f"    Suggestion: {w['suggestion']}", body_style))
            elements.append(Spacer(1, 5*mm))

        # Ergo
        ergo = metrics.get("ergo", {})
        elements.append(Paragraph("Ergonomic Assessment", h2_style))
        elements.append(Paragraph(
            f"  Trunk risk ratio: {ergo.get('trunk_risk_ratio', 0):.1%} "
            f"(threshold: {ergo.get('trunk_threshold_deg', 40)} deg)", body_style))
        elements.append(Paragraph(
            f"  Shoulder risk ratio: {ergo.get('shoulder_risk_ratio', 0):.1%} "
            f"(threshold: {ergo.get('shoulder_threshold_deg', 60)} deg)", body_style))
        elements.append(Spacer(1, 8*mm))

        # Timeline
        elements.append(Paragraph("Motion Timeline", h2_style))
        tl_data = [["#", "Start(s)", "End(s)", "Label", "Duration(s)", "NVA"]]
        for lbl in labels[:30]:
            tl_data.append([
                str(lbl["segment_id"]),
                f"{lbl['start_sec']:.1f}",
                f"{lbl['end_sec']:.1f}",
                lbl["label"],
                f"{lbl['duration_sec']:.1f}",
                "Yes" if lbl["is_nva"] else "",
            ])
        t2 = Table(tl_data, colWidths=[10*mm, 22*mm, 22*mm, 30*mm, 25*mm, 15*mm])
        t2.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ]))
        elements.append(t2)

        doc.build(elements)
        return pdf_path

    def generate_xlsx(self, metrics: dict, labels: list[dict], project_dir: Path) -> Path:
        """Generate Excel report with KPI and timeline sheets."""
        xlsx_path = project_dir / "report.xlsx"
        wb = openpyxl.Workbook()

        # KPI Sheet
        ws_kpi = wb.active
        ws_kpi.title = "KPI"
        header_fill = PatternFill("solid", fgColor="2563EB")
        header_font = Font(color="FFFFFF", bold=True)

        ws_kpi.append(["KPI", "Value"])
        for cell in ws_kpi[1]:
            cell.fill = header_fill
            cell.font = header_font

        kpi = metrics.get("kpi", {})
        for k in self.template.get("focus_kpi", []):
            val = kpi.get(k, "N/A")
            ws_kpi.append([k, val])

        ws_kpi.column_dimensions["A"].width = 30
        ws_kpi.column_dimensions["B"].width = 20

        # Timeline Sheet
        ws_tl = wb.create_sheet("Timeline")
        ws_tl.append(["#", "Start(s)", "End(s)", "Label", "Label(JP)", "Duration(s)", "NVA"])
        for cell in ws_tl[1]:
            cell.fill = header_fill
            cell.font = header_font

        for lbl in labels:
            ws_tl.append([
                lbl["segment_id"], lbl["start_sec"], lbl["end_sec"],
                lbl["label"], lbl.get("label_jp", ""), lbl["duration_sec"],
                "Yes" if lbl["is_nva"] else ""
            ])

        # Waste Sheet
        ws_waste = wb.create_sheet("Waste Patterns")
        ws_waste.append(["ID", "Description", "Metric", "Actual", "Threshold", "Suggestion"])
        for cell in ws_waste[1]:
            cell.fill = header_fill
            cell.font = header_font

        for w in metrics.get("waste_fired", []):
            ws_waste.append([w["id"], w["description"], w["metric"],
                             w["actual_value"], w["threshold"], w["suggestion"]])

        wb.save(str(xlsx_path))
        return xlsx_path
