"""PDF compliance certificate generator service."""

import base64
import io
import logging
import os
from datetime import datetime
from pathlib import Path

from app.constants import RiskLevel, SUPPORTED_CHAINS
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
        Generate a compliance certificate PDF.

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
            )
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
            fontSize=24,
            spaceAfter=30,
            alignment=1,  # Center
            textColor=colors.HexColor("#1a1a2e"),
        )

        subtitle_style = ParagraphStyle(
            "CustomSubtitle",
            parent=styles["Heading2"],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor("#16213e"),
        )

        body_style = ParagraphStyle(
            "CustomBody",
            parent=styles["Normal"],
            fontSize=10,
            spaceAfter=6,
            textColor=colors.HexColor("#333333"),
        )

        # Title
        elements.append(
            Paragraph("Blockchain Transaction Compliance Certificate", title_style)
        )
        elements.append(Spacer(1, 10 * mm))

        # Generation info
        elements.append(
            Paragraph(
                f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                body_style,
            )
        )
        elements.append(
            Paragraph(
                f"Report ID: {report.tx_hash[:16]}...{report.analyzed_at.strftime('%Y%m%d%H%M%S')}",
                body_style,
            )
        )
        elements.append(Spacer(1, 10 * mm))

        # Transaction Details
        elements.append(Paragraph("Transaction Details", subtitle_style))
        
        chain_name = SUPPORTED_CHAINS.get(report.chain, None)
        chain_display = chain_name.name if chain_name else report.chain.title()

        tx_data = [
            ["Transaction Hash:", report.tx_hash],
            ["Blockchain Network:", chain_display],
            ["Analysis Timestamp:", report.analyzed_at.strftime("%Y-%m-%d %H:%M:%S UTC")],
            ["Trace Depth:", f"{report.trace_depth} hops"],
            ["Addresses Analyzed:", str(report.total_addresses_analyzed)],
            ["Transactions Analyzed:", str(report.total_transactions_analyzed)],
            ["API Calls Used:", str(report.api_calls_used)],
        ]

        tx_table = Table(tx_data, colWidths=[5 * cm, 12 * cm])
        tx_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f0f0")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#333333")),
                ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                ("ALIGN", (1, 0), (1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ])
        )
        elements.append(tx_table)
        elements.append(Spacer(1, 10 * mm))

        # Risk Assessment
        elements.append(Paragraph("Risk Assessment", subtitle_style))

        risk_color = self._get_risk_color(report.risk_score.level)
        
        risk_data = [
            ["Risk Score:", f"{report.risk_score.score}/100"],
            ["Risk Level:", report.risk_score.level.value],
        ]

        risk_table = Table(risk_data, colWidths=[5 * cm, 12 * cm])
        risk_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f0f0")),
                ("BACKGROUND", (1, 1), (1, 1), risk_color),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#333333")),
                ("TEXTCOLOR", (1, 1), (1, 1), colors.white),
                ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                ("ALIGN", (1, 0), (1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 1), (1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ])
        )
        elements.append(risk_table)
        elements.append(Spacer(1, 5 * mm))

        # Risk Reasons
        if report.risk_score.reasons:
            elements.append(Paragraph("Analysis Details:", body_style))
            for reason in report.risk_score.reasons:
                elements.append(
                    Paragraph(f"  - {reason}", body_style)
                )
        elements.append(Spacer(1, 10 * mm))

        # Flagged Entities
        if report.flagged_entities:
            elements.append(Paragraph("Flagged Entities", subtitle_style))
            
            entity_data = [["Address", "Tags", "Distance", "Contribution"]]
            
            for entity in report.flagged_entities[:20]:  # Limit to 20 entries
                address_display = f"{entity.address[:8]}...{entity.address[-6:]}"
                tags_display = ", ".join(t.value for t in entity.tags)
                entity_data.append([
                    address_display,
                    tags_display,
                    f"{entity.distance} hops",
                    f"{entity.contribution_score:.1f}",
                ])

            entity_table = Table(
                entity_data,
                colWidths=[4 * cm, 6 * cm, 3 * cm, 3 * cm],
            )
            entity_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                        colors.white,
                        colors.HexColor("#f8f8f8"),
                    ]),
                ])
            )
            elements.append(entity_table)
            
            if len(report.flagged_entities) > 20:
                elements.append(
                    Paragraph(
                        f"... and {len(report.flagged_entities) - 20} more entities",
                        body_style,
                    )
                )
        else:
            elements.append(
                Paragraph(
                    "No flagged entities detected during analysis.",
                    body_style,
                )
            )

        elements.append(Spacer(1, 15 * mm))

        # Disclaimer
        disclaimer_style = ParagraphStyle(
            "Disclaimer",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#666666"),
            spaceBefore=10,
        )
        
        elements.append(
            Paragraph(
                "DISCLAIMER: This compliance certificate is generated based on automated "
                "blockchain analysis and should not be considered as legal or financial advice. "
                "The risk assessment is based on publicly available blockchain data and "
                "heuristic analysis. Always consult with qualified compliance professionals "
                "for definitive assessments.",
                disclaimer_style,
            )
        )

        elements.append(Spacer(1, 5 * mm))
        
        elements.append(
            Paragraph(
                f"SafeTrace Blockchain Compliance Tool v1.0.0",
                disclaimer_style,
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
            logger.info(f"PDF saved to {file_path}")

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

    def _get_risk_color(self, level: RiskLevel) -> "colors.Color":
        """Get color for risk level."""
        from reportlab.lib import colors
        
        color_map = {
            RiskLevel.LOW: colors.HexColor("#28a745"),
            RiskLevel.MEDIUM: colors.HexColor("#ffc107"),
            RiskLevel.HIGH: colors.HexColor("#dc3545"),
        }
        return color_map.get(level, colors.HexColor("#6c757d"))

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
