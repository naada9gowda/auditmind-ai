# AuditMind AI — 3-Minute Video Demo & Walkthrough Script

**Total Runtime:** ~3 minutes  
**Format:** Screen recording of `preview.html` with voiceover narration.  
**Demonstrator Persona:** Software Engineer / Product Architect  

---

### [0:00 – 0:35] Scene 1: The Problem & The Core Premise

**Visual:**  
Camera focuses on the **Continuous Compliance Dashboard** in `preview.html`. Mouse hovers over the KPI cards: *Total Controls (20)*, *Open Findings (4)*, *Overdue Actions (1)*, *Recurring Findings (1)*.

**Voiceover:**  
> "Enterprise compliance teams face a constant, frustrating reality: audit amnesia. Every quarter, companies spend millions reviewing access controls, patching gaps with ad-hoc spreadsheets, only to have the exact same defect quietly return in the very next cycle.  
> 
> Traditional AI and standard RAG can't solve this because they only read static documents—they have no organizational memory of past audits or failed remediations.  
> 
> This is **AuditMind AI**, an enterprise assurance platform powered by **Hindsight persistent agent memory**."

---

### [0:35 – 1:15] Scene 2: The 3-Cycle Scenario & Chronic Recurrence

**Visual:**  
Click on **"8. Audit History"** in the left sidebar. Mouse scrolls down the vertical timeline showing the 3 cycles for **Control SEC-014**.

**Voiceover:**  
> "Let's look at a real scenario: Control SEC-014, Employee Access Reviews in IT Operations.  
> 
> Back in **January 2026 (Cycle 1)**, an audit identified 14 unreviewed privileged database accounts.  
> In **February**, IT Operations submitted a spreadsheet to patch the issue.  
> But in **April (Cycle 2)**, the same gap recurred.  
> And today, in **July (Cycle 3)**, the review is now 45 days overdue.  
> 
> Watch what happens when we examine this finding in the Findings Review queue."

---

### [1:15 – 2:05] Scene 3: Role Governance & Segregation of Duties

**Visual:**  
Click on **"3. Findings Review"**.  
1. Look at the top bar and click the **"⚙️ Owen (Owner)"** quick persona button.  
2. Show that the **Approve Finding** button is disabled, and an amber banner appears: *"Segregation of Duties Enforced: Owen Owner cannot approve findings in IT Operations."*  
3. Click the **"🛡️ Carlos (Officer)"** quick button. The banner turns teal, and the green **[✓ Approve Finding & Retain in Hindsight]** button becomes active.  
4. Click **Confirm & Approve**. Show the toast notification: *"Finding approved! Retained in Hindsight memory bank for SEC-014."*  
5. Click **"4. Remediation Tracker"**. Show Owen advancing items to *In Progress* and Carlos signing off *Completed*.

**Voiceover:**  
> "Security compliance demands strict role governance. Here in the top bar, we can switch personas in one click.  
> 
> When logged in as **Owen Owner**, the IT manager, segregation of duties prevents Owen from self-approving his own findings or signing off his own remediations.  
> 
> When we switch to **Carlos Compliance**, full assurance authority is granted. When Carlos approves this finding, AuditMind AI triggers a **Hindsight Retain** call, permanently indexing this defect, department, and context into the organization's memory bank."

---

### [2:05 – 2:45] Scene 4: The Payoff — Hindsight Memory ON vs. Stateless Baseline

**Visual:**  
Click on **"9. AI Audit Assistant"**.  
1. Click the starter query: **"Has SEC-014 been a problem before?"** with **🧠 Hindsight Memory ON**.  
2. Show the grounded answer citing Cycle 1 (Jan), Cycle 2 (Apr), and Cycle 3 (Jul).  
3. Click on the citation chip **"📄 AUD-2026-001, Page 4"**. The **Source Drawer** slides open from the right, highlighting the exact excerpt and PyMuPDF extracted page text.  
4. Toggle the demo switch to **"Stateless Baseline"** and ask the same question.  
5. Show the stark contrast: the baseline agent only sees the current open finding and has no awareness of prior cycle history.

**Voiceover:**  
> "Now for the core payoff: our AI Audit Assistant.  
> 
> When we ask: *'Has SEC-014 been a problem before?'* with **Hindsight Memory ON**, the agent immediately recalls the entire cross-cycle lineage. It explains the January finding, the fragile spreadsheet patch in February, and the April recurrence. Every claim has a clickable citation chip that opens our **Source Document Drawer**, showing the verbatim text extracted via PyMuPDF.  
> 
> But look what happens when we switch to the **Stateless Baseline**. The agent has total amnesia. It only sees today's document, missing the chronic pattern entirely."

---

### [2:45 – 3:15] Scene 5: Hindsight Memory Explorer & Wrap Up

**Visual:**  
Click on **"10. Memory Explorer"**.  
Show the 3 pillars: **Retain**, **Recall**, and **Reflect**. Type `SEC-014` into the live search box to show the retained memory chain.  
End on the Dashboard view.

**Voiceover:**  
> "Under the hood in our **Memory Explorer**, we can inspect the active memory bank. Hindsight doesn't just store embeddings—it **Retains** structured facts, **Recalls** temporal context, and **Reflects** to detect systemic weaknesses.  
> 
> With AuditMind AI and Hindsight, enterprises don't just survive audit cycles—they build continuous, self-improving assurance posture.  
> 
> Thank you."
