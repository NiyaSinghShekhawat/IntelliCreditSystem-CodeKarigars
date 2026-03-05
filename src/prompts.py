import sys
from pathlib import Path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


# ─── MAIN CREDIT ANALYSIS PROMPT ─────────────────────────────────────────────

CREDIT_ANALYSIS_PROMPT = """You are a Senior Credit Manager at an Indian bank with 20 years of experience.
You are analyzing a loan application for an Indian company.

COMPANY FINANCIAL DATA:
{financial_data}

EXTERNAL RESEARCH:
{research_data}

OFFICER OBSERVATIONS:
{qualitative_data}

Analyze this data and respond in EXACTLY this format — do not add anything extra:

DECISION: [Approve / Reject / Conditional Approval]
LIMIT: Rs.[amount in lakhs]
RATE: [x.x]% per annum

REASONING CHAIN:
1. GST Analysis      -> [your finding] -> [impact: increases/decreases risk]
2. Bank Statements   -> [your finding] -> [impact: increases/decreases risk]
3. External Research -> [your finding] -> [impact: increases/decreases risk]
4. Primary Inputs    -> [officer observation] -> [impact on final score]

DECISIVE FACTOR: [single biggest reason for your decision in one sentence]

EARLY WARNING SIGNALS:
- [signal 1 to monitor going forward]
- [signal 2 to monitor going forward]
- [signal 3 to monitor going forward]

LOAN CONDITIONS:
- [condition 1 if approving, else write NA]
- [condition 2 if approving, else write NA]

Remember:
- All amounts in Indian Rupees
- Be specific about Indian financial context (GSTR, ITC, CIBIL, NPA)
- Flag any circular trading or ITC manipulation explicitly
- Consider sector-specific risks for Indian market
"""


# ─── FIVE Cs PROMPT ──────────────────────────────────────────────────────────

FIVE_CS_PROMPT = """You are a Senior Credit Manager at an Indian bank.
Evaluate the Five Cs of Credit for this company based on the data below.

COMPANY DATA:
{company_data}

Rate each C on a scale of 0-10 and provide specific reasons.
Respond in EXACTLY this format:

CHARACTER: [score]/10
Reasons:
- [reason 1 based on GST filing regularity, litigation, news]
- [reason 2]

CAPACITY: [score]/10
Reasons:
- [reason 1 based on cash flow, DSCR, revenue trend]
- [reason 2]

CAPITAL: [score]/10
Reasons:
- [reason 1 based on net worth, debt-equity ratio]
- [reason 2]

COLLATERAL: [score]/10
Reasons:
- [reason 1 based on collateral coverage ratio]
- [reason 2]

CONDITIONS: [score]/10
Reasons:
- [reason 1 based on sector outlook, market conditions]
- [reason 2]

OVERALL ASSESSMENT: [brief paragraph summarizing all five Cs]
"""


# ─── RESEARCH SUMMARY PROMPT ─────────────────────────────────────────────────

RESEARCH_SUMMARY_PROMPT = """You are a credit risk analyst at an Indian bank.
Summarize the following research findings about a company applying for a loan.

COMPANY NAME: {company_name}

NEWS ARTICLES FOUND:
{news_data}

MCA FILINGS:
{mca_data}

LITIGATION RECORDS:
{litigation_data}

Write a concise 3-paragraph research summary covering:
1. Media reputation and any negative news
2. Regulatory and legal standing
3. Overall external risk assessment

Be specific. Mention company names, dates, and amounts where available.
Flag any RBI/SEBI enforcement actions explicitly.
"""


# ─── EARLY WARNING SIGNALS PROMPT ────────────────────────────────────────────

EARLY_WARNING_PROMPT = """You are a credit monitoring officer at an Indian bank.
Based on the following borrower profile, identify early warning signals to monitor.

BORROWER DATA:
{borrower_data}

List exactly 5 early warning signals that the bank should monitor after loan disbursement.
Format each as:
SIGNAL [n]: [What to monitor] | [Trigger threshold] | [Action if triggered]

Example:
SIGNAL 1: GST filing regularity | If filing gaps exceed 2 months | Put account under watch
"""


# ─── QUALITATIVE ADJUSTMENT PROMPT ───────────────────────────────────────────

QUALITATIVE_ADJUSTMENT_PROMPT = """You are a credit officer reviewing site visit notes.
A loan applicant has a base risk score of {base_score} (0=lowest risk, 1=highest risk).

SITE VISIT NOTES:
{site_visit_notes}

MANAGEMENT INTERVIEW NOTES:
{management_notes}

Based on these observations, should the risk score be adjusted?
Respond in EXACTLY this format:

ADJUSTMENT: [increase / decrease / no change]
DELTA: [0.00 to 0.25]
REASON: [one sentence explaining the adjustment]
NEW_SCORE: [adjusted score between 0.0 and 1.0]
"""


# ─── CAM EXECUTIVE SUMMARY PROMPT ────────────────────────────────────────────

CAM_SUMMARY_PROMPT = """You are writing the executive summary section of a
Credit Appraisal Memorandum (CAM) for an Indian bank's credit committee.

COMPANY: {company_name}
DECISION: {decision}
LOAN LIMIT: Rs. {loan_limit}
INTEREST RATE: {interest_rate}%
RISK SCORE: {risk_score}/10
RISK CATEGORY: {risk_category}

KEY FINDINGS:
{key_findings}

Write a professional 2-paragraph executive summary suitable for a bank's
credit committee. Use formal Indian banking language.
Mention specific figures. Do not use bullet points.
"""


# ─── HELPER: Format financial data for prompts ───────────────────────────────

def format_financial_data(gst_data=None, bank_data=None, itr_data=None,
                          reconciliation=None) -> str:
    """Format extracted financial data into prompt-ready text"""
    lines = []

    if gst_data:
        lines.append("GST RETURN DATA:")
        lines.append(f"  GSTIN: {gst_data.gstin or 'Not found'}")
        lines.append(f"  Company: {gst_data.company_name or 'Not found'}")
        lines.append(f"  Turnover: Rs. {gst_data.turnover:,.0f}")
        lines.append(f"  Total Tax Paid: Rs. {gst_data.total_tax:,.0f}")
        lines.append(f"  ITC Claimed: Rs. {gst_data.itc_claimed:,.0f}")
        lines.append(f"  Filing Regular: {gst_data.filing_regular}")

    if reconciliation:
        lines.append("\nGST RECONCILIATION (2A vs 3B):")
        lines.append(f"  Mismatches Found: {reconciliation.total_mismatches}")
        lines.append(f"  Risk Flag: {reconciliation.risk_flag}")
        lines.append(f"  Max Variance: {reconciliation.variance_pct}%")
        lines.append(
            f"  Circular Trading: {reconciliation.circular_trading_flag}")
        if reconciliation.summary:
            lines.append(f"  Summary: {reconciliation.summary}")

    if bank_data:
        lines.append("\nBANK STATEMENT DATA:")
        lines.append(f"  Bank: {bank_data.bank_name or 'Not specified'}")
        lines.append(f"  Total Credits: Rs. {bank_data.total_credits:,.0f}")
        lines.append(f"  Total Debits: Rs. {bank_data.total_debits:,.0f}")
        lines.append(
            f"  Avg Monthly Balance: Rs. {bank_data.average_monthly_balance:,.0f}")
        lines.append(f"  EMI Bounces: {bank_data.emi_bounce_count}")

    if itr_data:
        lines.append("\nITR DATA:")
        lines.append(f"  PAN: {itr_data.pan or 'Not found'}")
        lines.append(
            f"  Assessment Year: {itr_data.assessment_year or 'Not found'}")
        lines.append(f"  Gross Income: Rs. {itr_data.gross_income:,.0f}")
        lines.append(f"  Net Income: Rs. {itr_data.net_income:,.0f}")
        lines.append(f"  Net Worth: Rs. {itr_data.net_worth:,.0f}")

    return "\n".join(lines) if lines else "No financial data available"


def format_research_data(research=None) -> str:
    """Format research findings into prompt-ready text"""
    if not research:
        return "No external research data available"

    lines = []
    lines.append(f"Company: {research.company_name}")
    lines.append(f"News Risk Score: {research.news_risk_score}/10")
    lines.append(f"Negative News Items: {len(research.negative_news)}")
    lines.append(f"Litigation Found: {research.litigation_found}")
    lines.append(f"MCA Charges: {len(research.mca_charges)}")
    lines.append(f"RBI/SEBI Actions: {len(research.rbi_sebi_actions)}")

    if research.negative_news:
        lines.append("\nNEGATIVE NEWS:")
        for item in research.negative_news[:3]:
            lines.append(f"  - {item.title} ({item.date})")

    if research.litigation_details:
        lines.append("\nLITIGATION:")
        for detail in research.litigation_details[:3]:
            lines.append(f"  - {detail}")

    if research.research_summary:
        lines.append(f"\nSUMMARY: {research.research_summary}")

    return "\n".join(lines)


def format_qualitative_data(qualitative=None) -> str:
    """Format officer inputs into prompt-ready text"""
    if not qualitative:
        return "No officer observations provided"

    lines = []
    if qualitative.site_visit_notes:
        lines.append(f"Site Visit Notes: {qualitative.site_visit_notes}")
    if qualitative.management_interview_notes:
        lines.append(
            f"Management Interview: {qualitative.management_interview_notes}")
    lines.append(f"Debt/Equity Ratio: {qualitative.debt_equity_ratio}")
    lines.append(
        f"Collateral Coverage: {qualitative.collateral_coverage * 100:.0f}%")
    lines.append(f"Sector Risk Score: {qualitative.sector_risk_score}/10")
    lines.append(f"Promoter Score: {qualitative.promoter_score}/10")

    return "\n".join(lines)


# ─── QUICK TEST ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Prompts loaded successfully!")
    print(f"\nAvailable prompts:")
    print("  - CREDIT_ANALYSIS_PROMPT")
    print("  - FIVE_CS_PROMPT")
    print("  - RESEARCH_SUMMARY_PROMPT")
    print("  - EARLY_WARNING_PROMPT")
    print("  - QUALITATIVE_ADJUSTMENT_PROMPT")
    print("  - CAM_SUMMARY_PROMPT")

    print("\nSample formatted financial data:")
    from src.schemas import GSTData
    sample_gst = GSTData(
        gstin="27AABCU9603R1ZX",
        company_name="ABC Private Limited",
        turnover=4500000,
        total_tax=500000,
        itc_claimed=80000
    )
    print(format_financial_data(gst_data=sample_gst))
