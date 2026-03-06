from src.cam_generator import CAMGenerator
from src.agent import CreditAgent
from src.five_cs import FiveCsAnalyzer
from src.risk_engine import RiskEngine
from src.researcher import ResearchAgent
from src.reconciler import GSTReconciler
from src.extractor import FinancialExtractor
from src.schemas import (
    CreditAppraisalResult, GSTData, BankStatementData,
    GSTReconciliationResult, QualitativeInputs,
    ResearchFindings, ITRData
)
import time
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))


# ─── TEST DATA ────────────────────────────────────────────────────────────────

SCENARIOS = {
    "low": {
        "company": "Safe Industries Pvt Ltd",
        "gst": GSTData(
            gstin="27AABCS1234R1ZX",
            company_name="Safe Industries Pvt Ltd",
            turnover=8000000,
            total_tax=800000,
            itc_claimed=200000,
            filing_regular=True
        ),
        "bank": BankStatementData(
            bank_name="HDFC Bank",
            total_credits=7500000,
            total_debits=6000000,
            average_monthly_balance=800000,
            emi_bounce_count=0
        ),
        "recon": GSTReconciliationResult(
            total_mismatches=0,
            risk_flag=False,
            variance_pct=3.0,
            circular_trading_flag=False,
            summary="Clean reconciliation."
        ),
        "qualitative": QualitativeInputs(
            site_visit_notes="Factory running at full capacity. New orders from Tata Motors.",
            debt_equity_ratio=0.8,
            collateral_coverage=1.2,
            net_worth_inr=15000000,
            sector_risk_score=3,
            promoter_score=9
        ),
        "mock_level": "low",
        "expected_decision": "APPROVE",
        "expected_max_score": 0.35
    },
    "medium": {
        "company": "ABC Manufacturing Pvt Ltd",
        "gst": GSTData(
            gstin="27AABCM5678R1ZX",
            company_name="ABC Manufacturing Pvt Ltd",
            turnover=4500000,
            total_tax=500000,
            itc_claimed=80000,
            filing_regular=True
        ),
        "bank": BankStatementData(
            bank_name="SBI",
            total_credits=4200000,
            total_debits=3800000,
            average_monthly_balance=350000,
            emi_bounce_count=2
        ),
        "recon": GSTReconciliationResult(
            total_mismatches=1,
            risk_flag=False,
            variance_pct=9.0,
            circular_trading_flag=False,
            summary="Minor variance within range."
        ),
        "qualitative": QualitativeInputs(
            site_visit_notes="Factory at 60% capacity. Some idle machinery.",
            debt_equity_ratio=1.8,
            collateral_coverage=0.8,
            net_worth_inr=5000000,
            sector_risk_score=5,
            promoter_score=6
        ),
        "mock_level": "medium",
        "expected_decision": "CONDITIONAL",
        "expected_max_score": 0.65
    },
    "high": {
        "company": "XYZ Traders Pvt Ltd",
        "gst": GSTData(
            gstin="27AABCX9999R1ZX",
            company_name="XYZ Traders Pvt Ltd",
            turnover=2000000,
            total_tax=200000,
            itc_claimed=500000,
            filing_regular=False
        ),
        "bank": BankStatementData(
            bank_name="Axis Bank",
            total_credits=1800000,
            total_debits=1750000,
            average_monthly_balance=50000,
            emi_bounce_count=5
        ),
        "recon": GSTReconciliationResult(
            total_mismatches=4,
            risk_flag=True,
            variance_pct=35.0,
            circular_trading_flag=True,
            summary="Multiple mismatches. Circular trading detected."
        ),
        "qualitative": QualitativeInputs(
            site_visit_notes="Factory shut. Idle machinery. Poor condition.",
            debt_equity_ratio=4.2,
            collateral_coverage=0.3,
            net_worth_inr=500000,
            sector_risk_score=9,
            promoter_score=2
        ),
        "mock_level": "high",
        "expected_decision": "REJECT",
        "expected_max_score": 1.0
    }
}

# ─── HELPERS ─────────────────────────────────────────────────────────────────


def build_result(scenario: dict) -> CreditAppraisalResult:
    return CreditAppraisalResult(
        company_name=scenario["company"],
        gst_data=scenario["gst"],
        bank_data=scenario["bank"],
        gst_reconciliation=scenario["recon"],
        qualitative_inputs=scenario["qualitative"]
    )


def print_header(text: str):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)


def print_result(label: str, passed: bool, detail: str = ""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status}  {label}")
    if detail:
        print(f"         {detail}")

# ─── MAIN TEST RUNNER ─────────────────────────────────────────────────────────


def run_all_tests():
    total_start = time.time()
    all_passed = True
    results_summary = []

    print_header("IntelliCredit — End-to-End Pipeline Test")
    print(f"  Testing {len(SCENARIOS)} scenarios: low / medium / high risk")

    # ── Load engines ─────────────────────────────────────────────────────────
    print("\n📦 Loading engines...")
    try:
        researcher = ResearchAgent()
        risk_engine = RiskEngine()
        five_cs = FiveCsAnalyzer()
        agent = CreditAgent()
        cam = CAMGenerator()
        print("  All engines loaded successfully.")
    except Exception as e:
        print(f"  ❌ Engine loading failed: {e}")
        return False

    # ── Run each scenario ─────────────────────────────────────────────────────
    for level, scenario in SCENARIOS.items():
        print_header(
            f"Scenario: {level.upper()} RISK — {scenario['company']}"
        )
        scenario_start = time.time()
        scenario_passed = True

        try:
            result = build_result(scenario)

            # Step 1: Research
            print("  🔎 Running research...")
            result.research = researcher.research_with_mock(
                scenario["company"], scenario["mock_level"]
            )
            research_ok = result.research is not None
            print_result("Research agent", research_ok)
            scenario_passed &= research_ok

            # Step 2: Five Cs
            print("  📊 Running Five Cs...")
            result.five_cs = five_cs.analyze(result)
            five_cs_ok = (
                result.five_cs is not None and
                0 <= result.five_cs.overall_score <= 10
            )
            print_result(
                "Five Cs analysis",
                five_cs_ok,
                f"Overall: {result.five_cs.overall_score}/10"
            )
            scenario_passed &= five_cs_ok

            # Step 3: Risk scoring
            print("  🤖 Running XGBoost risk scoring...")
            result.risk_prediction = risk_engine.score(result)
            score = result.risk_prediction.risk_score
            score_ok = 0.0 <= score <= 1.0
            print_result(
                "XGBoost scoring",
                score_ok,
                f"Score: {score:.3f}"
            )
            scenario_passed &= score_ok

            # Step 4: LLM reasoning
            print("  🧠 Running LLM reasoning (Groq)...")
            result = agent.analyze(result)
            decision_str = str(
                result.risk_prediction.decision
            ).replace("DecisionType.", "")
            llm_ok = result.reasoning_chain is not None
            print_result(
                "LLM reasoning",
                llm_ok,
                f"Decision: {decision_str}"
            )
            scenario_passed &= llm_ok

            # Step 5: Decision check
            expected = scenario["expected_decision"]
            decision_ok = expected in decision_str.upper()
            print_result(
                f"Decision matches expected ({expected})",
                decision_ok,
                f"Got: {decision_str}"
            )
            scenario_passed &= decision_ok

            # Step 6: CAM generation
            print("  📄 Generating CAM reports...")
            paths = cam.generate_both(result)
            pdf_ok = Path(paths["pdf"]).exists()
            docx_ok = Path(paths["docx"]).exists()
            print_result("PDF generated", pdf_ok, paths["pdf"])
            print_result("DOCX generated", docx_ok, paths["docx"])
            scenario_passed &= (pdf_ok and docx_ok)

        except Exception as e:
            print(f"  ❌ Scenario failed with error: {e}")
            import traceback
            traceback.print_exc()
            scenario_passed = False

        elapsed = time.time() - scenario_start
        status = "✅ PASSED" if scenario_passed else "❌ FAILED"
        print(f"\n  {status} in {elapsed:.1f}s")

        all_passed &= scenario_passed
        results_summary.append({
            "scenario": level,
            "company": scenario["company"],
            "passed": scenario_passed,
            "time": elapsed
        })

    # ── Final Summary ─────────────────────────────────────────────────────────
    total_elapsed = time.time() - total_start
    print_header("TEST SUMMARY")

    passed_count = sum(1 for r in results_summary if r["passed"])
    total_count = len(results_summary)

    for r in results_summary:
        status = "✅" if r["passed"] else "❌"
        print(f"  {status} {r['scenario'].upper():8} "
              f"{r['company']:35} {r['time']:.1f}s")

    print(f"\n  Result: {passed_count}/{total_count} scenarios passed")
    print(f"  Total time: {total_elapsed:.1f}s")

    if all_passed:
        print("\n  🎉 ALL TESTS PASSED — Pipeline is production ready!")
    else:
        print("\n  ⚠️  Some tests failed — review errors above.")

    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
