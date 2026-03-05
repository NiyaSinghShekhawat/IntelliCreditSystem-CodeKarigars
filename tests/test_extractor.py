from src.schemas import ParsedDocument, DocumentType
from src.extractor import FinancialExtractor
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))
extractor = FinancialExtractor()
print("GSTIN test...")
fake_gst = ParsedDocument(
    source_file="test.pdf",
    document_type=DocumentType.GST_RETURN,
    raw_text="GSTIN: 27AABCU9603R1ZX Legal Name: ABC PRIVATE LIMITED Total Turnover: 45,00,000 IGST: 2,50,000 CGST: 1,25,000 SGST: 1,25,000 ITC: 80,000"
)
result = extractor.extract_gst(fake_gst)
print(f"GSTIN: {result.gstin}")
print(f"Turnover: {result.turnover}")
print(f"Total Tax: {result.total_tax}")
print("DONE")
