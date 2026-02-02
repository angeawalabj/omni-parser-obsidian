"""
Auditor Module – Pre-flight Analysis of Source Files

Purpose:
- Analyze source HTML and ENEX files BEFORE transformation
- Detect complexity risks (tables, images, code blocks, nesting)
- Prevent silent data loss during conversion
- Produce a reliable audit report usable by the pipeline

This module is fail-soft, idempotent, and production-ready.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List
from dataclasses import dataclass, field
from datetime import datetime

from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET


# ============================================================
# Configuration
# ============================================================

MAX_SAFE_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

COMPLEXITY_WEIGHTS = {
    "size_kb": 0.1,
    "table": 10,
    "nested_table": 20,
    "merged_cells": 15,
    "image": 5,
    "code": 3,
}


# ============================================================
# Data Models
# ============================================================

@dataclass(slots=True)
class FileAudit:
    filepath: Path
    file_size: int
    table_count: int = 0
    image_count: int = 0
    code_block_count: int = 0
    has_tables: bool = False
    has_images: bool = False
    has_code_blocks: bool = False
    complexity_score: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


@dataclass(slots=True)
class AuditReport:
    audited_at: datetime = field(default_factory=datetime.utcnow)
    total_files: int = 0
    total_tables: int = 0
    total_images: int = 0
    total_code_blocks: int = 0
    total_size: int = 0
    is_valid: bool = True
    file_audits: List[FileAudit] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


# ============================================================
# Auditor
# ============================================================

class SourceAuditor:
    """
    Pre-flight auditor for migration pipelines.
    """

    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger(__name__)

    # -------------------------
    # Public API
    # -------------------------

    def audit_directory(self, source_dir: Path) -> AuditReport:
        report = AuditReport()

        if not source_dir.exists():
            report.is_valid = False
            report.errors.append(f"Source directory not found: {source_dir}")
            return report

        files = (
            list(source_dir.rglob("*.html")) +
            list(source_dir.rglob("*.enex"))
        )

        if not files:
            report.is_valid = False
            report.errors.append("No HTML or ENEX files found.")
            return report

        self.logger.info("Starting audit", extra={"files": len(files)})

        for filepath in files:
            file_audit = self._audit_file(filepath)
            report.file_audits.append(file_audit)

            report.total_files += 1
            report.total_tables += file_audit.table_count
            report.total_images += file_audit.image_count
            report.total_code_blocks += file_audit.code_block_count
            report.total_size += file_audit.file_size

            report.warnings.extend(file_audit.warnings)
            report.errors.extend(file_audit.errors)

        if report.errors:
            report.is_valid = False

        return report

    # -------------------------
    # Internal Processing
    # -------------------------

    def _audit_file(self, filepath: Path) -> FileAudit:
        audit = FileAudit(
            filepath=filepath,
            file_size=filepath.stat().st_size
        )

        if audit.file_size > MAX_SAFE_FILE_SIZE:
            audit.warnings.append(
                f"Large file detected ({audit.file_size / 1024 / 1024:.1f} MB)"
            )

        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")

            if filepath.suffix.lower() == ".enex":
                self._audit_enex(content, audit)
            else:
                self._audit_html(content, audit)

            audit.has_tables = audit.table_count > 0
            audit.has_images = audit.image_count > 0
            audit.has_code_blocks = audit.code_block_count > 0

            audit.complexity_score = self._calculate_complexity(audit)

            if audit.complexity_score > 120:
                audit.warnings.append(
                    f"High complexity score: {audit.complexity_score}"
                )

        except Exception as exc:
            self.logger.exception("Audit failed", extra={"file": filepath.name})
            audit.errors.append(str(exc))

        return audit

    def _audit_html(self, content: str, audit: FileAudit) -> None:
        try:
            soup = BeautifulSoup(content, "lxml")
        except Exception:
            soup = BeautifulSoup(content, "html.parser")

        tables = soup.find_all("table")
        audit.table_count += len(tables)

        for table in tables:
            if table.find("table"):
                audit.warnings.append("Nested table detected")
            if table.find(attrs={"rowspan": True}) or table.find(attrs={"colspan": True}):
                audit.warnings.append("Merged table cells detected")

        audit.image_count += len(soup.find_all("img"))
        audit.code_block_count += len(soup.find_all(["pre", "code"]))

    def _audit_enex(self, content: str, audit: FileAudit) -> None:
        try:
            root = ET.fromstring(content)
        except ET.ParseError as exc:
            audit.errors.append(f"Invalid ENEX XML: {exc}")
            return

        for note in root.findall(".//note"):
            note_content = note.find("content")
            if note_content is not None and note_content.text:
                self._audit_html(note_content.text, audit)

            resources = note.findall(".//resource")
            audit.image_count += len(resources)

    # -------------------------
    # Complexity Scoring
    # -------------------------

    def _calculate_complexity(self, audit: FileAudit) -> int:
        score = 0

        score += int((audit.file_size / 1024) * COMPLEXITY_WEIGHTS["size_kb"])
        score += audit.table_count * COMPLEXITY_WEIGHTS["table"]
        score += audit.image_count * COMPLEXITY_WEIGHTS["image"]
        score += audit.code_block_count * COMPLEXITY_WEIGHTS["code"]

        if any("nested" in w.lower() for w in audit.warnings):
            score += COMPLEXITY_WEIGHTS["nested_table"]

        if any("merged" in w.lower() for w in audit.warnings):
            score += COMPLEXITY_WEIGHTS["merged_cells"]

        return score

    # -------------------------
    # Reporting
    # -------------------------

    def generate_text_report(self, report: AuditReport) -> str:
        lines = [
            "=" * 70,
            "OMNI-PARSER – PRE-FLIGHT AUDIT REPORT",
            "=" * 70,
            f"Audited At: {report.audited_at.isoformat()} UTC",
            f"Total Files: {report.total_files}",
            f"Total Size: {report.total_size / 1024 / 1024:.2f} MB",
            f"Tables: {report.total_tables}",
            f"Images: {report.total_images}",
            f"Code Blocks: {report.total_code_blocks}",
            "",
            f"STATUS: {'PASSED' if report.is_valid else 'FAILED'}",
        ]

        if report.errors:
            lines.append("\nERRORS:")
            for err in report.errors:
                lines.append(f"  • {err}")

        if report.warnings:
            lines.append("\nWARNINGS:")
            for warn in report.warnings[:10]:
                lines.append(f"  • {warn}")
            if len(report.warnings) > 10:
                lines.append(f"  ... and {len(report.warnings) - 10} more")

        lines.append("=" * 70)
        return "\n".join(lines)
