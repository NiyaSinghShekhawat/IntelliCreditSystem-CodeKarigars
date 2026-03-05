# src/parser.py
from config import SUPPORTED_FORMATS, MAX_FILE_SIZE_MB, DEBUG_MODE
from src.schemas import ParsedDocument, ExtractedTable, DocumentType
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter
import os
import sys
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))


class DocumentParser:
    """
    Universal document parser using Docling.
    Handles PDF, Excel, DOCX, and images.
    """

    def __init__(self):
        print("Loading Docling converter... (first time may take 1-2 min)")
        self.converter = DocumentConverter(
            allowed_formats=[
                InputFormat.PDF,
                InputFormat.DOCX,
                InputFormat.XLSX,
                InputFormat.IMAGE,
                InputFormat.HTML,
            ]
        )
        print("Docling ready.")

    # ─── MAIN METHOD ─────────────────────────────────────────────────────────

    def parse(self, file_path: str) -> ParsedDocument:
        """
        Parse any supported document and return structured output.
        This is the only method you need to call from outside.
        """
        path = Path(file_path)

        # Validate file exists
        if not path.exists():
            return ParsedDocument(
                source_file=file_path,
                error=f"File not found: {file_path}"
            )

        # Validate file format
        if path.suffix.lower() not in SUPPORTED_FORMATS:
            return ParsedDocument(
                source_file=file_path,
                error=f"Unsupported format: {path.suffix}. Supported: {SUPPORTED_FORMATS}"
            )

        # Validate file size
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            return ParsedDocument(
                source_file=file_path,
                error=f"File too large: {size_mb:.1f}MB. Max: {MAX_FILE_SIZE_MB}MB"
            )

        try:
            if DEBUG_MODE:
                print(f"Parsing: {path.name}")

            # Run Docling conversion
            result = self.converter.convert(str(path))
            doc = result.document

            # Extract text
            raw_text = doc.export_to_text()
            markdown = doc.export_to_markdown()

            # Extract tables
            tables = self._extract_tables(doc)

            # Auto-detect document type from filename + content
            doc_type = self._detect_document_type(path.name, raw_text)

            # Count pages
            page_count = self._get_page_count(doc)

            if DEBUG_MODE:
                print(f"Parsed {path.name}: {len(raw_text)} chars, "
                      f"{len(tables)} tables, {page_count} pages")

            return ParsedDocument(
                source_file=str(path),
                document_type=doc_type,
                raw_text=raw_text,
                markdown=markdown,
                tables=tables,
                page_count=page_count
            )

        except Exception as e:
            print(f"Error parsing {path.name}: {e}")
            return ParsedDocument(
                source_file=file_path,
                error=str(e)
            )

    # ─── TABLE EXTRACTION ────────────────────────────────────────────────────

    def _extract_tables(self, doc) -> list[ExtractedTable]:
        """Extract all tables from parsed document"""
        tables = []

        try:
            for i, table in enumerate(doc.tables):
                try:
                    # Get table as dataframe
                    df = table.export_to_dataframe()

                    if df.empty:
                        continue

                    extracted = ExtractedTable(
                        table_index=i,
                        headers=list(df.columns.astype(str)),
                        rows=df.values.tolist(),
                        raw_text=df.to_string()
                    )
                    tables.append(extracted)

                except Exception as e:
                    if DEBUG_MODE:
                        print(f"Could not extract table {i}: {e}")
                    continue

        except Exception as e:
            if DEBUG_MODE:
                print(f"Table extraction error: {e}")

        return tables

    # ─── DOCUMENT TYPE DETECTION ─────────────────────────────────────────────

    def _detect_document_type(self, filename: str, text: str) -> DocumentType:
        """
        Auto-detect document type from filename and content.
        Used to route data to the right extractor later.
        """
        filename_lower = filename.lower()
        text_lower = text.lower()[:2000]  # Check first 2000 chars only

        # Check filename first
        if any(kw in filename_lower for kw in ["gst", "gstr", "3b", "2a", "r1"]):
            return DocumentType.GST_RETURN

        if any(kw in filename_lower for kw in ["itr", "income_tax", "incometax"]):
            return DocumentType.ITR

        if any(kw in filename_lower for kw in ["bank", "statement", "account"]):
            return DocumentType.BANK_STATEMENT

        if any(kw in filename_lower for kw in ["annual", "ar_", "annual_report"]):
            return DocumentType.ANNUAL_REPORT

        if any(kw in filename_lower for kw in ["balance", "p&l", "financial"]):
            return DocumentType.FINANCIAL_STATEMENT

        if any(kw in filename_lower for kw in ["legal", "notice", "court", "summon"]):
            return DocumentType.LEGAL_NOTICE

        # Check content if filename didn't match
        if any(kw in text_lower for kw in ["gstin", "gstr", "igst", "cgst", "sgst"]):
            return DocumentType.GST_RETURN

        if any(kw in text_lower for kw in ["assessment year", "income tax return", "pan"]):
            return DocumentType.ITR

        if any(kw in text_lower for kw in ["account no", "debit", "credit", "balance"]):
            return DocumentType.BANK_STATEMENT

        if any(kw in text_lower for kw in ["directors report", "auditors report", "annual report"]):
            return DocumentType.ANNUAL_REPORT

        return DocumentType.OTHER

    # ─── PAGE COUNT ──────────────────────────────────────────────────────────

    def _get_page_count(self, doc) -> int:
        """Get number of pages in document"""
        try:
            return len(doc.pages) if hasattr(doc, 'pages') else 0
        except:
            return 0

    # ─── BATCH PARSING ───────────────────────────────────────────────────────

    def parse_multiple(self, file_paths: list[str]) -> list[ParsedDocument]:
        """Parse multiple documents at once"""
        results = []
        for i, path in enumerate(file_paths):
            print(f"Parsing file {i+1}/{len(file_paths)}: {Path(path).name}")
            result = self.parse(path)
            results.append(result)
        return results

    # ─── QUICK SUMMARY ───────────────────────────────────────────────────────

    def get_summary(self, parsed: ParsedDocument) -> dict:
        """
        Get a quick summary of parsed document.
        Useful for debugging and logging.
        """
        return {
            "file": Path(parsed.source_file).name,
            "type": parsed.document_type.value,
            "pages": parsed.page_count,
            "tables": len(parsed.tables),
            "text_length": len(parsed.raw_text),
            "has_error": parsed.error is not None,
            "error": parsed.error
        }


# ─── QUICK TEST ──────────────────────────────────────────────────────────────
# Run this file directly to test: python src/parser.py

if __name__ == "__main__":
    parser = DocumentParser()

    # Test with any PDF you have
    test_file = input(
        "Enter path to a PDF to test (or press Enter to skip): ").strip()

    if test_file and Path(test_file).exists():
        result = parser.parse(test_file)
        summary = parser.get_summary(result)

        print("\n--- PARSE RESULT ---")
        print(f"File:   {summary['file']}")
        print(f"Type:   {summary['type']}")
        print(f"Pages:  {summary['pages']}")
        print(f"Tables: {summary['tables']}")
        print(f"Text:   {summary['text_length']} characters")

        if result.error:
            print(f"Error:  {result.error}")
        else:
            print("\n--- FIRST 500 CHARS OF TEXT ---")
            print(result.raw_text[:500])

            if result.tables:
                print(f"\n--- FIRST TABLE ---")
                t = result.tables[0]
                print(f"Headers: {t.headers}")
                print(f"Rows: {len(t.rows)}")
    else:
        print("No test file provided. Parser loaded successfully.")
# ```

# ---

# Once pasted, you can ** quickly test it ** works by running:
# ```
# python src/parser.py
