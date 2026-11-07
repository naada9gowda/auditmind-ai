export type UserRole = 'admin' | 'compliance_officer' | 'control_owner' | 'auditor';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  organisation_id: string;
}

export type ControlStatus = 'Compliant' | 'Needs Review' | 'Gap Identified' | 'Not Assessed';

export interface Control {
  id: string;
  organisation_id: string;
  control_code: string;
  title: string;
  description?: string | null;
  owner: string;
  cadence: string;
  evidence_expectation?: string | null;
  status: ControlStatus;
  computed_status?: ControlStatus | string;
}

export type FindingSeverity = 'High' | 'Medium' | 'Low';
export type FindingStatus = 'Open' | 'In Remediation' | 'Ready for Review' | 'Closed';
export type ReviewStatus = 'Draft' | 'Approved' | 'Rejected';

export interface Finding {
  id: string;
  organisation_id: string;
  control_id?: string | null;
  audit_cycle_id?: string | null;
  department?: string | null;
  severity: FindingSeverity;
  description: string;
  status: FindingStatus;
  source_document_id?: string | null;
  source_page?: number | null;
  source_excerpt?: string | null;
  ai_generated: boolean;
  review_status: ReviewStatus;
  is_recurrence: boolean;
}

export type RemediationStatus = 'Planned' | 'In Progress' | 'Ready for Review' | 'Completed';

export interface RemediationAction {
  id: string;
  organisation_id: string;
  finding_id: string;
  owner: string;
  action: string;
  due_date?: string | null;
  status: RemediationStatus;
  is_overdue?: boolean;
  evidence_note?: string | null;
}

export type DocumentType = 'policy' | 'audit_report' | 'evidence';
export type ProcessingStatus = 'Uploaded' | 'Processing' | 'Processed' | 'Failed';

export interface DocumentPage {
  id?: string;
  document_id: string;
  page_number: number;
  text: string;
}

export interface DocumentItem {
  id: string;
  organisation_id: string;
  filename: string;
  doc_type: DocumentType;
  version?: string | null;
  storage_ref?: string | null;
  processing_status: ProcessingStatus;
  uploaded_at: string;
  extracted_date?: string | null;
  pages?: DocumentPage[];
}

export type EvidenceAssessment = 
  | 'Candidate Match' 
  | 'Missing' 
  | 'Expired' 
  | 'Incomplete' 
  | 'Requires Human Review';

export interface Evidence {
  id: string;
  organisation_id: string;
  document_id?: string | null;
  control_id: string;
  evidence_date?: string | null;
  review_status: ReviewStatus;
  excerpt?: string | null;
  page_number?: number | null;
  assessment: EvidenceAssessment;
  reviewed_by?: string | null;
}

export interface AuditCycle {
  id: string;
  organisation_id: string;
  name: string;
  start_date: string;
  end_date: string;
}

export interface StatusHistoryEntry {
  id: string;
  organisation_id: string;
  entity_type: string;
  entity_id: string;
  old_status: string;
  new_status: string;
  changed_by: string;
  changed_at: string;
  note?: string | null;
}

export interface RelatedFindingSuggestion {
  id?: string;
  related_finding_id: string;
  match_score: number;
  match_reason: string;
  reviewed_by?: string | null;
}

export interface FindingHistoryResponse {
  finding_id: string;
  is_recurrence: boolean;
  status_history: StatusHistoryEntry[];
  related_findings: RelatedFindingSuggestion[];
}

export interface ApproveFindingResponse {
  finding: Finding;
  related_findings_created: number;
  related_findings: Array<{
    related_finding_id: string;
    match_score: number;
    match_reason: string;
  }>;
  message: string;
}

export interface TimelineEntry {
  event_type: 'audit_cycle' | 'finding' | 'remediation' | 'status_change' | string;
  event_date?: string | null;
  entity_id: string;
  entity_type: string;
  summary: string;
  detail?: string | null;
}

export interface TimelineResponse {
  control_id: string;
  control_code: string;
  entries: TimelineEntry[];
  message?: string | null;
}

export interface RiskComponent {
  name: string;
  points: number;
  reason: string;
}

export interface RiskItem {
  finding_id: string;
  score: number;
  level: 'High' | 'Medium' | 'Low';
  components: RiskComponent[];
  explanation: string;
  control_id?: string | null;
  control_code?: string;
  control_title?: string;
  department?: string;
  severity: FindingSeverity | string;
  description: string;
  status: FindingStatus | string;
  is_recurrence?: boolean;
  review_status?: ReviewStatus | string;
  source_document_id?: string | null;
  source_page?: number | null;
  source_excerpt?: string | null;
}

export interface RisksResponse {
  disclaimer: string;
  risks: RiskItem[];
}

export interface AnalyticsSummary {
  control_status_counts: Record<string, number>;
  open_findings_by_severity: Record<string, number>;
  overdue_actions_count: number;
  recurring_findings_count: number;
  findings_per_dept_per_cycle: Array<{
    cycle_name: string;
    [dept: string]: any;
  }>;
  risk_by_control: Array<{
    control_code: string;
    risk_score: number;
  }>;
  disclaimer: string;
}

export interface ChatReference {
  type: 'control' | 'finding' | 'document' | string;
  id: string;
  label: string;
  page?: number | null;
  excerpt?: string | null;
}

export interface ChatResponse {
  answer: string;
  references: ChatReference[];
  used_history: boolean;
  model_unavailable: boolean;
}

export interface AnalyzeDocumentResponse {
  document_id: string;
  doc_type: string;
  control_matches: number;
  evidence_items_created: number;
  evidence_ids: string[];
  findings_created: number;
  finding_ids: string[];
  note: string;
}
