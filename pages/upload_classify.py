# pages/upload_classify.py
"""
Stage 2 of the new pipeline:
  Upload → Auto-classify (PyMuPDF, instant)
         → HITL confirm + schema edit
         → Run Extraction → extract_by_doc_type() per file
         → Render results table per doc
         → Save to Supabase
"""
import streamlit as st
import tempfile
import os
from pathlib import Path
import pandas as pd
from src.classifier import classify_document, LABEL_MAP, ALL_DOC_TYPES
from src.schemas import DocumentClassification


# ─── HELPERS ──────────────────────────────────────────────────────────────────

def confidence_badge(conf: float) -> str:
    if conf >= 0.75:
        return f"<span style='background:#E6F5EE;color:#0E7A4A;border:1px solid #A8D8C0;padding:2px 8px;border-radius:20px;font-size:0.7rem;font-weight:700;'>HIGH {conf:.0%}</span>"
    elif conf >= 0.45:
        return f"<span style='background:#FFF3E0;color:#B86A00;border:1px solid #F5C87A;padding:2px 8px;border-radius:20px;font-size:0.7rem;font-weight:700;'>MED {conf:.0%}</span>"
    else:
        return f"<span style='background:#FDEAEA;color:#B0001E;border:1px solid #F5A8B0;padding:2px 8px;border-radius:20px;font-size:0.7rem;font-weight:700;'>LOW {conf:.0%}</span>"


DEFAULT_SCHEMAS = {
    "ANNUAL_REPORT": [
        {"field": "revenue_cr",
            "description": "Total revenue / income from operations (₹ Cr)"},
        {"field": "pat_cr",
            "description": "Profit after tax (₹ Cr)"},
        {"field": "total_assets_cr",     "description": "Total assets (₹ Cr)"},
        {"field": "net_worth_cr",
            "description": "Net worth / shareholders equity (₹ Cr)"},
        {"field": "total_debt_cr",
            "description": "Total borrowings (₹ Cr)"},
        {"field": "ebitda_cr",           "description": "EBITDA (₹ Cr)"},
        {"field": "interest_expense_cr",
            "description": "Finance costs / interest paid (₹ Cr)"},
        {"field": "fy_year",
            "description": "Financial year (e.g. FY24)"},
    ],
    "ALM": [
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
        {"field": "bucket_3_6m_liab_cr",
            "description": "Liabilities maturing in 3-6 months (₹ Cr)"},
        {"field": "bucket_1yr_plus_assets_cr",
            "description": "Assets maturing beyond 1 year (₹ Cr)"},
        {"field": "bucket_1yr_plus_liab_cr",
            "description": "Liabilities maturing beyond 1 year (₹ Cr)"},
        {"field": "liquidity_gap_cr",
            "description": "Net cumulative liquidity gap (₹ Cr)"},
    ],
    "SHAREHOLDING_PATTERN": [
        {"field": "promoter_holding_pct",
            "description": "Promoter + promoter group holding (%)"},
        {"field": "public_holding_pct",
            "description": "Public / non-promoter holding (%)"},
        {"field": "fii_holding_pct",
            "description": "FII / FPI holding (%)"},
        {"field": "dii_holding_pct",
            "description": "DII / mutual fund holding (%)"},
        {"field": "pledged_shares_pct",
            "description": "% of promoter shares pledged"},
        {"field": "total_shares",
            "description": "Total paid-up shares outstanding"},
    ],
    "BORROWING_PROFILE": [
        {"field": "total_borrowings_cr",
            "description": "Total borrowings outstanding (₹ Cr)"},
        {"field": "secured_borrowings_cr",
            "description": "Secured borrowings (₹ Cr)"},
        {"field": "unsecured_borrowings_cr",
            "description": "Unsecured borrowings (₹ Cr)"},
        {"field": "ncd_outstanding_cr",
            "description": "NCDs / debentures outstanding (₹ Cr)"},
        {"field": "bank_loans_cr",
            "description": "Bank term loans outstanding (₹ Cr)"},
        {"field": "credit_rating",
            "description": "Latest credit rating (e.g. AA-, A+)"},
        {"field": "number_of_lenders",
            "description": "Total number of active lenders"},
        {"field": "debt_equity_ratio",       "description": "Debt / equity ratio"},
    ],
    "PORTFOLIO_PERFORMANCE": [
        {"field": "aum_cr",
            "description": "Total AUM / loan book (₹ Cr)"},
        {"field": "disbursements_cr",
            "description": "Disbursements in the period (₹ Cr)"},
        {"field": "gnpa_pct",
            "description": "Gross NPA % of portfolio"},
        {"field": "nnpa_pct",                  "description": "Net NPA %"},
        {"field": "collection_efficiency_pct",
            "description": "Collection efficiency (%)"},
        {"field": "par_30_pct",
            "description": "Portfolio at risk > 30 days (%)"},
        {"field": "yield_on_portfolio_pct",
            "description": "Yield on portfolio (%)"},
        {"field": "cost_of_funds_pct",
            "description": "Cost of funds (%)"},
        {"field": "nim_pct",
            "description": "Net interest margin (%)"},
    ],
    "UNKNOWN": [
        {"field": "field_1", "description": "Describe field 1"},
        {"field": "field_2", "description": "Describe field 2"},
    ]
}


# ─── EXTRACTION CARD ──────────────────────────────────────────────────────────

def _render_extraction_card(filename: str, clf, result):
    """Render extracted fields as a clean light-themed card."""
    if result is None:
        st.error(f"No data extracted from {filename}")
        return

    conf = result.extraction_confidence
    conf_color = "#0E7A4A" if conf >= 0.7 else "#B86A00" if conf >= 0.4 else "#B0001E"
    border_color = "#A8D8C0" if conf >= 0.7 else "#F5C87A" if conf >= 0.4 else "#F5A8B0"

    st.markdown(f"""
    <div class='ic-card' style='border-left:4px solid {border_color};padding:1.2rem 1.4rem;'>
        <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:0.8rem;'>
            <div>
                <div style='font-weight:600;font-size:0.92rem;color:var(--navy);'>{filename}</div>
                <div style='font-size:0.74rem;color:var(--text-muted);margin-top:2px;'>{clf.doc_type_label if clf else ""}</div>
            </div>
            <div style='font-family:JetBrains Mono,monospace;font-size:0.85rem;font-weight:700;color:{conf_color};'>
                {conf:.0%} confidence
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Build rows
    skip = {"extraction_confidence", "extraction_notes"}
    fields = []
    for field, value in result.model_dump().items():
        if field in skip or value is None:
            continue
        label = (field
                 .replace("_", " ")
                 .replace(" cr", " (₹ Cr)")
                 .replace(" pct", " (%)")
                 .title())
        if isinstance(value, float):
            formatted = f"{value:,.2f}"
        elif isinstance(value, list):
            formatted = ", ".join(str(x) for x in value) if value else "—"
        else:
            formatted = str(value)
        fields.append({"Field": label, "Extracted Value": formatted})

    if fields:
        df = pd.DataFrame(fields)
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Field":           st.column_config.TextColumn(width="medium"),
                "Extracted Value": st.column_config.TextColumn(width="medium"),
            }
        )
    else:
        st.warning("No fields extracted — document may be image-only or scanned.")

    if result.extraction_notes:
        for note in result.extraction_notes:
            st.caption(f"ℹ️ {note}")

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<hr class='ic-divider' style='margin:0.5rem 0;'>",
                unsafe_allow_html=True)


# ─── DB SAVE ──────────────────────────────────────────────────────────────────

def _save_extractions_to_db():
    case_id = st.session_state.get("case_id")
    if not case_id:
        return
    try:
        from src.database import update_case
        results = st.session_state.get("hitl_extractions", {})
        serialized = {
            fname: result.model_dump()
            for fname, result in results.items()
            if result is not None
        }
        if serialized:
            update_case(case_id, {"five_cs_json": serialized})
    except Exception as e:
        st.caption(f"ℹ️ Could not save to DB: {e}")


# ─── EXTRACTION RUNNER ────────────────────────────────────────────────────────

def _run_extraction():
    col_re, _ = st.columns([2, 6])
    with col_re:
        if st.button("🔄 Re-extract all", use_container_width=True):
            st.session_state.hitl_extractions = {}
            st.rerun()
    """Run extractors on all confirmed + classified files. Re-renders on reruns."""
    from src.extractors_v2 import extract_by_doc_type
    from src.classifier import extract_financial_text

    uploaded_files = st.session_state.get("hitl_upload_files", [])
    classifications = st.session_state.get("hitl_classifications", {})

    if not uploaded_files:
        return

    st.markdown("<hr class='ic-divider'>", unsafe_allow_html=True)
    st.markdown("<p class='ic-section-title'>Extraction Results</p>",
                unsafe_allow_html=True)

    if "hitl_extractions" not in st.session_state:
        st.session_state.hitl_extractions = {}

    for uf in uploaded_files:
        clf = classifications.get(uf.name)
        if not clf or clf.doc_type == "UNKNOWN":
            st.warning(f"⚠️ Skipping {uf.name} — classified as UNKNOWN.")
            continue

        # Already extracted — just re-render, no work needed
        if uf.name in st.session_state.hitl_extractions:
            _render_extraction_card(
                uf.name, clf,
                st.session_state.hitl_extractions[uf.name]
            )
            continue

        # Run extraction
        with st.spinner(f"Extracting {clf.doc_type_label} from {uf.name}..."):
            suffix = Path(uf.name).suffix
            uf.seek(0)
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uf.read())
                tmp_path = tmp.name
            uf.seek(0)

            result = None
            try:
                text = extract_financial_text(tmp_path, max_chars=8000)
                print(
                    f"[EXTRACT] {uf.name} → {clf.doc_type}, text={len(text)} chars")
                result = extract_by_doc_type(clf.doc_type, text, tables=None)
                print(
                    f"[EXTRACT] Done: confidence={result.extraction_confidence:.0%}, notes={result.extraction_notes}")
            except Exception as e:
                import traceback
                traceback.print_exc()
                st.error(f"Extraction failed for {uf.name}: {e}")
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

            st.session_state.hitl_extractions[uf.name] = result

        _render_extraction_card(uf.name, clf, result)

    _save_extractions_to_db()


# ─── MAIN RENDER ──────────────────────────────────────────────────────────────

def render():
    print("[UPLOAD_CLASSIFY] render() called")

    st.markdown("<p class='ic-section-title'>Document Upload & Classification</p>",
                unsafe_allow_html=True)
    st.caption(
        "Upload up to 5 documents. The AI will auto-classify each one — review and confirm before extraction.")

    # ── Stage 1: Upload ───────────────────────────────────────────────────────
    uploaded_files = st.file_uploader(
        "Upload documents (PDF, Excel, Word)",
        type=["pdf", "xlsx", "xls", "docx"],
        accept_multiple_files=True,
        key="hitl_uploader"
    )

    if not uploaded_files:
        st.markdown("""
        <div class='ic-card' style='text-align:center;padding:2.5rem;'>
            <div style='font-size:2rem;margin-bottom:0.5rem;'>📂</div>
            <div style='font-weight:600;color:var(--text-sec);'>No files uploaded yet</div>
            <div style='font-size:0.82rem;color:var(--text-muted);margin-top:0.25rem;'>
                Upload ALM, Shareholding Pattern, Borrowing Profile, Annual Report, or Portfolio data
            </div>
        </div>
        """, unsafe_allow_html=True)
        # Clear stale state when user removes all files
        for key in ["classified_files", "file_schemas", "hitl_confirmed",
                    "hitl_extractions", "hitl_upload_files", "hitl_classifications",
                    "hitl_schemas", "run_extraction"]:
            st.session_state.pop(key, None)
        return

    # ── Stage 2: Session state init ───────────────────────────────────────────
    for key in ["classified_files", "file_schemas", "hitl_confirmed"]:
        if key not in st.session_state:
            st.session_state[key] = {}

    # ── Stage 3: Auto-classify new files ─────────────────────────────────────
    new_files = [
        f for f in uploaded_files if f.name not in st.session_state.classified_files]

    if new_files:
        with st.spinner(f"🔍 Classifying {len(new_files)} file(s)..."):
            for uf in new_files:
                print(f"[CLASSIFY] Starting: {uf.name}")
                suffix = Path(uf.name).suffix

                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(uf.read())
                    tmp_path = tmp.name
                uf.seek(0)

                try:
                    from src.classifier import extract_financial_text, classify_document
                    text = extract_financial_text(tmp_path, max_chars=12000)
                    print(
                        f"[CLASSIFY] Text length: {len(text)}, preview: {text[:100]!r}")
                    classification = classify_document(uf.name, text)
                    print(
                        f"[CLASSIFY] → {classification.doc_type} ({classification.confidence:.0%})")
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    classification = DocumentClassification(
                        doc_type="UNKNOWN",
                        doc_type_label=LABEL_MAP["UNKNOWN"],
                        confidence=0.0,
                        reasoning=f"Error: {str(e)[:80]}",
                        key_signals=[]
                    )
                finally:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass

                st.session_state.classified_files[uf.name] = classification
                st.session_state.file_schemas[uf.name] = [
                    dict(row) for row in DEFAULT_SCHEMAS.get(
                        classification.doc_type, DEFAULT_SCHEMAS["UNKNOWN"]
                    )
                ]
                st.session_state.hitl_confirmed[uf.name] = False
                print(f"[CLASSIFY] Saved to session: {uf.name}")

    # ── Stage 4: HITL review panel ────────────────────────────────────────────
    st.markdown("<hr class='ic-divider'>", unsafe_allow_html=True)
    st.markdown("<p class='ic-section-title'>Step 1 — Review & confirm classifications</p>",
                unsafe_allow_html=True)

    all_confirmed = True
    for uf in uploaded_files:
        clf = st.session_state.classified_files.get(uf.name)
        if not clf:
            continue

        confirmed = st.session_state.hitl_confirmed.get(uf.name, False)
        card_border = "border-left:4px solid var(--approve);" if confirmed else "border-left:4px solid var(--steel);"

        st.markdown(
            f"<div class='ic-card' style='{card_border}padding:1.1rem 1.4rem;'>", unsafe_allow_html=True)

        col_name, col_badge, col_type, col_action = st.columns(
            [3, 1.2, 3, 1.5])

        with col_name:
            st.markdown(f"""
            <div style='font-weight:600;font-size:0.9rem;color:var(--navy);'>{uf.name}</div>
            <div style='font-size:0.73rem;color:var(--text-muted);margin-top:2px;'>{uf.size//1024} KB</div>
            """, unsafe_allow_html=True)

        with col_badge:
            st.markdown(confidence_badge(clf.confidence),
                        unsafe_allow_html=True)
            if clf.key_signals:
                st.markdown(
                    f"<div style='font-size:0.68rem;color:var(--text-muted);margin-top:4px;'>"
                    f"{', '.join(clf.key_signals[:2])}</div>",
                    unsafe_allow_html=True
                )

        with col_type:
            current_idx = ALL_DOC_TYPES.index(
                clf.doc_type) if clf.doc_type in ALL_DOC_TYPES else len(ALL_DOC_TYPES) - 1
            options_labels = [LABEL_MAP[t] for t in ALL_DOC_TYPES]
            selected_label = st.selectbox(
                "Type", options_labels,
                index=current_idx,
                key=f"type_{uf.name}",
                label_visibility="collapsed"
            )
            selected_type = ALL_DOC_TYPES[options_labels.index(selected_label)]

            # User changed the type manually
            if selected_type != clf.doc_type:
                clf.doc_type = selected_type
                clf.doc_type_label = LABEL_MAP[selected_type]
                clf.user_override = selected_type
                clf.confidence = 1.0
                st.session_state.classified_files[uf.name] = clf
                st.session_state.file_schemas[uf.name] = [
                    dict(row) for row in DEFAULT_SCHEMAS.get(selected_type, DEFAULT_SCHEMAS["UNKNOWN"])
                ]
                st.session_state.hitl_confirmed[uf.name] = False
                # Remove stale extraction if type changed
                st.session_state.get("hitl_extractions", {}).pop(uf.name, None)
                st.rerun()

            st.markdown(
                f"<div style='font-size:0.72rem;color:var(--text-muted);margin-top:4px;font-style:italic;'>"
                f"{clf.reasoning}</div>",
                unsafe_allow_html=True
            )

        with col_action:
            if not confirmed:
                if st.button("✓ Confirm", key=f"confirm_{uf.name}", type="primary", use_container_width=True):
                    st.session_state.hitl_confirmed[uf.name] = True
                    clf.user_confirmed = True
                    st.session_state.classified_files[uf.name] = clf
                    st.rerun()
            else:
                st.markdown(
                    "<div style='color:var(--approve);font-weight:600;font-size:0.85rem;padding-top:0.4rem;'>✓ Confirmed</div>",
                    unsafe_allow_html=True
                )
                if st.button("Edit", key=f"edit_{uf.name}", use_container_width=True):
                    st.session_state.hitl_confirmed[uf.name] = False
                    st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

        if not confirmed:
            all_confirmed = False

    # ── Stage 5: Schema editor (only when all confirmed) ─────────────────────
    if all_confirmed and uploaded_files:
        st.markdown("<hr class='ic-divider'>", unsafe_allow_html=True)
        st.markdown(
            "<p class='ic-section-title'>Step 2 — Review extraction schema (optional)</p>", unsafe_allow_html=True)
        st.caption(
            "These are the fields that will be extracted from each document. Add, remove, or rename as needed.")

        for uf in uploaded_files:
            clf = st.session_state.classified_files.get(uf.name)
            if not clf:
                continue
            with st.expander(f"📄 {uf.name}  —  {clf.doc_type_label}", expanded=False):
                schema_df = pd.DataFrame(
                    st.session_state.file_schemas[uf.name])
                edited_df = st.data_editor(
                    schema_df,
                    key=f"schema_{uf.name}",
                    num_rows="dynamic",
                    use_container_width=True,
                    column_config={
                        "field":       st.column_config.TextColumn("Field Name", width="medium"),
                        "description": st.column_config.TextColumn("Description", width="large"),
                    }
                )
                st.session_state.file_schemas[uf.name] = edited_df.to_dict(
                    "records")

        # Run extraction button
        st.markdown("<hr class='ic-divider'>", unsafe_allow_html=True)
        col_btn, _ = st.columns([2, 6])
        with col_btn:
            if st.button("▶  Run Extraction & Analysis", type="primary", use_container_width=True):
                # Package state for extraction
                st.session_state["hitl_upload_files"] = uploaded_files
                st.session_state["hitl_classifications"] = st.session_state.classified_files
                st.session_state["hitl_schemas"] = st.session_state.file_schemas
                st.session_state["run_extraction"] = True
                st.rerun()

    elif not all_confirmed and uploaded_files:
        st.info("⬆️ Confirm all classifications above to proceed to the schema editor.")

    # ── Stage 6: Run or re-render extraction results ──────────────────────────
    if st.session_state.get("run_extraction") and st.session_state.get("hitl_upload_files"):
        st.session_state["run_extraction"] = False  # reset flag immediately
        _run_extraction()
    elif st.session_state.get("hitl_extractions") and st.session_state.get("hitl_upload_files"):
        # Reruns after extraction — just re-render, no re-processing
        _run_extraction()
