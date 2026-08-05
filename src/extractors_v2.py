# src/extractors_v2.py
"""
Extractors for the 5 new document types required by Vivriti Capital hackathon:
  - Annual Report    (P&L, Balance Sheet, Cashflow)
  - ALM              (Asset-Liability Management)
  - Shareholding Pattern
  - Borrowing Profile
  - Portfolio / Performance Data

Each extractor:
  1. Tries regex/keyword extraction first (fast, deterministic)
  2. Falls back to Groq LLM if regex yields < 3 fields
  3. Returns a typed Pydantic model
"""

import re
import json
from typing import Optional
from pydantic import BaseModel, Field


# ─── PYDANTIC MODELS ──────────────────────────────────────────────────────────

class AnnualReportData(BaseModel):
    """Extracted from Annual Report — P&L, Balance Sheet, Cashflow"""
    fy_year: Optional[str] = None
    revenue_cr: Optional[float] = None
    pat_cr: Optional[float] = None
    total_assets_cr: Optional[float] = None
    net_worth_cr: Optional[float] = None
    total_debt_cr: Optional[float] = None
    ebitda_cr: Optional[float] = None
    interest_expense_cr: Optional[float] = None
    depreciation_cr: Optional[float] = None
    operating_cashflow_cr: Optional[float] = None
    capex_cr: Optional[float] = None
    dividend_paid_cr: Optional[float] = None
    extraction_confidence: float = 0.0
    extraction_notes: list[str] = []


class ALMData(BaseModel):
    """Extracted from ALM (Asset-Liability Management) table"""
    # Assets by maturity bucket (₹ Cr)
    bucket_0_30d_assets_cr: Optional[float] = None
    bucket_31_60d_assets_cr: Optional[float] = None
    bucket_61_90d_assets_cr: Optional[float] = None
    bucket_1_3m_assets_cr: Optional[float] = None
    bucket_3_6m_assets_cr: Optional[float] = None
    bucket_6_12m_assets_cr: Optional[float] = None
    bucket_1_3yr_assets_cr: Optional[float] = None
    bucket_3_5yr_assets_cr: Optional[float] = None
    bucket_5yr_plus_assets_cr: Optional[float] = None
    total_assets_cr: Optional[float] = None
    # Liabilities by maturity bucket (₹ Cr)
    bucket_0_30d_liab_cr: Optional[float] = None
    bucket_31_60d_liab_cr: Optional[float] = None
    bucket_61_90d_liab_cr: Optional[float] = None
    bucket_1_3m_liab_cr: Optional[float] = None
    bucket_3_6m_liab_cr: Optional[float] = None
    bucket_6_12m_liab_cr: Optional[float] = None
    bucket_1_3yr_liab_cr: Optional[float] = None
    bucket_3_5yr_liab_cr: Optional[float] = None
    bucket_5yr_plus_liab_cr: Optional[float] = None
    total_liab_cr: Optional[float] = None
    # Derived
    liquidity_gap_cr: Optional[float] = None
    cumulative_gap_cr: Optional[float] = None
    extraction_confidence: float = 0.0
    extraction_notes: list[str] = []


class ShareholdingData(BaseModel):
    """Extracted from Shareholding Pattern"""
    promoter_holding_pct: Optional[float] = None
    promoter_group_holding_pct: Optional[float] = None
    public_holding_pct: Optional[float] = None
    fii_fpi_holding_pct: Optional[float] = None
    dii_holding_pct: Optional[float] = None
    mutual_fund_holding_pct: Optional[float] = None
    individual_holding_pct: Optional[float] = None
    pledged_shares_pct: Optional[float] = None
    total_shares: Optional[int] = None
    as_of_date: Optional[str] = None
    extraction_confidence: float = 0.0
    extraction_notes: list[str] = []


class BorrowingProfileData(BaseModel):
    """Extracted from Borrowing Profile"""
    total_borrowings_cr: Optional[float] = None
    secured_borrowings_cr: Optional[float] = None
    unsecured_borrowings_cr: Optional[float] = None
    ncd_outstanding_cr: Optional[float] = None
    bank_loans_cr: Optional[float] = None
    ecb_cr: Optional[float] = None
    subordinated_debt_cr: Optional[float] = None
    credit_rating: Optional[str] = None
    rating_agency: Optional[str] = None
    number_of_lenders: Optional[int] = None
    debt_equity_ratio: Optional[float] = None
    interest_coverage_ratio: Optional[float] = None
    weighted_avg_cost_pct: Optional[float] = None
    as_of_date: Optional[str] = None
    extraction_confidence: float = 0.0
    extraction_notes: list[str] = []


class PortfolioPerformanceData(BaseModel):
    """Extracted from Portfolio / Performance Data"""
    aum_cr: Optional[float] = None
    disbursements_cr: Optional[float] = None
    disbursements_yoy_growth_pct: Optional[float] = None
    number_of_loans: Optional[int] = None
    number_of_customers: Optional[int] = None
    gnpa_pct: Optional[float] = None
    nnpa_pct: Optional[float] = None
    collection_efficiency_pct: Optional[float] = None
    par_30_pct: Optional[float] = None
    par_60_pct: Optional[float] = None
    par_90_pct: Optional[float] = None
    yield_on_portfolio_pct: Optional[float] = None
    cost_of_funds_pct: Optional[float] = None
    nim_pct: Optional[float] = None
    credit_cost_pct: Optional[float] = None
    roe_pct: Optional[float] = None
    roa_pct: Optional[float] = None
    capital_adequacy_ratio_pct: Optional[float] = None
    as_of_date: Optional[str] = None
    extraction_confidence: float = 0.0
    extraction_notes: list[str] = []


# ─── HELPER FUNCTIONS ─────────────────────────────────────────────────────────

def _parse_number(text: str) -> Optional[float]:
    """
    Parse Indian-format numbers from text.
    Handles: 1,234.56 / 1234.56 / 12.34 crore / ₹1,234 cr
    """
    if not text:
        return None
    # Remove currency symbols, commas, whitespace
    cleaned = re.sub(r'[₹$,\s]', '', str(text).strip())
    # Remove trailing units
    cleaned = re.sub(
        r'(?i)(crore|cr|lakh|mn|million|billion|%).*$', '', cleaned)
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _find_amount(text: str, patterns: list[str], window: int = 80) -> Optional[float]:
    """
    Find a number near any of the given keyword patterns in text.
    Returns the first valid number found within `window` chars after the keyword.
    """
    text_lower = text.lower()
    for pattern in patterns:
        idx = text_lower.find(pattern.lower())
        if idx == -1:
            continue
        # Look at the text window after the keyword
        snippet = text[idx:idx + window]
        # Find all numbers in that snippet
        numbers = re.findall(r'[\d,]+\.?\d*', snippet)
        for n in numbers:
            val = _parse_number(n)
            if val is not None and val > 0:
                return val
    return None


def _count_filled(obj: BaseModel) -> int:
    """Count how many non-None, non-metadata fields are filled."""
    skip = {'extraction_confidence', 'extraction_notes'}
    return sum(
        1 for k, v in obj.model_dump().items()
        if k not in skip and v is not None
    )


def _llm_extract(doc_type: str, text: str, schema_fields: list[dict]) -> dict:
    """
    Use Groq LLM to extract structured data from document text.
    Returns a dict of field -> value.
    Uses first 4000 + last 4000 chars to capture both headers and summary totals.
    """
    from config import get_groq_client
    client = get_groq_client()

    fields_desc = "\n".join(
        f"- {f['field']}: {f['description']}" for f in schema_fields
    )

    # Smart truncation: first 4k chars (headers/cover) + last 4k (summary totals)
    if len(text) > 8000:
        text_for_llm = text[:4000] + \
            "\n...[middle truncated]...\n" + text[-4000:]
    else:
        text_for_llm = text

    prompt = f"""You are a financial data extractor for an NBFC credit underwriting system.

Extract the following fields from this {doc_type} document.
Return ONLY valid JSON with the exact field names below.
Use null for any field you cannot find. All monetary values in ₹ Crore.
Do NOT include units in the values — just the number.
Look carefully through ALL sections — key values often appear in summary tables at the end.

Fields to extract:
{fields_desc}

Document text:
{text_for_llm}

Respond ONLY with valid JSON, no markdown fences, no explanation:"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.05,
            max_tokens=1200
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"```(?:json)?|```", "", raw).strip()
        return json.loads(raw)
    except Exception as e:
        print(f"[EXTRACTOR] LLM extraction failed for {doc_type}: {e}")
        return {}


# ─── ANNUAL REPORT EXTRACTOR ──────────────────────────────────────────────────

def extract_annual_report(text: str, tables: list = None) -> AnnualReportData:
    """Extract P&L, Balance Sheet, Cashflow from annual report text."""
    data = AnnualReportData()
    notes = []

    # FY year
    fy_match = re.search(
        r'(?:FY|F\.Y\.|financial year)[.\s]*(\d{2,4}[-–]\d{2,4}|\d{4})', text, re.I)
    if fy_match:
        data.fy_year = fy_match.group(1)

    # Revenue
    data.revenue_cr = _find_amount(text, [
        "revenue from operations", "total income", "total revenue",
        "net revenue", "income from operations"
    ])

    # PAT
    data.pat_cr = _find_amount(text, [
        "profit after tax", "pat", "profit for the year",
        "net profit after tax", "profit after taxation"
    ])

    # Total assets
    data.total_assets_cr = _find_amount(text, [
        "total assets", "total asset"
    ])

    # Net worth
    data.net_worth_cr = _find_amount(text, [
        "net worth", "shareholders equity", "shareholders' equity",
        "total equity", "equity share capital", "total stockholders"
    ])

    # Total debt / borrowings
    data.total_debt_cr = _find_amount(text, [
        "total borrowings", "total debt", "borrowings",
        "total financial liabilities"
    ])

    # EBITDA
    data.ebitda_cr = _find_amount(text, [
        "ebitda", "earnings before interest, tax",
        "operating profit before depreciation"
    ])

    # Interest expense
    data.interest_expense_cr = _find_amount(text, [
        "finance costs", "interest expense", "interest paid",
        "finance cost", "interest on borrowings"
    ])

    # Operating cashflow
    data.operating_cashflow_cr = _find_amount(text, [
        "net cash from operating", "cash flow from operations",
        "cash generated from operations", "operating activities"
    ])

    filled = _count_filled(data)
    data.extraction_confidence = min(filled / 8, 1.0)

    # LLM fallback if < 3 fields extracted
    if filled < 3:
        notes.append("Regex yielded < 3 fields — using LLM extraction.")
        llm_result = _llm_extract("Annual Report", text, [
            {"field": "revenue_cr",
                "description": "Total revenue/income from operations (₹ Cr)"},
            {"field": "pat_cr",
                "description": "Profit after tax (₹ Cr)"},
            {"field": "total_assets_cr",
                "description": "Total assets (₹ Cr)"},
            {"field": "net_worth_cr",
                "description": "Net worth / shareholders equity (₹ Cr)"},
            {"field": "total_debt_cr",
                "description": "Total borrowings (₹ Cr)"},
            {"field": "ebitda_cr",           "description": "EBITDA (₹ Cr)"},
            {"field": "interest_expense_cr",
                "description": "Finance costs / interest expense (₹ Cr)"},
            {"field": "fy_year",
                "description": "Financial year (e.g. FY24)"},
        ])
        for field, value in llm_result.items():
            if value is not None and hasattr(data, field):
                try:
                    setattr(data, field, value)
                except Exception:
                    pass
        data.extraction_confidence = min(_count_filled(data) / 8, 1.0)

    data.extraction_notes = notes
    return data


# ─── ALM EXTRACTOR ────────────────────────────────────────────────────────────

def extract_alm(text: str, tables: list = None) -> ALMData:
    """Extract Asset-Liability Management maturity bucket data."""
    data = ALMData()
    notes = []

    # Try to find ALM table in extracted tables first
    if tables:
        for table in tables:
            raw = table.get("raw_text", "").lower()
            if any(kw in raw for kw in ["1-30", "31-60", "bucket", "maturity", "outflow"]):
                notes.append(
                    f"Found ALM table (index {table.get('table_index', '?')})")
                # Parse rows looking for asset/liability totals
                rows = table.get("rows", [])
                for row in rows:
                    row_text = " ".join(str(c) for c in row).lower()
                    if "total asset" in row_text or "assets" in row_text:
                        nums = [_parse_number(c) for c in row if _parse_number(
                            c) and _parse_number(c) > 0]
                        if len(nums) >= 2:
                            data.total_assets_cr = nums[-1]
                    if "total liabilit" in row_text or "liabilities" in row_text:
                        nums = [_parse_number(c) for c in row if _parse_number(
                            c) and _parse_number(c) > 0]
                        if len(nums) >= 2:
                            data.total_liab_cr = nums[-1]
                break

    # Regex fallback on raw text
    data.bucket_0_30d_assets_cr = _find_amount(
        text, ["1-30 days", "0-30 days", "upto 30"])
    data.bucket_1_3m_assets_cr = _find_amount(
        text, ["1-3 months", "31-90 days", "over 1 month"])
    data.bucket_3_6m_assets_cr = _find_amount(
        text, ["3-6 months", "91-180 days"])
    data.bucket_6_12m_assets_cr = _find_amount(
        text, ["6-12 months", "6 months to 1 year"])
    data.liquidity_gap_cr = _find_amount(
        text, ["liquidity gap", "net gap", "cumulative gap"])

    filled = _count_filled(data)
    data.extraction_confidence = min(filled / 6, 1.0)

    if filled < 2:
        notes.append(
            "Limited ALM data found via regex — using LLM extraction.")
        llm_result = _llm_extract("ALM", text, [
            {"field": "bucket_0_30d_assets_cr",
                "description": "Assets maturing in 0-30 days (₹ Cr)"},
            {"field": "bucket_0_30d_liab_cr",
                "description": "Liabilities maturing in 0-30 days (₹ Cr)"},
            {"field": "bucket_1_3m_assets_cr",
                "description": "Assets maturing in 1-3 months (₹ Cr)"},
            {"field": "bucket_1_3m_liab_cr",
                "description": "Liabilities maturing in 1-3 months (₹ Cr)"},
            {"field": "bucket_3_6m_assets_cr",
                "description": "Assets maturing in 3-6 months (₹ Cr)"},
            {"field": "total_assets_cr",
                "description": "Total assets in ALM statement (₹ Cr)"},
            {"field": "total_liab_cr",
                "description": "Total liabilities in ALM statement (₹ Cr)"},
            {"field": "liquidity_gap_cr",
                "description": "Net liquidity gap (₹ Cr)"},
        ])
        for field, value in llm_result.items():
            if value is not None and hasattr(data, field):
                try:
                    setattr(data, field, value)
                except Exception:
                    pass
        data.extraction_confidence = min(_count_filled(data) / 6, 1.0)

    # Derive liquidity gap if not found
    if data.liquidity_gap_cr is None and data.total_assets_cr and data.total_liab_cr:
        data.liquidity_gap_cr = round(
            data.total_assets_cr - data.total_liab_cr, 2)
        notes.append(
            "Liquidity gap derived from total assets - total liabilities.")

    data.extraction_notes = notes
    return data


# ─── SHAREHOLDING EXTRACTOR ───────────────────────────────────────────────────

def extract_shareholding(text: str, tables: list = None) -> ShareholdingData:
    """Extract shareholding pattern data."""
    data = ShareholdingData()
    notes = []

    # Promoter holding
    promoter_match = re.search(
        r'promoter(?:s)?(?:\s+(?:group|holding))?[^\d]{0,40}([\d.]+)\s*%?', text, re.I
    )
    if promoter_match:
        data.promoter_holding_pct = float(promoter_match.group(1))

    # Public holding
    public_match = re.search(
        r'public(?:\s+(?:shareholding|holding))?[^\d]{0,40}([\d.]+)\s*%?', text, re.I
    )
    if public_match:
        data.public_holding_pct = float(public_match.group(1))

    # FII/FPI
    fii_match = re.search(
        r'(?:fii|fpi|foreign\s+(?:portfolio|institutional))[^\d]{0,50}([\d.]+)\s*%?', text, re.I
    )
    if fii_match:
        data.fii_fpi_holding_pct = float(fii_match.group(1))

    # Pledged shares
    pledge_match = re.search(
        r'pledge[ds]?(?:\s+shares?)?[^\d]{0,50}([\d.]+)\s*%?', text, re.I
    )
    if pledge_match:
        data.pledged_shares_pct = float(pledge_match.group(1))

    # Mutual funds
    mf_match = re.search(
        r'mutual\s+fund[s]?[^\d]{0,50}([\d.]+)\s*%?', text, re.I
    )
    if mf_match:
        data.mutual_fund_holding_pct = float(mf_match.group(1))

    # As of date
    date_match = re.search(
        r'as\s+(?:on|of|at)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+\s+\d{4})', text, re.I
    )
    if date_match:
        data.as_of_date = date_match.group(1)

    # Derive public if not found but promoter is
    if data.public_holding_pct is None and data.promoter_holding_pct is not None:
        data.public_holding_pct = round(100 - data.promoter_holding_pct, 2)
        notes.append("Public holding derived as 100% - promoter holding.")

    filled = _count_filled(data)
    data.extraction_confidence = min(filled / 5, 1.0)

    if filled < 2:
        notes.append("Limited shareholding data — using LLM extraction.")
        llm_result = _llm_extract("Shareholding Pattern", text, [
            {"field": "promoter_holding_pct",
                "description": "Promoter + promoter group holding (%)"},
            {"field": "public_holding_pct",
                "description": "Public / non-promoter holding (%)"},
            {"field": "fii_fpi_holding_pct",
                "description": "FII / FPI holding (%)"},
            {"field": "dii_holding_pct",
                "description": "DII / mutual fund holding (%)"},
            {"field": "pledged_shares_pct",
                "description": "% of promoter shares pledged"},
            {"field": "as_of_date",
                "description": "Date of shareholding data"},
        ])
        for field, value in llm_result.items():
            if value is not None and hasattr(data, field):
                try:
                    setattr(data, field, value)
                except Exception:
                    pass
        data.extraction_confidence = min(_count_filled(data) / 5, 1.0)

    data.extraction_notes = notes
    return data


# ─── BORROWING PROFILE EXTRACTOR ──────────────────────────────────────────────

def extract_borrowing_profile(text: str, tables: list = None) -> BorrowingProfileData:
    """Extract borrowing profile and debt structure data."""
    data = BorrowingProfileData()
    notes = []

    # Total borrowings
    data.total_borrowings_cr = _find_amount(text, [
        "total borrowings", "total debt", "borrowings outstanding",
        "total financial liabilities", "total indebtedness"
    ])

    # Secured
    data.secured_borrowings_cr = _find_amount(text, [
        "secured borrowings", "secured loans", "secured debt"
    ])

    # Unsecured
    data.unsecured_borrowings_cr = _find_amount(text, [
        "unsecured borrowings", "unsecured loans", "unsecured debt"
    ])

    # NCDs
    data.ncd_outstanding_cr = _find_amount(text, [
        "non-convertible debentures", "ncd", "debentures outstanding",
        "listed ncds", "privately placed ncds"
    ])

    # Bank loans
    data.bank_loans_cr = _find_amount(text, [
        "bank loans", "term loans from banks", "bank borrowings",
        "loans from banks"
    ])

    # Credit rating
    rating_match = re.search(
        r'(?:rated|rating|credit\s+rating)[^\w]{0,30}([A-Z]{1,3}[+\-]?\d?(?:\s*(?:stable|positive|negative|watch))?)',
        text, re.I
    )
    if rating_match:
        data.credit_rating = rating_match.group(1).strip()

    # Rating agency
    for agency in ["CRISIL", "ICRA", "CARE", "India Ratings", "Brickwork", "ACUITE"]:
        if agency.lower() in text.lower():
            data.rating_agency = agency
            break

    # Number of lenders
    lender_match = re.search(r'(\d+)\s*(?:\+)?\s*lenders?', text, re.I)
    if lender_match:
        data.number_of_lenders = int(lender_match.group(1))

    # Weighted avg cost
    cost_match = re.search(
        r'(?:weighted\s+average\s+cost|average\s+cost\s+of\s+(?:funds|borrowing))[^\d]{0,30}([\d.]+)\s*%?',
        text, re.I
    )
    if cost_match:
        data.weighted_avg_cost_pct = float(cost_match.group(1))

    filled = _count_filled(data)
    data.extraction_confidence = min(filled / 6, 1.0)

    if filled < 3:
        notes.append("Limited borrowing data — using LLM extraction.")
        llm_result = _llm_extract("Borrowing Profile", text, [
            {"field": "total_borrowings_cr",
                "description": "Total borrowings outstanding (₹ Cr)"},
            {"field": "secured_borrowings_cr",
                "description": "Secured borrowings (₹ Cr)"},
            {"field": "unsecured_borrowings_cr",
                "description": "Unsecured borrowings (₹ Cr)"},
            {"field": "ncd_outstanding_cr",
                "description": "NCDs outstanding (₹ Cr)"},
            {"field": "bank_loans_cr",
                "description": "Bank term loans (₹ Cr)"},
            {"field": "credit_rating",
                "description": "Latest credit rating (e.g. AA-, A+)"},
            {"field": "number_of_lenders",
                "description": "Total number of active lenders"},
            {"field": "weighted_avg_cost_pct",
                "description": "Weighted average cost of funds (%)"},
        ])
        for field, value in llm_result.items():
            if value is not None and hasattr(data, field):
                try:
                    setattr(data, field, value)
                except Exception:
                    pass
        data.extraction_confidence = min(_count_filled(data) / 6, 1.0)

    data.extraction_notes = notes
    return data


# ─── PORTFOLIO PERFORMANCE EXTRACTOR ─────────────────────────────────────────

def extract_portfolio_performance(text: str, tables: list = None) -> PortfolioPerformanceData:
    """Extract AUM, NPA, collection efficiency, and other portfolio metrics."""
    data = PortfolioPerformanceData()
    notes = []

    # AUM
    data.aum_cr = _find_amount(text, [
        "assets under management", "aum", "loan book", "total aum",
        "portfolio size", "gross loan book"
    ])

    # Disbursements
    data.disbursements_cr = _find_amount(text, [
        "disbursements", "disbursed", "total disbursement",
        "loans disbursed", "amount disbursed"
    ])

    # GNPA
    gnpa_match = re.search(
        r'(?:gnpa|gross\s+npa)[^\d]{0,30}([\d.]+)\s*%?', text, re.I
    )
    if gnpa_match:
        data.gnpa_pct = float(gnpa_match.group(1))

    # NNPA
    nnpa_match = re.search(
        r'(?:nnpa|net\s+npa)[^\d]{0,30}([\d.]+)\s*%?', text, re.I
    )
    if nnpa_match:
        data.nnpa_pct = float(nnpa_match.group(1))

    # Collection efficiency
    ce_match = re.search(
        r'collection\s+efficiency[^\d]{0,30}([\d.]+)\s*%?', text, re.I
    )
    if ce_match:
        data.collection_efficiency_pct = float(ce_match.group(1))

    # PAR 30
    par30_match = re.search(
        r'par\s*[-–]?\s*30[^\d]{0,30}([\d.]+)\s*%?', text, re.I
    )
    if par30_match:
        data.par_30_pct = float(par30_match.group(1))

    # NIM
    nim_match = re.search(
        r'(?:nim|net\s+interest\s+margin)[^\d]{0,30}([\d.]+)\s*%?', text, re.I
    )
    if nim_match:
        data.nim_pct = float(nim_match.group(1))

    # Yield on portfolio
    yield_match = re.search(
        r'yield\s+on\s+(?:portfolio|advances|loans)[^\d]{0,30}([\d.]+)\s*%?', text, re.I
    )
    if yield_match:
        data.yield_on_portfolio_pct = float(yield_match.group(1))

    # Cost of funds
    cof_match = re.search(
        r'cost\s+of\s+funds[^\d]{0,30}([\d.]+)\s*%?', text, re.I
    )
    if cof_match:
        data.cost_of_funds_pct = float(cof_match.group(1))

    # ROE
    roe_match = re.search(
        r'(?:roe|return\s+on\s+equity)[^\d]{0,30}([\d.]+)\s*%?', text, re.I
    )
    if roe_match:
        data.roe_pct = float(roe_match.group(1))

    # ROA
    roa_match = re.search(
        r'(?:roa|return\s+on\s+assets)[^\d]{0,30}([\d.]+)\s*%?', text, re.I
    )
    if roa_match:
        data.roa_pct = float(roa_match.group(1))

    # CAR / CRAR
    car_match = re.search(
        r'(?:car|crar|capital\s+adequacy)[^\d]{0,30}([\d.]+)\s*%?', text, re.I
    )
    if car_match:
        data.capital_adequacy_ratio_pct = float(car_match.group(1))

    # YoY growth
    yoy_match = re.search(
        r'(?:yoy|year.on.year)\s+(?:growth|increase)[^\d]{0,30}([\d.]+)\s*%?', text, re.I
    )
    if yoy_match:
        data.disbursements_yoy_growth_pct = float(yoy_match.group(1))

    filled = _count_filled(data)
    data.extraction_confidence = min(filled / 10, 1.0)

    if filled < 3:
        notes.append("Limited portfolio data — using LLM extraction.")
        llm_result = _llm_extract("Portfolio Performance", text, [
            {"field": "aum_cr",
                "description": "Total AUM / loan book (₹ Cr)"},
            {"field": "disbursements_cr",
                "description": "Disbursements in period (₹ Cr)"},
            {"field": "gnpa_pct",                  "description": "Gross NPA %"},
            {"field": "nnpa_pct",                  "description": "Net NPA %"},
            {"field": "collection_efficiency_pct",
                "description": "Collection efficiency (%)"},
            {"field": "par_30_pct",
                "description": "Portfolio at risk > 30 days (%)"},
            {"field": "nim_pct",
                "description": "Net interest margin (%)"},
            {"field": "yield_on_portfolio_pct",
                "description": "Yield on portfolio (%)"},
            {"field": "cost_of_funds_pct",
                "description": "Cost of funds (%)"},
            {"field": "capital_adequacy_ratio_pct",
                "description": "Capital adequacy ratio / CRAR (%)"},
        ])
        for field, value in llm_result.items():
            if value is not None and hasattr(data, field):
                try:
                    setattr(data, field, value)
                except Exception:
                    pass
        data.extraction_confidence = min(_count_filled(data) / 10, 1.0)

    data.extraction_notes = notes
    return data


# ─── UNIFIED DISPATCHER ───────────────────────────────────────────────────────

def extract_by_doc_type(
    doc_type: str,
    text: str,
    tables: list = None
) -> Optional[BaseModel]:
    """
    Route to the correct extractor based on classified doc_type.
    Returns the appropriate Pydantic model or None for UNKNOWN.
    """
    dispatch = {
        "ANNUAL_REPORT":         extract_annual_report,
        "ALM":                   extract_alm,
        "SHAREHOLDING_PATTERN":  extract_shareholding,
        "BORROWING_PROFILE":     extract_borrowing_profile,
        "PORTFOLIO_PERFORMANCE": extract_portfolio_performance,
    }
    fn = dispatch.get(doc_type)
    if fn is None:
        return None
    return fn(text, tables)


def enrich_qualitative_inputs(extractions: dict, base_inputs):
    """Merge extracted doc data into QualitativeInputs."""
    from src.schemas import QualitativeInputs

    updated = base_inputs.model_copy()
    notes = list(base_inputs.auto_filled_fields or [])

    for fname, data in extractions.items():
        if data is None:
            continue

        if isinstance(data, AnnualReportData):
            if data.total_debt_cr and data.net_worth_cr and data.net_worth_cr > 0:
                de = round(data.total_debt_cr / data.net_worth_cr, 2)
                if updated.debt_equity_ratio == 1.5:
                    updated.debt_equity_ratio = de
                    notes.append(
                        f"D/E ratio auto-filled from Annual Report: {de:.2f}x")
            if data.net_worth_cr and updated.net_worth_inr == 0:
                updated.net_worth_inr = data.net_worth_cr * 1e7
                notes.append(
                    f"Net worth auto-filled from Annual Report: ₹{data.net_worth_cr} Cr")

        elif isinstance(data, BorrowingProfileData):
            if data.debt_equity_ratio and updated.debt_equity_ratio == 1.5:
                updated.debt_equity_ratio = data.debt_equity_ratio
                notes.append(
                    f"D/E ratio from Borrowing Profile: {data.debt_equity_ratio:.2f}x")

        elif isinstance(data, ShareholdingData):
            if data.pledged_shares_pct and data.pledged_shares_pct > 50:
                updated.promoter_score = max(1, updated.promoter_score - 2)
                notes.append(
                    f"Promoter score reduced: {data.pledged_shares_pct:.0f}% shares pledged")

    updated.auto_filled_fields = notes
    return updated
