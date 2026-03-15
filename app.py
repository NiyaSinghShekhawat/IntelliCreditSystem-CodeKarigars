from datetime import datetime
import os
import tempfile
import streamlit as st
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="IntelliCredit — AI Credit Engine",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── GLOBAL CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── FIX 1: All CSS variables in ONE :root block ── */
:root {
    --bg:         #0A0E1A;
    --surface:    #0D1226;
    --surface-2:  #111830;
    --surface-3:  #161E38;
    --border:     #1E2A4A;
    --border-2:   #243052;
    --navy:       #1A237E;
    --navy-light: #283593;
    --blue:       #1565C0;
    --blue-light: #1976D2;
    --steel:      #42A5F5;
    --steel-dim:  #1E88E5;
    --teal:       #00BFA5;
    --teal-dim:   #00897B;
    --gold:       #C9970A;
    --gold-light: #E8B020;
    --text:       #F0F2FF;
    --text-sec:   #C5CAE9;
    --text-muted: #7986CB;
    --text-hint:  #5C6BC0;
    --approve:    #00E676;
    --approve-bg: #0A2218;
    --approve-bd: #1B5E20;
    --warn:       #FFD740;
    --warn-bg:    #1A1400;
    --warn-bd:    #F57F17;
    --reject:     #FF5252;
    --reject-bg:  #1A0000;
    --reject-bd:  #B71C1C;
    --info:       #40C4FF;
    --info-bg:    #001829;
    --info-bd:    #0277BD;
}

/* ── Base ── */
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; color: var(--text) !important; background: var(--bg) !important; }
.stApp { background: var(--bg) !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2.5rem 3rem !important; max-width: 1440px !important; }
p, span, li { color: var(--text) !important; }
h1, h2, h3, h4, h5, h6 { color: var(--text) !important; }
.stMarkdown p, .stMarkdown li { color: var(--text) !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--surface); }
::-webkit-scrollbar-thumb { background: var(--border-2); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--steel-dim); }

/* ── Sidebar ── */
[data-testid="stSidebar"] { background: var(--surface) !important; border-right: 1px solid var(--border) !important; }
[data-testid="stSidebar"] * { color: var(--text-sec) !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: var(--text) !important; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] div, [data-testid="stSidebar"] label { color: #C5CAE9 !important; }
[data-testid="stSidebar"] label { font-size: 0.72rem !important; letter-spacing: 0.08em !important; text-transform: uppercase !important; }
[data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea { background: var(--surface-3) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; color: var(--text) !important; }
[data-testid="stSidebar"] hr { border-color: var(--border) !important; }
[data-testid="stSidebar"] .stButton > button { background: var(--surface-3) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; color: var(--text-sec) !important; font-size: 0.84rem !important; font-weight: 500 !important; width: 100% !important; padding: 0.55rem 1rem !important; transition: all 0.2s !important; text-align: left !important; }
[data-testid="stSidebar"] .stButton > button:hover { background: var(--navy) !important; border-color: var(--blue-light) !important; color: var(--text) !important; }
[data-testid="stSidebar"] [data-baseweb="select"] > div { background: var(--surface-3) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; color: var(--text) !important; }
[data-testid="stSidebar"] [data-baseweb="select"] span { color: var(--text) !important; }
[data-testid="stSidebar"] .stNumberInput > div { background: var(--surface-3) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; }
[data-testid="stSidebar"] .stNumberInput input { color: var(--text) !important; background: transparent !important; border: none !important; }
[data-testid="stSidebar"] .stNumberInput button { background: var(--surface-2) !important; border: none !important; color: var(--text-sec) !important; }

/* ── Main buttons ── */
.stButton > button { background: linear-gradient(135deg, var(--navy), var(--blue)) !important; color: var(--gold-light) !important; border: 1px solid var(--blue-light) !important; border-radius: 10px !important; font-family: 'DM Sans', sans-serif !important; font-weight: 700 !important; font-size: 0.9rem !important; letter-spacing: 0.04em !important; padding: 0.6rem 1.4rem !important; box-shadow: 0 4px 12px rgba(26,35,126,0.4) !important; transition: all 0.2s !important; }
.stButton > button:hover { background: linear-gradient(135deg, var(--navy-light), var(--blue-light)) !important; box-shadow: 0 6px 18px rgba(26,35,126,0.6) !important; }
.stButton > button:disabled { background: var(--surface-3) !important; color: var(--text-muted) !important; border-color: var(--border) !important; box-shadow: none !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 10px !important; padding: 4px !important; gap: 4px !important; }
.stTabs [data-baseweb="tab"] { background: transparent !important; color: var(--text-sec) !important; border-radius: 7px !important; font-family: 'DM Sans', sans-serif !important; font-weight: 500 !important; font-size: 0.88rem !important; padding: 0.45rem 1.1rem !important; transition: all 0.2s !important; }
.stTabs [aria-selected="true"] { background: var(--navy) !important; color: var(--gold-light) !important; }

/* ── Form inputs ── */
.stTextInput input, .stTextArea textarea, .stNumberInput input { background: var(--surface-2) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; color: var(--text) !important; font-family: 'DM Sans', sans-serif !important; }
.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus { border-color: var(--steel) !important; box-shadow: 0 0 0 3px rgba(66,165,245,0.15) !important; }
.stTextInput label, .stTextArea label, .stSelectbox label, .stNumberInput label, .stSlider label, .stFileUploader label, .stCheckbox label { color: var(--text-sec) !important; font-size: 0.80rem !important; font-weight: 500 !important; letter-spacing: 0.04em !important; }
.stNumberInput input { color: var(--text) !important; }

/* ── Selectbox ── */
[data-baseweb="select"] > div { background: var(--surface-2) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; color: var(--text) !important; }
[data-baseweb="select"] span { color: var(--text) !important; }
[data-baseweb="select"] [data-testid="stMarkdown"] p, [data-baseweb="select"] div { color: var(--text) !important; }
[data-baseweb="popover"] > div { background: var(--surface-2) !important; border: 1px solid var(--border) !important; }
[role="option"] { background: var(--surface-2) !important; color: var(--text-sec) !important; }
[role="option"]:hover { background: var(--navy) !important; color: var(--text) !important; }

/* ── Slider / Checkbox ── */
[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] { background: var(--steel) !important; border-color: var(--steel) !important; }
[data-testid="stSlider"] [data-testid="stTickBarMin"], [data-testid="stSlider"] [data-testid="stTickBarMax"] { color: #7986CB !important; }
[data-testid="stCheckbox"] span { border-color: var(--border) !important; border-radius: 4px !important; }
[data-testid="stCheckbox"] input:checked + span { background: var(--blue) !important; border-color: var(--steel) !important; }

/* ── Metrics ── */
[data-testid="metric-container"] { background: linear-gradient(135deg, var(--surface), var(--surface-2)) !important; border: 1px solid var(--border) !important; border-radius: 12px !important; padding: 1rem 1.2rem !important; box-shadow: 0 4px 16px rgba(0,0,0,0.3) !important; }
[data-testid="metric-container"] label { color: #C5CAE9 !important; font-size: 0.72rem !important; text-transform: uppercase !important; letter-spacing: 0.08em !important; font-weight: 600 !important; }
[data-testid="metric-container"] [data-testid="stMetricValue"] { color: var(--gold-light) !important; font-size: 1.6rem !important; font-weight: 700 !important; font-family: 'JetBrains Mono', monospace !important; }

/* ── Alerts ── */
.stAlert { border-radius: 10px !important; }
div[data-testid="stNotification"] { background: var(--surface-2) !important; border: 1px solid var(--border) !important; border-radius: 10px !important; }
.stAlert p, .stAlert div, div[data-testid="stNotification"] p { color: var(--text) !important; }

/* ── Expanders ── */
.stExpander { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 10px !important; }
.stExpander summary, .stExpander summary * { color: #C5CAE9 !important; font-weight: 500 !important; }
.stExpander summary:hover { color: var(--text) !important; }
details[open] .stExpander > div, .stExpander [data-testid="stExpanderDetails"] * { color: var(--text) !important; }

/* ── Download buttons ── */
.stDownloadButton > button { background: var(--surface-2) !important; color: var(--steel) !important; border: 1.5px solid var(--border) !important; border-radius: 8px !important; font-weight: 500 !important; }
.stDownloadButton > button:hover { background: var(--surface-3) !important; border-color: var(--steel) !important; color: var(--text) !important; }

/* ── File uploader ── */
[data-testid="stFileUploader"] { background: transparent !important; }
[data-testid="stFileUploadDropzone"] { background: var(--surface-2) !important; border: 1.5px dashed var(--border-2) !important; border-radius: 10px !important; color: var(--text-sec) !important; }
[data-testid="stFileUploadDropzone"]:hover { border-color: var(--steel) !important; background: var(--surface-3) !important; }
[data-testid="stFileUploadDropzone"] span { color: var(--text-sec) !important; }
[data-testid="stFileUploadDropzone"] button { background: var(--navy) !important; color: var(--gold-light) !important; border: 1px solid var(--blue-light) !important; border-radius: 6px !important; font-size: 0.8rem !important; }
[data-testid="stFileUploaderFileName"] { color: var(--steel) !important; font-size: 0.82rem !important; }

/* ── Data editor ── */
[data-testid="stDataEditor"] { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 8px !important; }
[data-testid="stDataEditor"] * { color: var(--text) !important; }
[data-testid="stDataEditor"] th { background: var(--surface-3) !important; color: var(--text-sec) !important; font-size: 0.72rem !important; font-weight: 700 !important; text-transform: uppercase !important; letter-spacing: 0.07em !important; }
[data-testid="stDataEditor"] td { color: var(--text) !important; background: var(--surface) !important; border-color: var(--border) !important; }
[data-testid="stDataEditor"] input { color: var(--text) !important; background: var(--surface-2) !important; }
[data-testid="stDataFrame"] * { color: var(--text) !important; }
[data-testid="stDataFrame"] th { background: var(--surface-3) !important; color: var(--text-sec) !important; }

/* ── Caption / Spinner ── */
.stCaption, [data-testid="stCaptionContainer"] p { color: #7986CB !important; font-size: 0.78rem !important; }
[data-testid="stSpinner"] p, div[data-testid="stSpinner"] > div > p { color: var(--text-sec) !important; font-size: 0.9rem !important; }

/* ── Custom Components ── */
.ic-page-header { display: flex; align-items: center; gap: 1rem; padding: 1.4rem 1.8rem; background: linear-gradient(135deg, var(--surface), var(--surface-2)); border: 1px solid var(--border); border-radius: 14px; margin-bottom: 1.5rem; box-shadow: 0 4px 20px rgba(0,0,0,0.4); }
.ic-logo-mark { width: 44px; height: 44px; background: var(--navy); border: 1px solid var(--blue-light); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 1.3rem; flex-shrink: 0; }
.ic-page-header h1 { font-family: 'DM Serif Display', serif !important; font-size: 1.5rem !important; color: var(--text) !important; margin: 0 !important; line-height: 1.2 !important; }
.ic-page-header p { font-size: 0.82rem !important; color: var(--text-muted) !important; margin: 2px 0 0 !important; }
.ic-badge-row { display: flex; gap: 6px; margin-top: 6px; flex-wrap: wrap; }
.ic-badge { font-size: 0.68rem; font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase; padding: 2px 8px; border-radius: 20px; background: var(--surface-3); border: 1px solid var(--border); color: #C5CAE9; }
.ic-section-title { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #7986CB !important; margin: 0 0 0.75rem; padding-bottom: 0.5rem; border-bottom: 1px solid var(--border); }
.ic-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.4rem; margin-bottom: 1rem; box-shadow: 0 4px 16px rgba(0,0,0,0.3); }
.ic-card, .ic-card * { color: var(--text) !important; }
.ic-upload-zone { border: none !important; padding: 0 !important; margin-bottom: 0.75rem !important; background: transparent !important; }
.ic-upload-label { font-size: 0.78rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.07em; color: var(--text-sec); margin-bottom: 2px; display: block; }
.ic-upload-desc { font-size: 0.74rem; color: var(--text-muted); margin-bottom: 0.5rem; display: block; }
.ic-divider { border: none; border-top: 1px solid var(--border); margin: 1.2rem 0; }

.decision-approve { background: var(--approve-bg); border: 1px solid var(--approve-bd); border-left: 5px solid var(--approve); padding: 1rem 1.4rem; border-radius: 10px; font-size: 1.15rem; font-weight: 700; color: var(--approve); margin-bottom: 0.75rem; font-family: 'DM Sans', sans-serif; box-shadow: 0 4px 20px rgba(0,230,118,0.15); }
.decision-reject { background: var(--reject-bg); border: 1px solid var(--reject-bd); border-left: 5px solid var(--reject); padding: 1rem 1.4rem; border-radius: 10px; font-size: 1.15rem; font-weight: 700; color: var(--reject); margin-bottom: 0.75rem; font-family: 'DM Sans', sans-serif; box-shadow: 0 4px 20px rgba(255,82,82,0.15); }
.decision-conditional { background: var(--warn-bg); border: 1px solid var(--warn-bd); border-left: 5px solid var(--warn); padding: 1rem 1.4rem; border-radius: 10px; font-size: 1.15rem; font-weight: 700; color: var(--warn); margin-bottom: 0.75rem; font-family: 'DM Sans', sans-serif; box-shadow: 0 4px 20px rgba(255,215,64,0.15); }
.decisive-factor { background: var(--info-bg); border-left: 4px solid var(--steel); padding: 0.7rem 1.1rem; border-radius: 8px; margin: 0 0 1rem; font-size: 0.88rem; color: var(--text); }
.decisive-factor strong { color: var(--gold-light); font-weight: 700; }
.warning-box { background: var(--warn-bg); border-left: 3px solid var(--warn); padding: 0.65rem 1rem; border-radius: 6px; margin: 0.3rem 0; color: var(--warn); font-size: 0.85rem; }
.flag-box { background: var(--reject-bg); border-left: 3px solid var(--reject); padding: 0.65rem 1rem; border-radius: 6px; margin: 0.3rem 0; color: var(--reject); font-size: 0.85rem; }
.news-negative { background: var(--reject-bg); border-left: 3px solid var(--reject); padding: 0.55rem 0.85rem; border-radius: 6px; margin: 0.3rem 0; font-size: 0.83rem; color: var(--reject); }
.news-positive { background: var(--approve-bg); border-left: 3px solid var(--approve); padding: 0.55rem 0.85rem; border-radius: 6px; margin: 0.3rem 0; font-size: 0.83rem; color: var(--approve); }

.dash-metric { background: linear-gradient(135deg, var(--surface), var(--surface-2)); border: 1px solid var(--border); border-radius: 12px; padding: 1rem 1.2rem; box-shadow: 0 4px 16px rgba(0,0,0,0.3); }
.dm-label { font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); margin-bottom: 4px; }
.dm-value { font-family: 'JetBrains Mono', monospace; font-size: 1.6rem; font-weight: 700; color: var(--gold-light); line-height: 1.1; }
.dash-col-header { font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #7986CB !important; padding-bottom: 0.5rem; border-bottom: 1px solid var(--border); margin-bottom: 0.5rem; }

.badge { display: inline-block; font-size: 0.68rem; font-weight: 700; letter-spacing: 0.07em; text-transform: uppercase; padding: 3px 9px; border-radius: 20px; }
.badge-approve  { background: var(--approve-bg); color: var(--approve); border: 1px solid var(--approve-bd); }
.badge-reject   { background: var(--reject-bg);  color: var(--reject);  border: 1px solid var(--reject-bd); }
.badge-warn     { background: var(--warn-bg);     color: var(--warn);    border: 1px solid var(--warn-bd); }
.badge-progress { background: var(--info-bg);     color: var(--info);    border: 1px solid var(--info-bd); }

.step-bar { display: flex; gap: 0; margin-bottom: 1.5rem; border-radius: 8px; overflow: hidden; border: 1px solid var(--border); }
.step-item { flex: 1; padding: 0.6rem 0.8rem; font-size: 0.78rem; font-weight: 500; text-align: center; background: var(--surface-2); color: #7986CB !important; border-right: 1px solid var(--border); letter-spacing: 0.03em; }
.step-item:last-child { border-right: none; }
.step-item.active { background: var(--navy); color: var(--gold-light) !important; font-weight: 600; }
.step-item.done   { background: var(--approve-bg); color: var(--approve) !important; font-weight: 600; }

.sidebar-brand { padding: 1.2rem 0 1rem; border-bottom: 1px solid var(--border); margin-bottom: 1rem; }
.brand-name { font-family: 'DM Serif Display', serif; font-size: 1.3rem; color: var(--gold); letter-spacing: 0.02em; }
.brand-sub  { font-size: 0.68rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.1em; margin-top: 2px; }

.ic-extract-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.ic-extract-table th { background: var(--surface-3); color: var(--text-sec); font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; padding: 0.6rem 1rem; text-align: left; border-bottom: 1px solid var(--border); }
.ic-extract-table td { padding: 0.55rem 1rem; color: var(--text); border-bottom: 1px solid var(--border); }
.ic-extract-table tr:last-child td { border-bottom: none; }
.ic-extract-table td:first-child { color: var(--text-sec); font-weight: 500; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; }
.ic-extract-table td:last-child { color: var(--steel); font-weight: 600; font-family: 'JetBrains Mono', monospace; }
</style>
""", unsafe_allow_html=True)

# ─── SESSION STATE ────────────────────────────────────────────────────────────
for key, default in {
    "page": "dashboard", "entity_id": None, "case_id": None,
    "onboard_step": 1, "demo": {}, "analysis_result": None,
    "switch_to_results": False, "swot_result": None,
    "auto_run_analysis": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
demo = st.session_state.get("demo", {})

with st.sidebar:
    st.markdown("""
    <div class="sidebar-brand">
        <div class="brand-name">IntelliCredit</div>
        <div class="brand-sub">AI Credit Intelligence · v2.0</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🏠  Officer Dashboard",  use_container_width=True):
        st.session_state.page = "dashboard"
        st.rerun()
    if st.button("📋  New Case",            use_container_width=True):
        st.session_state.page = "onboarding"
        st.session_state.ob_success = False
        st.rerun()
    if st.button("📂  Upload & Classify",   use_container_width=True):
        st.session_state.page = "classify"
        st.rerun()
    if st.button("➕  Run Analysis",        use_container_width=True):
        st.session_state.page = "analysis"
        st.rerun()

    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.72rem;color:#3A5A7A;line-height:1.7;'>"
        "<strong style='color:#5A8AAA;'>IntelliCredit v2.0</strong><br>"
        "Groq LLaMA 3.3 70B · XGBoost + SHAP<br>"
        "Docling · ChromaDB · Supabase<br>"
        "<span style='color:#2A4A6A;'>Codekarigars · Vivriti Capital</span>"
        "</div>",
        unsafe_allow_html=True
    )


# ─── ENGINE LOADER ────────────────────────────────────────────────────────────
@st.cache_resource
def load_engines():
    from src.parser import DocumentParser
    from src.extractor import FinancialExtractor
    from src.reconciler import GSTReconciler
    from src.researcher import ResearchAgent
    from src.risk_engine import RiskEngine
    from src.five_cs import FiveCsAnalyzer
    from src.agent import CreditAgent
    from src.cam_generator import CAMGenerator
    return {
        "parser":      DocumentParser(),
        "extractor":   FinancialExtractor(),
        "reconciler":  GSTReconciler(),
        "researcher":  ResearchAgent(),
        "risk_engine": RiskEngine(),
        "five_cs":     FiveCsAnalyzer(),
        "agent":       CreditAgent(),
        "cam":         CAMGenerator(),
    }


# ─── DASHBOARD ────────────────────────────────────────────────────────────────
def render_dashboard():
    try:
        from src.database import get_all_cases
        cases = get_all_cases()
    except Exception:
        cases = []

    st.markdown("""
    <div class="ic-page-header">
        <div class="ic-logo-mark">🏦</div>
        <div>
            <h1>Officer Dashboard</h1>
            <p>Active and completed credit assessment cases · Codekarigars</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    total = len(cases)
    approved = sum(1 for c in cases if c.get("decision") == "APPROVE")
    conditional = sum(1 for c in cases if c.get("decision") == "CONDITIONAL")
    rejected = sum(1 for c in cases if c.get("decision") == "REJECT")
    in_progress = sum(1 for c in cases if c.get("status") == "IN_PROGRESS")

    c1, c2, c3, c4, c5 = st.columns(5)
    for col, (lbl, val, clr) in zip([c1, c2, c3, c4, c5], [
        ("Total Cases",  total,       "#F0F2FF"),
        ("In Progress",  in_progress, "#42A5F5"),
        ("Approved",     approved,    "#00E676"),
        ("Conditional",  conditional, "#FFD740"),
        ("Rejected",     rejected,    "#FF5252"),
    ]):
        with col:
            st.markdown(f"<div class='dash-metric'><div class='dm-label'>{lbl}</div>"
                        f"<div class='dm-value' style='color:{clr};'>{val}</div></div>",
                        unsafe_allow_html=True)

    st.markdown("<hr class='ic-divider'>", unsafe_allow_html=True)

    fc1, fc2, fc3 = st.columns([2, 2, 4])
    with fc1:
        filter_dec = st.selectbox("Decision", ["All", "APPROVE", "CONDITIONAL", "REJECT", "IN PROGRESS"],
                                  label_visibility="collapsed")
    with fc2:
        sectors = ["All Sectors"] + sorted(set(
            c.get("entities", {}).get("sector", "") for c in cases
            if c.get("entities", {}).get("sector")
        ))
        filter_sec = st.selectbox(
            "Sector", sectors, label_visibility="collapsed")
    with fc3:
        if st.button("📋  New Case", type="primary"):
            st.session_state.page = "onboarding"
            st.session_state.ob_success = False
            st.rerun()

    filtered = [c for c in cases if
                (filter_dec == "All" or
                 (filter_dec == "IN PROGRESS" and c.get("status") == "IN_PROGRESS") or
                 c.get("decision") == filter_dec) and
                (filter_sec == "All Sectors" or c.get("entities", {}).get("sector") == filter_sec)]

    st.markdown(f"<p style='font-size:0.78rem;color:var(--text-muted);margin-bottom:0.6rem;'>"
                f"{len(filtered)} case(s)</p>", unsafe_allow_html=True)

    if not filtered:
        st.markdown("<div class='ic-card' style='text-align:center;padding:3rem;'>"
                    "<div style='font-size:2.5rem;margin-bottom:0.75rem;'>📂</div>"
                    "<div style='font-weight:600;color:var(--text-sec);'>No cases found</div>"
                    "<div style='font-size:0.85rem;color:var(--text-muted);margin-top:0.3rem;'>"
                    "Create a new case to get started</div></div>", unsafe_allow_html=True)
        return

    h1, h2, h3, h4, h5, h6 = st.columns([3, 2, 1.5, 1.5, 1.5, 1.2])
    for col, lbl in zip([h1, h2, h3, h4, h5, h6],
                        ["Company", "Sector", "Loan Amount", "Risk Score", "Decision", "Action"]):
        col.markdown(
            f"<div class='dash-col-header'>{lbl}</div>", unsafe_allow_html=True)

    for case in filtered:
        entity = case.get("entities") or {}
        c1, c2, c3, c4, c5, c6 = st.columns([3, 2, 1.5, 1.5, 1.5, 1.2])
        with c1:
            st.markdown(f"<div style='font-weight:600;font-size:0.9rem;color:var(--text);'>"
                        f"{entity.get('company_name','—')}</div>"
                        f"<div style='font-size:0.73rem;color:var(--text-muted);"
                        f"font-family:JetBrains Mono,monospace;'>{entity.get('loan_type','')}</div>",
                        unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div style='font-size:0.85rem;color:var(--text-sec);'>"
                        f"{entity.get('sector','—')}</div>", unsafe_allow_html=True)
        with c3:
            amt = entity.get('loan_amount_cr')
            st.markdown(f"<div style='font-family:JetBrains Mono,monospace;font-size:0.85rem;"
                        f"color:var(--text);'>{'₹'+str(amt)+' Cr' if amt else '—'}</div>",
                        unsafe_allow_html=True)
        with c4:
            score = case.get("risk_score")
            clr = "#00E676" if score and score < 0.35 else "#FFD740" if score and score < 0.65 else "#FF5252" if score else "var(--text-muted)"
            st.markdown(f"<div style='font-family:JetBrains Mono,monospace;font-size:0.88rem;"
                        f"font-weight:700;color:{clr};'>{'%.3f'%score if score else '—'}</div>",
                        unsafe_allow_html=True)
        with c5:
            dec = (case.get("decision") or "").upper()
            status = case.get("status", "")
            if status == "IN_PROGRESS":
                badge = "<span class='badge badge-progress'>In Progress</span>"
            elif dec == "APPROVE":
                badge = "<span class='badge badge-approve'>Approve</span>"
            elif dec == "CONDITIONAL":
                badge = "<span class='badge badge-warn'>Conditional</span>"
            elif dec == "REJECT":
                badge = "<span class='badge badge-reject'>Reject</span>"
            else:
                badge = "<span class='badge badge-progress'>Pending</span>"
            st.markdown(badge, unsafe_allow_html=True)
        with c6:
            if st.button("Open →", key=f"open_{case['id']}"):
                st.session_state.entity_id = case.get("entity_id")
                st.session_state.case_id = case["id"]
                st.session_state.page = "case_view"
                st.rerun()
        st.markdown("<hr class='ic-divider' style='margin:0.4rem 0;'>",
                    unsafe_allow_html=True)


# ─── ANALYSIS PAGE ────────────────────────────────────────────────────────────
def render_analysis():
    # ── Pull context from session state (set by onboarding) ──────────────────
    company_name = st.session_state.get("company_name", "")
    ob_form = st.session_state.get("ob_form", {})
    promoter_name = ob_form.get("promoter_name", "")
    loan_amount_cr = float(ob_form.get("loan_amount_cr") or 0)
    loan_amount_requested = int(
        loan_amount_cr * 1e7) if loan_amount_cr > 0 else 2500000
    loan_purpose = ob_form.get("loan_purpose", "Working Capital")
    use_mock_research = True
    mock_risk_level = "medium"

    # Guard — no company loaded
    if not company_name:
        st.markdown("""
        <div class='ic-card' style='text-align:center;padding:3rem;'>
            <div style='font-size:2.5rem;margin-bottom:0.75rem;'>🔍</div>
            <div style='font-weight:600;font-size:1rem;color:var(--text-sec);'>No case loaded</div>
            <div style='font-size:0.85rem;color:var(--text-muted);margin-top:0.3rem;'>
                Create a case first via <strong>📋 New Case</strong> in the sidebar,
                then upload documents and continue to analysis.
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.session_state.get("auto_run_analysis"):
            st.session_state["auto_run_analysis"] = False
        return

    st.markdown(f"""
    <div class="ic-page-header">
        <div class="ic-logo-mark">🔍</div>
        <div>
            <h1>Credit Analysis — {company_name}</h1>
            <p>AI-powered appraisal · GST reconciliation · Five Cs · XGBoost + SHAP</p>
            <div class="ic-badge-row">
                <span class="ic-badge">Groq LLaMA 3.3 70B</span>
                <span class="ic-badge">XGBoost + SHAP</span>
                <span class="ic-badge">Docling Parser</span>
                <span class="ic-badge">ChromaDB RAG</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Auto-run from Upload & Classify continue button
    auto_run = st.session_state.get("auto_run_analysis", False)
    if auto_run:
        st.session_state["auto_run_analysis"] = False

    if st.session_state.get("switch_to_results"):
        st.session_state["switch_to_results"] = False
        import streamlit.components.v1 as _c
        _c.html("""<script>setTimeout(function(){
            var t=window.parent.document.querySelectorAll('[data-baseweb="tab"]');
            if(t.length>=3)t[2].click();},300);</script>""", height=0)

    tab1, tab2, tab3 = st.tabs(
        ["📁  Upload Documents", "👤  Officer Inputs", "📊  Results"])

    # ── Tab 1: Upload ─────────────────────────────────────────────────────────
    with tab1:
        st.markdown(
            "<p class='ic-section-title'>Financial Documents</p>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<div class='ic-upload-zone'><span class='ic-upload-label'>📋 GST Return</span><span class='ic-upload-desc'>GSTR-3B / GSTR-2A — PDF or Excel</span>", unsafe_allow_html=True)
            gst_file = st.file_uploader(
                "GST",  type=["pdf", "xlsx", "xls"], key="gst",  label_visibility="collapsed")
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<div class='ic-upload-zone'><span class='ic-upload-label'>📝 Income Tax Return</span><span class='ic-upload-desc'>ITR — PDF or Excel</span>", unsafe_allow_html=True)
            itr_file = st.file_uploader(
                "ITR",  type=["pdf", "xlsx"],       key="itr",  label_visibility="collapsed")
            st.markdown("</div>", unsafe_allow_html=True)
        with col2:
            st.markdown("<div class='ic-upload-zone'><span class='ic-upload-label'>🏦 Bank Statement</span><span class='ic-upload-desc'>PDF or Excel format</span>", unsafe_allow_html=True)
            bank_file = st.file_uploader(
                "Bank", type=["pdf", "xlsx"],       key="bank", label_visibility="collapsed")
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<div class='ic-upload-zone'><span class='ic-upload-label'>📎 Other Documents</span><span class='ic-upload-desc'>Annual report, projections, etc.</span>", unsafe_allow_html=True)
            other_file = st.file_uploader(
                "Other", type=["pdf", "docx", "xlsx"], key="other", label_visibility="collapsed")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            "<hr class='ic-divider'><p class='ic-section-title'>GST Reconciliation — GSTR-2A vs 3B</p>", unsafe_allow_html=True)
        st.caption(
            "Upload both to detect ITC manipulation and circular trading patterns.")
        col3, col4 = st.columns(2)
        with col3:
            st.markdown("<div class='ic-upload-zone'><span class='ic-upload-label'>GSTR-2A</span><span class='ic-upload-desc'>Auto-populated from suppliers</span>", unsafe_allow_html=True)
            gstr_2a_file = st.file_uploader(
                "2A", type=["pdf", "xlsx"], key="gstr2a", label_visibility="collapsed")
            st.markdown("</div>", unsafe_allow_html=True)
        with col4:
            st.markdown("<div class='ic-upload-zone'><span class='ic-upload-label'>GSTR-3B</span><span class='ic-upload-desc'>Self-declared return</span>", unsafe_allow_html=True)
            gstr_3b_file = st.file_uploader(
                "3B", type=["pdf", "xlsx"], key="gstr3b", label_visibility="collapsed")
            st.markdown("</div>", unsafe_allow_html=True)

        uploaded = [f"✅ {lbl}: {f.name}" for f, lbl in [
            (gst_file, "GST"), (bank_file, "Bank"), (itr_file, "ITR"),
            (other_file, "Other"), (gstr_2a_file, "GSTR-2A"), (gstr_3b_file, "GSTR-3B")] if f]
        if uploaded:
            st.success("  ·  ".join(uploaded))
        else:
            st.info(
                "No documents uploaded yet — you can still run analysis with manual officer inputs.")

    # ── Tab 2: Officer inputs ─────────────────────────────────────────────────
    with tab2:
        st.markdown(
            "<p class='ic-section-title'>Primary Due Diligence Inputs</p>", unsafe_allow_html=True)
        st.caption("These inputs adjust the AI risk score (max ±0.25 delta).")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<div class='ic-card'>", unsafe_allow_html=True)
            site_visit_notes = st.text_area("🏭 Site Visit Notes", value="",
                                            placeholder="e.g. Factory running at full capacity...", height=150)
            management_notes = st.text_area("👥 Management Interview Notes", value="",
                                            placeholder="e.g. Promoter has 15 years experience...", height=150)
            st.markdown("</div>", unsafe_allow_html=True)
        with col2:
            st.markdown("<div class='ic-card'>", unsafe_allow_html=True)
            _derived = st.session_state.get("derived_financials", {})
            _auto_de = _derived.get("debt_equity_ratio")
            _auto_nw = _derived.get("net_worth_inr")
            de_val = float(_auto_de or 1.5)
            debt_equity = st.slider("📊 D/E Ratio"+(" 🔒" if _auto_de else ""),
                                    0.0, 5.0, round(de_val, 1), 0.1)
            collateral_pct = st.slider(
                "🏠 Collateral Coverage (%)", 0, 200, 75, 5)
            _nw_val = int(_auto_nw or 5000000)
            net_worth = st.number_input("💰 Net Worth (₹)"+(" 🔒" if _auto_nw else ""),
                                        min_value=0, value=_nw_val, step=100000, format="%d")
            promoter_score = st.slider("⭐ Promoter Integrity Score", 1, 10, 7,
                                       help="1=Very Poor, 10=Excellent")
            sector_risk = st.slider("🏭 Sector Risk Score", 1, 10, 5,
                                    help="1=Very Low Risk, 10=Very High Risk")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<hr class='ic-divider'><p class='ic-section-title'>Qualitative Score Preview</p>",
                    unsafe_allow_html=True)
        if site_visit_notes:
            from config import SITE_VISIT_RISK_KEYWORDS, SITE_VISIT_POSITIVE_KEYWORDS
            nl = site_visit_notes.lower()
            rh = sum(1 for kw in SITE_VISIT_RISK_KEYWORDS if kw in nl)
            ph = sum(1 for kw in SITE_VISIT_POSITIVE_KEYWORDS if kw in nl)
            if ph > rh:
                st.success(
                    f"✅ Positive signals ({ph} positive vs {rh} risk). Score will decrease.")
            elif rh > ph:
                st.warning(
                    f"⚠️ Risk signals ({rh} risk vs {ph} positive). Score will increase.")
            else:
                st.info("ℹ️ Neutral notes — no score adjustment.")
        else:
            st.info("Enter site visit notes to see score preview.")

    # ── Run button ────────────────────────────────────────────────────────────
    st.markdown("<hr class='ic-divider'>", unsafe_allow_html=True)
    col_run, _ = st.columns([2, 6])
    with col_run:
        if not company_name:
            st.warning("⚠️ No case loaded.")
            _clicked = st.button("🔍  Run AI Credit Analysis",
                                 disabled=True, use_container_width=True)
        else:
            _clicked = st.button("🔍  Run AI Credit Analysis",
                                 use_container_width=True)
    run_button = _clicked or auto_run

    # ── Tab 3: Results ────────────────────────────────────────────────────────
    with tab3:
        if not st.session_state.get("analysis_result"):
            st.markdown("<div class='ic-card' style='text-align:center;padding:3rem;'>"
                        "<div style='font-size:2.5rem;margin-bottom:0.75rem;'>📊</div>"
                        "<div style='font-weight:600;font-size:1rem;color:var(--text-sec);'>No analysis run yet</div>"
                        "<div style='font-size:0.85rem;color:var(--text-muted);margin-top:0.3rem;'>"
                        "Fill in details, upload documents, add officer inputs, then click Run.</div></div>",
                        unsafe_allow_html=True)
        else:
            result = st.session_state["analysis_result"]
            pred = result.risk_prediction

            if pred:
                ds = str(pred.decision).replace("DecisionType.", "")
                cs = str(pred.risk_category).replace("RiskCategory.", "")
                if "APPROVE" in ds.upper():
                    cc, ic = "decision-approve",    "✅"
                elif "REJECT" in ds.upper():
                    cc, ic = "decision-reject",     "❌"
                else:
                    cc, ic = "decision-conditional", "⚠️"
                st.markdown(
                    f'<div class="{cc}">{ic} AI DECISION: {ds}</div>', unsafe_allow_html=True)

                decisive = getattr(pred, "decisive_factor", "") or ""
                if decisive.strip():
                    st.markdown(f'<div class="decisive-factor"><strong>⚡ DECISIVE FACTOR &nbsp;</strong>{decisive}</div>',
                                unsafe_allow_html=True)

                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.metric("Risk Score",    f"{pred.risk_score:.3f}")
                with c2:
                    st.metric("Risk Category", cs)
                with c3:
                    st.metric("Loan Limit",
                              f"₹{pred.loan_limit_inr/100000:.1f}L")
                with c4:
                    st.metric("Interest Rate", f"{pred.interest_rate}% p.a.")

                if result.derived_financials:
                    d = result.derived_financials
                    st.markdown("<hr class='ic-divider'><p class='ic-section-title'>Auto-Derived Financial Ratios</p>",
                                unsafe_allow_html=True)
                    dc1, dc2, dc3, dc4 = st.columns(4)
                    with dc1:
                        if d.debt_equity_ratio is not None:
                            st.metric("D/E Ratio",
                                      f"{d.debt_equity_ratio:.2f}x")
                    with dc2:
                        if d.dscr is not None:
                            st.metric("DSCR",               f"{d.dscr:.2f}x")
                    with dc3:
                        if d.net_profit_margin is not None:
                            st.metric("Net Profit Margin",
                                      f"{d.net_profit_margin:.1f}%")
                    with dc4:
                        if d.data_completeness_pct is not None:
                            st.metric("Data Completeness",
                                      f"{d.data_completeness_pct:.0f}%")
                    if d.derivation_notes:
                        for note in d.derivation_notes:
                            st.caption(f"ℹ️ {note}")

                st.markdown("<hr class='ic-divider'>", unsafe_allow_html=True)
                cl, cr = st.columns(2)

                with cl:
                    st.markdown(
                        "<p class='ic-section-title'>Five Cs Scores</p>", unsafe_allow_html=True)
                    if result.five_cs:
                        import plotly.graph_objects as go
                        cs2 = result.five_cs
                        cats = ["Character", "Capacity",
                                "Capital", "Collateral", "Conditions"]
                        scrs = [cs2.character.score, cs2.capacity.score, cs2.capital.score,
                                cs2.collateral.score, cs2.conditions.score]
                        fig = go.Figure()
                        fig.add_trace(go.Scatterpolar(
                            r=scrs+[scrs[0]], theta=cats+[cats[0]], fill="toself",
                            fillcolor="rgba(26,35,126,0.25)", line=dict(color="#42A5F5", width=2)))
                        fig.update_layout(
                            polar=dict(
                                radialaxis=dict(visible=True, range=[
                                                0, 10], gridcolor="#1E2A4A", linecolor="#1E2A4A"),
                                angularaxis=dict(gridcolor="#1E2A4A"),
                                bgcolor="rgba(0,0,0,0)"),
                            showlegend=False, height=300,
                            margin=dict(l=40, r=40, t=30, b=30),
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#C5CAE9"))
                        st.plotly_chart(fig, use_container_width=True)
                        st.caption(
                            f"Overall Five Cs: **{result.five_cs.overall_score}/10**")

                with cr:
                    st.markdown(
                        "<p class='ic-section-title'>SHAP Risk Drivers</p>", unsafe_allow_html=True)
                    if pred.top_shap_factors:
                        import plotly.graph_objects as go
                        facs = pred.top_shap_factors
                        nms = [f.display_name for f in facs]
                        vals = [
                            f.shap_value if "increases" in f.direction else -f.shap_value for f in facs]
                        fig2 = go.Figure(go.Bar(
                            x=vals, y=nms, orientation="h",
                            marker_color=["#FF5252" if v > 0 else "#00E676" for v in vals]))
                        fig2.update_layout(
                            xaxis_title="Risk Impact", height=300,
                            margin=dict(l=180, r=40, t=20, b=40),
                            xaxis=dict(zeroline=True, zerolinewidth=1.5,
                                       zerolinecolor="#1E2A4A", color="#C5CAE9"),
                            yaxis=dict(color="#C5CAE9"),
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#C5CAE9"))
                        st.plotly_chart(fig2, use_container_width=True)

                st.markdown("<hr class='ic-divider'>", unsafe_allow_html=True)

                if result.gst_reconciliation:
                    st.markdown(
                        "<p class='ic-section-title'>GST Reconciliation</p>", unsafe_allow_html=True)
                    rec = result.gst_reconciliation
                    if rec.risk_flag:
                        st.markdown(
                            f'<div class="flag-box">🚨 GST Risk Flag: {rec.total_mismatches} mismatch(es). Max variance: {rec.variance_pct}%</div>', unsafe_allow_html=True)
                    else:
                        st.success(
                            f"✅ GST Reconciliation Passed. Variance: {rec.variance_pct}%")
                    if rec.circular_trading_flag:
                        st.markdown(
                            '<div class="flag-box">🚨 CIRCULAR TRADING DETECTED</div>', unsafe_allow_html=True)

                if result.five_cs:
                    st.markdown(
                        "<p class='ic-section-title'>Five Cs Detail</p>", unsafe_allow_html=True)
                    for lbl, obj in [("Character", result.five_cs.character), ("Capacity", result.five_cs.capacity),
                                     ("Capital", result.five_cs.capital), ("Collateral",
                                                                           result.five_cs.collateral),
                                     ("Conditions", result.five_cs.conditions)]:
                        with st.expander(f"{lbl}: {obj.score}/10 — {obj.summary}"):
                            for f in obj.factors:
                                st.markdown(f"• {f}")

                # ── FIX 4: SWOT shown ONCE, full width, after Five Cs detail ──
                if st.session_state.get("swot_result"):
                    st.markdown("<hr class='ic-divider'>",
                                unsafe_allow_html=True)
                    st.markdown(
                        "<p class='ic-section-title'>SWOT Analysis</p>", unsafe_allow_html=True)
                    from src.swot_generator import render_swot_ui
                    render_swot_ui(st.session_state["swot_result"])

                if pred.early_warning_signals:
                    st.markdown(
                        "<p class='ic-section-title'>Early Warning Signals</p>", unsafe_allow_html=True)
                    for w in pred.early_warning_signals:
                        st.markdown(f'<div class="warning-box">{"" if w.startswith("⚠️") else "⚠️ "}{w}</div>',
                                    unsafe_allow_html=True)

                st.markdown("<hr class='ic-divider'>", unsafe_allow_html=True)
                with st.expander("🤖 Full AI Reasoning Chain"):
                    chain = result.reasoning_chain or ""
                    st.text(chain) if chain.strip() else st.info(
                        "AI reasoning chain unavailable — Groq API limit reached.")

                if result.research:
                    with st.expander(f"📰 External Research (News Risk: {result.research.news_risk_score}/10)"):
                        r = result.research
                        st.markdown(r.research_summary)
                        if r.negative_news:
                            st.markdown("**Negative News:**")
                            for item in r.negative_news[:5]:
                                st.markdown(f'<div class="news-negative">🔴 {item.title}<br>'
                                            f'<span style="opacity:0.6;font-size:0.75rem">'
                                            f'{item.date} — {item.source}</span></div>', unsafe_allow_html=True)
                        if r.positive_news:
                            st.markdown("**Positive News:**")
                            for item in r.positive_news[:3]:
                                st.markdown(f'<div class="news-positive">🟢 {item.title}<br>'
                                            f'<span style="opacity:0.6;font-size:0.75rem">'
                                            f'{item.date} — {item.source}</span></div>', unsafe_allow_html=True)
                        if r.litigation_details:
                            st.markdown("**Litigation:**")
                            for lcase in r.litigation_details:
                                st.markdown(f"⚖️ {lcase}")

                st.markdown("<hr class='ic-divider'><p class='ic-section-title'>Reports</p>",
                            unsafe_allow_html=True)
                if "pdf_path" in st.session_state:
                    import base64 as _b64mod
                    with open(st.session_state["pdf_path"], "rb") as _f:
                        _pdf = _f.read()
                    _b64 = _b64mod.b64encode(_pdf).decode()
                    _uri = f"data:application/pdf;base64,{_b64}"
                    import streamlit.components.v1 as _comp
                    _comp.html(
                        f'<div style="margin-bottom:12px;">'
                        f'<button onclick="window.open(\'{_uri}\',\'_blank\')" '
                        f'style="background:#1A237E;color:#E8B020;font-weight:700;padding:10px 22px;'
                        f'border-radius:8px;cursor:pointer;font-size:0.9rem;border:1.5px solid #1976D2;'
                        f'font-family:sans-serif;">&#128196;&nbsp; View Investment Report</button>'
                        f'<span style="margin-left:10px;font-size:0.78rem;color:#7986CB;'
                        f'font-family:sans-serif;">Opens in new tab</span></div>', height=55)

                dl1, dl2 = st.columns(2)
                if "pdf_path" in st.session_state:
                    with dl1:
                        with open(st.session_state["pdf_path"], "rb") as f:
                            st.download_button("📄 Download PDF Report", data=f.read(),
                                               file_name=Path(
                                                   st.session_state["pdf_path"]).name,
                                               mime="application/pdf", use_container_width=True)
                if "docx_path" in st.session_state:
                    with dl2:
                        with open(st.session_state["docx_path"], "rb") as f:
                            st.download_button("📝 Download DOCX Report", data=f.read(),
                                               file_name=Path(
                                                   st.session_state["docx_path"]).name,
                                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                               use_container_width=True)

    # ════════════════════════════════════════════════════════════════════════
    # PIPELINE  (only runs when Run button is clicked)
    # ════════════════════════════════════════════════════════════════════════
    if run_button and company_name:
        with st.spinner("🔄 Loading AI engines..."):
            engines = load_engines()

        from src.schemas import CreditAppraisalResult, QualitativeInputs
        result = CreditAppraisalResult(company_name=company_name)

        # ── Parse documents ───────────────────────────────────────────────
        with st.spinner("📄 Parsing documents..."):
            parser = engines["parser"]
            extractor = engines["extractor"]
            rag = engines["agent"].rag
            _tmp = []

            def save_and_parse(uf):
                if not uf:
                    return None
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uf.name).suffix) as t:
                    t.write(uf.read())
                    tp = str(Path(t.name).resolve())
                _tmp.append(tp)
                p = parser.parse(tp)
                p.source_file = tp
                return p

            if gst_file:
                pg = save_and_parse(gst_file)
                if pg and not pg.error:
                    result.gst_data = extractor.extract_gst(pg)
                    rag.ingest(pg, company_name=company_name)
            if bank_file:
                pb = save_and_parse(bank_file)
                if pb and not pb.error:
                    result.bank_data = extractor.extract_bank(pb)
                    rag.ingest(pb, company_name=company_name)
            if itr_file:
                pi = save_and_parse(itr_file)
                if pi and not pi.error:
                    result.itr_data = extractor.extract_itr(pi)
                    rag.ingest(pi, company_name=company_name)
                    if result.itr_data.net_worth == 0:
                        st.warning("⚠️ ITR parsed but net worth is zero.")
                else:
                    st.warning(
                        f"⚠️ ITR could not be parsed: {getattr(pi,'error','unknown') if pi else 'None'}")
            if other_file:
                po = save_and_parse(other_file)
                if po and not po.error:
                    rag.ingest(po, company_name=company_name)
            for _f in _tmp:
                try:
                    os.unlink(_f)
                except OSError:
                    pass

            derived = engines["risk_engine"].derive_from_documents(result)
            result.derived_financials = derived
            st.session_state["derived_financials"] = {
                "debt_equity_ratio": derived.debt_equity_ratio,
                "net_worth_inr":     derived.net_worth_inr,
            }
            if derived.derivation_notes:
                for note in derived.derivation_notes:
                    st.info(f"📊 {note}")

        # ── GST reconciliation ────────────────────────────────────────────
        with st.spinner("🔍 Running GST reconciliation..."):
            if gstr_2a_file and gstr_3b_file:
                p2a = save_and_parse(gstr_2a_file)
                p3b = save_and_parse(gstr_3b_file)
                if p2a and p3b:
                    g2a = extractor.extract_gst(p2a)
                    g3b = extractor.extract_gst(p3b)
                    result.gst_reconciliation = engines["reconciler"].reconcile(
                        g2a, g3b)
                    result.gst_data = g3b
                    if not p2a.error:
                        rag.ingest(p2a, company_name=company_name)
                    if not p3b.error:
                        rag.ingest(p3b, company_name=company_name)
            elif result.gst_data:
                from src.schemas import GSTReconciliationResult
                result.gst_reconciliation = GSTReconciliationResult(
                    total_mismatches=0, risk_flag=False, variance_pct=0.0,
                    summary="Single GST file. Upload both GSTR-2A and 3B for full reconciliation.")

        # ── FIX 2: Research runs ONCE ─────────────────────────────────────
        with st.spinner("🔎 Researching company + sector..."):
            sector = st.session_state.get("ob_form", {}).get("sector", "")
            extracted_serial = {
                fname: (r.model_dump() if hasattr(r, "model_dump") else r)
                for fname, r in st.session_state.get("hitl_extractions", {}).items()
                if r is not None
            } if st.session_state.get("hitl_extractions") else None

            research_dict = engines["researcher"].research_full(
                company_name=company_name,
                promoter_name=promoter_name,
                sector=sector,
                extracted_data=extracted_serial,
                use_mock=use_mock_research,
                mock_level=mock_risk_level,
            )
            result.research_dict = research_dict

            from src.schemas import ResearchFindings, NewsItem
            result.research = ResearchFindings(
                company_name=company_name,
                negative_news=[
                    NewsItem(**n) for n in research_dict.get("negative_news", [])],
                positive_news=[
                    NewsItem(**p) for p in research_dict.get("positive_news", [])],
                litigation_found=research_dict.get("litigation_found", False),
                litigation_details=research_dict.get("litigation_details", []),
                mca_charges=research_dict.get("mca_charges", []),
                rbi_sebi_actions=research_dict.get("rbi_sebi_actions", []),
                news_risk_score=research_dict.get("news_risk_score", 0),
                research_summary=research_dict.get("research_summary", ""),
            )
            if st.session_state.get("case_id"):
                from src.database import update_case
                update_case(st.session_state["case_id"], {
                            "research_json": research_dict})

        # ── Qualitative inputs (enriched with HITL extractions) ───────────
        officer_inputs = QualitativeInputs(
            site_visit_notes=site_visit_notes,
            management_interview_notes=management_notes,
            debt_equity_ratio=debt_equity,
            collateral_coverage=collateral_pct / 100,
            net_worth_inr=float(net_worth),
            sector_risk_score=sector_risk,
            promoter_score=promoter_score,
        )

        hitl_extractions = st.session_state.get("hitl_extractions", {})
        if hitl_extractions:
            from src.extractors_v2 import (
                enrich_qualitative_inputs,
                AnnualReportData, ALMData, ShareholdingData,
                BorrowingProfileData, PortfolioPerformanceData,
            )
            type_map = {
                "ANNUAL_REPORT":         AnnualReportData,
                "ALM":                   ALMData,
                "SHAREHOLDING_PATTERN":  ShareholdingData,
                "BORROWING_PROFILE":     BorrowingProfileData,
                "PORTFOLIO_PERFORMANCE": PortfolioPerformanceData,
            }
            classifications = st.session_state.get("hitl_classifications", {})
            typed_extractions = {}
            for fname, data in hitl_extractions.items():
                if data is None:
                    continue
                clf = classifications.get(fname)
                doc_type = clf.doc_type if clf else "UNKNOWN"
                model_cls = type_map.get(doc_type)
                if model_cls and isinstance(data, dict):
                    try:
                        typed_extractions[fname] = model_cls(**data)
                    except Exception:
                        pass
                elif model_cls and hasattr(data, "model_dump"):
                    typed_extractions[fname] = data

            if typed_extractions:
                officer_inputs = enrich_qualitative_inputs(
                    typed_extractions, officer_inputs)
                result.hitl_extractions = {
                    fname: obj.model_dump() if hasattr(obj, "model_dump") else obj
                    for fname, obj in typed_extractions.items()
                }
                for note in (officer_inputs.auto_filled_fields or []):
                    st.info(f"📊 {note}")

        result.qualitative_inputs = engines["risk_engine"].build_qualitative_inputs(
            result.derived_financials, officer_inputs)

        # ── Five Cs + XGBoost + Reasoning ────────────────────────────────
        with st.spinner("📊 Running Five Cs analysis..."):
            result.five_cs = engines["five_cs"].analyze(result)
        with st.spinner("🤖 Scoring with XGBoost + SHAP..."):
            result.risk_prediction = engines["risk_engine"].score(
                result, requested_amount_inr=float(loan_amount_requested))
        with st.spinner("🧠 Running AI reasoning (Groq LLaMA)..."):
            result = engines["agent"].analyze(result)

        # ── Generate Investment Report ────────────────────────────────────
        with st.spinner("📄 Generating Investment Assessment Report..."):
            paths = engines["cam"].generate_both(result)
            st.session_state["pdf_path"] = paths["pdf"]
            st.session_state["docx_path"] = paths["docx"]

        # ── FIX 3: SWOT — safe NameError guard ───────────────────────────
        with st.spinner("🧩 Generating SWOT analysis..."):
            swot = None
            try:
                from src.swot_generator import generate_swot, save_swot_to_case
                swot = generate_swot(result=result)
                st.session_state["swot_result"] = swot
                if st.session_state.get("case_id"):
                    save_swot_to_case(st.session_state["case_id"], swot)
            except Exception as e:
                print(f"[SWOT] Failed: {e}")
            result.swot = swot   # None if failed — safe, no NameError

        # ── Save to Supabase ──────────────────────────────────────────────
        if st.session_state.get("case_id"):
            try:
                from src.database import update_case
                p = result.risk_prediction
                update_case(st.session_state["case_id"], {
                    "status":          "COMPLETED",
                    "decision":        str(p.decision).replace("DecisionType.", ""),
                    "risk_score":      float(p.risk_score),
                    "decisive_factor": getattr(p, "decisive_factor", None),
                    "cam_path":        paths.get("pdf", ""),
                })
            except Exception:
                pass

        st.session_state["analysis_result"] = result
        st.session_state["switch_to_results"] = True
        st.success("✅ Analysis complete!")
        st.balloons()
        st.rerun()


# ─── ROUTER ───────────────────────────────────────────────────────────────────
if st.session_state.page == "dashboard":
    render_dashboard()
elif st.session_state.page == "classify":
    from pages.upload_classify import render
    render()
elif st.session_state.page == "onboarding":
    from pages.onboarding import render
    render()
elif st.session_state.page == "case_view":
    from pages.case_view import render
    render()
else:
    render_analysis()
