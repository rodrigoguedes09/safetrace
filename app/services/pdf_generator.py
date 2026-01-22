"""PDF compliance certificate generator service."""

import base64
import io
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from app.constants import RiskLevel, RiskTag, SUPPORTED_CHAINS
from app.models.risk import RiskReport

logger = logging.getLogger(__name__)


class PDFGeneratorService:
    """
    Service for generating professional PDF compliance certificates.
    
    Uses ReportLab to create deterministic, reproducible PDF documents
    containing complete risk analysis results.
    """

    def __init__(self, output_dir: str = "./reports") -> None:
        """
        Initialize the PDF generator.

        Args:
            output_dir: Directory for saving generated PDFs.
        """
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def generate_certificate(
        self,
        report: RiskReport,
        save_to_file: bool = True,
    ) -> tuple[bytes, str | None]:
        """
        Generate a comprehensive compliance certificate PDF.

        Args:
            report: Risk report to convert to PDF.
            save_to_file: Whether to save the PDF to disk.

        Returns:
            Tuple of (PDF bytes, file path if saved).
        """
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import cm, mm
            from reportlab.platypus import (
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
                PageBreak,
            )
            from reportlab.graphics.shapes import Drawing, Rect
            from reportlab.graphics.charts.barcharts import HorizontalBarChart
        except ImportError as e:
            raise RuntimeError("ReportLab not installed") from e

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        elements = []

        # Custom styles
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=26,
            spaceAfter=12,
            alignment=1,  # Center
            textColor=colors.HexColor("#1a1a2e"),
            fontName="Helvetica-Bold",
        )

        subtitle_style = ParagraphStyle(
            "CustomSubtitle",
            parent=styles["Heading2"],
            fontSize=16,
            spaceBefore=15,
            spaceAfter=10,
            textColor=colors.HexColor("#16213e"),
            fontName="Helvetica-Bold",
        )
        
        section_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading3"],
            fontSize=13,
            spaceBefore=12,
            spaceAfter=8,
            textColor=colors.HexColor("#2c3e50"),
            fontName="Helvetica-Bold",
        )

        body_style = ParagraphStyle(
            "CustomBody",
            parent=styles["Normal"],
            fontSize=10,
            spaceAfter=6,
            textColor=colors.HexColor("#333333"),
            leading=14,
        )
        
        emphasis_style = ParagraphStyle(
            "Emphasis",
            parent=styles["Normal"],
            fontSize=10,
            spaceAfter=6,
            textColor=colors.HexColor("#2c3e50"),
            fontName="Helvetica-Bold",
        )

        # ===== COVER PAGE =====
        elements.append(Spacer(1, 3 * cm))
        elements.append(
            Paragraph("BLOCKCHAIN TRANSACTION", title_style)
        )
        elements.append(
            Paragraph("COMPLIANCE ANALYSIS REPORT", title_style)
        )
        elements.append(Spacer(1, 2 * cm))
        
        # Risk Score Box
        risk_color = self._get_risk_color(report.risk_score.level)
        risk_box_data = [[
            Paragraph(f"<b>RISK ASSESSMENT</b>", 
                     ParagraphStyle("CenterBold", parent=body_style, alignment=1, fontSize=14, fontName="Helvetica-Bold")),
            Paragraph(f"<b>{report.risk_score.score}/100</b>", 
                     ParagraphStyle("CenterScore", parent=body_style, alignment=1, fontSize=32, fontName="Helvetica-Bold", textColor=colors.white)),
            Paragraph(f"<b>{report.risk_score.level.value}</b>", 
                     ParagraphStyle("CenterLevel", parent=body_style, alignment=1, fontSize=18, fontName="Helvetica-Bold", textColor=colors.white))
        ]]
        
        risk_box = Table(risk_box_data, colWidths=[17 * cm])
        risk_box.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
                ("BACKGROUND", (0, 1), (-1, -1), risk_color),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 15),
                ("TOPPADDING", (0, 0), (-1, -1), 15),
                ("BOX", (0, 0), (-1, -1), 2, colors.HexColor("#333333")),
            ])
        )
        elements.append(risk_box)
        elements.append(Spacer(1, 2 * cm))

        # Report Info
        elements.append(
            Paragraph(
                f"<b>Report ID:</b> {report.tx_hash[:16]}...{report.analyzed_at.strftime('%Y%m%d%H%M%S')}",
                body_style,
            )
        )
        elements.append(
            Paragraph(
                f"<b>Generated:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                body_style,
            )
        )
        chain_name = SUPPORTED_CHAINS.get(report.chain, None)
        chain_display = chain_name.name if chain_name else report.chain.title()
        elements.append(
            Paragraph(
                f"<b>Blockchain:</b> {chain_display}",
                body_style,
            )
        )
        
        elements.append(PageBreak())

        # ===== EXECUTIVE SUMMARY =====
        elements.append(Paragraph("EXECUTIVE SUMMARY", subtitle_style))
        elements.append(Spacer(1, 5 * mm))
        
        # Summary paragraph based on risk level
        if report.risk_score.level == RiskLevel.LOW:
            summary_text = (
                f"This transaction analysis shows a <b>LOW RISK</b> profile with a score of {report.risk_score.score}/100. "
                f"Our comprehensive blockchain tracing analyzed {report.total_addresses_analyzed} addresses across "
                f"{report.trace_depth} hops and found minimal suspicious activity. This transaction appears to originate "
                f"from legitimate sources with no significant exposure to high-risk entities."
            )
        elif report.risk_score.level == RiskLevel.MEDIUM:
            summary_text = (
                f"This transaction analysis indicates a <b>MEDIUM RISK</b> profile with a score of {report.risk_score.score}/100. "
                f"Our investigation across {report.total_addresses_analyzed} addresses over {report.trace_depth} hops "
                f"detected some concerning patterns or connections. While not definitively malicious, this transaction "
                f"warrants additional due diligence before proceeding."
            )
        else:  # HIGH
            summary_text = (
                f"This transaction analysis reveals a <b>HIGH RISK</b> profile with a score of {report.risk_score.score}/100. "
                f"Our thorough investigation of {report.total_addresses_analyzed} addresses across {report.trace_depth} hops "
                f"identified significant connections to suspicious or illicit entities. <b>This transaction requires immediate "
                f"attention and enhanced due diligence procedures.</b>"
            )
        
        elements.append(Paragraph(summary_text, body_style))
        elements.append(Spacer(1, 5 * mm))

        # Key Findings
        elements.append(Paragraph("<b>Key Findings:</b>", emphasis_style))
        findings = [
            f"Analyzed {report.total_addresses_analyzed} unique addresses",
            f"Traced through {report.total_transactions_analyzed} transactions",
            f"Investigation depth: {report.trace_depth} hops from original transaction",
            f"Flagged entities detected: {len(report.flagged_entities)}",
            f"API calls utilized: {report.api_calls_used} (optimized via caching)",
        ]
        
        for finding in findings:
            elements.append(Paragraph(f"• {finding}", body_style))
        
        elements.append(Spacer(1, 10 * mm))

        # ===== TRANSACTION DETAILS =====
        elements.append(Paragraph("TRANSACTION DETAILS", subtitle_style))
        elements.append(Spacer(1, 3 * mm))

        tx_data = [
            ["Transaction Hash:", report.tx_hash],
            ["Blockchain Network:", chain_display],
            ["Analysis Timestamp:", report.analyzed_at.strftime("%Y-%m-%d %H:%M:%S UTC")],
            ["Trace Depth:", f"{report.trace_depth} hops"],
            ["Addresses Analyzed:", str(report.total_addresses_analyzed)],
            ["Transactions Analyzed:", str(report.total_transactions_analyzed)],
            ["API Calls Used:", str(report.api_calls_used)],
        ]

        tx_table = Table(tx_data, colWidths=[5.5 * cm, 11.5 * cm])
        tx_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8e8e8")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#333333")),
                ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                ("ALIGN", (1, 0), (1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#cccccc")),
            ])
        )
        elements.append(tx_table)
        elements.append(Spacer(1, 10 * mm))

        # ===== RISK ASSESSMENT =====
        elements.append(Paragraph("RISK ASSESSMENT", subtitle_style))
        elements.append(Spacer(1, 3 * mm))

        risk_data = [
            ["Risk Score:", f"{report.risk_score.score}/100"],
            ["Risk Level:", report.risk_score.level.value],
            ["Classification:", self._get_risk_classification(report.risk_score.level)],
        ]

        risk_table = Table(risk_data, colWidths=[5.5 * cm, 11.5 * cm])
        risk_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8e8e8")),
                ("BACKGROUND", (1, 1), (1, 1), risk_color),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#333333")),
                ("TEXTCOLOR", (1, 1), (1, 1), colors.white),
                ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                ("ALIGN", (1, 0), (1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 1), (1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#cccccc")),
            ])
        )
        elements.append(risk_table)
        elements.append(Spacer(1, 8 * mm))

        # Analysis Details
        elements.append(Paragraph("<b>Analysis Details:</b>", emphasis_style))
        if report.risk_score.reasons:
            for reason in report.risk_score.reasons:
                elements.append(Paragraph(f"• {reason}", body_style))
        else:
            elements.append(Paragraph("• No specific risk factors identified", body_style))
        
        elements.append(Spacer(1, 10 * mm))

        # ===== METHODOLOGY =====
        elements.append(Paragraph("ANALYSIS METHODOLOGY", subtitle_style))
        elements.append(Spacer(1, 3 * mm))
        
        elements.append(Paragraph("<b>Tracing Algorithm:</b>", section_style))
        elements.append(Paragraph(
            "Our analysis employs a Breadth-First Search (BFS) algorithm to trace the flow of funds "
            "from the target transaction. This method systematically explores transaction inputs and "
            "outputs, mapping the complete trail of funds up to the specified depth.",
            body_style
        ))
        elements.append(Spacer(1, 3 * mm))
        
        elements.append(Paragraph("<b>Risk Scoring Formula:</b>", section_style))
        elements.append(Paragraph(
            "Risk scores are calculated using a weighted formula that considers multiple factors:",
            body_style
        ))
        elements.append(Spacer(1, 2 * mm))
        elements.append(Paragraph(
            "<b>R = Σ(Vi × Wi × Di)</b>",
            ParagraphStyle("Formula", parent=body_style, alignment=1, fontSize=12, fontName="Helvetica-Bold")
        ))
        elements.append(Spacer(1, 2 * mm))
        elements.append(Paragraph(
            "Where: <b>Vi</b> = Risk factor presence (1 if detected), "
            "<b>Wi</b> = Weight for the risk factor, "
            "<b>Di</b> = Distance decay factor (0.5<super>distance</super>)",
            body_style
        ))
        elements.append(Spacer(1, 5 * mm))
        
        # Risk Factor Weights Table
        elements.append(Paragraph("<b>Risk Factor Weights:</b>", section_style))
        weight_data = [
            ["Risk Factor", "Weight", "Description"],
            ["Mixer/Tumbler", "1.0", "Services designed to obscure transaction trails"],
            ["Darknet Markets", "1.0", "Illegal marketplace transactions"],
            ["Sanctioned Entity", "1.0", "Addresses on government sanction lists"],
            ["Hack/Theft", "0.9", "Funds linked to known security breaches"],
            ["Scam", "0.8", "Fraudulent schemes and scam operations"],
            ["Gambling", "0.4", "Online gambling services"],
            ["Exchange", "-0.2", "Legitimate cryptocurrency exchanges (reduces risk)"],
        ]
        
        weight_table = Table(weight_data, colWidths=[4.5 * cm, 2.5 * cm, 10 * cm])
        weight_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f8f8")]),
            ])
        )
        elements.append(weight_table)
        elements.append(Spacer(1, 10 * mm))
        
        # ===== FLAGGED ENTITIES =====
        if report.flagged_entities:
            elements.append(PageBreak())
            elements.append(Paragraph("FLAGGED ENTITIES", subtitle_style))
            elements.append(Spacer(1, 3 * mm))
            
            elements.append(Paragraph(
                f"The analysis identified <b>{len(report.flagged_entities)} flagged entities</b> "
                f"with connections to suspicious or high-risk addresses. These entities were detected "
                f"within {report.trace_depth} hops from the target transaction.",
                body_style
            ))
            elements.append(Spacer(1, 5 * mm))
            
            entity_data = [["Address", "Risk Tags", "Distance", "Risk Score"]]
            
            for entity in report.flagged_entities[:30]:  # Show up to 30
                address_display = f"{entity.address[:10]}...{entity.address[-8:]}"
                tags_display = ", ".join(t.value.replace("_", " ").title() for t in entity.tags[:3])
                if len(entity.tags) > 3:
                    tags_display += f" +{len(entity.tags)-3}"
                    
                entity_data.append([
                    address_display,
                    tags_display,
                    f"{entity.distance} hops",
                    f"+{entity.contribution_score:.1f}",
                ])

            entity_table = Table(
                entity_data,
                colWidths=[5 * cm, 6 * cm, 3 * cm, 3 * cm],
            )
            entity_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (2, -1), "LEFT"),
                    ("ALIGN", (3, 0), (3, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fff3f3")]),
                ])
            )
            elements.append(entity_table)
            
            if len(report.flagged_entities) > 30:
                elements.append(Spacer(1, 3 * mm))
                elements.append(
                    Paragraph(
                        f"<i>Note: Showing 30 of {len(report.flagged_entities)} flagged entities. "
                        f"Additional entities available in detailed data export.</i>",
                        ParagraphStyle("Note", parent=body_style, fontSize=8, textColor=colors.HexColor("#666666"))
                    )
                )
            
            elements.append(Spacer(1, 8 * mm))
            
            # Entity breakdown by type
            elements.append(Paragraph("<b>Entity Type Breakdown:</b>", section_style))
            tag_counts = {}
            for entity in report.flagged_entities:
                for tag in entity.tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            
            if tag_counts:
                for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
                    elements.append(
                        Paragraph(
                            f"• <b>{tag.value.replace('_', ' ').title()}:</b> {count} entities",
                            body_style
                        )
                    )
        else:
            elements.append(Paragraph("FLAGGED ENTITIES", subtitle_style))
            elements.append(Spacer(1, 3 * mm))
            elements.append(
                Paragraph(
                    "✓ <b>No flagged entities detected during the analysis.</b> This transaction shows no "
                    "direct or indirect connections to known high-risk addresses within the analyzed depth.",
                    body_style,
                )
            )

        elements.append(Spacer(1, 10 * mm))

        # ===== RECOMMENDATIONS =====
        elements.append(Paragraph("RECOMMENDATIONS", subtitle_style))
        elements.append(Spacer(1, 3 * mm))
        
        recommendations = self._get_recommendations(report)
        for i, rec in enumerate(recommendations, 1):
            elements.append(Paragraph(f"<b>{i}.</b> {rec}", body_style))
            elements.append(Spacer(1, 2 * mm))
        
        elements.append(Spacer(1, 10 * mm))

        # ===== DATA SOURCES & LIMITATIONS =====
        elements.append(Paragraph("DATA SOURCES & LIMITATIONS", subtitle_style))
        elements.append(Spacer(1, 3 * mm))
        
        elements.append(Paragraph("<b>Data Sources:</b>", section_style))
        elements.append(Paragraph(
            "• Blockchain transaction data via Blockchair API<br/>"
            "• Public address labels and tags from blockchain explorers<br/>"
            "• Known risk entity databases (mixers, hacks, sanctions lists)",
            body_style
        ))
        elements.append(Spacer(1, 5 * mm))
        
        elements.append(Paragraph("<b>Limitations:</b>", section_style))
        elements.append(Paragraph(
            "• Analysis is limited to on-chain data and publicly available information<br/>"
            "• New or unlabeled addresses may not be flagged<br/>"
            "• Off-chain transactions and centralized exchange internals are not visible<br/>"
            f"• Analysis depth limited to {report.trace_depth} hops; deeper connections may exist",
            body_style
        ))

        elements.append(PageBreak())

        # ===== DISCLAIMER =====
        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#666666"),
            spaceBefore=10,
            leading=12,
        )
        
        elements.append(Paragraph("LEGAL DISCLAIMER", subtitle_style))
        elements.append(Spacer(1, 3 * mm))
        
        elements.append(
            Paragraph(
                "<b>Not Legal or Financial Advice:</b> This compliance certificate is generated through "
                "automated blockchain analysis using publicly available data and heuristic algorithms. "
                "It should NOT be considered as legal advice, financial advice, or a definitive determination "
                "of transaction legitimacy.",
                disclaimer_style,
            )
        )
        elements.append(Spacer(1, 3 * mm))
        
        elements.append(
            Paragraph(
                "<b>Professional Consultation Required:</b> Always consult with qualified legal, compliance, "
                "and financial professionals for definitive assessments. This report is a screening tool to "
                "assist in due diligence processes, not a replacement for professional judgment.",
                disclaimer_style,
            )
        )
        elements.append(Spacer(1, 3 * mm))
        
        elements.append(
            Paragraph(
                "<b>No Warranties:</b> SafeTrace provides this analysis on an 'as-is' basis without warranties "
                "of any kind. While we strive for accuracy, blockchain analysis is probabilistic in nature and "
                "false positives/negatives may occur.",
                disclaimer_style,
            )
        )
        
        elements.append(Spacer(1, 15 * mm))
        
        # Footer
        elements.append(
            Paragraph(
                f"<b>SafeTrace Blockchain Compliance Tool</b> • Version 1.0.0<br/>"
                f"Report Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}<br/>"
                f"© 2026 SafeTrace. All rights reserved.",
                ParagraphStyle("Footer", parent=disclaimer_style, alignment=1, fontSize=8),
            )
        )

        # Build PDF
        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        # Save to file if requested
        file_path = None
        if save_to_file:
            filename = f"compliance_{report.chain}_{report.tx_hash[:16]}_{report.analyzed_at.strftime('%Y%m%d%H%M%S')}.pdf"
            file_path = str(self._output_dir / filename)
            with open(file_path, "wb") as f:
                f.write(pdf_bytes)
            logger.info(f"Comprehensive PDF report saved to {file_path}")

        return pdf_bytes, file_path

    def generate_certificate_base64(self, report: RiskReport) -> str:
        """
        Generate a compliance certificate and return as base64 string.

        Args:
            report: Risk report to convert to PDF.

        Returns:
            Base64 encoded PDF string.
        """
        pdf_bytes, _ = self.generate_certificate(report, save_to_file=False)
        return base64.b64encode(pdf_bytes).decode("utf-8")

    def _get_risk_color(self, level: RiskLevel) -> Any:
        """Get color for risk level."""
        from reportlab.lib import colors
        
        color_map = {
            RiskLevel.LOW: colors.HexColor("#28a745"),
            RiskLevel.MEDIUM: colors.HexColor("#ffc107"),
            RiskLevel.HIGH: colors.HexColor("#dc3545"),
        }
        return color_map.get(level, colors.HexColor("#6c757d"))
    
    def _get_risk_classification(self, level: RiskLevel) -> str:
        """Get detailed classification text for risk level."""
        classifications = {
            RiskLevel.LOW: "Acceptable - Standard due diligence procedures apply",
            RiskLevel.MEDIUM: "Caution Advised - Enhanced due diligence recommended",
            RiskLevel.HIGH: "High Risk - Immediate attention and investigation required",
        }
        return classifications.get(level, "Unknown")
    
    def _get_recommendations(self, report: RiskReport) -> list[str]:
        """Generate recommendations based on risk level and findings."""
        recommendations = []
        
        if report.risk_score.level == RiskLevel.LOW:
            recommendations.extend([
                "<b>Proceed with standard procedures:</b> This transaction appears legitimate. "
                "Continue with normal business processes and standard KYC/AML procedures.",
                
                "<b>Maintain documentation:</b> Keep this compliance report on file for audit purposes "
                "and regulatory requirements.",
                
                "<b>Periodic review:</b> While currently low-risk, consider periodic re-evaluation "
                "for high-value or ongoing business relationships.",
            ])
        
        elif report.risk_score.level == RiskLevel.MEDIUM:
            recommendations.extend([
                "<b>Enhanced Due Diligence (EDD):</b> Conduct additional verification of the source "
                "of funds and the parties involved in this transaction.",
                
                "<b>Request documentation:</b> Obtain supporting documentation explaining the nature "
                "and purpose of this transaction from relevant parties.",
                
                "<b>Management review:</b> Escalate to compliance management for approval before "
                "proceeding with this transaction.",
                
                "<b>Monitor closely:</b> If proceeding, implement enhanced transaction monitoring "
                "for related accounts or future transactions.",
            ])
        
        else:  # HIGH
            recommendations.extend([
                "<b>DO NOT PROCEED without investigation:</b> This transaction exhibits significant "
                "risk indicators that require immediate attention and thorough investigation.",
                
                "<b>Senior management escalation:</b> Immediately escalate to senior compliance "
                "management and consider filing a Suspicious Activity Report (SAR) if applicable.",
                
                "<b>Comprehensive investigation:</b> Conduct a full investigation including source "
                "of funds analysis, beneficial ownership identification, and connection mapping.",
                
                "<b>Legal consultation:</b> Consult with legal counsel regarding potential regulatory "
                "obligations and sanctions screening requirements.",
                
                "<b>Account freezing consideration:</b> Evaluate whether to freeze related accounts "
                "pending investigation completion and regulatory guidance.",
            ])
        
        # Add specific recommendations based on flagged entities
        if report.flagged_entities:
            entity_types = set()
            for entity in report.flagged_entities:
                entity_types.update(entity.tags)
            
            if RiskTag.MIXER in entity_types or RiskTag.DARKNET in entity_types:
                recommendations.append(
                    "<b>Privacy service detected:</b> Connection to mixing services or darknet "
                    "markets identified. Investigate legitimate reasons for privacy protection "
                    "vs. potential illicit activity concealment."
                )
            
            if RiskTag.SANCTIONED in entity_types:
                recommendations.append(
                    "<b>CRITICAL - Sanctions exposure:</b> Connection to sanctioned entities detected. "
                    "Immediate sanctions screening and legal review required. Do not proceed without "
                    "explicit clearance from legal and compliance teams."
                )
        
        return recommendations

    def get_download_url(self, file_path: str, base_url: str = "") -> str:
        """
        Generate a download URL for a saved PDF.

        Args:
            file_path: Path to the saved PDF file.
            base_url: Base URL for the download endpoint.

        Returns:
            Download URL string.
        """
        filename = os.path.basename(file_path)
        return f"{base_url}/api/v1/compliance/download/{filename}"
