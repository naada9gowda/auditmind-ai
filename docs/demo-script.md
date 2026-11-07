# 60-Second Demo Walkthrough — AuditMind AI

> **Audience:** Hackathon Judges and Evaluators  
> **Duration:** 60 seconds  
> **Core Theme:** Continuous compliance monitoring, cross-cycle audit intelligence, and human-in-the-loop verification.

---

## Prerequisites (Before Demo Begins)
1. Backend running: `cd backend && python -m uvicorn app.main:app --reload --port 8000`
2. Frontend running: `cd frontend && npm run dev` (running at `http://localhost:5173`)
3. Database seeded with base data: `python -m app.seed --clean`
4. Sample reports available: `data/sample_audits/AUD-2026-001_Jan_Audit.pdf` and `AUD-2026-002_Apr_Audit.pdf`
5. Active user header: `Carlos Compliance` (`compliance_officer` role).

---

## Second-by-Second Walkthrough

### ⏱️ 00:00 – 00:10: Continuous Compliance Dashboard & Context
- **Action:** Open browser at `http://localhost:5173/`.
- **Display:** Point out the KPI summary cards (Total Controls, Open Gaps, Overdue Actions, Pending Reviews).
- **Narrative:**
  > *"Compliance teams typically struggle across repeated audit cycles, losing context on recurring gaps. Here is ABC Technologies' compliance workspace. Notice our ISO 27001 control register and audit cycle history."*
- **Action:** Navigate to **Document Centre** → Click **Upload**, drag in `AUD-2026-001` (January Audit Report).

---

### ⏱️ 00:10 – 00:20: Document Ingestion, Processing & Analysis
- **Action:** Click **Process**. PyMuPDF extracts text pages synchronously.
- **Action:** Click **Analyze**.
- **Display:** Show draft findings generated with the yellow `AiSuggestionBanner`. Highlight finding under control **SEC-014** (*User Access Review*) on page 4.
- **Narrative:**
  > *"The system ingests the report and extracts candidate findings. Notice this finding on SEC-014 stating 'approval records are missing'. It is explicitly labeled DRAFT — AI suggestions never become authoritative records on their own."*

---

### ⏱️ 00:20 – 00:30: Human-in-the-Loop Finding Review & Approval
- **Action:** Open **Findings Review** modal or drawer.
- **Display:** Show the side-by-side view: original source document page text on the left, verbatim extracted excerpt on the right.
- **Action:** Click **Approve** as `compliance_officer`.
- **Narrative:**
  > *"Carlos Compliance reviews the exact source text against the excerpt. With one click, he approves it. The finding transitions to an Approved record and an immutable status_history audit log is written."*

---

### ⏱️ 00:30 – 00:40: Multi-Cycle Recurrence Detection
- **Action:** Upload the next cycle report: `AUD-2026-002` (April Audit Report). Click **Analyze**, then navigate to review the new SEC-014 finding.
- **Action:** Click **Approve**.
- **Display:** The **"Possible related past findings"** section automatically appears beneath the finding. Show the January finding matched with reason:
  > *"Same control SEC-014, same department IT Operations, shared keywords: access, review, approval, missing"*
- **Narrative:**
  > *"When April's finding is approved, our relational SQL HistoryService immediately flags the January finding. No external vector database or Hindsight — pure structured SQL scoring on control ID, department, and token Jaccard similarity."*

---

### ⏱️ 00:40 – 00:50: Confirm Recurrence & Early-Warning Risk Escalation
- **Action:** Click **Confirm Recurrence**.
- **Display:** Navigate to **Risk Intelligence** view. Show the April finding's risk score jump (confirming recurrence adds up to +3 points). Click **Create Remediation** to assign an action to Owen Owner with a due date.
- **Narrative:**
  > *"Once Carlos confirms this is a recurring gap, the illustrative risk score automatically escalates. We immediately attach a tracked remediation action, creating accountability."*

---

### ⏱️ 00:50 – 01:00: Audit Assistant (Current vs. Historical Context)
- **Action:** Open **Audit Assistant** chat drawer.
- **Action:** Toggle **"Use history"** switch **OFF**. Prompt: *"Has SEC-014 been a problem before?"*
  - **Result:** Assistant answers based on isolated current cycle data only.
- **Action:** Toggle **"Use history"** switch **ON**. Submit the same question:
  - **Result:** Assistant cites both January and April findings with clickable references, dates, and remediation statuses.
- **Narrative:**
  > *"With history enabled, the assistant retrieves real database records across audit cycles. Every response includes verified source citations."*

---

## Closing Summary (5 Seconds)
> *"AuditMind AI delivers continuous compliance intelligence with human approval at every critical gate, transparent deterministic evidence checks, and zero autonomous certification."*
