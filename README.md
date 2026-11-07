# AuditMind AI — Continuous Compliance with Hindsight Agent Memory

> **Enterprise Continuous Assurance & Compliance Intelligence Platform**  
> Powered by **[Hindsight](https://github.com/vectorize-io/hindsight)** persistent memory and deterministic assurance rules.

[![Python](https://img.shields.io/badge/Python-3.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.162.0-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.4-blue.svg)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-38B2AC.svg)](https://tailwindcss.com/)
[![Hindsight Memory](https://img.shields.io/badge/Vectorize-Hindsight_Memory-0d9488.svg)](https://hindsight.vectorize.io/)

---

## Content Submission Deliverables

- 📄 **Technical Article (1,400 words):** [`article.md`](article.md) — *"Why Stateless AI Fails Enterprise Audits: Building Memory-Driven Compliance with Hindsight"*
- 📱 **LinkedIn Social Post:** [`social_post.md`](social_post.md) — Punchy executive post explaining compliance amnesia vs. Hindsight memory
- 🎥 **Video Demo Script (3 min):** [`video_script.md`](video_script.md) — Complete walkthrough script with timestamped visual cues and narration
- 🌐 **Instant Interactive Live Web Page:** [`frontend/preview.html`](frontend/preview.html) — Double-click to run in any browser with all 10 screens and 4-role switcher!

---

## How Hindsight Memory Is Used in AuditMind AI

1. **Retain (`hindsight_client.retain`)**: When an authorized compliance officer approves a draft finding or records a completed remediation, the structured audit memory is stored with rich metadata (`control_code`, `department`, `audit_period`, `severity`, `entity_type`).
2. **Recall (`hindsight_client.recall`)**: When new audit reports or questions arrive, AuditMind AI recalls past audit memories across preceding quarters and years.
3. **Reflect (`hindsight_client.reflect`)**: Synthesizes cross-cycle history to determine whether a recurring deficiency represents a chronic operational gap rather than an isolated defect, automatically escalating its predictive risk score.

---

## The Problem

Modern compliance and security teams manage dozens of ISO/IEC 27001 and SOC 2 controls across quarterly and annual audit cycles. In practice, audit management is plagued by fragmented spreadsheets, disconnected PDF reports, and tribal knowledge:
- **Repetitive Finding Gaps:** The same operational weaknesses (such as missing access review approvals or expired encryption certificates) recur across cycles because historical context is lost.
- **Manual Evidence Verification:** Teams manually inspect documents for dates, signatures, and scope, consuming hundreds of hours prior to each audit.
- **Disconnected Remediation:** Corrective actions live in separate issue trackers disconnected from the control register and audit trail.
- **Lack of Early Warnings:** Risks are only addressed retroactively during audit periods rather than proactively flagged through continuous signals.

**AuditMind AI** bridges this gap by maintaining continuous compliance visibility, correlating findings across audit cycles, and verifying evidence using deterministic rules with human-in-the-loop governance.

---

## Four Core Capabilities

1. **Continuous Compliance Monitoring**  
   Maintains a live ISO 27001-inspired control register, mapping evidence items to specific controls with review cadence tracking (`annual`, `quarterly`, `monthly`) and derived computed status signals.

2. **Audit History Intelligence**  
   Maintains structured relational records of past audit cycles, findings, and remediation history. Detects recurrence patterns by comparing approved finding records across cycles (using control code, department, keyword token overlap, and time proximity) and renders a chronological audit timeline.

3. **Risk Early-Warning Signals**  
   Calculates illustrative, transparent 0–10 risk indicators based on finding severity, confirmed recurrence count, overdue remediation days, and evidence gaps, ranking findings to highlight where attention is needed most.

4. **Evidence Verification Engine**  
   Provides document upload, layout-aware text extraction via PyMuPDF, and deterministic field-by-field verification (freshness window, required field regex patterns, and confidence scoring) to produce clear assessments (`Candidate Match`, `Incomplete`, `Expired`, `Missing`, `Requires Human Review`).

> [!IMPORTANT]
> **Advisory Contract:** All AI-extracted findings and evidence assessments are initially saved with `review_status="Draft"`. Only an authorized human reviewer (`compliance_officer` or `auditor`) can approve them. The system **never** marks a control compliant or closes a finding autonomously.

---

## Architecture

```mermaid
flowchart TD
    Client["Browser Client\n(React 18 + Vite 5 + TypeScript + Tailwind)"]
    API["FastAPI 0.162.0 Backend\n(Python 3.14 + Uvicorn)"]
    ORM["SQLAlchemy 2.0 ORM"]
    DB[("Relational DB\n(SQLite / DATABASE_URL)")]
    PDF["PyMuPDF (fitz)\nText Extraction Engine"]
    LLM["LLM Provider (Optional)\n(Groq / Gemini via httpx)"]

    Client -->|HTTP / JSON (REST)| API
    API -->|Data Access| ORM
    ORM -->|SQL Queries| DB
    API -->|Synchronous Ingestion| PDF
    API -.->|Optional Drafting\n(Fallback to Rules)| LLM
```

---

## Tech Stack

| Layer | Technologies & Actual Versions |
|---|---|
| **Backend** | Python 3.14, FastAPI 0.162.0, SQLAlchemy 2.0, Pydantic 2, Uvicorn, PyMuPDF (fitz) 1.24+, HTTPX 0.27+ |
| **Database** | SQLite (via `DATABASE_URL`, fully compatible with PostgreSQL) |
| **Frontend** | React 18, Vite 5, TypeScript 5, Tailwind CSS 3, Recharts, React Router 6 |
| **Testing** | pytest 8.0+, pytest-asyncio |
| **LLM Engine** | Optional runtime adapter (`groq`, `gemini`, or `none` for 100% deterministic local execution) |
| **Database Seed** | `python -m app.seed [--demo | --clean | --reset]` |

---

## Quick Start

### 1. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Seed the database with demo scenario (ABC Technologies 3-cycle audit history)
python -m app.seed --demo

# Start the backend server
uvicorn app.main:app --reload --port 8000
```
Interactive API documentation will be available at: [http://localhost:8000/docs](http://localhost:8000/docs).

### 2. Frontend Setup

```bash
cd frontend

# Install Node dependencies
npm install

# Start Vite development server
npm run dev
```
The frontend dashboard will be available at: [http://localhost:5173](http://localhost:5173).

### 3. One-Command Dev Launch

You can run both backend and frontend concurrently:

```bash
# Using Makefile
make dev

# Or on Windows using batch script
run_dev.bat
```

---

## Environment Variables

Configure these settings in your `.env` file (copied from `.env.example`):

| Variable | Default Value | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./auditmind.db` | SQLAlchemy connection string (SQLite or PostgreSQL) |
| `LLM_PROVIDER` | `none` | Runtime provider: `none` (deterministic), `groq`, or `gemini` |
| `GROQ_API_KEY` | *(empty)* | API key for Groq Cloud (required if `LLM_PROVIDER=groq`) |
| `GEMINI_API_KEY` | *(empty)* | API key for Google Gemini (required if `LLM_PROVIDER=gemini`) |
| `UPLOAD_DIR` | `./uploads` | Storage directory for uploaded compliance documents |
| `MAX_UPLOAD_MB` | `20` | Maximum allowable upload file size in megabytes |
| `VITE_API_URL` | `http://localhost:8000` | Backend API base URL for Vite frontend |

---

## 5-Step Demo Walkthrough

Follow these steps to demonstrate AuditMind AI's end-to-end intelligence:

1. **Dashboard Overview:** Explore ABC Technologies' ISO 27001 control register and audit cycle history. Observe open gaps and control statuses.
2. **Document Ingestion:** Navigate to **Document Centre**, upload the January audit report (`AUD-2026-001`), click **Process** for text extraction, then **Analyze**. Review the extracted draft finding for **SEC-014** (*User Access Review*) flagged on page 4.
3. **Human Approval:** Inspect the side-by-side source text comparison in **Findings Review**. Approve the finding as `compliance_officer` to promote it to an approved record with an immutable status history entry.
4. **Recurrence Detection:** Ingest the April audit report (`AUD-2026-002`) and analyze. Upon approving the repeated SEC-014 finding, the system immediately surfaces the January finding under **Possible related past findings** with detailed match reasons.
5. **Risk Escalation & Assistant Intelligence:** Confirm recurrence to observe the illustrative risk score increase. Open the **Audit Assistant** and toggle **"Use history"** ON to ask questions across multiple cycles, receiving responses with clickable database references.

---

## Running Tests

Execute the backend test suite with verbose output:

```bash
cd backend
python -m pytest tests/ -v
```

---

## Limitations

- **Audit-Support Tool, Not a Certification Authority:** AuditMind AI assists teams with evidence gathering, pattern detection, and workflow tracking. It does not provide legal or regulatory compliance certification. Final assessments must be made by qualified human auditors.
- **Illustrative Early-Warning Signals:** Risk scores (0–10) are illustrative indicators intended to prioritize team attention, not mathematically validated actuarial predictive models.
- **Synthetic Demo Data:** The provided pre-seeded scenario (ABC Technologies) is synthetic data created specifically for evaluation and testing.
- **LLM Advisory Nature:** Runtime LLM outputs are probabilistic suggestions unverified for accuracy until reviewed and approved by human operators.
- **No Live Enterprise System Telemetry:** Ingestion currently relies on uploaded files and documents; it does not connect to live identity providers or cloud infrastructure APIs.
- **SQLite Default:** SQLite is configured by default for zero-setup demo portability. Replace with PostgreSQL in production deployments.

---

## AI-Assisted Development

> This project was built with **Claude**, **Antigravity** (Google DeepMind), and **ChatGPT** as development tools. All generated code was reviewed, refined, and tested by the team. These tools were used for development assistance only. If a runtime LLM provider (Groq or Gemini) is configured via `LLM_PROVIDER`, the application uses it exclusively for extraction and drafting — but all outputs require human approval before becoming authoritative records.
