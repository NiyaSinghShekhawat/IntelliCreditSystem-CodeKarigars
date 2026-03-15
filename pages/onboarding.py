# pages/onboarding.py
"""
Multi-step entity onboarding form.
Step 1: Company Information
Step 2: Loan Details  
Step 3: Review & Confirm → saves to Supabase, creates case_id
"""
import streamlit as st
from src.database import save_entity, create_case


# ─── STEP BAR ─────────────────────────────────────────────────────────────────

def _step_bar(current: int):
    steps = ["Company Info", "Loan Details", "Review & Confirm"]
    items = ""
    for i, label in enumerate(steps, 1):
        if i < current:
            cls = "done"
            prefix = "✓"
        elif i == current:
            cls = "active"
            prefix = str(i)
        else:
            cls = "step-item"
            prefix = str(i)
        items += f"<div class='step-item {cls}'>{prefix}. {label}</div>"
    st.markdown(f"<div class='step-bar'>{items}</div>", unsafe_allow_html=True)


# ─── FIELD HELPERS ────────────────────────────────────────────────────────────

def _field_label(label: str, required: bool = False) -> str:
    req = " <span style='color:var(--reject);'>*</span>" if required else ""
    return f"<div style='font-size:0.78rem;font-weight:600;color:var(--text-sec);letter-spacing:0.04em;margin-bottom:4px;'>{label}{req}</div>"


def _review_row(label: str, value: str):
    st.markdown(f"""
    <div style='display:flex;justify-content:space-between;align-items:center;
                padding:0.55rem 0;border-bottom:1px solid var(--surface-2);'>
        <div style='font-size:0.78rem;color:var(--text-muted);font-weight:500;
                    text-transform:uppercase;letter-spacing:0.06em;'>{label}</div>
        <div style='font-size:0.88rem;color:var(--navy);font-weight:600;
                    font-family:JetBrains Mono,monospace;'>{value or "—"}</div>
    </div>
    """, unsafe_allow_html=True)


# ─── STEP 1: COMPANY INFO ─────────────────────────────────────────────────────

def _step1():
    st.markdown("""
    <div style='margin-bottom:1.2rem;'>
        <div style='font-size:1rem;font-weight:600;color:var(--navy);'>Company Information</div>
        <div style='font-size:0.82rem;color:var(--text-muted);margin-top:2px;'>
            Basic entity details for the credit assessment
        </div>
    </div>
    """, unsafe_allow_html=True)

    f = st.session_state.get("ob_form", {})

    col1, col2 = st.columns(2)
    with col1:
        company_name = st.text_input(
            "Company Name *",
            value=f.get("company_name", ""),
            placeholder="e.g. Radiant Infratech Pvt Ltd"
        )
        cin = st.text_input(
            "CIN (Corporate Identity Number)",
            value=f.get("cin", ""),
            placeholder="L12345MH2010PLC123456"
        )
        sector = st.selectbox(
            "Sector *",
            ["", "Manufacturing", "Trading", "Infrastructure",
             "Healthcare", "Technology", "FMCG", "Real Estate",
             "Logistics", "Financial Services", "NBFC / Fintech",
             "Agriculture", "Education", "Hospitality", "Other"],
            index=["", "Manufacturing", "Trading", "Infrastructure",
                   "Healthcare", "Technology", "FMCG", "Real Estate",
                   "Logistics", "Financial Services", "NBFC / Fintech",
                   "Agriculture", "Education", "Hospitality", "Other"
                   ].index(f.get("sector", "")) if f.get("sector", "") in
            ["", "Manufacturing", "Trading", "Infrastructure",
             "Healthcare", "Technology", "FMCG", "Real Estate",
             "Logistics", "Financial Services", "NBFC / Fintech",
             "Agriculture", "Education", "Hospitality", "Other"] else 0
        )
        sub_sector = st.text_input(
            "Sub-sector",
            value=f.get("sub_sector", ""),
            placeholder="e.g. Civil Construction, MSME Lending"
        )

    with col2:
        pan = st.text_input(
            "PAN",
            value=f.get("pan", ""),
            placeholder="ABCDE1234F"
        )
        gstin = st.text_input(
            "GSTIN",
            value=f.get("gstin", ""),
            placeholder="27ABCDE1234F1Z5"
        )
        turnover = st.number_input(
            "Annual Turnover (₹ Cr)",
            min_value=0.0,
            value=float(f.get("turnover_cr", 0.0)),
            step=0.5,
            format="%.2f"
        )
        incorporation_year = st.number_input(
            "Year of Incorporation",
            min_value=1900,
            max_value=2025,
            value=int(f.get("incorporation_year", 2010)),
            step=1,
            format="%d"
        )

    st.markdown("<hr class='ic-divider'>", unsafe_allow_html=True)

    # Promoter details
    st.markdown("""
    <div style='font-size:0.85rem;font-weight:600;color:var(--navy);margin-bottom:0.75rem;'>
        Promoter / Key Contact
    </div>
    """, unsafe_allow_html=True)

    col3, col4 = st.columns(2)
    with col3:
        promoter_name = st.text_input(
            "Promoter / Director Name",
            value=f.get("promoter_name", ""),
            placeholder="Mr. Rajesh Kumar"
        )
        promoter_pan = st.text_input(
            "Promoter PAN",
            value=f.get("promoter_pan", ""),
            placeholder="ABCDE1234F"
        )
    with col4:
        promoter_phone = st.text_input(
            "Contact Number",
            value=f.get("promoter_phone", ""),
            placeholder="+91 98765 43210"
        )
        promoter_email = st.text_input(
            "Email Address",
            value=f.get("promoter_email", ""),
            placeholder="rajesh@company.com"
        )

    # Validation & Next
    st.markdown("<hr class='ic-divider'>", unsafe_allow_html=True)
    col_gap, col_next = st.columns([6, 1.5])
    with col_next:
        if st.button("Next →", type="primary", use_container_width=True):
            if not company_name.strip():
                st.error("Company name is required.")
            elif not sector:
                st.error("Sector is required.")
            else:
                st.session_state.ob_form = {
                    **st.session_state.get("ob_form", {}),
                    "company_name":      company_name.strip(),
                    "cin":               cin.strip() or None,
                    "pan":               pan.strip() or None,
                    "gstin":             gstin.strip() or None,
                    "sector":            sector,
                    "sub_sector":        sub_sector.strip() or None,
                    "turnover_cr":       turnover if turnover > 0 else None,
                    "incorporation_year": incorporation_year,
                    "promoter_name":     promoter_name.strip() or None,
                    "promoter_pan":      promoter_pan.strip() or None,
                    "promoter_phone":    promoter_phone.strip() or None,
                    "promoter_email":    promoter_email.strip() or None,
                }
                st.session_state.ob_step = 2
                st.rerun()


# ─── STEP 2: LOAN DETAILS ─────────────────────────────────────────────────────

def _step2():
    st.markdown("""
    <div style='margin-bottom:1.2rem;'>
        <div style='font-size:1rem;font-weight:600;color:var(--navy);'>Loan Request Details</div>
        <div style='font-size:0.82rem;color:var(--text-muted);margin-top:2px;'>
            Specifics of the credit facility being requested
        </div>
    </div>
    """, unsafe_allow_html=True)

    f = st.session_state.get("ob_form", {})

    col1, col2 = st.columns(2)
    with col1:
        loan_type = st.selectbox(
            "Loan Type *",
            ["", "Term Loan", "Working Capital", "Cash Credit",
             "Letter of Credit", "Bank Guarantee", "Overdraft",
             "Supply Chain Finance", "Co-lending", "NCD"],
            index=["", "Term Loan", "Working Capital", "Cash Credit",
                   "Letter of Credit", "Bank Guarantee", "Overdraft",
                   "Supply Chain Finance", "Co-lending", "NCD"
                   ].index(f.get("loan_type", "")) if f.get("loan_type", "") in
            ["", "Term Loan", "Working Capital", "Cash Credit",
             "Letter of Credit", "Bank Guarantee", "Overdraft",
             "Supply Chain Finance", "Co-lending", "NCD"] else 0
        )
        loan_amount = st.number_input(
            "Loan Amount (₹ Cr) *",
            min_value=0.0,
            value=float(f.get("loan_amount_cr", 0.0)),
            step=0.5,
            format="%.2f"
        )
        loan_purpose = st.selectbox(
            "Loan Purpose",
            ["Working Capital", "Capital Expenditure", "Machinery Purchase",
             "Business Expansion", "Trade Finance", "Debt Refinancing",
             "Real Estate", "Other"],
            index=["Working Capital", "Capital Expenditure", "Machinery Purchase",
                   "Business Expansion", "Trade Finance", "Debt Refinancing",
                   "Real Estate", "Other"
                   ].index(f.get("loan_purpose", "Working Capital"))
            if f.get("loan_purpose", "Working Capital") in
            ["Working Capital", "Capital Expenditure", "Machinery Purchase",
             "Business Expansion", "Trade Finance", "Debt Refinancing",
             "Real Estate", "Other"] else 0
        )

    with col2:
        tenure_months = st.number_input(
            "Tenure (months) *",
            min_value=1,
            max_value=360,
            value=int(f.get("loan_tenure_months", 12)),
            step=1,
            format="%d"
        )
        interest_rate = st.number_input(
            "Expected Interest Rate (% p.a.)",
            min_value=0.0,
            max_value=36.0,
            value=float(f.get("interest_rate", 12.0)),
            step=0.25,
            format="%.2f"
        )
        repayment_frequency = st.selectbox(
            "Repayment Frequency",
            ["Monthly", "Quarterly", "Half-yearly", "Bullet"],
            index=["Monthly", "Quarterly", "Half-yearly", "Bullet"
                   ].index(f.get("repayment_frequency", "Monthly"))
            if f.get("repayment_frequency", "Monthly") in
            ["Monthly", "Quarterly", "Half-yearly", "Bullet"] else 0
        )

    st.markdown("<hr class='ic-divider'>", unsafe_allow_html=True)

    # Collateral
    st.markdown("""
    <div style='font-size:0.85rem;font-weight:600;color:var(--navy);margin-bottom:0.75rem;'>
        Collateral Details
    </div>
    """, unsafe_allow_html=True)

    col3, col4 = st.columns(2)
    with col3:
        collateral_type = st.selectbox(
            "Primary Collateral Type",
            ["", "Immovable Property", "Plant & Machinery",
             "Receivables", "Fixed Deposits", "Shares / Securities",
             "Inventory", "Personal Guarantee", "None / Unsecured"],
        )
        collateral_value = st.number_input(
            "Collateral Value (₹ Cr)",
            min_value=0.0,
            value=0.0,
            step=0.5,
            format="%.2f"
        )
    with col4:
        collateral_coverage = round(
            (collateral_value / loan_amount * 100) if loan_amount > 0 else 0, 1
        )
        st.markdown(f"""
        <div class='ic-card' style='margin-top:1.6rem;text-align:center;'>
            <div style='font-size:0.72rem;color:var(--text-muted);text-transform:uppercase;
                        letter-spacing:0.08em;font-weight:600;margin-bottom:4px;'>
                Collateral Coverage
            </div>
            <div style='font-size:2rem;font-weight:700;font-family:JetBrains Mono,monospace;
                        color:{"var(--approve)" if collateral_coverage >= 100
                               else "var(--warn)" if collateral_coverage >= 60
                               else "var(--reject)"};'>
                {collateral_coverage:.0f}%
            </div>
            <div style='font-size:0.72rem;color:var(--text-muted);margin-top:2px;'>
                {"✓ Fully covered" if collateral_coverage >= 100
                 else "⚠ Partially covered" if collateral_coverage >= 60
                 else "✗ Under-collateralised"}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Back / Next
    st.markdown("<hr class='ic-divider'>", unsafe_allow_html=True)
    col_back, col_gap, col_next = st.columns([1.5, 5, 1.5])
    with col_back:
        if st.button("← Back", use_container_width=True):
            st.session_state.ob_step = 1
            st.rerun()
    with col_next:
        if st.button("Next →", type="primary", use_container_width=True):
            if not loan_type:
                st.error("Loan type is required.")
            elif loan_amount <= 0:
                st.error("Loan amount must be greater than 0.")
            else:
                st.session_state.ob_form = {
                    **st.session_state.get("ob_form", {}),
                    "loan_type":             loan_type,
                    "loan_amount_cr":        loan_amount,
                    "loan_purpose":          loan_purpose,
                    "loan_tenure_months":    tenure_months,
                    "interest_rate":         interest_rate,
                    "repayment_frequency":   repayment_frequency,
                    "collateral_type":       collateral_type or None,
                    "collateral_value_cr":   collateral_value if collateral_value > 0 else None,
                    "collateral_coverage_pct": collateral_coverage,
                }
                st.session_state.ob_step = 3
                st.rerun()


# ─── STEP 3: REVIEW & CONFIRM ─────────────────────────────────────────────────

def _step3():
    st.markdown("""
    <div style='margin-bottom:1.2rem;'>
        <div style='font-size:1rem;font-weight:600;color:var(--navy);'>Review & Confirm</div>
        <div style='font-size:0.82rem;color:var(--text-muted);margin-top:2px;'>
            Verify all details before creating the case
        </div>
    </div>
    """, unsafe_allow_html=True)

    f = st.session_state.get("ob_form", {})

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("<div class='ic-card'>", unsafe_allow_html=True)
        st.markdown("""
        <div style='font-size:0.72rem;font-weight:700;text-transform:uppercase;
                    letter-spacing:0.1em;color:var(--text-muted);margin-bottom:0.75rem;
                    padding-bottom:0.4rem;border-bottom:1px solid var(--border);'>
            Company Details
        </div>
        """, unsafe_allow_html=True)
        _review_row("Company", f.get("company_name", ""))
        _review_row("CIN", f.get("cin", ""))
        _review_row("PAN", f.get("pan", ""))
        _review_row("GSTIN", f.get("gstin", ""))
        _review_row(
            "Sector", f"{f.get('sector','')} {('· ' + f.get('sub_sector','')) if f.get('sub_sector') else ''}")
        _review_row("Turnover", f"₹ {f.get('turnover_cr', '—')} Cr")
        _review_row("Incorporated", str(f.get("incorporation_year", "")))
        st.markdown("<div style='margin-top:0.75rem;'>",
                    unsafe_allow_html=True)
        st.markdown("""
        <div style='font-size:0.72rem;font-weight:700;text-transform:uppercase;
                    letter-spacing:0.1em;color:var(--text-muted);margin:0.75rem 0 0.5rem;
                    padding-bottom:0.4rem;border-bottom:1px solid var(--border);'>
            Promoter
        </div>
        """, unsafe_allow_html=True)
        _review_row("Name", f.get("promoter_name", ""))
        _review_row("PAN", f.get("promoter_pan", ""))
        _review_row("Phone", f.get("promoter_phone", ""))
        _review_row("Email", f.get("promoter_email", ""))
        st.markdown("</div></div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div class='ic-card'>", unsafe_allow_html=True)
        st.markdown("""
        <div style='font-size:0.72rem;font-weight:700;text-transform:uppercase;
                    letter-spacing:0.1em;color:var(--text-muted);margin-bottom:0.75rem;
                    padding-bottom:0.4rem;border-bottom:1px solid var(--border);'>
            Loan Details
        </div>
        """, unsafe_allow_html=True)
        _review_row("Type", f.get("loan_type", ""))
        _review_row("Amount", f"₹ {f.get('loan_amount_cr', '—')} Cr")
        _review_row("Purpose", f.get("loan_purpose", ""))
        _review_row("Tenure", f"{f.get('loan_tenure_months', '—')} months")
        _review_row("Interest Rate", f"{f.get('interest_rate', '—')}% p.a.")
        _review_row("Repayment", f.get("repayment_frequency", ""))
        st.markdown("""
        <div style='font-size:0.72rem;font-weight:700;text-transform:uppercase;
                    letter-spacing:0.1em;color:var(--text-muted);margin:0.75rem 0 0.5rem;
                    padding-bottom:0.4rem;border-bottom:1px solid var(--border);'>
            Collateral
        </div>
        """, unsafe_allow_html=True)
        _review_row("Type", f.get("collateral_type", ""))
        _review_row("Value", f"₹ {f.get('collateral_value_cr', '—')} Cr")
        _review_row("Coverage", f"{f.get('collateral_coverage_pct', 0):.0f}%")
        st.markdown("</div>", unsafe_allow_html=True)

    # Back / Create
    st.markdown("<hr class='ic-divider'>", unsafe_allow_html=True)
    col_back, col_gap, col_create = st.columns([1.5, 4, 2])
    with col_back:
        if st.button("← Back", use_container_width=True):
            st.session_state.ob_step = 2
            st.rerun()
    with col_create:
        if st.button("✓ Create Case", type="primary", use_container_width=True):
            with st.spinner("Creating case in database..."):
                try:
                    # Build entity payload — only include non-None values
                    entity_payload = {
                        k: v for k, v in {
                            "company_name":      f.get("company_name"),
                            "cin":               f.get("cin"),
                            "pan":               f.get("pan"),
                            "sector":            f.get("sector"),
                            "sub_sector":        f.get("sub_sector"),
                            "turnover_cr":       f.get("turnover_cr"),
                            "loan_type":         f.get("loan_type"),
                            "loan_amount_cr":    f.get("loan_amount_cr"),
                            "loan_tenure_months": f.get("loan_tenure_months"),
                            "interest_rate":     f.get("interest_rate"),
                        }.items() if v is not None
                    }

                    entity_id = save_entity(entity_payload)
                    case_id = create_case(entity_id)

                    # Store in session for downstream pipeline
                    st.session_state.entity_id = entity_id
                    st.session_state.case_id = case_id
                    st.session_state.company_name = f.get("company_name")

                    # Reset form state
                    st.session_state.ob_step = 1
                    st.session_state.ob_form = {}

                    st.success(f"✅ Case created! ID: `{case_id[:8]}...`")
                    st.balloons()

                    # Route to classify page
                    import time
                    time.sleep(1)
                    st.session_state.page = "classify"
                    st.rerun()

                except Exception as e:
                    st.error(f"Failed to create case: {e}")
                    import traceback
                    traceback.print_exc()


# ─── MAIN RENDER ──────────────────────────────────────────────────────────────

def render():
    # Init step
    if "ob_step" not in st.session_state:
        st.session_state.ob_step = 1
    if "ob_form" not in st.session_state:
        st.session_state.ob_form = {}

    # Page header
    st.markdown("""
    <div class="ic-page-header">
        <div class="ic-logo-mark">📋</div>
        <div>
            <h1>New Credit Case</h1>
            <p>Onboard a new entity for AI-powered credit assessment · Codekarigars</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Step bar
    _step_bar(st.session_state.ob_step)

    # Render current step inside a card
    st.markdown("<div class='ic-card'>", unsafe_allow_html=True)

    if st.session_state.ob_step == 1:
        _step1()
    elif st.session_state.ob_step == 2:
        _step2()
    elif st.session_state.ob_step == 3:
        _step3()

    st.markdown("</div>", unsafe_allow_html=True)
