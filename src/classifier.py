# src/classifier.py
# import json
# import re
# from typing import Optional
# from src.schemas import DocumentClassification
# src/classifier.py  — top of file, add these
import json
import re
from pathlib import Path  # ← fixes "Path is not defined"
from typing import Optional
from src.schemas import DocumentClassification

CLASSIFICATION_SIGNALS = {
    "ANNUAL_REPORT": [
        "profit and loss", "balance sheet", "cash flow statement",
        "independent auditor", "board's report", "revenue from operations",
        "total assets", "total liabilities", "earnings per share",
        "statement of profit", "notes to accounts", "schedule iii"
    ],
    "ALM": [
        "asset liability", "maturity profile", "bucket", "outflows",
        "inflows", "1-30 days", "31-60", "over 5 years",
        "structural liquidity", "dynamic liquidity", "alm committee",
        "rate sensitive", "interest rate sensitivity", "gap analysis"
    ],
    "SHAREHOLDING_PATTERN": [
        "promoter", "public shareholding", "pledge", "encumbered",
        "demat", "physical shares", "institutional investors",
        "foreign portfolio", "mutual fund holding", "shareholding pattern",
        "promoter group", "non-promoter", "depository receipts"
    ],
    "BORROWING_PROFILE": [
        "borrowings", "debentures", "ncd", "term loan lenders",
        "debt funding", "credit rating", "subordinated debt",
        "external commercial borrowing", "lender", "sanction limit",
        "outstanding amount", "borrowing mix", "secured borrowings",
        "unsecured borrowings", "interest coverage"
    ],
    "PORTFOLIO_PERFORMANCE": [
        "aum", "assets under management", "disbursement", "gnpa",
        "nnpa", "collection efficiency", "portfolio at risk",
        "par 30", "par 60", "loan book", "npa", "write-off",
        "yield on portfolio", "cost of funds", "net interest margin",
        "credit cost", "stage 1", "stage 2", "stage 3"
    ]
}

LABEL_MAP = {
    "ANNUAL_REPORT":         "Annual Report (P&L / Balance Sheet / Cashflow)",
    "ALM":                   "ALM (Asset-Liability Management)",
    "SHAREHOLDING_PATTERN":  "Shareholding Pattern",
    "BORROWING_PROFILE":     "Borrowing Profile",
    "PORTFOLIO_PERFORMANCE": "Portfolio / Performance Data",
    "UNKNOWN":               "Unknown — needs manual classification"
}

ALL_DOC_TYPES = list(LABEL_MAP.keys())


def extract_preview_text(file_path: str, max_chars: int = 3000) -> str:
    """
    Fast text preview for classification — avoids full Docling parse.
    Uses PyMuPDF for PDFs, openpyxl for Excel, plain read for others.
    """
    suffix = Path(file_path).suffix.lower()
    try:
        if suffix == ".pdf":
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            text = ""
            # Only read first 5 pages — enough for classification
            for page in doc[:15]:
                text += page.get_text()
                if len(text) >= max_chars:
                    break
            doc.close()
            return text[:max_chars]

        elif suffix in (".xlsx", ".xls"):
            import openpyxl
            wb = openpyxl.load_workbook(
                file_path, read_only=True, data_only=True)
            text = ""
            for sheet in wb.sheetnames[:3]:
                ws = wb[sheet]
                for row in ws.iter_rows(max_row=30, values_only=True):
                    text += " ".join(str(c) for c in row if c) + "\n"
            wb.close()
            return text[:max_chars]

        elif suffix == ".docx":
            from docx import Document
            doc = Document(file_path)
            text = "\n".join(p.text for p in doc.paragraphs[:50])
            return text[:max_chars]

    except Exception as e:
        return f"preview_error: {str(e)}"

    return ""


def extract_financial_text(file_path: str, max_chars: int = 12000) -> str:
    """
    Targeted extraction for financial data — scans ALL pages but only
    keeps text from pages containing financial keywords.
    Much faster than full Docling, smarter than first-N-pages.
    """
    suffix = Path(file_path).suffix.lower()
    if suffix != ".pdf":
        return extract_preview_text(file_path, max_chars)

    try:
        import fitz
        doc = fitz.open(file_path)

        FINANCIAL_KEYWORDS = [
            "profit and loss", "balance sheet", "cash flow",
            "revenue from operations", "total income", "total assets",
            "net worth", "borrowings", "aum", "gnpa", "disbursement",
            "promoter", "shareholding", "maturity", "asset liability",
            "pat", "ebitda", "interest expense", "finance cost",
            "total equity", "net profit", "earnings per share"
        ]

        financial_pages = []
        cover_pages = []

        for i, page in enumerate(doc):
            text = page.get_text("text")
            text_lower = text.lower()

            # Score this page
            hits = sum(1 for kw in FINANCIAL_KEYWORDS if kw in text_lower)

            if hits >= 2:
                financial_pages.append((i, hits, text))
            elif i < 10:
                # Always include first 10 pages for context
                cover_pages.append(text)

        doc.close()

        # Sort financial pages by relevance score (most hits first)
        financial_pages.sort(key=lambda x: x[1], reverse=True)

        # Build output: cover context + top financial pages
        combined = "\n".join(cover_pages[:3])  # first 3 pages for context
        combined += "\n\n--- FINANCIAL SECTIONS ---\n\n"

        # top 15 most relevant pages
        for _, hits, text in financial_pages[:15]:
            combined += text + "\n\n"
            if len(combined) >= max_chars:
                break

        print(
            f"[EXTRACT_TEXT] Found {len(financial_pages)} financial pages, using top {min(15, len(financial_pages))}")
        return combined[:max_chars]

    except Exception as e:
        print(f"[EXTRACT_TEXT] Error: {e}, falling back to preview")
        return extract_preview_text(file_path, max_chars)


def classify_by_keywords(text: str) -> tuple[str, float, dict]:
    """Fast keyword pre-classifier. Returns (doc_type, confidence, score_map)."""
    text_lower = text.lower()
    scores = {
        doc_type: sum(1 for kw in keywords if kw in text_lower)
        for doc_type, keywords in CLASSIFICATION_SIGNALS.items()
    }

    best = max(scores, key=scores.get)
    total_hits = sum(scores.values())

    if scores[best] < 2 or total_hits == 0:
        return "UNKNOWN", 0.15, scores

    confidence = round(min(scores[best] / total_hits, 0.95), 2)
    return best, confidence, scores


def classify_with_llm(filename: str, text_preview: str, kw_hint: str) -> DocumentClassification:
    """LLM-based classifier with keyword hint. Falls back gracefully."""
    from config import get_groq_client
    client = get_groq_client()

    prompt = f"""You are a financial document classifier for an NBFC credit underwriting system.

Classify the document into EXACTLY ONE of:
- ANNUAL_REPORT    : P&L, Balance Sheet, Cashflow, Auditor Report, Board Report
- ALM              : Asset-Liability table with maturity buckets / time bands
- SHAREHOLDING_PATTERN : Promoter %, public holding %, pledge data
- BORROWING_PROFILE : Lender list, NCD details, borrowing mix, credit ratings
- PORTFOLIO_PERFORMANCE : AUM, disbursements, NPA%, collection efficiency
- UNKNOWN          : Cannot be determined

Filename: {filename}
Keyword pre-classification hint: {kw_hint}

Document preview:
{text_preview[:700]}

Respond ONLY with valid JSON — no markdown, no explanation outside the JSON:
{{
  "doc_type": "<type>",
  "confidence": <0.0-1.0>,
  "reasoning": "<one sentence>",
  "key_signals": ["<signal1>", "<signal2>", "<signal3>"]
}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"```(?:json)?|```", "", raw).strip()
        data = json.loads(raw)

        doc_type = data.get("doc_type", kw_hint)
        if doc_type not in ALL_DOC_TYPES:
            doc_type = "UNKNOWN"

        return DocumentClassification(
            doc_type=doc_type,
            doc_type_label=LABEL_MAP[doc_type],
            confidence=float(data.get("confidence", 0.5)),
            reasoning=data.get("reasoning", "LLM classification"),
            key_signals=data.get("key_signals", [])
        )

    except Exception as e:
        # Graceful fallback to keyword result
        kw_type, kw_conf, _ = classify_by_keywords(text_preview)
        return DocumentClassification(
            doc_type=kw_type,
            doc_type_label=LABEL_MAP.get(kw_type, "Unknown"),
            confidence=kw_conf,
            reasoning=f"LLM unavailable — keyword fallback. ({str(e)[:60]})",
            key_signals=[]
        )


def classify_document(filename: str, parsed_text: str) -> DocumentClassification:
    """
    Main entry point. Keyword pass first — if confidence ≥ 0.75, skip LLM.
    Otherwise calls LLM with keyword hint.
    """
    kw_type, kw_conf, kw_scores = classify_by_keywords(parsed_text)

    # High-confidence keyword match → skip LLM (saves API calls)
    if kw_conf >= 0.75:
        matched_signals = [
            kw for kw in CLASSIFICATION_SIGNALS.get(kw_type, [])
            if kw in parsed_text.lower()
        ][:4]
        return DocumentClassification(
            doc_type=kw_type,
            doc_type_label=LABEL_MAP[kw_type],
            confidence=kw_conf,
            reasoning=f"High-confidence keyword match ({kw_conf:.0%}).",
            key_signals=matched_signals
        )

    # Low confidence → LLM with keyword hint
    return classify_with_llm(filename, parsed_text, kw_type)
