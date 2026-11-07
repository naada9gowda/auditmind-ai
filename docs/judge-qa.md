# Judge Q&A — AuditMind AI

Key questions and answers for hackathon judges and technical evaluators.

---

### Q: Are you using Hindsight or any external memory product?
**A:** **No.** All audit history queries run directly against our own relational database (PostgreSQL/SQLite) using structured SQL queries via SQLAlchemy. The `HistoryService` retrieves real approved finding records, status history trails, and audit cycle links. There is no external memory product, no third-party vector/embeddings database, and zero dependence on Hindsight or external memory services.

---

### Q: What are Claude, Antigravity, and ChatGPT used for?
**A:** They were used for **development assistance only** — generating boilerplate, suggesting architectural approaches, and reviewing logic during the build. If a runtime LLM provider (`groq` or `gemini`) is configured via `LLM_PROVIDER`, the application uses it exclusively for document text extraction and draft finding suggestions at runtime. All runtime LLM output is strictly validated against Pydantic schemas, stored with `ai_generated=True` and `review_status="Draft"`, and requires explicit human approval before entering any authoritative record.

---

### Q: How is this different from a document chatbot?
**A:** AuditMind AI is a comprehensive compliance management and audit intelligence platform, not a document chat interface.
- **Continuous Compliance Register:** Tracks ISO 27001-inspired controls, cadences, and evidence states across time.
- **Audit Findings Lifecycle:** Manages findings with strict role-based state machines (`Open` → `In Remediation` → `Ready for Review` → `Closed`) backed by an append-only `status_history` audit trail.
- **Multi-Cycle Recurrence Intelligence:** Connects findings across historical audit cycles (e.g., January, April, and July audits) using deterministic match scoring (control overlap, department match, keyword Jaccard similarity, time proximity).
- **Early-Warning Risk Scoring:** Computes illustrative risk signals combining severity, confirmed recurrence count, overdue remediation days, and evidence gaps.
- **Deterministic Evidence Verification:** Performs regex-based field-level verification against control-specific requirements rather than probabilistic LLM guessing.
A standard chatbot cannot perform cross-cycle relational recurrence analysis, maintain an immutable audit trail, or enforce governance state machines.

---

### Q: How do you reduce hallucinations?
**A:** Hallucination prevention is designed into the core system architecture:
1. **Source Backing & References:** Every claim in assistant responses is backed by retrieved database records and presented with exact source document names, page numbers, and verbatim excerpts.
2. **Draft Isolation:** All extracted findings and mapped evidence are persisted with `review_status="Draft"`. Nothing becomes authoritative without human reviewer confirmation.
3. **Deterministic Evidence Verification:** The evidence verifier checks specific text patterns and required fields deterministically — it does not ask an LLM for an opinion on compliance.
4. **Retrieved, Never Recalled:** History is retrieved via structured SQL queries, not recalled from model memory. The model (if enabled) is supplied only with actual database records relevant to the query.
5. **No Groundless Assertions:** If no matching records exist, the system deterministically reports `"I found no relevant records for that."` rather than speculating.
6. **Strict Schema Validation & Fallback:** All LLM outputs are parsed through Pydantic v2 schemas; any parsing or schema validation failure falls back cleanly to deterministic rule-based logic.

---

### Q: Does this certify compliance? Can we use it in a real audit?
**A:** **No.** AuditMind AI is an **audit-support and intelligence tool**, not a certification authority or regulatory body. It surfaces gaps, tracks remediations, identifies recurrence patterns, and gathers evidence for qualified human auditors to examine. The final compliance determination must always be made by an authorized, qualified human auditor. Risk scores are explicitly labeled as **illustrative early-warning signals**, and every status transition requires authorized human sign-off.

---

### Q: What if the LLM is unavailable?
**A:** **Everything still works.** When `LLM_PROVIDER=none` (the default configuration) or if an external provider experiences an outage or rate limit, AuditMind AI falls back seamlessly to deterministic rule-based text extraction, keyword mapping, regex pattern matching, and templated assistant answers. The user interface displays a clear notice when operating in deterministic mode.
