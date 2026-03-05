from config import FIVE_CS_WEIGHTS
from src.schemas import (
    CreditAppraisalResult, FiveCsResult, CScore
)
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


class FiveCsAnalyzer:
    """
    Five Cs of Credit assessment for Indian corporate lending.
    Character, Capacity, Capital, Collateral, Conditions.
    Each scored 0-10. Weighted average gives overall score.
    """

    def analyze(self, result: CreditAppraisalResult) -> FiveCsResult:
        """Main entry point — analyze all five Cs"""
        character = self._score_character(result)
        capacity = self._score_capacity(result)
        capital = self._score_capital(result)
        collateral = self._score_collateral(result)
        conditions = self._score_conditions(result)

        # Weighted overall score
        overall = (
            character.score * FIVE_CS_WEIGHTS["character"] +
            capacity.score * FIVE_CS_WEIGHTS["capacity"] +
            capital.score * FIVE_CS_WEIGHTS["capital"] +
            collateral.score * FIVE_CS_WEIGHTS["collateral"] +
            conditions.score * FIVE_CS_WEIGHTS["conditions"]
        )

        return FiveCsResult(
            character=character,
            capacity=capacity,
            capital=capital,
            collateral=collateral,
            conditions=conditions,
            overall_score=round(overall, 2)
        )

    # ─── CHARACTER ───────────────────────────────────────────────────────────

    def _score_character(self,
                         result: CreditAppraisalResult) -> CScore:
        """
        Character = willingness to repay.
        Based on: GST filing regularity, litigation,
        negative news, promoter integrity.
        """
        score = 10.0
        factors = []
        details = {}

        # GST filing regularity
        if result.gst_data:
            if result.gst_data.filing_regular:
                factors.append("GST returns filed regularly — positive signal")
                details["gst_regular"] = True
            else:
                score -= 2.0
                factors.append(
                    "Irregular GST filing history — negative signal")
                details["gst_regular"] = False

        # GST reconciliation flags
        if result.gst_reconciliation:
            if result.gst_reconciliation.risk_flag:
                score -= 2.5
                factors.append(
                    f"GSTR-2A vs 3B mismatch detected "
                    f"({result.gst_reconciliation.variance_pct}% variance)"
                )
            if result.gst_reconciliation.circular_trading_flag:
                score -= 3.0
                factors.append(
                    "Circular trading pattern detected — serious concern"
                )

        # Litigation
        if result.research:
            if result.research.litigation_found:
                score -= 2.0
                factors.append(
                    f"Active litigation found: "
                    f"{len(result.research.litigation_details)} case(s)"
                )
            if result.research.rbi_sebi_actions:
                score -= 3.0
                factors.append(
                    "RBI/SEBI enforcement action on record — critical flag"
                )
            neg_news = len(result.research.negative_news)
            if neg_news > 3:
                score -= 1.5
                factors.append(
                    f"{neg_news} negative news articles found"
                )
            elif neg_news > 0:
                score -= 0.5
                factors.append(f"{neg_news} negative news article(s) found")

        # Promoter score
        if result.qualitative_inputs:
            p_score = result.qualitative_inputs.promoter_score
            details["promoter_score"] = p_score
            if p_score >= 8:
                factors.append(f"High promoter integrity score ({p_score}/10)")
            elif p_score >= 5:
                score -= 1.0
                factors.append(f"Average promoter score ({p_score}/10)")
            else:
                score -= 2.5
                factors.append(
                    f"Low promoter integrity score ({p_score}/10) — concern"
                )

        score = round(max(0.0, min(10.0, score)), 1)
        return CScore(
            score=score,
            factors=factors,
            details=details,
            summary=self._character_summary(score)
        )

    def _character_summary(self, score: float) -> str:
        if score >= 8:
            return "Excellent character profile. Strong compliance history."
        elif score >= 6:
            return "Good character with minor concerns. Monitor regularly."
        elif score >= 4:
            return "Moderate character risk. Additional due diligence needed."
        else:
            return "Poor character profile. High risk of wilful default."

    # ─── CAPACITY ────────────────────────────────────────────────────────────

    def _score_capacity(self,
                        result: CreditAppraisalResult) -> CScore:
        """
        Capacity = ability to repay from cash flows.
        Based on: DSCR, revenue trend, bank credits vs debits.
        """
        score = 5.0  # Start neutral
        factors = []
        details = {}

        # Bank statement analysis
        if result.bank_data:
            credits = result.bank_data.total_credits
            debits = result.bank_data.total_debits
            avg_bal = result.bank_data.average_monthly_balance
            bounces = result.bank_data.emi_bounce_count

            details["total_credits"] = credits
            details["total_debits"] = debits

            # Credit-debit ratio
            if credits > 0:
                cd_ratio = (credits - debits) / credits
                details["cd_ratio"] = round(cd_ratio, 3)

                if cd_ratio > 0.20:
                    score += 2.0
                    factors.append(
                        f"Strong surplus cash flow "
                        f"({cd_ratio*100:.1f}% net margin on credits)"
                    )
                elif cd_ratio > 0.10:
                    score += 1.0
                    factors.append(
                        f"Moderate cash flow surplus ({cd_ratio*100:.1f}%)"
                    )
                elif cd_ratio > 0:
                    factors.append(
                        f"Thin cash flow margin ({cd_ratio*100:.1f}%)"
                    )
                else:
                    score -= 2.0
                    factors.append(
                        "Debits exceed credits — negative cash flow signal"
                    )

            # Average balance
            if avg_bal > 500000:
                score += 1.5
                factors.append(
                    f"Healthy average balance "
                    f"(Rs.{avg_bal:,.0f})"
                )
            elif avg_bal > 100000:
                score += 0.5
                factors.append(
                    f"Adequate average balance (Rs.{avg_bal:,.0f})"
                )
            else:
                score -= 1.0
                factors.append(
                    f"Low average balance (Rs.{avg_bal:,.0f})"
                )

            # EMI bounces
            if bounces == 0:
                score += 1.0
                factors.append("No EMI bounces — clean repayment record")
            elif bounces <= 2:
                score -= 0.5
                factors.append(f"{bounces} EMI bounce(s) — minor concern")
            else:
                score -= 2.0
                factors.append(
                    f"{bounces} EMI bounces — serious repayment concern"
                )

        # GST turnover as proxy for revenue
        if result.gst_data and result.gst_data.turnover > 0:
            turnover = result.gst_data.turnover
            details["gst_turnover"] = turnover

            if turnover > 5_000_000:
                score += 1.0
                factors.append(
                    f"Strong GST turnover (Rs.{turnover:,.0f})"
                )
            elif turnover > 1_000_000:
                factors.append(
                    f"Moderate GST turnover (Rs.{turnover:,.0f})"
                )
            else:
                score -= 1.0
                factors.append(
                    f"Low GST turnover (Rs.{turnover:,.0f})"
                )

        score = round(max(0.0, min(10.0, score)), 1)
        return CScore(
            score=score,
            factors=factors,
            details=details,
            summary=self._capacity_summary(score)
        )

    def _capacity_summary(self, score: float) -> str:
        if score >= 8:
            return "Excellent repayment capacity. Strong and consistent cash flows."
        elif score >= 6:
            return "Good capacity with adequate cash flows to service debt."
        elif score >= 4:
            return "Moderate capacity. Cash flows need monitoring post-disbursement."
        else:
            return "Weak repayment capacity. High risk of default on repayment."

    # ─── CAPITAL ─────────────────────────────────────────────────────────────

    def _score_capital(self,
                       result: CreditAppraisalResult) -> CScore:
        """
        Capital = financial strength / net worth.
        Based on: D/E ratio, net worth, ITR data.
        """
        score = 5.0
        factors = []
        details = {}

        if result.qualitative_inputs:
            de_ratio = result.qualitative_inputs.debt_equity_ratio
            details["debt_equity_ratio"] = de_ratio

            if de_ratio < 1.0:
                score += 3.0
                factors.append(
                    f"Excellent D/E ratio ({de_ratio}) — low leverage"
                )
            elif de_ratio < 2.0:
                score += 1.5
                factors.append(
                    f"Acceptable D/E ratio ({de_ratio})"
                )
            elif de_ratio < 3.0:
                score -= 1.0
                factors.append(
                    f"Elevated D/E ratio ({de_ratio}) — moderate leverage"
                )
            else:
                score -= 3.0
                factors.append(
                    f"High D/E ratio ({de_ratio}) — over-leveraged"
                )

            net_worth = result.qualitative_inputs.net_worth_inr
            details["net_worth"] = net_worth
            if net_worth > 10_000_000:
                score += 2.0
                factors.append(
                    f"Strong net worth (Rs.{net_worth:,.0f})"
                )
            elif net_worth > 1_000_000:
                score += 1.0
                factors.append(
                    f"Adequate net worth (Rs.{net_worth:,.0f})"
                )

        if result.itr_data:
            net_income = result.itr_data.net_income
            if net_income > 0:
                score += 1.0
                factors.append(
                    f"Positive net income per ITR "
                    f"(Rs.{net_income:,.0f})"
                )
            elif net_income < 0:
                score -= 2.0
                factors.append("Negative net income reported in ITR")

        score = round(max(0.0, min(10.0, score)), 1)
        return CScore(
            score=score,
            factors=factors,
            details=details,
            summary=self._capital_summary(score)
        )

    def _capital_summary(self, score: float) -> str:
        if score >= 8:
            return "Strong capital base. Well-capitalized with low leverage."
        elif score >= 6:
            return "Adequate capital. Leverage within acceptable limits."
        elif score >= 4:
            return "Moderate capital concerns. Leverage needs monitoring."
        else:
            return "Weak capital base. High leverage poses significant risk."

    # ─── COLLATERAL ──────────────────────────────────────────────────────────

    def _score_collateral(self,
                          result: CreditAppraisalResult) -> CScore:
        """
        Collateral = security coverage.
        Based on: collateral coverage ratio.
        """
        score = 5.0
        factors = []
        details = {}

        if result.qualitative_inputs:
            coverage = result.qualitative_inputs.collateral_coverage
            details["coverage_ratio"] = coverage

            if coverage >= 1.5:
                score += 4.0
                factors.append(
                    f"Excellent collateral coverage "
                    f"({coverage*100:.0f}% of loan value)"
                )
            elif coverage >= 1.0:
                score += 2.5
                factors.append(
                    f"Adequate collateral coverage ({coverage*100:.0f}%)"
                )
            elif coverage >= 0.75:
                score += 1.0
                factors.append(
                    f"Partial collateral coverage ({coverage*100:.0f}%)"
                )
            else:
                score -= 2.0
                factors.append(
                    f"Insufficient collateral ({coverage*100:.0f}%) — "
                    f"below minimum threshold"
                )

        if not factors:
            factors.append("Collateral details not provided by officer")

        score = round(max(0.0, min(10.0, score)), 1)
        return CScore(
            score=score,
            factors=factors,
            details=details,
            summary=self._collateral_summary(score)
        )

    def _collateral_summary(self, score: float) -> str:
        if score >= 8:
            return "Excellent collateral cover. Strong security for the bank."
        elif score >= 6:
            return "Adequate collateral. Loan well-secured."
        elif score >= 4:
            return "Partial collateral. Consider additional security."
        else:
            return "Insufficient collateral. High unsecured exposure."

    # ─── CONDITIONS ──────────────────────────────────────────────────────────

    def _score_conditions(self,
                          result: CreditAppraisalResult) -> CScore:
        """
        Conditions = external environment.
        Based on: sector risk, economic conditions.
        """
        score = 7.0  # Start optimistic
        factors = []
        details = {}

        if result.qualitative_inputs:
            sector_risk = result.qualitative_inputs.sector_risk_score
            details["sector_risk_score"] = sector_risk

            if sector_risk <= 3:
                score += 2.0
                factors.append(
                    f"Low sector risk ({sector_risk}/10) — "
                    f"favourable industry conditions"
                )
            elif sector_risk <= 5:
                factors.append(
                    f"Moderate sector risk ({sector_risk}/10)"
                )
            elif sector_risk <= 7:
                score -= 2.0
                factors.append(
                    f"Elevated sector risk ({sector_risk}/10) — "
                    f"challenging industry conditions"
                )
            else:
                score -= 4.0
                factors.append(
                    f"High sector risk ({sector_risk}/10) — "
                    f"distressed industry"
                )

        # Research-based conditions
        if result.research:
            if result.research.rbi_sebi_actions:
                score -= 2.0
                factors.append(
                    "Regulatory action by RBI/SEBI — adverse conditions"
                )

        if not factors:
            factors.append(
                "General market conditions — no specific sector data provided"
            )

        score = round(max(0.0, min(10.0, score)), 1)
        return CScore(
            score=score,
            factors=factors,
            details=details,
            summary=self._conditions_summary(score)
        )

    def _conditions_summary(self, score: float) -> str:
        if score >= 8:
            return "Favourable external conditions. Low macro risk."
        elif score >= 6:
            return "Neutral conditions. Standard sector risk."
        elif score >= 4:
            return "Challenging conditions. Sector headwinds present."
        else:
            return "Adverse conditions. High macro and sector risk."


# ─── QUICK TEST ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from src.schemas import (
        CreditAppraisalResult, GSTData, BankStatementData,
        GSTReconciliationResult, QualitativeInputs,
        ResearchFindings, ITRData
    )

    analyzer = FiveCsAnalyzer()

    print("="*50)
    print("TEST: Five Cs Analysis")
    print("="*50)

    test = CreditAppraisalResult(
        company_name="ABC Private Limited",
        gst_data=GSTData(
            turnover=4500000,
            total_tax=500000,
            itc_claimed=80000,
            filing_regular=True
        ),
        bank_data=BankStatementData(
            total_credits=4200000,
            total_debits=3500000,
            average_monthly_balance=450000,
            emi_bounce_count=1
        ),
        gst_reconciliation=GSTReconciliationResult(
            total_mismatches=1,
            risk_flag=False,
            variance_pct=8.5,
            circular_trading_flag=False
        ),
        itr_data=None,
        research=ResearchFindings(
            company_name="ABC Private Limited",
            litigation_found=False,
            news_risk_score=2.0,
            negative_news=[],
            rbi_sebi_actions=[]
        ),
        qualitative_inputs=QualitativeInputs(
            debt_equity_ratio=1.5,
            collateral_coverage=0.85,
            net_worth_inr=5000000,
            sector_risk_score=4,
            promoter_score=7
        )
    )

    result = analyzer.analyze(test)

    print(f"\nCharacter:  {result.character.score}/10")
    print(f"  {result.character.summary}")
    for f in result.character.factors:
        print(f"  - {f}")

    print(f"\nCapacity:   {result.capacity.score}/10")
    print(f"  {result.capacity.summary}")
    for f in result.capacity.factors:
        print(f"  - {f}")

    print(f"\nCapital:    {result.capital.score}/10")
    print(f"  {result.capital.summary}")
    for f in result.capital.factors:
        print(f"  - {f}")

    print(f"\nCollateral: {result.collateral.score}/10")
    print(f"  {result.collateral.summary}")
    for f in result.collateral.factors:
        print(f"  - {f}")

    print(f"\nConditions: {result.conditions.score}/10")
    print(f"  {result.conditions.summary}")
    for f in result.conditions.factors:
        print(f"  - {f}")

    print(f"\n{'='*50}")
    print(f"OVERALL FIVE Cs SCORE: {result.overall_score}/10")
    print(f"{'='*50}")
