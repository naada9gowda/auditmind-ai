"""
seed.py — Idempotent seed script for AuditMind AI.

Usage:
    python -m app.seed                # base seed: org + users + controls
    python -m app.seed --demo         # base + 3-cycle ABC Technologies scenario
    python -m app.seed --clean        # wipe + re-seed org/users/controls only
    python -m app.seed --reset        # wipe only demo data, keep base

Creates (base):
  - 1 organisation:  "ABC Technologies"
  - 4 users:         admin, compliance_officer, control_owner, auditor
  - 20 ISO 27001-inspired controls (including SEC-014 "Employee access reviews")

Demo adds (--demo):
  - 3 audit cycles  (Jan / Apr / Jul 2026)
  - ~30 findings distributed across 4 departments + 3 audit cycles
  - 15 remediation actions mixing statuses
  - related_findings for the SEC-014 recurrence chain
  - status_history rows for key transitions

Safe to run multiple times — existing records are detected by unique keys.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from typing import Optional

from app.models.organisation import Organisation
from app.models.user import User
from app.models.control import Control

# ── Seed data ──────────────────────────────────────────────────────────────────

ORG_NAME = "ABC Technologies"

USERS = [
    {
        "name": "Alice Admin",
        "email": "alice.admin@abctech.example",
        "role": "admin",
    },
    {
        "name": "Carlos Compliance",
        "email": "carlos.compliance@abctech.example",
        "role": "compliance_officer",
    },
    {
        "name": "Owen Owner",
        "email": "owen.owner@abctech.example",
        "role": "control_owner",
    },
    {
        "name": "Audrey Auditor",
        "email": "audrey.auditor@abctech.example",
        "role": "auditor",
    },
]

# 20 ISO/IEC 27001-inspired controls
# Departments: IT Operations, HR, Finance, Engineering
CONTROLS = [
    {
        "control_code": "SEC-001",
        "title": "Information Security Policy",
        "description": "A set of policies for information security shall be defined, approved by management, published, and communicated.",
        "owner": "Chief Information Security Officer",
        "cadence": "annual",
        "evidence_expectation": "Signed policy document with management approval date.",
        "status": "Compliant",
    },
    {
        "control_code": "SEC-002",
        "title": "Access Control Policy",
        "description": "An access control policy shall be established, documented, and reviewed based on business and security requirements.",
        "owner": "IT Operations Manager",
        "cadence": "annual",
        "evidence_expectation": "Access control policy document with version history and approvals.",
        "status": "Compliant",
    },
    {
        "control_code": "SEC-003",
        "title": "Cryptographic Controls",
        "description": "A policy on the use of cryptographic controls for protection of information shall be developed and implemented.",
        "owner": "IT Operations Manager",
        "cadence": "annual",
        "evidence_expectation": "Encryption standards document and evidence of implementation in key systems.",
        "status": "Needs Review",
    },
    {
        "control_code": "SEC-004",
        "title": "Physical Security Perimeter",
        "description": "Security perimeters shall be defined and used to protect areas that contain sensitive information and information-processing facilities.",
        "owner": "Facilities Manager",
        "cadence": "semi-annual",
        "evidence_expectation": "Physical access logs, security perimeter inspection report.",
        "status": "Compliant",
    },
    {
        "control_code": "SEC-005",
        "title": "Clear Desk and Clear Screen Policy",
        "description": "A clear desk policy for papers and removable storage media and a clear screen policy for information-processing facilities shall be adopted.",
        "owner": "HR Manager",
        "cadence": "annual",
        "evidence_expectation": "Policy document and evidence of communication to all staff.",
        "status": "Not Assessed",
    },
    {
        "control_code": "SEC-006",
        "title": "Network Security Management",
        "description": "Networks shall be managed and controlled to protect information in systems and applications.",
        "owner": "IT Operations Manager",
        "cadence": "quarterly",
        "evidence_expectation": "Network architecture diagram, firewall rule review report, vulnerability scan results.",
        "status": "Needs Review",
    },
    {
        "control_code": "SEC-007",
        "title": "Secure Software Development",
        "description": "Rules for the development of software and systems shall be established and applied to developments within the organisation.",
        "owner": "Engineering Lead",
        "cadence": "semi-annual",
        "evidence_expectation": "Secure SDLC policy, evidence of code reviews, SAST/DAST scan results.",
        "status": "Gap Identified",
    },
    {
        "control_code": "SEC-008",
        "title": "Information Security Incident Management",
        "description": "Management responsibilities and procedures shall be established to ensure a quick, effective, and orderly response to information security incidents.",
        "owner": "Chief Information Security Officer",
        "cadence": "semi-annual",
        "evidence_expectation": "Incident response plan, evidence of tabletop exercise or drill within the period.",
        "status": "Compliant",
    },
    {
        "control_code": "SEC-009",
        "title": "Business Continuity Planning",
        "description": "The organisation shall determine its requirements for information security and the continuity of information security management in adverse situations.",
        "owner": "IT Operations Manager",
        "cadence": "annual",
        "evidence_expectation": "BCP/DR plan document, evidence of annual test/exercise results.",
        "status": "Needs Review",
    },
    {
        "control_code": "SEC-010",
        "title": "Supplier Security Assessment",
        "description": "Information security requirements for mitigating the risks associated with supplier access to the organisation's assets shall be agreed and documented.",
        "owner": "Procurement Manager",
        "cadence": "annual",
        "evidence_expectation": "Completed supplier security questionnaires, risk ratings, and signed agreements.",
        "status": "Not Assessed",
    },
    {
        "control_code": "SEC-011",
        "title": "Information Security Risk Assessment",
        "description": "The organisation shall perform information security risk assessments at planned intervals or when significant changes are proposed.",
        "owner": "Chief Information Security Officer",
        "cadence": "annual",
        "evidence_expectation": "Risk register with current risk ratings, treatment plans, and approval signatures.",
        "status": "Compliant",
    },
    {
        "control_code": "SEC-012",
        "title": "Asset Inventory Management",
        "description": "Assets associated with information and information-processing facilities shall be identified and an inventory of these assets shall be drawn up and maintained.",
        "owner": "IT Operations Manager",
        "cadence": "quarterly",
        "evidence_expectation": "Up-to-date asset inventory report with owner assignments and classification labels.",
        "status": "Needs Review",
    },
    {
        "control_code": "SEC-013",
        "title": "Vulnerability Management",
        "description": "Technical vulnerabilities of information systems in use shall be obtained in a timely fashion and the organisation's exposure to such vulnerabilities evaluated.",
        "owner": "IT Operations Manager",
        "cadence": "monthly",
        "evidence_expectation": "Vulnerability scan reports, patch status report, exception register.",
        "status": "Gap Identified",
    },
    {
        # Required control per spec
        "control_code": "SEC-014",
        "title": "Employee Access Reviews",
        "description": (
            "Formal user access rights reviews shall be conducted at regular intervals "
            "to ensure that users retain only the access rights required for their current role. "
            "Leavers and role-changers must be actioned within defined SLAs."
        ),
        "owner": "IT Operations Manager",
        "cadence": "quarterly",
        "evidence_expectation": (
            "Signed access review record with approval from IT Operations Manager "
            "and HR, covering all privileged accounts and application access lists."
        ),
        "status": "Needs Review",
    },
    {
        "control_code": "SEC-015",
        "title": "Security Awareness and Training",
        "description": "All employees of the organisation and, where relevant, contractors shall receive appropriate awareness education and training.",
        "owner": "HR Manager",
        "cadence": "annual",
        "evidence_expectation": "Training completion records showing >90% staff completion within the period.",
        "status": "Compliant",
    },
    {
        "control_code": "SEC-016",
        "title": "Data Classification",
        "description": "Information shall be classified in terms of legal requirements, value, criticality, and sensitivity to unauthorised disclosure or modification.",
        "owner": "Chief Information Security Officer",
        "cadence": "annual",
        "evidence_expectation": "Data classification policy and evidence of labelling across key data stores.",
        "status": "Not Assessed",
    },
    {
        "control_code": "SEC-017",
        "title": "Change Management",
        "description": "Changes to the organisation, business processes, information-processing facilities, and systems that affect information security shall be controlled.",
        "owner": "Engineering Lead",
        "cadence": "quarterly",
        "evidence_expectation": "Change log from ITSM tool covering the period, with approvals and rollback evidence.",
        "status": "Compliant",
    },
    {
        "control_code": "SEC-018",
        "title": "Audit Logging and Monitoring",
        "description": "Event logs recording user activities, exceptions, faults, and information security events shall be produced, kept, and regularly reviewed.",
        "owner": "IT Operations Manager",
        "cadence": "monthly",
        "evidence_expectation": "Log retention policy, evidence of centralised log aggregation, and sample review reports.",
        "status": "Compliant",
    },
    {
        "control_code": "SEC-019",
        "title": "Password Management Policy",
        "description": "A password management system shall be implemented that enforces minimum complexity, rotation, and prohibits re-use of recent passwords.",
        "owner": "IT Operations Manager",
        "cadence": "annual",
        "evidence_expectation": "Password policy document and system configuration screenshots showing enforcement.",
        "status": "Compliant",
    },
    {
        "control_code": "SEC-020",
        "title": "Third-Party Risk Assessment",
        "description": "Risks associated with the use of third-party products or services shall be identified, assessed, and treated prior to engagement and throughout the relationship.",
        "owner": "Chief Information Security Officer",
        "cadence": "annual",
        "evidence_expectation": "Third-party risk register with ratings, review dates, and mitigating controls documented.",
        "status": "Not Assessed",
    },
]

# ---------------------------------------------------------------------------
# Demo marker — all demo records carry this note in status_history or can be
# identified by membership in demo audit cycles.
# ---------------------------------------------------------------------------
_DEMO_CYCLE_NAMES = (
    "January 2026 Audit",
    "April 2026 Audit",
    "July 2026 Audit",
)


# ---------------------------------------------------------------------------
# Base seed
# ---------------------------------------------------------------------------

def seed(session_factory=None, bind_engine=None) -> dict:
    """
    Create seed data idempotently (org + users + controls).

    Returns a dict of created/found objects for use by the demo seeder.
    """
    import app.database as db_module

    _engine = bind_engine or db_module.engine
    _session_factory = session_factory or db_module.SessionLocal

    db_module.Base.metadata.create_all(bind=_engine)

    # Apply is_recurrence migration if column is missing
    _apply_migrations(_engine)

    db = _session_factory()
    result: dict = {}
    try:
        # -- Organisation ----------------------------------------------------------
        org = db.query(Organisation).filter_by(name=ORG_NAME).first()
        if not org:
            org = Organisation(name=ORG_NAME, created_at=datetime.now(timezone.utc))
            db.add(org)
            db.flush()
            print(f"  [+] Created organisation: {org.name}  id={org.id}")
        else:
            print(f"  [=] Organisation already exists: {org.name}  id={org.id}")
        result["org"] = org

        # -- Users -----------------------------------------------------------------
        created_users: list[User] = []
        for u in USERS:
            user = db.query(User).filter_by(email=u["email"]).first()
            if not user:
                user = User(organisation_id=org.id, **u)
                db.add(user)
                db.flush()
                print(f"  [+] Created user: {user.name} ({user.role})  id={user.id}")
            else:
                print(f"  [=] User already exists: {user.name}  id={user.id}")
            created_users.append(user)
        result["users"] = created_users

        # -- Controls --------------------------------------------------------------
        created_controls: list[Control] = []
        for c in CONTROLS:
            control = db.query(Control).filter_by(
                organisation_id=org.id,
                control_code=c["control_code"],
            ).first()
            if not control:
                control = Control(organisation_id=org.id, **c)
                db.add(control)
                db.flush()
                print(f"  [+] Created control: {control.control_code} - {control.title}")
            else:
                print(f"  [=] Control already exists: {control.control_code} - {control.title}")
            created_controls.append(control)
        result["controls"] = created_controls

        db.commit()
        print("\nBase seed complete.")
        print("\n-- User IDs (use as X-User-Id header) --")
        for u in created_users:
            db.refresh(u)
            print(f"  {u.role:<22}  {u.id}  ({u.email})")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return result


def _apply_migrations(engine) -> None:
    """Add any columns that may not exist in legacy DB files (SQLite only)."""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE findings ADD COLUMN is_recurrence BOOLEAN DEFAULT 0"))
            conn.commit()
            print("  [migrate] Added is_recurrence column to findings.")
        except Exception:
            pass  # column already exists — ignore


# ---------------------------------------------------------------------------
# Demo seed
# ---------------------------------------------------------------------------

def seed_demo(session_factory=None, bind_engine=None) -> None:
    """
    Seed the 3-cycle ABC Technologies audit scenario.

    Idempotent: skips already-present audit cycles (detected by name).
    Requires base seed to have been run first (org + users + controls must exist).
    """
    import app.database as db_module
    from app.models.audit_cycle import AuditCycle
    from app.models.finding import Finding
    from app.models.remediation import RemediationAction
    from app.models.related_finding import RelatedFinding
    from app.models.status_history import StatusHistory

    _session_factory = session_factory or db_module.SessionLocal
    db = _session_factory()

    try:
        # -- Resolve base objects --------------------------------------------------
        org = db.query(Organisation).filter_by(name=ORG_NAME).first()
        if not org:
            raise RuntimeError("Base seed must be run before --demo.")

        def _user(role: str) -> User:
            return db.query(User).filter_by(
                organisation_id=org.id, role=role
            ).first()

        def _ctrl(code: str) -> Control:
            return db.query(Control).filter_by(
                organisation_id=org.id, control_code=code
            ).first()

        admin = _user("admin")
        co = _user("compliance_officer")
        owner = _user("control_owner")
        auditor = _user("auditor")

        # -- Audit Cycles ----------------------------------------------------------
        cycles: dict[str, AuditCycle] = {}
        cycle_defs = [
            ("January 2026 Audit",  date(2026, 1, 10), date(2026, 1, 31)),
            ("April 2026 Audit",    date(2026, 4,  5), date(2026, 4, 25)),
            ("July 2026 Audit",     date(2026, 7,  1), date(2026, 7, 20)),
        ]
        for name, start, end in cycle_defs:
            cy = db.query(AuditCycle).filter_by(
                organisation_id=org.id, name=name
            ).first()
            if not cy:
                cy = AuditCycle(
                    organisation_id=org.id,
                    name=name,
                    start_date=start,
                    end_date=end,
                )
                db.add(cy)
                db.flush()
                print(f"  [+] Created audit cycle: {name}  id={cy.id}")
            else:
                print(f"  [=] Audit cycle already exists: {name}")
            cycles[name] = cy

        jan = cycles["January 2026 Audit"]
        apr = cycles["April 2026 Audit"]
        jul = cycles["July 2026 Audit"]

        now = datetime.now(timezone.utc)

        # Helper: create or find finding by description prefix + cycle
        def _finding(
            cycle: AuditCycle,
            ctrl_code: Optional[str],
            dept: str,
            severity: str,
            description: str,
            status: str = "Open",
            review_status: str = "Approved",
            is_recurrence: bool = False,
        ) -> Finding:
            existing = db.query(Finding).filter(
                Finding.organisation_id == org.id,
                Finding.audit_cycle_id == cycle.id,
                Finding.description == description,
            ).first()
            if existing:
                return existing
            ctrl = _ctrl(ctrl_code) if ctrl_code else None
            f = Finding(
                organisation_id=org.id,
                audit_cycle_id=cycle.id,
                control_id=ctrl.id if ctrl else None,
                department=dept,
                severity=severity,
                description=description,
                status=status,
                review_status=review_status,
                ai_generated=False,
                is_recurrence=is_recurrence,
            )
            db.add(f)
            db.flush()
            return f

        def _sh(entity_type: str, entity_id: str, old: str, new: str, actor_id: str, note: str = "") -> None:
            """Add a status_history row."""
            sh = StatusHistory(
                organisation_id=org.id,
                entity_type=entity_type,
                entity_id=entity_id,
                old_status=old,
                new_status=new,
                changed_by=actor_id,
                changed_at=now,
                note=note,
            )
            db.add(sh)

        def _rem(
            finding: Finding,
            action: str,
            owner_name: str,
            due: date,
            rem_status: str,
            evidence: Optional[str] = None,
        ) -> RemediationAction:
            existing = db.query(RemediationAction).filter(
                RemediationAction.finding_id == finding.id,
                RemediationAction.action == action,
            ).first()
            if existing:
                return existing
            r = RemediationAction(
                organisation_id=org.id,
                finding_id=finding.id,
                owner=owner_name,
                action=action,
                due_date=due,
                status=rem_status,
                evidence_note=evidence,
            )
            db.add(r)
            db.flush()
            return r

        # ── January 2026 findings ─────────────────────────────────────────────────

        # SEC-014 (primary chain — High, IT Operations)
        f_jan_014 = _finding(
            jan, "SEC-014", "IT Operations", "High",
            "Employee access reviews for IT Operations are incomplete and approval records are missing. "
            "The quarterly access review due January 2026 was not completed. "
            "Privileged account access lists have not been reviewed or signed off by the IT Operations Manager. "
            "Several leavers from Q4 2025 still retain active system access.",
            status="Closed",
        )
        _sh("finding", f_jan_014.id, "Open", "In Remediation", co.id, "Remediation assigned to control owner.")
        _sh("finding", f_jan_014.id, "In Remediation", "Ready for Review", owner.id, "Access review completed Feb 2026.")
        _sh("finding", f_jan_014.id, "Ready for Review", "Closed", co.id, "Evidence reviewed and accepted.")

        # SEC-002 (IT Operations, Medium)
        f_jan_002 = _finding(
            jan, "SEC-002", "IT Operations", "Medium",
            "Access Control Policy has not been reviewed or updated in over 14 months. "
            "The current version does not reflect changes in cloud-based access management introduced in Q3 2025.",
            status="Closed",
        )
        _sh("finding", f_jan_002.id, "Open", "In Remediation", co.id, "Policy review assigned.")
        _sh("finding", f_jan_002.id, "In Remediation", "Closed", co.id, "Updated policy approved.")

        # SEC-008 (IT Operations, High) — Patch Management
        f_jan_008 = _finding(
            jan, "SEC-008", "IT Operations", "High",
            "Incident response plan has not been tested in the past 12 months. "
            "No tabletop exercise or drill evidence is available for the current period. "
            "Automated incident detection rules are outdated.",
            status="Closed",
        )
        _sh("finding", f_jan_008.id, "Open", "In Remediation", co.id)
        _sh("finding", f_jan_008.id, "In Remediation", "Closed", co.id, "Tabletop exercise conducted.")

        # SEC-007 / HR — Background checks (Medium)
        f_jan_007 = _finding(
            jan, "SEC-007", "HR", "Medium",
            "Background screening process for contractors is not consistently applied. "
            "12 contractor onboardings in Q4 2025 lacked documented background check results. "
            "No formal tracking mechanism is in place for contractor screening status.",
            status="Closed",
        )
        _sh("finding", f_jan_007.id, "Open", "Closed", co.id, "Process updated and training completed.")

        # SEC-010 / Finance — Audit Logging (High)
        f_jan_010 = _finding(
            jan, "SEC-010", "Finance", "High",
            "Supplier security assessments are overdue for 6 critical vendors. "
            "Risk ratings for two top-tier suppliers have not been updated since 2024. "
            "Signed security agreements are missing for one active supplier.",
            status="Closed",
        )
        _sh("finding", f_jan_010.id, "Open", "In Remediation", co.id)
        _sh("finding", f_jan_010.id, "In Remediation", "Closed", co.id, "All supplier reviews completed.")

        # SEC-003 / Engineering — Crypto (Medium)
        f_jan_003 = _finding(
            jan, "SEC-003", "Engineering", "Medium",
            "Cryptographic key management procedures are not documented. "
            "No formal key rotation schedule exists for application encryption keys. "
            "TLS certificate inventory is incomplete.",
            status="Closed",
        )
        _sh("finding", f_jan_003.id, "Open", "Closed", co.id)

        # SEC-013 / IT Operations — Vuln Management (Medium)
        f_jan_013 = _finding(
            jan, "SEC-013", "IT Operations", "Medium",
            "Monthly vulnerability scans are not being conducted. "
            "Last confirmed scan is from October 2025. "
            "Exception register for unpatched systems has not been reviewed.",
            status="Closed",
        )
        _sh("finding", f_jan_013.id, "Open", "Closed", admin.id)

        # SEC-016 / Finance — Data Classification (Low)
        f_jan_016 = _finding(
            jan, "SEC-016", "Finance", "Low",
            "Data classification labels are inconsistently applied across Finance file shares. "
            "Several sensitive documents are missing classification markings.",
            status="Closed",
        )
        _sh("finding", f_jan_016.id, "Open", "Closed", co.id)

        # SEC-012 / IT Operations — Asset Inventory (Low)
        f_jan_012 = _finding(
            jan, "SEC-012", "IT Operations", "Low",
            "Asset inventory for cloud-hosted instances is incomplete. "
            "12 instances in the development environment are untagged and unclassified.",
            status="Closed",
        )
        _sh("finding", f_jan_012.id, "Open", "Closed", admin.id)

        # SEC-011 / Finance — Risk Assessment (Low)
        f_jan_011 = _finding(
            jan, "SEC-011", "Finance", "Low",
            "Risk assessment for the Finance department has not been updated following organisational restructure in November 2025.",
            status="Closed",
        )
        _sh("finding", f_jan_011.id, "Open", "Closed", co.id)

        # ── January remediations ──────────────────────────────────────────────────

        r_jan_014 = _rem(
            f_jan_014,
            "Conduct quarterly access review with IT Operations — obtain reviewer name, review date, and approval signature from IT Operations Manager.",
            "Owen Owner",
            date(2026, 2, 28),
            "Completed",
            "Access review completed February 2026. Approval signature obtained from IT Operations Manager. All leaver accounts deactivated.",
        )
        _sh("remediation", r_jan_014.id, "Planned", "In Progress", owner.id)
        _sh("remediation", r_jan_014.id, "In Progress", "Completed", co.id, "Evidence verified.")

        _rem(f_jan_002, "Update Access Control Policy to reflect cloud access management changes.", "Carlos Compliance", date(2026, 2, 15), "Completed", "Policy v2.3 approved by CISO.")
        _rem(f_jan_008, "Schedule and conduct full incident response tabletop exercise.", "Alice Admin", date(2026, 3, 31), "Completed", "Tabletop exercise completed 2026-03-15.")
        _rem(f_jan_007, "Implement contractor background screening tracker and update HR onboarding checklist.", "Owen Owner", date(2026, 2, 28), "Completed")
        _rem(f_jan_010, "Complete outstanding supplier security assessments and obtain signed agreements.", "Carlos Compliance", date(2026, 3, 15), "Completed")

        # ── April 2026 findings ───────────────────────────────────────────────────

        # SEC-014 (recurrence — High, IT Operations)
        f_apr_014 = _finding(
            apr, "SEC-014", "IT Operations", "High",
            "Employee access reviews for IT Operations remain incomplete in Q2 2026. "
            "Approval records are again missing from the access review documentation. "
            "Privileged accounts have not been audited since the January remediation. "
            "The root cause — absence of an automated review schedule — has not been addressed.",
            status="In Remediation",
            is_recurrence=True,
        )
        _sh("finding", f_apr_014.id, "Open", "In Remediation", co.id, "Recurrence of January finding — escalated.")

        # SEC-007 / HR (Low — improved from Medium)
        f_apr_007 = _finding(
            apr, "SEC-007", "HR", "Low",
            "Background screening process has improved but documentation for 2 recent contractor onboardings remains incomplete.",
            status="Closed",
        )
        _sh("finding", f_apr_007.id, "Open", "Closed", co.id, "Resolved quickly — minor gap.")

        # SEC-013 / HR (Medium)
        f_apr_013 = _finding(
            apr, "SEC-013", "HR", "Medium",
            "Vulnerability scan schedule has not been formalised. "
            "No SLA exists for remediation of critical CVEs. "
            "Patch status report shows 8 critical patches pending beyond 30-day threshold.",
            status="In Remediation",
        )
        _sh("finding", f_apr_013.id, "Open", "In Remediation", co.id)

        # SEC-010 / Finance (Medium — partially remediated)
        f_apr_010 = _finding(
            apr, "SEC-010", "Finance", "Medium",
            "Two supplier security assessments completed in January have lapsed. "
            "Supplier risk ratings require quarterly refresh which was not performed.",
            status="In Remediation",
        )
        _sh("finding", f_apr_010.id, "Open", "In Remediation", co.id)

        # SEC-016 / Finance (Low)
        f_apr_016 = _finding(
            apr, "SEC-016", "Finance", "Low",
            "Data classification labelling in Finance improved but 3 legacy file shares remain unlabelled.",
            status="Closed",
        )
        _sh("finding", f_apr_016.id, "Open", "Closed", admin.id)

        # SEC-004 / Engineering (High) — Network Security
        f_apr_004 = _finding(
            apr, "SEC-004", "Engineering", "High",
            "Network perimeter review identified 2 misconfigured firewall rules permitting unnecessary inbound traffic. "
            "Penetration test findings from March 2026 have not been remediated.",
            status="In Remediation",
        )
        _sh("finding", f_apr_004.id, "Open", "In Remediation", co.id)

        # SEC-003 / Engineering (Low — improved)
        f_apr_003 = _finding(
            apr, "SEC-003", "Engineering", "Low",
            "Key rotation schedule is now documented but TLS certificates for 2 internal services have expired.",
            status="Closed",
        )
        _sh("finding", f_apr_003.id, "Open", "Closed", admin.id)

        # SEC-006 / IT Operations (Medium)
        f_apr_006 = _finding(
            apr, "SEC-006", "IT Operations", "Medium",
            "Network security review report is 5 months overdue. "
            "Firewall rule review has not been conducted since November 2025.",
            status="In Remediation",
        )
        _sh("finding", f_apr_006.id, "Open", "In Remediation", owner.id)

        # SEC-017 / Engineering (Low)
        f_apr_017 = _finding(
            apr, "SEC-017", "Engineering", "Low",
            "Change management records for 4 production deployments in Q1 2026 are missing approval signatures.",
            status="Closed",
        )
        _sh("finding", f_apr_017.id, "Open", "Closed", admin.id)

        # ── April remediations ────────────────────────────────────────────────────

        _rem(
            f_apr_014,
            "Establish automated quarterly access review schedule with calendar reminders and define approval workflow for IT Operations Manager.",
            "Owen Owner",
            date(2026, 5, 31),
            "In Progress",
        )
        _rem(f_apr_013, "Define SLA for critical CVE remediation and implement monthly patch status report.", "Owen Owner", date(2026, 5, 15), "In Progress")
        _rem(f_apr_010, "Implement quarterly supplier risk refresh process with automated reminders.", "Carlos Compliance", date(2026, 5, 31), "In Progress")
        _rem(f_apr_004, "Remediate firewall misconfigurations and address open penetration test findings.", "Owen Owner", date(2026, 5, 20), "In Progress")
        _rem(f_apr_006, "Conduct overdue network security review and schedule quarterly reviews going forward.", "Owen Owner", date(2026, 5, 10), "Completed", "Network review conducted May 2026.")

        # ── July 2026 findings ────────────────────────────────────────────────────

        # SEC-014 (recurrence — Medium, reviews completed but one approval missing)
        f_jul_014 = _finding(
            jul, "SEC-014", "IT Operations", "Medium",
            "Employee access reviews for IT Operations are now completed for Q3 2026. "
            "However, the approval signature from the IT Operations Manager is still missing from the official record. "
            "All reviewer names and review dates are present. Leaver accounts have been deactivated.",
            status="In Remediation",
            is_recurrence=True,
        )
        _sh("finding", f_jul_014.id, "Open", "In Remediation", co.id, "Partial remediation — approval still outstanding.")

        # SEC-008 / IT Operations (Low — resolved)
        f_jul_008 = _finding(
            jul, "SEC-008", "IT Operations", "Low",
            "Incident response plan is current and tested. Minor gap: post-incident review template not yet updated.",
            status="Closed",
        )
        _sh("finding", f_jul_008.id, "Open", "Closed", co.id)

        # SEC-004 / Engineering (Medium)
        f_jul_004 = _finding(
            jul, "SEC-004", "Engineering", "Medium",
            "Firewall misconfigurations from April have been remediated. "
            "However, two newly identified rules require review before next quarter.",
            status="Open",
        )

        # SEC-012 / Engineering (Low)
        f_jul_012 = _finding(
            jul, "SEC-012", "Engineering", "Low",
            "Asset inventory is now 95% complete. 3 non-production instances remain untagged.",
            status="Open",
        )

        # SEC-010 / Finance (Low)
        f_jul_010 = _finding(
            jul, "SEC-010", "Finance", "Low",
            "Supplier risk ratings refreshed. One minor supplier assessment is pending sign-off.",
            status="Open",
        )

        # SEC-013 / IT Operations (Low)
        f_jul_013 = _finding(
            jul, "SEC-013", "IT Operations", "Low",
            "Vulnerability scan SLA now defined. One critical patch from June remains undeployed beyond the 30-day threshold.",
            status="Open",
        )

        # SEC-018 / Finance (Low)
        f_jul_018 = _finding(
            jul, "SEC-018", "Finance", "Low",
            "Audit log review schedule is in place. Sample review for June is missing from the evidence pack.",
            status="Open",
        )

        # SEC-006 / IT Operations (Low)
        f_jul_006 = _finding(
            jul, "SEC-006", "IT Operations", "Low",
            "Network security quarterly review is now on schedule. Firewall documentation needs a minor update.",
            status="Open",
        )

        # ── July remediations ─────────────────────────────────────────────────────

        _rem(
            f_jul_014,
            "Obtain missing approval signature from IT Operations Manager for Q3 2026 access review record.",
            "Owen Owner",
            date(2026, 8, 15),
            "Planned",
        )
        _rem(f_jul_004, "Review and document newly identified firewall rules before next quarter.", "Owen Owner", date(2026, 8, 31), "Planned")
        _rem(f_jul_013, "Deploy outstanding critical patch and document exception if delayed.", "Owen Owner", date(2026, 7, 31), "Planned")

        db.flush()

        # ── Related findings — SEC-014 recurrence chain ───────────────────────────

        def _related(finding: Finding, related: Finding, score: float, reason: str, reviewer_id: Optional[str] = None) -> None:
            existing = db.query(RelatedFinding).filter(
                RelatedFinding.finding_id == finding.id,
                RelatedFinding.related_finding_id == related.id,
            ).first()
            if not existing:
                rf = RelatedFinding(
                    organisation_id=org.id,
                    finding_id=finding.id,
                    related_finding_id=related.id,
                    match_score=score,
                    match_reason=reason,
                    reviewed_by=reviewer_id,
                )
                db.add(rf)

        _related(
            f_apr_014, f_jan_014, 0.87,
            "Same control SEC-014, same department IT Operations, 5 shared keywords: access, review, approval, incomplete, missing.",
            reviewer_id=co.id,
        )
        _related(
            f_jul_014, f_apr_014, 0.82,
            "Same control SEC-014, same department IT Operations, 4 shared keywords: access, review, approval, missing.",
            reviewer_id=co.id,
        )
        _related(
            f_jul_014, f_jan_014, 0.75,
            "Same control SEC-014, same department IT Operations, 4 shared keywords: access, review, missing, approval.",
            reviewer_id=co.id,
        )

        db.commit()
        print("\nDemo seed complete.")
        print(f"  Audit cycles:         {len(cycles)}")
        findings_count = db.query(Finding).filter(Finding.organisation_id == org.id).count()
        print(f"  Total findings:       {findings_count}")
        rem_count = db.query(RemediationAction).filter(RemediationAction.organisation_id == org.id).count()
        print(f"  Remediation actions:  {rem_count}")
        rel_count = db.query(RelatedFinding).filter(RelatedFinding.organisation_id == org.id).count()
        print(f"  Related findings:     {rel_count}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Reset demo data
# ---------------------------------------------------------------------------

def reset_demo(session_factory=None, bind_engine=None) -> None:
    """
    Delete all demo data (audit cycles + their findings / remediations /
    related_findings / status_history rows).  Leaves org, users, controls intact.
    """
    import app.database as db_module
    from app.models.audit_cycle import AuditCycle
    from app.models.finding import Finding
    from app.models.remediation import RemediationAction
    from app.models.related_finding import RelatedFinding
    from app.models.status_history import StatusHistory

    _session_factory = session_factory or db_module.SessionLocal
    db = _session_factory()

    try:
        org = db.query(Organisation).filter_by(name=ORG_NAME).first()
        if not org:
            print("No organisation found — nothing to reset.")
            return

        demo_cycles = (
            db.query(AuditCycle)
            .filter(
                AuditCycle.organisation_id == org.id,
                AuditCycle.name.in_(list(_DEMO_CYCLE_NAMES)),
            )
            .all()
        )
        cycle_ids = [c.id for c in demo_cycles]

        demo_findings = (
            db.query(Finding)
            .filter(
                Finding.organisation_id == org.id,
                Finding.audit_cycle_id.in_(cycle_ids),
            )
            .all()
        ) if cycle_ids else []
        finding_ids = [f.id for f in demo_findings]

        # Delete in dependency order
        if finding_ids:
            db.query(RelatedFinding).filter(
                RelatedFinding.organisation_id == org.id,
                RelatedFinding.finding_id.in_(finding_ids),
            ).delete(synchronize_session=False)
            db.query(StatusHistory).filter(
                StatusHistory.organisation_id == org.id,
                StatusHistory.entity_id.in_(finding_ids),
            ).delete(synchronize_session=False)
            db.query(RemediationAction).filter(
                RemediationAction.organisation_id == org.id,
                RemediationAction.finding_id.in_(finding_ids),
            ).delete(synchronize_session=False)
            db.query(Finding).filter(Finding.id.in_(finding_ids)).delete(synchronize_session=False)

        for c in demo_cycles:
            db.delete(c)

        db.commit()
        print(f"  [reset] Removed {len(demo_cycles)} audit cycles, {len(finding_ids)} findings.")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Clean — wipe everything and re-seed base
# ---------------------------------------------------------------------------

def clean_seed(session_factory=None, bind_engine=None) -> None:
    """
    Wipe all data for the demo org and re-run base seed.
    Useful before a live demo starting from a clean slate.
    """
    import app.database as db_module
    from sqlalchemy import text

    _engine = bind_engine or db_module.engine
    _session_factory = session_factory or db_module.SessionLocal

    db_module.Base.metadata.drop_all(bind=_engine)
    db_module.Base.metadata.create_all(bind=_engine)
    print("  [clean] All tables dropped and recreated.")
    seed(session_factory=_session_factory, bind_engine=_engine)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AuditMind AI seed script")
    parser.add_argument("--demo",  action="store_true", help="Seed the 3-cycle demo scenario on top of base seed")
    parser.add_argument("--reset", action="store_true", help="Delete only demo data (audit cycles + findings etc.)")
    parser.add_argument("--clean", action="store_true", help="Wipe all data and re-run base seed")
    args = parser.parse_args()

    if args.clean:
        print("Cleaning and re-seeding AuditMind AI database...\n")
        clean_seed()
    elif args.reset:
        print("Resetting demo data...\n")
        reset_demo()
    elif args.demo:
        print("Seeding AuditMind AI database (base + demo)...\n")
        seed()
        print()
        seed_demo()
    else:
        print("Seeding AuditMind AI database (base)...\n")
        seed()

    sys.exit(0)
