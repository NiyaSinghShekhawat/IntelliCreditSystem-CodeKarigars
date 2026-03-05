from config import (
    CAM_BANK_NAME, CAM_REPORT_TITLE,
    CAM_AUTHOR, OUTPUTS_DIR
)
from src.schemas import CreditAppraisalResult
from datetime import datetime
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


class CAMGenerator:
    """
    Generates Credit Appraisal Memorandum in both PDF and DOCX formats.
    PDF via ReportLab, DOCX via python-docx.
    """

    def generate_both(self, result: CreditAppraisalResult) -> dict:
        """Generate both PDF and DOCX reports. Returns file paths."""
        company_safe = result.company_name.replace(" ", "_").replace("/", "-")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")

        pdf_path = str(OUTPUTS_DIR / f"CAM_{company_safe}_{timestamp}.pdf")
        docx_path = str(OUTPUTS_DIR / f"CAM_{company_safe}_{timestamp}.docx")

        print(f"Generating PDF CAM...")
        self.generate_pdf(result, pdf_path)

        print(f"Generating DOCX CAM...")
        self.generate_docx(result, docx_path)

        print(f"Reports saved to {OUTPUTS_DIR}")
        return {"pdf": pdf_path, "docx": docx_path}

    # ─── PDF GENERATION ──────────────────────────────────────────────────────

    def generate_pdf(self, result: CreditAppraisalResult,
                     output_path: str) -> str:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch, cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer,
            Table, TableStyle, HRFlowable
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "Title", parent=styles["Heading1"],
            fontSize=16, textColor=colors.HexColor("#1a237e"),
            alignment=TA_CENTER, spaceAfter=6
        )
        subtitle_style = ParagraphStyle(
            "Subtitle", parent=styles["Normal"],
            fontSize=10, textColor=colors.grey,
            alignment=TA_CENTER, spaceAfter=12
        )
        h2_style = ParagraphStyle(
            "H2", parent=styles["Heading2"],
            fontSize=12, textColor=colors.HexColor("#1a237e"),
            spaceBefore=12, spaceAfter=6,
            borderPad=4
        )
        body_style = ParagraphStyle(
            "Body", parent=styles["Normal"],
            fontSize=9, spaceAfter=4, leading=14
        )
        bold_style = ParagraphStyle(
            "Bold", parent=styles["Normal"],
            fontSize=9, fontName="Helvetica-Bold"
        )

        # Decision colors
        pred = result.risk_prediction
        if pred:
            decision_str = str(pred.decision).replace(
                "DecisionType.", ""
            )
            category_str = str(pred.risk_category).replace(
                "RiskCategory.", ""
            )
            if "APPROVE" in decision_str.upper():
                decision_color = colors.HexColor("#2e7d32")
            elif "REJECT" in decision_str.upper():
                decision_color = colors.HexColor("#c62828")
            else:
                decision_color = colors.HexColor("#f57f17")
        else:
            decision_str = "Pending"
            category_str = "Unknown"
            decision_color = colors.grey

        story = []

        # ── Header ──────────────────────────────────────────────────────────
        story.append(Paragraph(CAM_BANK_NAME, subtitle_style))
        story.append(Paragraph(CAM_REPORT_TITLE, title_style))
        story.append(Paragraph(
            f"Generated: {datetime.now().strftime('%d %B %Y, %I:%M %p')} | "
            f"Prepared by: {CAM_AUTHOR}",
            subtitle_style
        ))
        story.append(HRFlowable(
            width="100%", thickness=2,
            color=colors.HexColor("#1a237e")
        ))
        story.append(Spacer(1, 0.2*inch))

        # ── Executive Summary Box ────────────────────────────────────────────
        story.append(Paragraph("1. EXECUTIVE SUMMARY", h2_style))

        exec_data = [
            ["Company Name", result.company_name],
            ["CIN / GSTIN", result.gst_data.gstin
             if result.gst_data else "N/A"],
            ["Report Date", datetime.now().strftime("%d-%m-%Y")],
        ]
        if pred:
            exec_data += [
                ["AI Decision", decision_str],
                ["Risk Category", category_str],
                ["Risk Score", f"{pred.risk_score:.3f} / 1.000"],
                ["Loan Limit", f"Rs. {pred.loan_limit_inr:,.0f}"],
                ["Interest Rate", f"{pred.interest_rate}% p.a."],
            ]

        exec_table = Table(exec_data, colWidths=[4*cm, 12*cm])
        exec_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1),
             colors.HexColor("#e8eaf6")),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1),
             [colors.white, colors.HexColor("#f5f5f5")]),
        ]))
        story.append(exec_table)
        story.append(Spacer(1, 0.2*inch))

        # ── Reasoning Chain ──────────────────────────────────────────────────
        story.append(Paragraph("2. AI REASONING CHAIN", h2_style))
        if result.reasoning_chain:
            for line in result.reasoning_chain.split("\n"):
                if line.strip():
                    story.append(Paragraph(line.strip(), body_style))
        else:
            story.append(Paragraph("Reasoning not available.", body_style))
        story.append(Spacer(1, 0.15*inch))

        # ── Five Cs ──────────────────────────────────────────────────────────
        story.append(Paragraph("3. FIVE Cs ANALYSIS", h2_style))
        if result.five_cs:
            cs = result.five_cs
            five_cs_data = [
                ["C", "Score", "Summary"],
                ["Character",
                 f"{cs.character.score}/10",
                 cs.character.summary],
                ["Capacity",
                 f"{cs.capacity.score}/10",
                 cs.capacity.summary],
                ["Capital",
                 f"{cs.capital.score}/10",
                 cs.capital.summary],
                ["Collateral",
                 f"{cs.collateral.score}/10",
                 cs.collateral.summary],
                ["Conditions",
                 f"{cs.conditions.score}/10",
                 cs.conditions.summary],
                ["OVERALL",
                 f"{cs.overall_score}/10", "Weighted average"],
            ]
            cs_table = Table(
                five_cs_data,
                colWidths=[3*cm, 2.5*cm, 10.5*cm]
            )
            cs_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0),
                 colors.HexColor("#1a237e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("BACKGROUND", (0, -1), (-1, -1),
                 colors.HexColor("#e8eaf6")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (1, 1), (-1, -2),
                 [colors.white, colors.HexColor("#f5f5f5")]),
            ]))
            story.append(cs_table)
        else:
            story.append(Paragraph(
                "Five Cs analysis not available.", body_style
            ))
        story.append(Spacer(1, 0.15*inch))

        # ── SHAP Risk Drivers ────────────────────────────────────────────────
        story.append(Paragraph("4. AI RISK DRIVERS (SHAP)", h2_style))
        if pred and pred.top_shap_factors:
            shap_data = [["Factor", "Impact", "Direction"]]
            for f in pred.top_shap_factors:
                shap_data.append([
                    f.display_name,
                    f"{f.shap_value:.4f}",
                    f.direction
                ])
            shap_table = Table(
                shap_data,
                colWidths=[7*cm, 3*cm, 6*cm]
            )
            shap_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0),
                 colors.HexColor("#1a237e")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("PADDING", (0, 0), (-1, -1), 6),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.white, colors.HexColor("#f5f5f5")]),
            ]))
            story.append(shap_table)
        story.append(Spacer(1, 0.15*inch))

        # ── Early Warning Signals ────────────────────────────────────────────
        story.append(Paragraph(
            "5. EARLY WARNING SIGNALS", h2_style
        ))
        if pred and pred.early_warning_signals:
            for w in pred.early_warning_signals:
                story.append(Paragraph(f"• {w}", body_style))
        else:
            story.append(Paragraph("No specific warnings.", body_style))
        story.append(Spacer(1, 0.15*inch))

        # ── Research Findings ────────────────────────────────────────────────
        story.append(Paragraph("6. EXTERNAL RESEARCH", h2_style))
        if result.research:
            r = result.research
            story.append(Paragraph(
                f"News Risk Score: {r.news_risk_score}/10 | "
                f"Negative Articles: {len(r.negative_news)} | "
                f"Litigation: {'Yes' if r.litigation_found else 'No'} | "
                f"MCA Charges: {len(r.mca_charges)}",
                bold_style
            ))
            story.append(Spacer(1, 0.1*inch))
            if r.research_summary:
                story.append(Paragraph(r.research_summary, body_style))
            if r.negative_news:
                story.append(Paragraph(
                    "Negative News:", bold_style
                ))
                for item in r.negative_news[:5]:
                    story.append(Paragraph(
                        f"• {item.title} ({item.date}) — {item.source}",
                        body_style
                    ))
        else:
            story.append(Paragraph(
                "No external research conducted.", body_style
            ))
        story.append(Spacer(1, 0.15*inch))

        # ── Recommendation ───────────────────────────────────────────────────
        story.append(Paragraph("7. RECOMMENDATION", h2_style))
        if pred:
            rec_color = decision_color
            rec_style = ParagraphStyle(
                "Rec", parent=styles["Normal"],
                fontSize=12, fontName="Helvetica-Bold",
                textColor=rec_color
            )
            story.append(Paragraph(
                f"DECISION: {decision_str}", rec_style
            ))
            story.append(Spacer(1, 0.1*inch))
            if pred.decisive_factor:
                story.append(Paragraph(
                    f"Decisive Factor: {pred.decisive_factor}",
                    body_style
                ))
        story.append(Spacer(1, 0.2*inch))

        # ── Footer ───────────────────────────────────────────────────────────
        story.append(HRFlowable(
            width="100%", thickness=1, color=colors.grey
        ))
        story.append(Paragraph(
            f"This CAM was generated by {CAM_AUTHOR}. "
            f"For internal use only. "
            f"Subject to credit committee approval.",
            ParagraphStyle(
                "Footer", parent=styles["Normal"],
                fontSize=7, textColor=colors.grey,
                alignment=TA_CENTER
            )
        ))

        doc.build(story)
        print(f"PDF saved: {output_path}")
        return output_path

    # ─── DOCX GENERATION ─────────────────────────────────────────────────────

    def generate_docx(self, result: CreditAppraisalResult,
                      output_path: str) -> str:
        from docx import Document
        from docx.shared import Pt, Cm, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement

        doc = Document()

        # Page margins
        for section in doc.sections:
            section.top_margin = Cm(2)
            section.bottom_margin = Cm(2)
            section.left_margin = Cm(2.5)
            section.right_margin = Cm(2.5)

        pred = result.risk_prediction
        decision_str = "Pending"
        category_str = "Unknown"
        if pred:
            decision_str = str(pred.decision).replace(
                "DecisionType.", ""
            )
            category_str = str(pred.risk_category).replace(
                "RiskCategory.", ""
            )

        def add_heading(text, level=1):
            h = doc.add_heading(text, level=level)
            h.runs[0].font.color.rgb = RGBColor(0x1a, 0x23, 0x7e)
            return h

        def add_row(table, label, value):
            row = table.add_row()
            row.cells[0].text = label
            row.cells[1].text = str(value)
            row.cells[0].paragraphs[0].runs[0].bold = True
            return row

        # ── Title ────────────────────────────────────────────────────────────
        title = doc.add_paragraph(CAM_BANK_NAME)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title.runs[0].font.size = Pt(10)
        title.runs[0].font.color.rgb = RGBColor(0x75, 0x75, 0x75)

        title2 = doc.add_paragraph(CAM_REPORT_TITLE)
        title2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title2.runs[0].font.size = Pt(18)
        title2.runs[0].bold = True
        title2.runs[0].font.color.rgb = RGBColor(0x1a, 0x23, 0x7e)

        date_para = doc.add_paragraph(
            f"Generated: {datetime.now().strftime('%d %B %Y')} | "
            f"Prepared by: {CAM_AUTHOR}"
        )
        date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        date_para.runs[0].font.size = Pt(9)
        date_para.runs[0].font.color.rgb = RGBColor(0x75, 0x75, 0x75)

        doc.add_paragraph()

        # ── Executive Summary ────────────────────────────────────────────────
        add_heading("1. EXECUTIVE SUMMARY", level=1)
        table = doc.add_table(rows=0, cols=2)
        table.style = "Table Grid"
        table.columns[0].width = Cm(4)
        table.columns[1].width = Cm(12)

        add_row(table, "Company Name", result.company_name)
        add_row(table, "GSTIN",
                result.gst_data.gstin if result.gst_data else "N/A")
        add_row(table, "Report Date",
                datetime.now().strftime("%d-%m-%Y"))
        if pred:
            add_row(table, "AI Decision", decision_str)
            add_row(table, "Risk Category", category_str)
            add_row(table, "Risk Score",
                    f"{pred.risk_score:.3f} / 1.000")
            add_row(table, "Loan Limit",
                    f"Rs. {pred.loan_limit_inr:,.0f}")
            add_row(table, "Interest Rate",
                    f"{pred.interest_rate}% p.a.")

        doc.add_paragraph()

        # ── Reasoning Chain ──────────────────────────────────────────────────
        add_heading("2. AI REASONING CHAIN", level=1)
        if result.reasoning_chain:
            for line in result.reasoning_chain.split("\n"):
                if line.strip():
                    doc.add_paragraph(line.strip())
        else:
            doc.add_paragraph("Reasoning not available.")

        doc.add_paragraph()

        # ── Five Cs ──────────────────────────────────────────────────────────
        add_heading("3. FIVE Cs ANALYSIS", level=1)
        if result.five_cs:
            cs = result.five_cs
            cs_table = doc.add_table(rows=1, cols=3)
            cs_table.style = "Table Grid"
            hdr = cs_table.rows[0].cells
            hdr[0].text = "C"
            hdr[1].text = "Score"
            hdr[2].text = "Summary"
            for cell in hdr:
                cell.paragraphs[0].runs[0].bold = True

            for label, score_obj in [
                ("Character", cs.character),
                ("Capacity", cs.capacity),
                ("Capital", cs.capital),
                ("Collateral", cs.collateral),
                ("Conditions", cs.conditions),
            ]:
                row = cs_table.add_row().cells
                row[0].text = label
                row[1].text = f"{score_obj.score}/10"
                row[2].text = score_obj.summary

            overall_row = cs_table.add_row().cells
            overall_row[0].text = "OVERALL"
            overall_row[1].text = f"{cs.overall_score}/10"
            overall_row[2].text = "Weighted average"
            for cell in overall_row:
                cell.paragraphs[0].runs[0].bold = True

        doc.add_paragraph()

        # ── SHAP Factors ─────────────────────────────────────────────────────
        add_heading("4. AI RISK DRIVERS (SHAP)", level=1)
        if pred and pred.top_shap_factors:
            shap_table = doc.add_table(rows=1, cols=3)
            shap_table.style = "Table Grid"
            hdr = shap_table.rows[0].cells
            hdr[0].text = "Factor"
            hdr[1].text = "Impact"
            hdr[2].text = "Direction"
            for cell in hdr:
                cell.paragraphs[0].runs[0].bold = True
            for f in pred.top_shap_factors:
                row = shap_table.add_row().cells
                row[0].text = f.display_name
                row[1].text = f"{f.shap_value:.4f}"
                row[2].text = f.direction

        doc.add_paragraph()

        # ── Early Warnings ───────────────────────────────────────────────────
        add_heading("5. EARLY WARNING SIGNALS", level=1)
        if pred and pred.early_warning_signals:
            for w in pred.early_warning_signals:
                doc.add_paragraph(f"• {w}")
        else:
            doc.add_paragraph("No specific warnings.")

        doc.add_paragraph()

        # ── Research ─────────────────────────────────────────────────────────
        add_heading("6. EXTERNAL RESEARCH", level=1)
        if result.research:
            r = result.research
            doc.add_paragraph(
                f"News Risk Score: {r.news_risk_score}/10 | "
                f"Negative Articles: {len(r.negative_news)} | "
                f"Litigation: {'Yes' if r.litigation_found else 'No'}"
            )
            if r.research_summary:
                doc.add_paragraph(r.research_summary)
            if r.negative_news:
                doc.add_paragraph("Negative News:").runs[0].bold = True
                for item in r.negative_news[:5]:
                    doc.add_paragraph(
                        f"• {item.title} ({item.date})"
                    )
        else:
            doc.add_paragraph("No external research conducted.")

        doc.add_paragraph()

        # ── Recommendation ───────────────────────────────────────────────────
        add_heading("7. RECOMMENDATION", level=1)
        if pred:
            rec = doc.add_paragraph(f"DECISION: {decision_str}")
            rec.runs[0].bold = True
            rec.runs[0].font.size = Pt(14)
            if pred.decisive_factor:
                doc.add_paragraph(
                    f"Decisive Factor: {pred.decisive_factor}"
                )

        # ── Footer ───────────────────────────────────────────────────────────
        footer = doc.sections[0].footer
        footer_para = footer.paragraphs[0]
        footer_para.text = (
            f"Generated by {CAM_AUTHOR} | {CAM_BANK_NAME} | "
            f"Internal Use Only | "
            f"{datetime.now().strftime('%d-%m-%Y')}"
        )
        footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer_para.runs[0].font.size = Pt(8)
        footer_para.runs[0].font.color.rgb = RGBColor(
            0x75, 0x75, 0x75
        )

        doc.save(output_path)
        print(f"DOCX saved: {output_path}")
        return output_path


# ─── QUICK TEST ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from src.schemas import (
        CreditAppraisalResult, GSTData, BankStatementData,
        GSTReconciliationResult, QualitativeInputs,
        ResearchFindings, FiveCsResult, CScore,
        RiskPrediction, RiskCategory, DecisionType, SHAPFactor,
        NewsItem
    )

    print("="*50)
    print("TEST: CAM Generator")
    print("="*50)

    # Build complete test result
    test = CreditAppraisalResult(
        company_name="ABC Private Limited",
        gst_data=GSTData(
            gstin="27AABCU9603R1ZX",
            company_name="ABC Private Limited",
            turnover=4500000,
            total_tax=500000,
            itc_claimed=80000,
            filing_regular=True
        ),
        bank_data=BankStatementData(
            bank_name="HDFC Bank",
            total_credits=4200000,
            total_debits=3500000,
            average_monthly_balance=450000,
            emi_bounce_count=1
        ),
        gst_reconciliation=GSTReconciliationResult(
            total_mismatches=1,
            risk_flag=False,
            variance_pct=8.5,
            circular_trading_flag=False,
            summary="Minor ITC variance within acceptable range."
        ),
        research=ResearchFindings(
            company_name="ABC Private Limited",
            negative_news=[
                NewsItem(
                    title="ABC Pvt Ltd faces GST notice for ITC mismatch",
                    url="https://economictimes.com",
                    date="20240201",
                    source="economictimes.indiatimes.com",
                    is_negative=True,
                    keywords_found=["GST"]
                )
            ],
            positive_news=[],
            news_risk_score=3.5,
            litigation_found=False,
            mca_charges=[],
            rbi_sebi_actions=[],
            research_summary="One GST-related news item found. No litigation."
        ),
        five_cs=FiveCsResult(
            character=CScore(
                score=9.0,
                summary="Excellent character profile.",
                factors=["Regular GST filing"]
            ),
            capacity=CScore(
                score=6.0,
                summary="Good repayment capacity.",
                factors=["16.7% cash flow surplus"]
            ),
            capital=CScore(
                score=7.5,
                summary="Adequate capital.",
                factors=["D/E ratio 1.5"]
            ),
            collateral=CScore(
                score=6.0,
                summary="Adequate collateral.",
                factors=["85% coverage"]
            ),
            conditions=CScore(
                score=7.0,
                summary="Neutral conditions.",
                factors=["Moderate sector risk"]
            ),
            overall_score=7.15
        ),
        risk_prediction=RiskPrediction(
            risk_score=0.35,
            risk_category=RiskCategory.MEDIUM,
            decision=DecisionType.CONDITIONAL,
            loan_limit_inr=2500000,
            interest_rate=11.3,
            top_shap_factors=[
                SHAPFactor(
                    feature_name="emi_bounce_count",
                    shap_value=0.10,
                    direction="increases risk",
                    display_name="EMI Bounce Count"
                ),
                SHAPFactor(
                    feature_name="debt_equity_ratio",
                    shap_value=0.08,
                    direction="decreases risk",
                    display_name="Healthy D/E Ratio"
                ),
            ],
            decisive_factor=(
                "Conditional approval — GST filing regular but "
                "minor ITC variance needs clarification."
            ),
            early_warning_signals=[
                "Monitor GST filing regularity monthly",
                "Track EMI payment pattern quarterly",
                "Watch for sudden large cash withdrawals"
            ]
        ),
        reasoning_chain="""DECISION: Conditional Approval
LIMIT: Rs.25 lakhs
RATE: 11.3% per annum

REASONING CHAIN:
1. GST Analysis      -> Regular filing, minor ITC variance -> Low risk
2. Bank Statements   -> Healthy credits, 1 EMI bounce -> Moderate risk
3. External Research -> One GST notice, no litigation -> Low risk
4. Primary Inputs    -> D/E 1.5, collateral 85% -> Moderate risk

DECISIVE FACTOR: Strong GST compliance with minor ITC clarification needed.

EARLY WARNING SIGNALS:
- Monitor GST filing regularity monthly
- Track EMI payment pattern"""
    )

    generator = CAMGenerator()
    paths = generator.generate_both(test)

    print(f"\nFiles generated:")
    print(f"PDF:  {paths['pdf']}")
    print(f"DOCX: {paths['docx']}")
    print("\nOpen the outputs/ folder to view the reports!")
