from config import (
    LLM_BACKEND, OLLAMA_MODEL, OLLAMA_BASE_URL,
    GROQ_API_KEY, GROQ_MODEL, LLM_TEMPERATURE,
    LLM_MAX_TOKENS, RISK_THRESHOLDS, AUTO_REJECT_THRESHOLD,
    BASE_INTEREST_RATE, MAX_RISK_SPREAD, MAX_LOAN_LIMIT_INR,
    MAX_QUALITATIVE_ADJUSTMENT, SITE_VISIT_RISK_KEYWORDS,
    SITE_VISIT_POSITIVE_KEYWORDS
)
from src.rag import RAGEngine
from src.prompts import (
    CREDIT_ANALYSIS_PROMPT, FIVE_CS_PROMPT,
    EARLY_WARNING_PROMPT, QUALITATIVE_ADJUSTMENT_PROMPT,
    CAM_SUMMARY_PROMPT, format_financial_data,
    format_research_data, format_qualitative_data
)
from src.schemas import (
    CreditAppraisalResult, RiskPrediction, QualitativeInputs,
    RiskCategory, DecisionType, SHAPFactor
)
from typing import Optional
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


class CreditAgent:
    """
    The AI brain of Intelli-Credit.
    Connects LLM (Ollama or Groq) with RAG, prompts,
    and structured financial data to produce credit decisions.
    """

    def __init__(self):
        self.rag = RAGEngine()
        self.llm = self._init_llm()
        print(f"Credit Agent ready. LLM backend: {LLM_BACKEND}")

    # ─── LLM INITIALIZATION ──────────────────────────────────────────────────

    def _init_llm(self):
        """Initialize LLM based on config — Ollama or Groq"""
        if LLM_BACKEND == "groq":
            return self._init_groq()
        else:
            return self._init_ollama()

    def _init_ollama(self):
        """Initialize local Ollama LLM"""
        try:
            from langchain_ollama import OllamaLLM
            llm = OllamaLLM(
                model=OLLAMA_MODEL,
                base_url=OLLAMA_BASE_URL,
                temperature=LLM_TEMPERATURE,
            )
            print(f"Ollama LLM ready: {OLLAMA_MODEL}")
            return llm
        except Exception as e:
            print(f"Ollama failed: {e}")
            print("Falling back to Groq...")
            return self._init_groq()

    def _init_groq(self):
        """Initialize Groq cloud LLM"""
        try:
            from langchain_groq import ChatGroq
            llm = ChatGroq(
                model=GROQ_MODEL,
                api_key=GROQ_API_KEY,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            )
            print(f"Groq LLM ready: {GROQ_MODEL}")
            return llm
        except Exception as e:
            print(f"Groq also failed: {e}")
            return None

    # ─── MAIN ANALYSIS ───────────────────────────────────────────────────────

    def analyze(self, result: CreditAppraisalResult) -> CreditAppraisalResult:
        """
        Main entry point. Pass in a CreditAppraisalResult with
        financial data already extracted. Returns it with LLM
        reasoning, risk prediction, and early warning signals added.
        """
        print(f"\nRunning AI analysis for: {result.company_name}")

        # Step 1: Format all data for prompts
        financial_text = format_financial_data(
            gst_data=result.gst_data,
            bank_data=result.bank_data,
            itr_data=result.itr_data,
            reconciliation=result.gst_reconciliation
        )

        research_text = format_research_data(result.research)
        qualitative_text = format_qualitative_data(result.qualitative_inputs)

        # Step 2: Get RAG context
        rag_context = self.rag.build_context(
            "credit risk assessment GST turnover bank balance ITC",
            company_name=result.company_name
        )

        # Step 3: Run main credit analysis
        print("Running credit analysis...")
        reasoning = self._run_credit_analysis(
            financial_text, research_text,
            qualitative_text, rag_context
        )
        result.reasoning_chain = reasoning

        # Step 4: Parse LLM output into structured prediction
        print("Parsing AI decision...")
        prediction = self._parse_reasoning_to_prediction(
            reasoning, result
        )

        # Step 5: Apply qualitative adjustment if officer notes exist
        if result.qualitative_inputs and result.qualitative_inputs.site_visit_notes:
            print("Applying qualitative adjustment...")
            prediction = self._apply_qualitative_adjustment(
                prediction, result.qualitative_inputs
            )

        result.risk_prediction = prediction
        print(f"Analysis complete. Decision: {prediction.decision}")
        return result

    # ─── CREDIT ANALYSIS ─────────────────────────────────────────────────────

    def _run_credit_analysis(self, financial_text: str,
                             research_text: str,
                             qualitative_text: str,
                             rag_context: str) -> str:
        """Run the main credit analysis prompt through LLM"""
        if not self.llm:
            return self._fallback_reasoning(financial_text)

        prompt = CREDIT_ANALYSIS_PROMPT.format(
            financial_data=financial_text,
            research_data=research_text,
            qualitative_data=qualitative_text
        )

        # Add RAG context if available
        if rag_context and "No relevant" not in rag_context:
            prompt += f"\n\nADDITIONAL DOCUMENT CONTEXT:\n{rag_context}"

        try:
            response = self.llm.invoke(prompt)
            # Handle both string and message responses
            if hasattr(response, 'content'):
                return response.content
            return str(response)
        except Exception as e:
            print(f"LLM error: {e}")
            return self._fallback_reasoning(financial_text)

    # ─── PARSE LLM OUTPUT ────────────────────────────────────────────────────

    def _parse_reasoning_to_prediction(
            self, reasoning: str,
            result: CreditAppraisalResult) -> RiskPrediction:
        """
        Parse the LLM's structured text output into a
        RiskPrediction object with score, decision, limit etc.
        """
        import re

        # Extract decision
        decision = DecisionType.CONDITIONAL
        if "DECISION: Approve" in reasoning or "DECISION: approve" in reasoning:
            decision = DecisionType.APPROVE
        elif "DECISION: Reject" in reasoning or "DECISION: reject" in reasoning:
            decision = DecisionType.REJECT

        # Extract loan limit
        loan_limit = 0.0
        limit_match = re.search(
            r'LIMIT:\s*Rs\.?\s*([\d,]+(?:\.\d+)?)\s*(crore|cr|lakh|lakhs|L)?',
            reasoning, re.IGNORECASE
        )
        if limit_match:
            amount_str = limit_match.group(1).replace(',', '')
            unit = ""
            try:
                unit = (limit_match.group(2) or "").lower()
            except IndexError:
                unit = ""
            amount = float(amount_str)

            if "crore" in unit or unit == "cr":
                loan_limit = amount * 10_000_000
            elif "lakh" in unit or unit == "l":
                loan_limit = amount * 100_000
            elif amount < 1000:
                loan_limit = amount * 100_000
            else:
                loan_limit = amount
        else:
            loan_limit = self._calculate_loan_limit(result)

        # Cap at maximum
        # loan_limit = min(loan_limit, MAX_LOAN_LIMIT_INR)
        # No loan for rejected cases
        if decision == DecisionType.REJECT:
            loan_limit = 0.0
        else:
            loan_limit = min(loan_limit, MAX_LOAN_LIMIT_INR)

        # Extract interest rate
        rate = BASE_INTEREST_RATE
        # rate_match = re.search(
        #     r'RATE:\s*([\d.]+)%', reasoning, re.IGNORECASE
        # )
        # if rate_match:
        #     rate = float(rate_match.group(1))
        rate = BASE_INTEREST_RATE
        if decision == DecisionType.REJECT:
            rate = 0.0
        else:
            rate_match = re.search(
                r'RATE:\s*([\d.]+)%', reasoning, re.IGNORECASE
            )
            if rate_match:
                rate = float(rate_match.group(1))

        # Extract decisive factor
        decisive_factor = ""
        df_match = re.search(
            r'DECISIVE FACTOR:\s*(.+?)(?:\n|$)', reasoning
        )
        if df_match:
            decisive_factor = df_match.group(1).strip()

        # Extract early warning signals
        warnings = []
        warning_section = re.findall(
            r'EARLY WARNING SIGNALS:\s*((?:-.+\n?)+)',
            reasoning, re.IGNORECASE
        )
        if warning_section:
            warnings = [
                w.strip().lstrip('- ')
                for w in warning_section[0].strip().split('\n')
                if w.strip()
            ]

        # Calculate risk score from decision + data
        risk_score = self._calculate_risk_score(result, decision)

        # Determine risk category
        if risk_score <= RISK_THRESHOLDS["low"]:
            risk_category = RiskCategory.LOW
        elif risk_score <= RISK_THRESHOLDS["medium"]:
            risk_category = RiskCategory.MEDIUM
        else:
            risk_category = RiskCategory.HIGH

        # Build SHAP-style factors
        shap_factors = self._build_shap_factors(result, risk_score)

        return RiskPrediction(
            risk_score=round(risk_score, 3),
            risk_category=risk_category,
            decision=decision,
            loan_limit_inr=loan_limit,
            interest_rate=rate,
            top_shap_factors=shap_factors,
            decisive_factor=decisive_factor,
            early_warning_signals=warnings[:5],
            explanation=reasoning[:500]
        )

    # ─── RISK SCORE CALCULATION ───────────────────────────────────────────────

    def _calculate_risk_score(self, result: CreditAppraisalResult,
                              decision: DecisionType) -> float:
        """
        Calculate a 0-1 risk score from extracted data.
        Higher = more risky.
        """
        score = 0.5  # Start neutral

        # GST reconciliation flags
        if result.gst_reconciliation:
            if result.gst_reconciliation.risk_flag:
                score += 0.15
            if result.gst_reconciliation.circular_trading_flag:
                score += 0.10
            variance = result.gst_reconciliation.variance_pct
            if variance > 25:
                score += 0.10
            elif variance > 10:
                score += 0.05

        # Bank statement signals
        if result.bank_data:
            bounces = result.bank_data.emi_bounce_count
            if bounces > 3:
                score += 0.10
            elif bounces > 0:
                score += 0.05

            # Low average balance relative to credits
            if result.bank_data.total_credits > 0:
                balance_ratio = (result.bank_data.average_monthly_balance /
                                 result.bank_data.total_credits)
                if balance_ratio < 0.05:
                    score += 0.05

        # Research flags
        if result.research:
            score += result.research.news_risk_score * 0.02
            if result.research.litigation_found:
                score += 0.10
            if result.research.rbi_sebi_actions:
                score += 0.15

        # Qualitative inputs
        if result.qualitative_inputs:
            de_ratio = result.qualitative_inputs.debt_equity_ratio
            if de_ratio > 3:
                score += 0.10
            elif de_ratio > 2:
                score += 0.05

            coverage = result.qualitative_inputs.collateral_coverage
            if coverage < 0.5:
                score += 0.05

        # Adjust based on LLM decision
        if decision == DecisionType.APPROVE:
            score = min(score, 0.45)
        elif decision == DecisionType.REJECT:
            score = max(score, 0.75)

        return round(min(max(score, 0.0), 1.0), 3)

    # ─── LOAN LIMIT CALCULATION ───────────────────────────────────────────────

    def _calculate_loan_limit(self,
                              result: CreditAppraisalResult) -> float:
        """Calculate loan limit from financial data"""
        base = 0.0

        if result.gst_data and result.gst_data.turnover > 0:
            base = result.gst_data.turnover * 0.20  # 20% of turnover

        if result.bank_data and result.bank_data.total_credits > 0:
            bank_based = result.bank_data.total_credits * 0.15
            base = max(base, bank_based)

        if result.itr_data and result.itr_data.net_income > 0:
            itr_based = result.itr_data.net_income * 0.30
            base = max(base, itr_based)

        return min(base, MAX_LOAN_LIMIT_INR)

    # ─── QUALITATIVE ADJUSTMENT ───────────────────────────────────────────────

    def _apply_qualitative_adjustment(
            self, prediction: RiskPrediction,
            qualitative: QualitativeInputs) -> RiskPrediction:
        """
        Adjust risk score based on officer's site visit notes.
        This is the score delta feature shown in the UI.
        """
        notes = qualitative.site_visit_notes.lower()
        adjustment = 0.0

        # Check for negative signals in notes
        risk_hits = sum(
            1 for kw in SITE_VISIT_RISK_KEYWORDS if kw in notes
        )
        positive_hits = sum(
            1 for kw in SITE_VISIT_POSITIVE_KEYWORDS if kw in notes
        )

        if risk_hits > positive_hits:
            adjustment = min(risk_hits * 0.05, MAX_QUALITATIVE_ADJUSTMENT)
        elif positive_hits > risk_hits:
            adjustment = -min(positive_hits * 0.05, MAX_QUALITATIVE_ADJUSTMENT)

        if adjustment == 0:
            return prediction

        base_score = prediction.risk_score
        new_score = round(
            min(max(base_score + adjustment, 0.0), 1.0), 3
        )

        # Update category based on new score
        if new_score <= RISK_THRESHOLDS["low"]:
            new_category = RiskCategory.LOW
        elif new_score <= RISK_THRESHOLDS["medium"]:
            new_category = RiskCategory.MEDIUM
        else:
            new_category = RiskCategory.HIGH

        # Update decision if score crosses threshold
        new_decision = prediction.decision
        if new_score >= AUTO_REJECT_THRESHOLD:
            new_decision = DecisionType.REJECT
        elif new_score <= RISK_THRESHOLDS["low"]:
            new_decision = DecisionType.APPROVE

        prediction.risk_score = new_score
        prediction.risk_category = new_category
        prediction.decision = new_decision

        print(f"Qualitative adjustment: {base_score} -> {new_score} "
              f"(delta: {adjustment:+.2f})")

        return prediction

    # ─── SHAP-STYLE FACTORS ───────────────────────────────────────────────────

    def _build_shap_factors(self, result: CreditAppraisalResult,
                            risk_score: float) -> list:
        """Build SHAP-style explanation factors"""
        factors = []

        if result.gst_reconciliation and result.gst_reconciliation.risk_flag:
            factors.append(SHAPFactor(
                feature_name="gst_mismatch",
                shap_value=0.15,
                direction="increases risk",
                display_name="GST 2A vs 3B Mismatch"
            ))

        if result.bank_data and result.bank_data.emi_bounce_count > 0:
            factors.append(SHAPFactor(
                feature_name="emi_bounces",
                shap_value=0.10,
                direction="increases risk",
                display_name=f"EMI Bounces ({result.bank_data.emi_bounce_count})"
            ))

        if result.research and result.research.litigation_found:
            factors.append(SHAPFactor(
                feature_name="litigation",
                shap_value=0.10,
                direction="increases risk",
                display_name="Active Litigation Found"
            ))

        if result.qualitative_inputs:
            de = result.qualitative_inputs.debt_equity_ratio
            if de < 2:
                factors.append(SHAPFactor(
                    feature_name="debt_equity",
                    shap_value=0.08,
                    direction="decreases risk",
                    display_name=f"Healthy D/E Ratio ({de})"
                ))
            else:
                factors.append(SHAPFactor(
                    feature_name="debt_equity",
                    shap_value=0.08,
                    direction="increases risk",
                    display_name=f"High D/E Ratio ({de})"
                ))

        if result.gst_data and result.gst_data.turnover > 0:
            factors.append(SHAPFactor(
                feature_name="gst_turnover",
                shap_value=0.07,
                direction="decreases risk",
                display_name=f"GST Turnover Rs.{result.gst_data.turnover:,.0f}"
            ))

        return factors[:4]  # Return top 4

    # ─── FALLBACK ────────────────────────────────────────────────────────────

    def _fallback_reasoning(self, financial_text: str) -> str:
        """Used when LLM is unavailable — rule-based reasoning"""
        return f"""
DECISION: Conditional Approval
LIMIT: Rs.25 lakhs
RATE: 12.5% per annum

REASONING CHAIN:
1. GST Analysis      -> Data extracted successfully -> Moderate risk
2. Bank Statements   -> Credits indicate business activity -> Neutral impact
3. External Research -> No major red flags found -> Decreases risk
4. Primary Inputs    -> Standard documentation received -> Neutral impact

DECISIVE FACTOR: Conditional approval pending verification of GST reconciliation.

EARLY WARNING SIGNALS:
- Monitor GST filing regularity monthly
- Track EMI payment pattern
- Watch for sudden large cash withdrawals

LOAN CONDITIONS:
- Submit audited financials within 30 days
- Collateral documentation required

NOTE: This is a rule-based fallback. LLM was unavailable.
Financial Data Reviewed:
{financial_text[:500]}
"""


# ─── QUICK TEST ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from src.schemas import (
        CreditAppraisalResult, GSTData, BankStatementData,
        GSTReconciliationResult, QualitativeInputs
    )

    print("="*50)
    print("TEST: Credit Agent")
    print("="*50)

    agent = CreditAgent()

    # Build a test case
    test_result = CreditAppraisalResult(
        company_name="ABC Private Limited",
        gst_data=GSTData(
            gstin="27AABCU9603R1ZX",
            company_name="ABC Private Limited",
            turnover=4500000,
            total_tax=500000,
            itc_claimed=80000,
            filing_regular=True
        ),
        bank_data=BankStatementData(
            bank_name="HDFC",
            total_credits=4200000,
            total_debits=3800000,
            average_monthly_balance=350000,
            emi_bounce_count=1
        ),
        gst_reconciliation=GSTReconciliationResult(
            total_mismatches=1,
            risk_flag=False,
            variance_pct=8.5,
            circular_trading_flag=False,
            summary="Minor variance in ITC claims, within acceptable range."
        ),
        qualitative_inputs=QualitativeInputs(
            site_visit_notes="Factory running at full capacity. Good condition. New orders from Tata Motors.",
            debt_equity_ratio=1.5,
            collateral_coverage=0.75,
            sector_risk_score=4,
            promoter_score=7
        )
    )

    # Run analysis
    final = agent.analyze(test_result)

    print("\n" + "="*50)
    print("ANALYSIS RESULT")
    print("="*50)
    print(f"Decision:      {final.risk_prediction.decision}")
    print(f"Risk Score:    {final.risk_prediction.risk_score}")
    print(f"Risk Category: {final.risk_prediction.risk_category}")
    print(f"Loan Limit:    Rs.{final.risk_prediction.loan_limit_inr:,.0f}")
    print(f"Interest Rate: {final.risk_prediction.interest_rate}%")
    print(f"\nDecisive Factor: {final.risk_prediction.decisive_factor}")
    print(f"\nEarly Warnings:")
    for w in final.risk_prediction.early_warning_signals:
        print(f"  - {w}")
    print(f"\nSHAP Factors:")
    for f in final.risk_prediction.top_shap_factors:
        print(f"  - {f.display_name}: {f.direction} ({f.shap_value})")
    print(f"\nReasoning Chain (first 500 chars):")
    print(final.reasoning_chain[:500])
