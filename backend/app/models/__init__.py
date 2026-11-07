"""
models/__init__.py

Import all model classes here so SQLAlchemy's metadata is fully populated
before `Base.metadata.create_all()` is called. The `all_models` symbol is
imported in database.py solely as a side-effect trigger.
"""

from app.models.organisation import Organisation
from app.models.user import User
from app.models.control import Control
from app.models.document import Document, DocumentPage
from app.models.evidence import Evidence
from app.models.audit_cycle import AuditCycle
from app.models.finding import Finding
from app.models.remediation import RemediationAction
from app.models.status_history import StatusHistory
from app.models.related_finding import RelatedFinding
from app.models.activity_log import ActivityLog

# Convenience tuple used by database.init_db() to trigger this import.
all_models = (
    Organisation,
    User,
    Control,
    Document,
    DocumentPage,
    Evidence,
    AuditCycle,
    Finding,
    RemediationAction,
    StatusHistory,
    RelatedFinding,
    ActivityLog,
)
