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
    """A single table extracted from a document"""
    table_index: int
    headers: List[str] = []
    rows: List[List[str]] = []
    raw_text: str = ""


class ParsedDocument(BaseModel):
    """Output of the Docling parser for any document"""
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
    """Extracted GST return data"""
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
    """Result of GSTR-2A vs GSTR-3B reconciliation"""
    total_mismatches: int = 0
    risk_flag: bool = False
    variance_pct: float = 0.0
    circular_trading_flag: bool = False
    mismatches: List[Dict[str, Any]] = []
    summary: str = ""

# ─── BANK STATEMENT DATA ─────────────────────────────────────────────────────


class BankStatementData(BaseModel):
    """Extracted bank statement data"""
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    period: Optional[str] = None
    opening_balance: float = 0.0
    closing_balance: float = 0.0
    total_credits: float = 0.0
    total_debits: float = 0.0
    monthly_balances: List[float] = []
    monthly_credits: List[float] = []
    emi_bounce_count: int = 0
    large_unusual_transactions: List[Dict[str, Any]] = []
    average_monthly_balance: float = 0.0

# ─── ITR DATA ────────────────────────────────────────────────────────────────


class ITRData(BaseModel):
    """Extracted ITR data"""
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

# ─── RESEARCH DATA ───────────────────────────────────────────────────────────


class NewsItem(BaseModel):
    """A single news article"""
    title: str
    url: str = ""
    date: str = ""
    source: str = ""
    is_negative: bool = False
    keywords_found: List[str] = []


class ResearchFindings(BaseModel):
    """Output of the research agent"""
    company_name: str
    negative_news: List[NewsItem] = []
    positive_news: List[NewsItem] = []
    litigation_found: bool = False
    litigation_details: List[str] = []
    mca_charges: List[Dict[str, Any]] = []
    rbi_sebi_actions: List[str] = []
    news_risk_score: float = 0.0   # 0-10
    research_summary: str = ""

# ─── FIVE Cs ─────────────────────────────────────────────────────────────────


class CScore(BaseModel):
    """Score for a single C"""
    score: float        # 0-10
    factors: List[str] = []
    details: Dict[str, Any] = {}
    summary: str = ""


class FiveCsResult(BaseModel):
    """Complete Five Cs assessment"""
    character: CScore
    capacity: CScore
    capital: CScore
    collateral: CScore
    conditions: CScore
    overall_score: float = 0.0   # Weighted average

# ─── RISK SCORING ────────────────────────────────────────────────────────────


class SHAPFactor(BaseModel):
    """A single SHAP explanation factor"""
    feature_name: str
    shap_value: float
    direction: str   # "increases risk" or "decreases risk"
    display_name: str = ""


class RiskPrediction(BaseModel):
    """Output of the risk scoring engine"""
    risk_score: float           # 0.0 to 1.0
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
    """Officer's primary due diligence inputs"""
    site_visit_notes: str = ""
    management_interview_notes: str = ""
    debt_equity_ratio: float = 1.5
    collateral_coverage: float = 0.6
    net_worth_inr: float = 0.0
    sector_risk_score: int = 5      # 1-10, officer's assessment
    promoter_score: int = 5         # 1-10, integrity assessment


class QualitativeAdjustment(BaseModel):
    """How officer inputs adjusted the base risk score"""
    base_score: float
    adjusted_score: float
    adjustment_delta: float
    adjustment_reason: str

# ─── FINAL CAM OUTPUT ────────────────────────────────────────────────────────


class CreditAppraisalResult(BaseModel):
    """The complete output of the entire pipeline"""
    company_name: str
    cin: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.now)

    # Document data
    gst_data: Optional[GSTData] = None
    bank_data: Optional[BankStatementData] = None
    itr_data: Optional[ITRData] = None
    gst_reconciliation: Optional[GSTReconciliationResult] = None

    # Research
    research: Optional[ResearchFindings] = None

    # Analysis
    five_cs: Optional[FiveCsResult] = None
    qualitative_inputs: Optional[QualitativeInputs] = None
    qualitative_adjustment: Optional[QualitativeAdjustment] = None

    # Final decision
    risk_prediction: Optional[RiskPrediction] = None

    # LLM reasoning
    reasoning_chain: str = ""

    # Report paths
    pdf_report_path: Optional[str] = None
    docx_report_path: Optional[str] = None
