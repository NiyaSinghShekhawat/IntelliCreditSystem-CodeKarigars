# src/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# ─── ENUMS ───────────────────────────────────────────────────────────────────


class RiskCategory(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class DecisionType(str, Enum):
    APPROVE = "Approve"
    CONDITIONAL = "Conditional Approval"
    REJECT = "Reject"


class DocumentType(str, Enum):
    GST_RETURN = "GST_RETURN"
    ITR = "ITR"
    BANK_STATEMENT = "BANK_STATEMENT"
    ANNUAL_REPORT = "ANNUAL_REPORT"
    FINANCIAL_STATEMENT = "FINANCIAL_STATEMENT"
    LEGAL_NOTICE = "LEGAL_NOTICE"
    OTHER = "OTHER"


# ─── DOCUMENT PARSING ────────────────────────────────────────────────────────

class ExtractedTable(BaseModel):
    table_index: int
    headers: List[str] = []
    rows: List[List[str]] = []
    raw_text: str = ""


class ParsedDocument(BaseModel):
    source_file: str
    document_type: DocumentType = DocumentType.OTHER
    raw_text: str = ""
    markdown: str = ""
    tables: List[ExtractedTable] = []
    page_count: int = 0
    extracted_at: datetime = Field(default_factory=datetime.now)
    error: Optional[str] = None


# ─── GST DATA ────────────────────────────────────────────────────────────────

class GSTData(BaseModel):
    gstin: Optional[str] = None
    company_name: Optional[str] = None
    tax_period: Optional[str] = None
    turnover: float = 0.0
    igst: float = 0.0
    cgst: float = 0.0
    sgst: float = 0.0
    total_tax: float = 0.0
    itc_claimed: float = 0.0
    filing_date: Optional[str] = None
    filing_regular: bool = True


class GSTReconciliationResult(BaseModel):
    total_mismatches: int = 0
    risk_flag: bool = False
    variance_pct: float = 0.0
    circular_trading_flag: bool = False
    mismatches: List[Dict[str, Any]] = []
    summary: str = ""


# ─── BANK STATEMENT DATA ─────────────────────────────────────────────────────

class BankStatementData(BaseModel):
    account_number: Optional[str] = None
    account_holder: Optional[str] = None
    bank_name: Optional[str] = None
    period: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    opening_balance: float = 0.0
    closing_balance: float = 0.0
    total_credits: float = 0.0
    total_debits: float = 0.0
    monthly_balances: List[float] = []
    monthly_credits: List[float] = []
    monthly_debits: List[float] = []
    emi_bounce_count: int = 0
    large_unusual_transactions: List[Dict[str, Any]] = []
    average_monthly_balance: float = 0.0


# ─── ITR DATA ────────────────────────────────────────────────────────────────

class ITRData(BaseModel):
    pan: Optional[str] = None
    assessment_year: Optional[str] = None
    gross_income: float = 0.0
    net_income: float = 0.0
    tax_paid: float = 0.0
    tds: float = 0.0
    depreciation: float = 0.0
    net_worth: float = 0.0
    total_assets: float = 0.0
    total_liabilities: float = 0.0
    long_term_debt: float = 0.0
    short_term_debt: float = 0.0
    revenue: float = 0.0
    ebitda: float = 0.0
    interest_expense: float = 0.0


# ─── DERIVED FINANCIALS ──────────────────────────────────────────────────────

class DerivedFinancials(BaseModel):
    debt_equity_ratio: Optional[float] = None
    net_worth_inr: Optional[float] = None
    total_debt_inr: Optional[float] = None
    current_ratio: Optional[float] = None
    dscr: Optional[float] = None
    net_profit_margin: Optional[float] = None
    avg_monthly_balance_inr: Optional[float] = None
    monthly_credit_avg_inr: Optional[float] = None
    credit_utilisation_pct: Optional[float] = None
    gst_turnover_inr: Optional[float] = None
    itc_claimed_inr: Optional[float] = None
    effective_tax_rate_pct: Optional[float] = None
    data_completeness_pct: float = 0.0
    derivation_notes: List[str] = []
    auto_filled_fields: List[str] = []


# ─── RESEARCH DATA ───────────────────────────────────────────────────────────

class NewsItem(BaseModel):
    title: str
    url: str = ""
    date: str = ""
    source: str = ""
    is_negative: bool = False
    keywords_found: List[str] = []


class ResearchFindings(BaseModel):
    company_name: str
    negative_news: List[NewsItem] = []
    positive_news: List[NewsItem] = []
    litigation_found: bool = False
    litigation_details: List[str] = []
    mca_charges: List[Dict[str, Any]] = []
    rbi_sebi_actions: List[str] = []
    news_risk_score: float = 0.0
    research_summary: str = ""


# ─── FIVE Cs ─────────────────────────────────────────────────────────────────

class CScore(BaseModel):
    score: float
    factors: List[str] = []
    details: Dict[str, Any] = {}
    summary: str = ""


class FiveCsResult(BaseModel):
    character: CScore
    capacity: CScore
    capital: CScore
    collateral: CScore
    conditions: CScore
    overall_score: float = 0.0


# ─── RISK SCORING ────────────────────────────────────────────────────────────

class SHAPFactor(BaseModel):
    feature_name: str
    shap_value: float
    direction: str
    display_name: str = ""


class RiskPrediction(BaseModel):
    risk_score: float
    risk_category: RiskCategory
    decision: DecisionType
    loan_limit_inr: float
    interest_rate: float
    top_shap_factors: List[SHAPFactor] = []
    explanation: str = ""
    decisive_factor: str = ""
    early_warning_signals: List[str] = []


# ─── QUALITATIVE INPUTS ──────────────────────────────────────────────────────

class QualitativeInputs(BaseModel):
    # OFFICER — must be entered manually
    site_visit_notes: str = ""
    management_interview_notes: str = ""
    promoter_score: int = 5
    sector_risk_score: int = 5
    collateral_coverage: float = 0.6

    # AUTO — pre-filled from documents, officer can override
    debt_equity_ratio: float = 1.5
    net_worth_inr: float = 0.0

    # Tracks which fields were auto-filled (for UI lock icon)
    # Single definition — Optional list, defaults to empty list
    auto_filled_fields: Optional[List[str]] = None


class QualitativeAdjustment(BaseModel):
    base_score: float
    adjusted_score: float
    adjustment_delta: float
    adjustment_reason: str


# ─── DOCUMENT CLASSIFICATION ─────────────────────────────────────────────────

class DocumentClassification(BaseModel):
    doc_type: str
    doc_type_label: str
    confidence: float
    reasoning: str
    key_signals: List[str]
    user_confirmed: bool = False
    user_override: Optional[str] = None


# ─── FINAL CAM OUTPUT ────────────────────────────────────────────────────────

class CreditAppraisalResult(BaseModel):
    company_name: str
    cin: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.now)

    # Document data
    gst_data: Optional[GSTData] = None
    bank_data: Optional[BankStatementData] = None
    itr_data: Optional[ITRData] = None
    gst_reconciliation: Optional[GSTReconciliationResult] = None

    # Auto-derived ratios
    derived_financials: Optional[DerivedFinancials] = None

    # Research
    research: Optional[ResearchFindings] = None

    # Analysis
    five_cs: Optional[FiveCsResult] = None
    qualitative_inputs: Optional[QualitativeInputs] = None
    qualitative_adjustment: Optional[QualitativeAdjustment] = None

    # v2.0 — HITL extractions, SWOT, triangulated research
    hitl_extractions: Optional[Dict[str, Any]] = None
    swot: Optional[Any] = None
    research_dict: Optional[Dict[str, Any]] = None

    # Final decision
    risk_prediction: Optional[RiskPrediction] = None

    # LLM reasoning
    reasoning_chain: str = ""

    # Report paths
    pdf_report_path: Optional[str] = None
    docx_report_path: Optional[str] = None

    loan_type:           Optional[str] = None
    loan_amount_cr:      Optional[float] = None
    loan_tenure_months:  Optional[int] = None
    sector:              Optional[str] = None
