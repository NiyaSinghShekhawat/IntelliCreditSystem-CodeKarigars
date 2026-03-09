# 🏦 IntelliCredit — AI-Powered Credit Appraisal System

> **Hackathon Project** · Built with Streamlit · Groq LLaMA 3.3 70B · XGBoost · ReportLab · ChromaDB

IntelliCredit is an end-to-end AI-assisted credit appraisal platform for Indian SME lending. It automates document parsing, financial ratio derivation, GST reconciliation, risk scoring, Five Cs analysis, external due diligence, and professional CAM report generation — all from a single web interface.

---

## ✨ Features

### 📄 Document Intelligence
- **Multi-format parser** — Docling-powered parsing for XLSX, PDF, scanned PDFs (via RapidOCR), and text documents
- **Dual LLM extraction** — Groq LLaMA 3.3 70B as primary extractor with automatic failover to Google Gemini 1.5 Flash when Groq is rate-limited
- **Multi-key Groq rotation** — cycles through up to 4 API keys before falling back to Gemini
- **Three-tier extraction chain (per document type)**:
  - GST: Groq/Gemini LLM → regex → openpyxl direct cell scan (always runs for xlsx, overrides LLM result)
  - Bank: Groq/Gemini LLM → regex → openpyxl summary row reader (always overrides avg balance with actual summary row value)
  - ITR: Groq/Gemini LLM → dual-strategy regex (colon-style + pipe-table) → openpyxl direct cell scan
- **Auto-fill pipeline** — financial ratios derived automatically from uploaded documents and pre-populated in the officer input form with 🔒 lock icons
- **Scanned PDF / OCR support** — RapidOCR fires automatically on image-based PDFs

### 🔍 GST Reconciliation
- Separate GSTR-2A and GSTR-3B upload with independent extraction pipelines
- GSTR-2A ITC extracted by summing the supplier ITC column (ignores embedded 3B reference rows)
- GSTR-2A vs GSTR-3B ITC variance analysis with fraud signal flagging
- Circular trading detection
- Configurable mismatch thresholds

### 📊 Risk Scoring Engine
- **XGBoost model** trained on synthetic data with SHAP explainability
- **Hard policy rule overrides** — GST ITC variance ≥50% forces a minimum CONDITIONAL decision regardless of XGBoost score (mirrors real bank credit policy); 20–50% applies a score penalty
- Accepts officer-requested loan amount as scoring input
- Loan limit calculated relative to requested amount (not a fixed formula)
- `MAX_LOAN_LIMIT_INR` = ₹50 Cr (configurable in `config.py`)
- Three risk categories: LOW / MEDIUM / HIGH → Three decisions: APPROVE / CONDITIONAL / REJECT
- **Decisive factor surfaced prominently** — shown immediately below the AI decision banner with gold accent styling

### 🤖 AI Agent (Groq LLaMA 3.3 70B)
- Full 4-step reasoning chain (GST → Bank → Research → Primary Inputs)
- Narrative decision — supplementary to XGBoost, never overrides model score
- Decisive factor and early warning signal extraction from LLM output
- RAG-backed context using ChromaDB + `all-MiniLM-L6-v2` embeddings
- Graceful fallback message shown in UI when Groq is rate-limited

### 🏅 Five Cs Credit Analysis
- Character, Capacity, Capital, Collateral, Conditions — scored 0–10
- GST mismatch flag automatically lowers Character score
- Capital section uses ITR-derived net worth (not officer slider default)
- Granular factor bullets per parameter with detailed reasoning

### 🔎 External Research & Due Diligence
- Google News + GDELT news search with accent-normalised relevance filtering
- 16 approved Indian and international news domains
- MCA charge check · e-Courts litigation search · RBI/SEBI regulatory action check
- News risk score 0–10

### 📋 Bank-Grade CAM Report (PDF + DOCX)
- **PDF** — 10-section Credit Appraisal Memorandum:
  - Navy letterhead cover page · CONFIDENTIAL watermark · credit committee approval block
  - Decisive factor highlighted on cover and recommendation pages
  - GST reconciliation section with ITC variance, risk flag, and mismatch summary
  - Semi-circular risk gauge (green / amber / red) · decision colour-coded badge
  - Standard credit conditions & covenants table · 4-column signature block
  - Legal disclaimer referencing RBI guidelines
- **DOCX** — matching structure, Arial font, navy section headers
- **Auto-reference number** — format `CAM/YYYY/COMP/DDHHMM`

### 🖥 UI / UX
- **Auto-switch to Results tab** after analysis completes
- Decisive factor shown with gold accent directly below AI decision banner
- Five Cs spider/radar chart (Plotly) · SHAP risk drivers horizontal bar chart
- Policy override warnings surfaced in Early Warning Signals

---

## 🗂 Project Structure

```
IntelliCredit/
├── app.py                      # Streamlit UI + analysis pipeline
├── config.py                   # Constants: bank name, limits, model paths, API keys
├── requirements.txt
└── src/
    ├── schemas.py              # Pydantic models (all data structures)
    ├── parser.py               # Docling parser + RapidOCR for scanned PDFs
    ├── extractor.py            # Groq + Gemini + regex + openpyxl extraction chain
    ├── reconciler.py           # GSTR-2A vs 3B reconciliation
    ├── researcher.py           # External news + MCA + court research
    ├── risk_engine.py          # XGBoost + SHAP + hard policy rules + loan limit
    ├── five_cs.py              # Five Cs credit analysis
    ├── agent.py                # Groq LLM reasoning agent
    ├── prompts.py              # All LLM prompt templates
    └── cam_generator.py        # PDF (ReportLab) + DOCX CAM generator
```

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.11+
- Groq API key ([console.groq.com](https://console.groq.com))
- Google Gemini API key — optional but recommended ([aistudio.google.com](https://aistudio.google.com))

### Install

```bash
git clone https://github.com/NiyaSinghShekhawat/IntelliCreditSystem.git
cd IntelliCreditSystem
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
pip install google-generativeai
```

### Configure

Create a `.env` file in the project root:

```env
# Primary LLM — Groq (multi-key rotation)
GROQ_API_KEY=your_primary_groq_key
GROQ_API_KEY_2=your_backup_groq_key
GROQ_API_KEY_3=your_third_groq_key

# Secondary LLM fallback — Gemini
GEMINI_API_KEY=your_gemini_api_key
```

> **Note:** Each `GROQ_API_KEY_N` must be from a **separate Groq account** with a different email. Keys sharing the same organisation share the daily token quota.

### Run

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501).

---

## 📋 How to Use

### Tab 1 — Upload Documents

| Field | Document | Format |
|---|---|---|
| Company Name | Manual entry | Text |
| GSTR-3B | GST return (filed by company) | XLSX |
| GSTR-2A | Auto-drafted ITC from suppliers | XLSX |
| Bank Statement | 6-month statement | XLSX |
| ITR / Balance Sheet | ITR-6 or financial statements | XLSX |
| Other Documents | Scanned certificates, KYC docs | PDF (OCR auto-applied) |
| Loan Amount Requested | Officer input | Number (₹) |

Click **Run AI Credit Analysis** — all steps are fully automated.

### Tab 2 — Officer Inputs

Auto-derived fields show 🔒 lock icons. Override any field manually — officer values always take precedence in scoring.

### Tab 3 — Results

Auto-opens when analysis completes.

- AI decision banner → decisive factor → risk metrics → financial ratios
- SHAP risk drivers chart · Five Cs radar chart
- GST reconciliation flag with variance %
- Early warning signals (including policy override notices)
- Full AI reasoning chain (expandable)
- Download PDF and DOCX CAM report buttons

---

## 🎨 Design Palette

| Colour | Hex | Usage |
|---|---|---|
| Deep Navy | `#0d1f5c` | Headers, borders, structural chrome |
| Gold | `#c9970a` | Cover accent, decisive factor label |
| Green | `#1a6b2a` | APPROVE decision |
| Amber | `#b85c00` | CONDITIONAL decision, warnings |
| Red | `#b71c1c` | REJECT decision, adverse items |

---

## 🧪 Mock Test Data

### Lakmé Cosmetics — GST flag scenario
- Turnover ₹168.5 Cr · Net Worth ₹74.5 Cr · D/E 0.54x · DSCR 5.89x
- ITC claimed (3B): ₹11 Cr · ITC available from suppliers (2A): ₹6.9 Cr
- **ITC variance 59.42%** → policy rule fires → **Expected: CONDITIONAL**

### Sunrise Apparels — high risk scenario
- Turnover ₹13.2 Cr · Net Worth ₹3.25 Cr · D/E 0.82x · ITC gap 62.5%
- **Expected: CONDITIONAL or REJECT**

---

## 🏗 Architecture

```
Upload Docs → Parse (Docling + RapidOCR)
                    ↓
    Extract: Groq LLM → Gemini fallback → Regex → openpyxl
                    ↓
         RAG Ingest (ChromaDB)
                    ↓
   GST Reconciliation (GSTR-2A supplier sum vs GSTR-3B)
                    ↓
       derive_from_documents() → derived_financials
                    ↓
   build_qualitative_inputs(derived, officer_inputs)
                    ↓
          five_cs.analyze()
                    ↓
   risk_engine.score() → XGBoost + SHAP
                    ↓
   Hard policy rules → GST variance floor if ≥ 50%
                    ↓
   agent.analyze() → narrative + decisive factor (LLM)
                    ↓
   cam.generate_both() → PDF (ReportLab) + DOCX
                    ↓
   Auto-switch to Results → Decisive factor + metrics
```

---

## 🔮 Future Scope

### 1. 🗄️ Multi-Client Data Store
Persist credit appraisal results across sessions using a structured database (Firebase / PostgreSQL). Each client gets a unique profile with full appraisal history — enabling relationship managers to track borrower health over time, compare successive applications, and flag deteriorating financial trends automatically. A **Portfolio Dashboard** would surface aggregate bank exposure by sector, risk category, and geography for senior credit management.

### 2. 💡 Government Scheme Recommendation Engine
Based on the borrower's loan amount, sector, business constitution (Pvt Ltd / Proprietorship / Partnership), and risk profile, automatically suggest applicable government lending schemes — MUDRA (Shishu / Kishor / Tarun), CGTMSE guarantee cover, SIDBI refinance, PM Vishwakarma, Stand-Up India, and state-level MSME subsidies. The engine would cross-reference RBI priority sector guidelines and MSME Ministry notifications to surface the most relevant schemes with eligibility criteria, subsidy amounts, and direct application links — helping credit officers maximise borrower benefit while also capturing available bank incentives under priority sector lending norms.

---

## 📦 Dependencies

```
streamlit
groq>=0.9.0
google-generativeai
xgboost
shap
chromadb
sentence-transformers
docling
openpyxl
reportlab
python-docx
pandas
requests
pydantic
python-dotenv
plotly
```

---

## 📝 Changelog

### v1.4 (Current)
- **Dual LLM backend** — Gemini 1.5 Flash fallback + multi-key Groq rotation (up to 4 keys)
- **GST reconciliation fix** — GSTR-2A ITC correctly summed from supplier column; embedded 3B reference rows skipped
- **Hard policy rule** — GST ITC variance ≥50% floors risk score to CONDITIONAL (0.35)
- **Decisive factor surfaced** — gold accent banner directly below AI decision
- **Auto tab switch** — Results tab opens automatically on analysis completion
- **Bank avg balance fix** — xlsx summary row always overrides Groq's inflated value
- **CAM GST section** — now shows reconciliation result, ITC variance %, and risk flag
- PDF modal removed (replaced with clean download buttons)
- Version label updated to v1.4 throughout

### v1.3
- Full bank-grade CAM redesign — 10 sections, cover page, running headers/footers, signature block
- Semi-circular risk gauge with colour zones · decision colour coding throughout

### v1.2
- Groq LLaMA 3.3 70B as primary extractor · three-tier ITR extraction chain
- Loan limit respects officer-requested amount · news relevance filtering with accent normalisation

### v1.1
- Auto-fill pipeline · RAG ingestion · SHAP explainability · GST circular trading · Five Cs engine

### v1.0
- Initial release — end-to-end pipeline from document upload to CAM generation

---

## 👩‍💻 Author

**Niya Singh Shekhawat**
GitHub: [@NiyaSinghShekhawat](https://github.com/NiyaSinghShekhawat)

---

*Built for a fintech hackathon. Not intended for production credit decisioning.*