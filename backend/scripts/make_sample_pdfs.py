"""
scripts/make_sample_pdfs.py — Generate synthetic PDF documents for AuditMind AI.

Run from anywhere:
    python backend/scripts/make_sample_pdfs.py

Generates 9 PDFs into the data/ directory:
  data/sample_audits/
    AUD-2026-001_January_Audit.pdf   (4+ pages; SEC-014 High on page 4)
    AUD-2026-002_April_Audit.pdf     (4+ pages; SEC-014 High)
    AUD-2026-003_July_Audit.pdf      (4+ pages; SEC-014 Medium)
  data/sample_evidence/
    Access_Review_Feb2026.pdf
    Access_Review_Jul2026.pdf
    Expired_Backup_Test_2024.pdf
  data/sample_policies/
    Access_Control_Policy_v2.pdf
    Information_Security_Policy_v3.pdf
    Cryptographic_Controls_Policy_v1.pdf

Each PDF contains explicit control IDs, dates, and reference IDs so the
extractor unit tests have realistic input.
"""

from __future__ import annotations

from pathlib import Path

try:
    import pymupdf as fitz  # PyMuPDF >= 2.x
except ImportError:
    import fitz  # type: ignore[no-redef]  # PyMuPDF 1.x

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent      # auditmind-ai/
_DATA_DIR = _REPO_ROOT / "data"
_AUDITS_DIR = _DATA_DIR / "sample_audits"
_EVIDENCE_DIR = _DATA_DIR / "sample_evidence"
_POLICIES_DIR = _DATA_DIR / "sample_policies"

# A4 dimensions in points
_W, _H = 595, 842
_MARGIN = 55
_CONTENT_RECT = fitz.Rect(_MARGIN, _MARGIN, _W - _MARGIN, _H - _MARGIN)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_doc() -> fitz.Document:
    return fitz.open()


def _add_page(doc: fitz.Document, body: str, header: str = "") -> None:
    """Add an A4 page with optional bold header and body text."""
    page = doc.new_page(width=_W, height=_H)
    y = _MARGIN
    if header:
        hdr_rect = fitz.Rect(_MARGIN, y, _W - _MARGIN, y + 36)
        page.insert_textbox(hdr_rect, header, fontsize=13, fontname="hebo", align=0)
        y += 42
    body_rect = fitz.Rect(_MARGIN, y, _W - _MARGIN, _H - _MARGIN)
    page.insert_textbox(body_rect, body, fontsize=10, fontname="helv", align=0)


def _save(doc: fitz.Document, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))
    doc.close()
    print(f"  [+] {path.relative_to(_REPO_ROOT)}")


# ---------------------------------------------------------------------------
# AUD-2026-001: January 2026 — SEC-014 HIGH (page 4), two other findings
# ---------------------------------------------------------------------------
def make_aud_2026_001() -> None:
    doc = _new_doc()

    # Page 1 — Cover
    _add_page(doc, header="ABC TECHNOLOGIES — INTERNAL AUDIT REPORT", body="""
Reference: AUD-2026-001
Audit Period: Q4 2025 / January 2026
Report Date: 15 January 2026
Prepared by: Internal Audit Team
Reviewed by: Chief Information Security Officer
Classification: Confidential — Internal Use Only

This report presents findings from the internal audit conducted for
ABC Technologies covering the period Q4 2025 through January 2026.
The audit assessed compliance with ISO/IEC 27001 controls across the
IT Operations, HR, Finance, and Engineering departments.

Report Status: Draft — Pending Compliance Officer Approval
""")

    # Page 2 — Scope and Methodology
    _add_page(doc, header="1. AUDIT SCOPE AND METHODOLOGY", body="""
1.1 Scope
This internal audit covers the following information-security controls:
  - Control SEC-014: Employee Access Reviews (IT Operations)
  - Control SEC-006: Network Security Management (IT Operations)
  - Control SEC-012: Asset Inventory Management (IT Operations)
  - Control SEC-003: Cryptographic Controls (Engineering)

Controls were assessed against the evidence expectations defined in the
ABC Technologies control register. Sampling methodology was used for
access reviews, with 100% coverage of privileged accounts.

1.2 Methodology
  - Document review: policies, previous audit reports, evidence submissions
  - Interviews: IT Operations Manager, HR Manager, Engineering Lead
  - Technical inspection: active directory exports, firewall rules, asset lists
  - Previous audit reference: See audit AUD-2025-004 (October 2025)

1.3 Audit Period
Fieldwork was conducted between 05 January 2026 and 15 January 2026.
Evidence was collected covering the period 01 October 2025 to 15 January 2026.
""")

    # Page 3 — Executive Summary (three findings)
    _add_page(doc, header="2. EXECUTIVE SUMMARY", body="""
Three findings were identified during this audit cycle. One finding is
rated High severity and two are rated Medium severity.

FINDING SUMMARY TABLE
  ID     Control    Title                                  Severity  Dept
  F1     SEC-014    Employee Access Reviews — Incomplete   High      IT Operations
  F2     SEC-006    Network Segmentation Gap               Medium    IT Operations
  F3     SEC-012    Asset Inventory Gaps                   Medium    IT Operations

Overall compliance posture for ABC Technologies remains adequate in most
areas. However the access review gap (F1) represents a material risk and
requires immediate remediation before the next quarterly review window.

The findings from the previous audit cycle (AUD-2025-004, October 2025)
included a similar access review gap that was partially remediated but
not fully closed. This recurrence increases severity.

Auditors recommend expedited completion of access reviews for all IT
Operations accounts within 14 days of this report date (15 January 2026).
""")

    # Page 4 — Finding F1 (the key page — SEC-014 High)
    _add_page(doc, header="3. DETAILED FINDINGS", body="""
FINDING F1: Employee Access Reviews — Incomplete Approval Records
Control:    SEC-014 Employee Access Reviews
Department: IT Operations
Severity:   High
Status:     Open
Report Date: 15 January 2026

DESCRIPTION
During the review of employee access records for the IT Operations department,
it was found that the quarterly access review for Q4 2025 has not been
completed. Specifically:

  1. Access review records are incomplete for 15 of 42 user accounts in the
     IT Operations team.
  2. Signed access review records with approval from the IT Operations Manager
     are missing for all 8 privileged accounts (admin-level system access).
  3. Three former employees (departed September–November 2025) retain active
     system access to production environments as of 15 January 2026.
  4. The HR sign-off confirming leavers were processed is absent.

EVIDENCE REQUIRED (per Control SEC-014 expectation)
Signed access review record with approval from IT Operations Manager and HR,
covering all privileged accounts and application access lists.

EVIDENCE REVIEWED
  - Active Directory export dated 10 January 2026
  - HR leaver list (Q4 2025) — received; no corresponding access revocation
  - Previous audit evidence: Access_Review_Q3_2025 — approved, but Q4 missing

RECOMMENDATION
  1. Complete access review for all IT Operations accounts immediately.
  2. Revoke access for three departed employees without delay.
  3. Obtain IT Operations Manager and HR approval signatures on the review record.
  4. Implement automated quarterly reminders tied to the HR offboarding process.
  5. Consider quarterly automated reporting from Active Directory to compliance team.

TARGET REMEDIATION DATE: 29 January 2026
OWNER: IT Operations Manager
""")

    # Page 5 — Findings F2 and F3
    _add_page(doc, header="3. DETAILED FINDINGS (continued)", body="""
FINDING F2: Network Segmentation Gap
Control:    SEC-006 Network Security Management
Department: IT Operations
Severity:   Medium
Status:     Open
Report Date: 15 January 2026

DESCRIPTION
A review of firewall rules identified 3 rules that allow unrestricted
east-west traffic between the production and staging network segments.
This violates the network segmentation policy in place since March 2025.

EVIDENCE REVIEWED
  - Firewall rule export dated 08 January 2026
  - Network architecture diagram (version 2.1, June 2025)

RECOMMENDATION
Review and tighten the three identified firewall rules. Engage the
Engineering Lead to validate that staging-to-production access is
restricted to defined CI/CD service accounts only.

TARGET REMEDIATION DATE: 12 February 2026
OWNER: IT Operations Manager

---

FINDING F3: Asset Inventory Gaps
Control:    SEC-012 Asset Inventory Management
Department: IT Operations
Severity:   Medium
Status:     Open
Report Date: 15 January 2026

DESCRIPTION
The current asset inventory is missing 12 endpoints added in Q4 2025
(end-user laptops and two servers). Asset classification labels are
absent for 5 existing records.

RECOMMENDATION
Update the asset inventory to include all Q4 2025 additions and apply
classification labels per the Data Classification Policy (Control SEC-016).

TARGET REMEDIATION DATE: 05 February 2026
OWNER: IT Operations Manager
""")

    _save(doc, _AUDITS_DIR / "AUD-2026-001_January_Audit.pdf")


# ---------------------------------------------------------------------------
# AUD-2026-002: April 2026 — SEC-014 HIGH, recurring gap
# ---------------------------------------------------------------------------
def make_aud_2026_002() -> None:
    doc = _new_doc()

    _add_page(doc, header="ABC TECHNOLOGIES — INTERNAL AUDIT REPORT", body="""
Reference: AUD-2026-002
Audit Period: Q1 2026 / April 2026
Report Date: 10 April 2026
Prepared by: Internal Audit Team
Reviewed by: Chief Information Security Officer
Classification: Confidential — Internal Use Only

This report presents findings from the Q1 2026 internal audit of ABC Technologies.
Prior audit: AUD-2026-001 (January 2026).
""")

    _add_page(doc, header="1. AUDIT SCOPE AND METHODOLOGY", body="""
1.1 Scope
Controls reviewed in this cycle:
  - Control SEC-014: Employee Access Reviews (IT Operations)
  - Control SEC-013: Vulnerability Management (IT Operations)
  - Control SEC-009: Business Continuity Planning (IT Operations)
  - Control SEC-010: Supplier Security Assessment (Procurement)

1.2 Methodology
  - Document review and evidence collection
  - Interviews with IT Operations Manager and Procurement Manager
  - Technical inspection: patch status reports, BCP test records

Fieldwork: 01 April 2026 to 10 April 2026.
""")

    _add_page(doc, header="2. EXECUTIVE SUMMARY", body="""
Three findings identified. One High, two Medium severity.

FINDING SUMMARY TABLE
  ID     Control    Title                                  Severity  Dept
  F1     SEC-014    Employee Access Reviews — Recurring    High      IT Operations
  F2     SEC-013    Vulnerability Scan Overdue             Medium    IT Operations
  F3     SEC-010    Supplier Assessments Incomplete        Medium    Procurement

Finding F1 is a recurrence of the same gap identified in AUD-2026-001
(January 2026). The partial remediation from that cycle was insufficient:
the Q1 2026 review was initiated but approvals remain unsigned.

This is the second consecutive audit cycle with an unresolved access
review gap for IT Operations (Control SEC-014). Escalation to senior
management is recommended if not resolved before the next review window.
""")

    _add_page(doc, header="3. DETAILED FINDINGS", body="""
FINDING F1: Employee Access Reviews — Recurring Approval Failure
Control:    SEC-014 Employee Access Reviews
Department: IT Operations
Severity:   High
Status:     Open
Report Date: 10 April 2026

DESCRIPTION
This finding is a recurrence of AUD-2026-001 / F1 (January 2026).
Although the IT Operations Manager initiated the Q1 2026 access review
in February 2026, the following gaps remain as of 10 April 2026:

  1. The access review for privileged accounts is 60% complete.
     Approval records (signed access review) are missing for 5 of 8
     privileged accounts.
  2. One former employee (departed February 2026) still has active
     access to two production systems.
  3. HR sign-off confirming the leaver was processed is absent.

Evidence submitted (Access_Review_Feb2026) is incomplete — no
IT Operations Manager approval signature is present on the document.

EVIDENCE REQUIRED (Control SEC-014)
Signed access review record with approval from IT Operations Manager
and HR, covering all privileged accounts and application access lists.

RECOMMENDATION
  1. Obtain IT Operations Manager signature on the February 2026 review.
  2. Complete the remaining 40% of privileged account reviews immediately.
  3. Revoke access for the February 2026 leaver without further delay.
  4. Formally escalate to CISO given this is a second-cycle recurrence.

TARGET REMEDIATION DATE: 24 April 2026
OWNER: IT Operations Manager
""")

    _add_page(doc, header="3. DETAILED FINDINGS (continued)", body="""
FINDING F2: Vulnerability Scan Overdue
Control:    SEC-013 Vulnerability Management
Department: IT Operations
Severity:   Medium
Status:     Open
Report Date: 10 April 2026

DESCRIPTION
The monthly vulnerability scan for March 2026 was not performed.
The last scan on record is dated 28 February 2026. Per Control SEC-013,
scans must be performed monthly and results reviewed within 5 business days.

RECOMMENDATION
Perform the overdue March scan immediately and schedule April scan.
Assign a named owner for the monthly vulnerability scan process.

TARGET REMEDIATION DATE: 17 April 2026
OWNER: IT Operations Manager

---

FINDING F3: Supplier Security Assessments Incomplete
Control:    SEC-010 Supplier Security Assessment
Department: Procurement
Severity:   Medium
Status:     Open
Report Date: 10 April 2026

DESCRIPTION
4 of 7 active suppliers have not had a security assessment completed
in the past 12 months. Control SEC-010 requires annual assessments.
Assessments for suppliers onboarded before January 2025 are overdue.

RECOMMENDATION
Complete overdue supplier assessments and implement annual review reminders.

TARGET REMEDIATION DATE: 30 April 2026
OWNER: Procurement Manager
""")

    _save(doc, _AUDITS_DIR / "AUD-2026-002_April_Audit.pdf")


# ---------------------------------------------------------------------------
# AUD-2026-003: July 2026 — SEC-014 MEDIUM (mostly resolved, one approval missing)
# ---------------------------------------------------------------------------
def make_aud_2026_003() -> None:
    doc = _new_doc()

    _add_page(doc, header="ABC TECHNOLOGIES — INTERNAL AUDIT REPORT", body="""
Reference: AUD-2026-003
Audit Period: Q2 2026 / July 2026
Report Date: 15 July 2026
Prepared by: Internal Audit Team
Reviewed by: Chief Information Security Officer
Classification: Confidential — Internal Use Only

This report presents findings from the Q2 2026 internal audit of ABC Technologies.
Prior audit: AUD-2026-002 (April 2026).
""")

    _add_page(doc, header="1. AUDIT SCOPE AND METHODOLOGY", body="""
1.1 Scope
Controls reviewed in this cycle:
  - Control SEC-014: Employee Access Reviews (IT Operations)
  - Control SEC-007: Secure Software Development (Engineering)
  - Control SEC-015: Security Awareness and Training (HR)
  - Control SEC-018: Audit Logging and Monitoring (IT Operations)

1.2 Methodology
  - Document review and evidence collection
  - Interviews with Engineering Lead, HR Manager, IT Operations Manager
  - Technical inspection: training records, log retention reports, SAST results

Fieldwork: 01 July 2026 to 15 July 2026.
""")

    _add_page(doc, header="2. EXECUTIVE SUMMARY", body="""
Two findings identified. Both Medium severity. This represents a material
improvement compared to AUD-2026-002 (April 2026, two High, one Medium)
and AUD-2026-001 (January 2026, one High, two Medium).

FINDING SUMMARY TABLE
  ID     Control    Title                                     Severity  Dept
  F1     SEC-014    Employee Access Reviews — One Approval    Medium    IT Operations
  F2     SEC-007    SAST Findings Not Formally Tracked        Medium    Engineering

The Q2 2026 access review (Control SEC-014) was largely completed on time.
However the IT Operations Manager approval signature is missing from the
July 2026 review record (Access_Review_Jul2026). All other elements —
including HR sign-off and privileged account coverage — are present and
satisfactory. This represents significant progress over prior cycles.
""")

    _add_page(doc, header="3. DETAILED FINDINGS", body="""
FINDING F1: Employee Access Reviews — Single Approval Missing
Control:    SEC-014 Employee Access Reviews
Department: IT Operations
Severity:   Medium
Status:     Open
Report Date: 15 July 2026

DESCRIPTION
The Q2 2026 employee access review for IT Operations was completed on
schedule (10 July 2026). All 42 user accounts were reviewed, all 8
privileged accounts were covered, and the HR sign-off confirming no
active leavers is present.

However, the IT Operations Manager approval signature is absent from
the final access review record (Access_Review_Jul2026). Per Control
SEC-014, both the IT Operations Manager and HR must approve the
completed review record before it can be considered evidenced.

This is a reduced scope versus previous audit cycles (AUD-2026-001,
AUD-2026-002) where multiple approval records and coverage gaps existed.

EVIDENCE REVIEWED
  - Access_Review_Jul2026 submitted 10 July 2026
  - Active Directory export 10 July 2026 — consistent with review
  - HR sign-off present and dated 10 July 2026
  - IT Operations Manager approval: MISSING

EVIDENCE REQUIRED (Control SEC-014)
Signed access review record with approval from IT Operations Manager
and HR, covering all privileged accounts and application access lists.

RECOMMENDATION
  1. Obtain IT Operations Manager signature on Access_Review_Jul2026.
  2. No further access or coverage gaps were identified — good progress.
  3. Consider implementing a digital approval workflow to avoid future
     omissions of approval signatures.

TARGET REMEDIATION DATE: 22 July 2026
OWNER: IT Operations Manager
""")

    _add_page(doc, header="3. DETAILED FINDINGS (continued)", body="""
FINDING F2: SAST Findings Not Formally Tracked
Control:    SEC-007 Secure Software Development
Department: Engineering
Severity:   Medium
Status:     Open
Report Date: 15 July 2026

DESCRIPTION
Static Application Security Testing (SAST) scans are being performed as
part of the CI/CD pipeline. However, findings from these scans are not
formally tracked in a risk register or issue tracker with assigned owners
and remediation deadlines. Three medium-severity SAST findings from
June 2026 have no documented remediation status.

RECOMMENDATION
Integrate SAST findings into the existing risk register process.
Assign owners and remediation SLAs to all open SAST findings.
Engineering Lead to review and triage the June 2026 findings within 10 days.

TARGET REMEDIATION DATE: 25 July 2026
OWNER: Engineering Lead
""")

    _save(doc, _AUDITS_DIR / "AUD-2026-003_July_Audit.pdf")


# ---------------------------------------------------------------------------
# Evidence: Access_Review_Feb2026.pdf — completed review, no manager approval
# ---------------------------------------------------------------------------
def make_access_review_feb2026() -> None:
    doc = _new_doc()
    _add_page(doc, header="EMPLOYEE ACCESS REVIEW — Q4 2025 / FEBRUARY 2026", body="""
Document Reference: EVD-2026-011
Control: SEC-014 Employee Access Reviews
Department: IT Operations
Review Date: 14 February 2026
Submitted by: Owen Owner (IT Operations Manager)
Classification: Confidential

REVIEW SUMMARY
This document records the completion of the Q4 2025 employee access review
for the IT Operations department, as required by Control SEC-014.

ACCOUNTS REVIEWED
  Total accounts in scope:  42
  Accounts reviewed:        42
  Access confirmed correct: 37
  Access modified:           4
  Access revoked:            1

PRIVILEGED ACCOUNTS
  Total privileged accounts: 8
  Reviewed:                  5    (63% complete)
  Pending review:            3

LEAVERS PROCESSED
  Leavers in period (Q4 2025): 1
  Access revoked:              1
  Access revocation date:      22 November 2025

REVIEW STATUS: PARTIALLY COMPLETE
  - Privileged account review not fully complete (3 accounts pending)
  - Review spreadsheet signed by control owner (see below)

SIGN-OFF
  Control Owner (IT Operations Manager): Owen Owner   Date: 14 February 2026
  IT Operations Manager Approval Signature:           [SIGNATURE MISSING]
  HR Sign-off:                                        [PENDING]

NOTE: This evidence document was submitted in response to audit finding F1
from AUD-2026-001 (January 2026). Completion of privileged account review
and approval signatures are required to fully satisfy Control SEC-014.
""")
    _save(doc, _EVIDENCE_DIR / "Access_Review_Feb2026.pdf")


# ---------------------------------------------------------------------------
# Evidence: Access_Review_Jul2026.pdf — full review, one approval missing
# ---------------------------------------------------------------------------
def make_access_review_jul2026() -> None:
    doc = _new_doc()
    _add_page(doc, header="EMPLOYEE ACCESS REVIEW — Q2 2026 / JULY 2026", body="""
Document Reference: EVD-2026-031
Control: SEC-014 Employee Access Reviews
Department: IT Operations
Review Date: 10 July 2026
Submitted by: Owen Owner (IT Operations Manager)
Classification: Confidential

REVIEW SUMMARY
This document records the completion of the Q2 2026 employee access review
for the IT Operations department, as required by Control SEC-014.

ACCOUNTS REVIEWED
  Total accounts in scope:  42
  Accounts reviewed:        42
  Access confirmed correct: 40
  Access modified:           2
  Access revoked:            0

PRIVILEGED ACCOUNTS
  Total privileged accounts: 8
  Reviewed:                  8    (100% complete)
  No privileged account changes required.

LEAVERS PROCESSED
  Leavers in period (Q2 2026): 0
  No leavers to process this quarter.

REVIEW STATUS: COMPLETE (pending IT Operations Manager approval signature)

SIGN-OFF
  Control Owner Submission:                           Owen Owner   10 July 2026
  HR Sign-off (confirming no active leavers):         HR Manager   10 July 2026
  IT Operations Manager Approval Signature:           [SIGNATURE MISSING]

NOTE: This evidence was submitted as part of the Q2 2026 internal audit
(reference AUD-2026-003, July 2026). All coverage requirements are met.
Only the IT Operations Manager approval signature remains outstanding.
""")
    _save(doc, _EVIDENCE_DIR / "Access_Review_Jul2026.pdf")


# ---------------------------------------------------------------------------
# Evidence: Expired_Backup_Test_2024.pdf — dated 2024, for backup control
# ---------------------------------------------------------------------------
def make_expired_backup_test() -> None:
    doc = _new_doc()
    _add_page(doc, header="BACKUP AND RECOVERY TEST RECORD — 2024", body="""
Document Reference: EVD-2024-008
Control: SEC-009 Business Continuity Planning
Department: IT Operations
Test Date: 20 March 2024
Submitted by: IT Operations Team
Classification: Internal Use Only

BACKUP RESTORE TEST SUMMARY
This document records the annual backup and recovery test performed for
ABC Technologies in accordance with Control SEC-009 Business Continuity
Planning requirements.

TEST SCOPE
  - Production database backup restore to staging environment
  - File server backup restore test (10 GB sample set)
  - Recovery time objective (RTO) verification
  - Recovery point objective (RPO) verification

TEST RESULTS
  Database restore:          PASS   (completed in 45 minutes, RTO target: 60 min)
  File server restore:       PASS   (completed in 22 minutes)
  RTO achieved:              Yes    (45 min actual vs 60 min target)
  RPO achieved:              Yes    (last backup 23:00 previous day, RPO target 24h)

TEST DATE: 20 March 2024
NEXT SCHEDULED TEST: March 2025

SIGN-OFF
  IT Operations Manager:     Approved   22 March 2024
  CISO Review:               Approved   25 March 2024

NOTE: This evidence is dated March 2024. As of the current audit cycle
(2026), this evidence is EXPIRED — a fresh annual test record for 2025
and 2026 must be provided to satisfy Control SEC-009.
""")
    _save(doc, _EVIDENCE_DIR / "Expired_Backup_Test_2024.pdf")


# ---------------------------------------------------------------------------
# Policy: Access_Control_Policy_v2.pdf
# ---------------------------------------------------------------------------
def make_access_control_policy() -> None:
    doc = _new_doc()
    _add_page(doc, header="ACCESS CONTROL POLICY — VERSION 2.0", body="""
Document Reference: POL-2025-002
Control: SEC-002 Access Control Policy
Version: 2.0
Effective Date: 01 March 2025
Review Date: 01 March 2026
Approved by: Chief Information Security Officer
Classification: Internal Use Only

1. PURPOSE
This policy establishes the requirements for controlling access to ABC
Technologies information systems, applications, and data assets.

2. SCOPE
Applies to all employees, contractors, and third parties with access
to ABC Technologies systems. Covers all system types: on-premises,
cloud, and hybrid.

3. ACCESS CONTROL PRINCIPLES
  3.1 Least privilege: users are granted minimum access required.
  3.2 Need-to-know: access to sensitive data is restricted to those
      with a documented business need.
  3.3 Separation of duties: critical functions require more than one
      person to complete.

4. USER ACCESS MANAGEMENT
  4.1 User provisioning must be approved by the department manager.
  4.2 Privileged access requires CISO approval.
  4.3 Access reviews (Control SEC-014) must be conducted quarterly.
  4.4 Leavers must have access revoked within 1 business day of departure.

5. PASSWORD REQUIREMENTS
  Minimum 12 characters, complexity enforced, 90-day rotation,
  no reuse of last 12 passwords. MFA required for all privileged accounts.

6. REVIEW AND COMPLIANCE
  This policy is reviewed annually. Non-compliance is reported to the
  CISO and may result in disciplinary action.

DOCUMENT HISTORY
  v1.0  January 2024  Initial release
  v2.0  March 2025    Added MFA requirement; updated leaver SLA to 1 day
""")
    _save(doc, _POLICIES_DIR / "Access_Control_Policy_v2.pdf")


# ---------------------------------------------------------------------------
# Policy: Information_Security_Policy_v3.pdf
# ---------------------------------------------------------------------------
def make_information_security_policy() -> None:
    doc = _new_doc()
    _add_page(doc, header="INFORMATION SECURITY POLICY — VERSION 3.0", body="""
Document Reference: POL-2025-001
Control: SEC-001 Information Security Policy
Version: 3.0
Effective Date: 15 January 2025
Review Date: 15 January 2026
Approved by: Chief Executive Officer
Classification: Internal Use Only

1. PURPOSE
This policy establishes the information security management framework
for ABC Technologies in accordance with ISO/IEC 27001.

2. POLICY STATEMENT
ABC Technologies is committed to protecting the confidentiality,
integrity, and availability of all information assets against threats.

3. SCOPE
Applies to all employees, contractors, board members, and third-party
service providers.

4. INFORMATION SECURITY OBJECTIVES
  4.1 Protect client and employee data from unauthorised disclosure.
  4.2 Maintain availability of critical systems at 99.5% or above.
  4.3 Detect and respond to security incidents within defined SLAs.
  4.4 Achieve and maintain ISO/IEC 27001 certification.

5. ROLES AND RESPONSIBILITIES
  - Board: Approve policy; ensure resources for ISMS.
  - CISO: Own and maintain the ISMS; report to Board.
  - All staff: Comply with policy; report security incidents.

6. SUPPORTING CONTROLS
  Key controls referenced: SEC-001 through SEC-020 (see control register).
  All controls are assessed quarterly or annually per their defined cadence.

7. REVIEW
This policy is reviewed annually by the CISO and approved by the CEO.

DOCUMENT HISTORY
  v1.0  January 2023  Initial release
  v2.0  January 2024  Updated to align with ISO 27001:2022
  v3.0  January 2025  Added supplier security obligations; updated roles
""")
    _save(doc, _POLICIES_DIR / "Information_Security_Policy_v3.pdf")


# ---------------------------------------------------------------------------
# Policy: Cryptographic_Controls_Policy_v1.pdf
# ---------------------------------------------------------------------------
def make_cryptographic_policy() -> None:
    doc = _new_doc()
    _add_page(doc, header="CRYPTOGRAPHIC CONTROLS POLICY — VERSION 1.0", body="""
Document Reference: POL-2024-003
Control: SEC-003 Cryptographic Controls
Version: 1.0
Effective Date: 01 June 2024
Review Date: 01 June 2025
Approved by: Chief Information Security Officer
Classification: Internal Use Only

1. PURPOSE
This policy defines the requirements for cryptographic controls used
to protect information at ABC Technologies.

2. SCOPE
Applies to all systems processing, storing, or transmitting sensitive
or confidential information.

3. APPROVED ALGORITHMS
  Symmetric encryption:  AES-256 (preferred), AES-128 (minimum)
  Asymmetric encryption: RSA-4096, RSA-2048 (minimum), ECC P-256
  Hashing:               SHA-256 (minimum), SHA-512 (preferred)
  TLS:                   TLS 1.2 (minimum), TLS 1.3 (preferred)
  Prohibited:            MD5, SHA-1, DES, 3DES, RC4, SSL 2.0/3.0

4. KEY MANAGEMENT
  4.1 Encryption keys must be generated using a cryptographically
      secure random number generator.
  4.2 Key length must meet the minimum standards above.
  4.3 Keys must be rotated at least annually or upon suspected compromise.
  4.4 Key storage must use a hardware security module (HSM) or equivalent
      approved key management service.
  4.5 Key access must be logged and reviewed quarterly.

5. CERTIFICATE MANAGEMENT
  All public-key certificates must use an approved CA.
  Certificate expiry must be monitored; renewal initiated 30 days prior.

6. REVIEW
This policy is reviewed annually by the CISO.

DOCUMENT HISTORY
  v1.0  June 2024  Initial release
""")
    _save(doc, _POLICIES_DIR / "Cryptographic_Controls_Policy_v1.pdf")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    print("Generating synthetic PDFs for AuditMind AI...\n")

    print("Audit Reports:")
    make_aud_2026_001()
    make_aud_2026_002()
    make_aud_2026_003()

    print("\nEvidence Documents:")
    make_access_review_feb2026()
    make_access_review_jul2026()
    make_expired_backup_test()

    print("\nPolicies:")
    make_access_control_policy()
    make_information_security_policy()
    make_cryptographic_policy()

    print("\nAll PDFs generated successfully.")
    print(f"Output directory: {_DATA_DIR}")


if __name__ == "__main__":
    main()
