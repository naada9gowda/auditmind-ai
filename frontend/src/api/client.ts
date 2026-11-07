import {
  User,
  Control,
  Finding,
  RemediationAction,
  DocumentItem,
  DocumentPage,
  Evidence,
  AuditCycle,
  FindingHistoryResponse,
  ApproveFindingResponse,
  TimelineResponse,
  RisksResponse,
  AnalyticsSummary,
  ChatResponse,
  AnalyzeDocumentResponse,
} from './types';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
  private currentUserId: string | null = null;

  setUserId(userId: string | null) {
    this.currentUserId = userId;
  }

  getUserId(): string | null {
    return this.currentUserId;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${BASE_URL}${endpoint}`;
    const headers = new Headers(options.headers || {});

    if (this.currentUserId && !headers.has('X-User-Id')) {
      headers.set('X-User-Id', this.currentUserId);
    }

    if (!headers.has('Accept')) {
      headers.set('Accept', 'application/json');
    }

    // Only set Content-Type to json if body is not FormData
    if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      try {
        const errorData = await response.json();
        if (errorData && typeof errorData === 'object' && 'detail' in errorData) {
          errorMessage = typeof errorData.detail === 'string'
            ? errorData.detail
            : JSON.stringify(errorData.detail);
        }
      } catch {
        // use default error message
      }
      throw new Error(errorMessage);
    }

    return response.json() as Promise<T>;
  }

  // ── Users & Auth ───────────────────────────────────────────────────────────
  async getMe(): Promise<User> {
    return this.request<User>('/api/me');
  }

  async getUsers(): Promise<User[]> {
    try {
      return await this.request<User[]>('/api/users');
    } catch {
      // Fallback: try /api/users/me or return known demo seed users
      return [
        {
          id: 'alice-admin-uuid',
          name: 'Alice Admin',
          email: 'alice.admin@abctech.example',
          role: 'admin',
          organisation_id: 'abc-tech',
        },
        {
          id: 'carlos-compliance-uuid',
          name: 'Carlos Compliance',
          email: 'carlos.compliance@abctech.example',
          role: 'compliance_officer',
          organisation_id: 'abc-tech',
        },
        {
          id: 'owen-owner-uuid',
          name: 'Owen Owner',
          email: 'owen.owner@abctech.example',
          role: 'control_owner',
          organisation_id: 'abc-tech',
        },
        {
          id: 'audrey-auditor-uuid',
          name: 'Audrey Auditor',
          email: 'audrey.auditor@abctech.example',
          role: 'auditor',
          organisation_id: 'abc-tech',
        },
      ];
    }
  }

  async getHealth(): Promise<{ status: string; service: string }> {
    return this.request('/api/health');
  }

  // ── Controls ───────────────────────────────────────────────────────────────
  async getControls(status?: string): Promise<Control[]> {
    const query = status ? `?status=${encodeURIComponent(status)}` : '';
    return this.request<Control[]>(`/api/controls${query}`);
  }

  async getControl(id: string): Promise<Control> {
    return this.request<Control>(`/api/controls/${id}`);
  }

  async updateControlStatus(id: string, newStatus: string, note?: string): Promise<Control> {
    const params = new URLSearchParams({ new_status: newStatus });
    if (note) params.append('note', note);
    return this.request<Control>(`/api/controls/${id}/status?${params.toString()}`, {
      method: 'POST',
    });
  }

  // ── Findings ───────────────────────────────────────────────────────────────
  async getFindings(params?: {
    control_id?: string;
    department?: string;
    status?: string;
    audit_cycle_id?: string;
    severity?: string;
    review_status?: string;
  }): Promise<Finding[]> {
    const query = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') {
          query.append(k, v);
        }
      });
    }
    const qs = query.toString();
    return this.request<Finding[]>(`/api/findings${qs ? `?${qs}` : ''}`);
  }

  async getFinding(id: string): Promise<Finding> {
    return this.request<Finding>(`/api/findings/${id}`);
  }

  async createFinding(payload: Partial<Finding>): Promise<Finding> {
    return this.request<Finding>('/api/findings', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async updateFinding(id: string, payload: Partial<Finding>): Promise<Finding> {
    return this.request<Finding>(`/api/findings/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  async changeFindingStatus(id: string, newStatus: string, note?: string): Promise<Finding> {
    const params = new URLSearchParams({ new_status: newStatus });
    if (note) params.append('note', note);
    return this.request<Finding>(`/api/findings/${id}/status?${params.toString()}`, {
      method: 'POST',
    });
  }

  async approveFinding(id: string): Promise<ApproveFindingResponse> {
    return this.request<ApproveFindingResponse>(`/api/findings/${id}/approve`, {
      method: 'POST',
    });
  }

  async reviewRelatedFinding(
    findingId: string,
    relatedId: string,
    decision: 'confirmed' | 'rejected'
  ): Promise<{ decision: string; related_finding_id: string; finding_id: string; is_recurrence: boolean; reviewed_by: string }> {
    return this.request(`/api/findings/${findingId}/related/${relatedId}/review`, {
      method: 'POST',
      body: JSON.stringify({ decision }),
    });
  }

  async getFindingHistory(findingId: string): Promise<FindingHistoryResponse> {
    return this.request<FindingHistoryResponse>(`/api/findings/${findingId}/history`);
  }

  // ── Remediations ───────────────────────────────────────────────────────────
  async getRemediations(findingId?: string, status?: string): Promise<RemediationAction[]> {
    const query = new URLSearchParams();
    if (findingId) query.append('finding_id', findingId);
    if (status) query.append('status', status);
    const qs = query.toString();
    return this.request<RemediationAction[]>(`/api/remediations${qs ? `?${qs}` : ''}`);
  }

  async createRemediation(payload: {
    finding_id: string;
    owner: string;
    action: string;
    due_date?: string | null;
    evidence_note?: string | null;
  }): Promise<RemediationAction> {
    return this.request<RemediationAction>('/api/remediations', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async changeRemediationStatus(id: string, newStatus: string, note?: string): Promise<RemediationAction> {
    const params = new URLSearchParams({ new_status: newStatus });
    if (note) params.append('note', note);
    return this.request<RemediationAction>(`/api/remediations/${id}/status?${params.toString()}`, {
      method: 'POST',
    });
  }

  // ── Documents ──────────────────────────────────────────────────────────────
  async getDocuments(docType?: string, processingStatus?: string): Promise<DocumentItem[]> {
    const query = new URLSearchParams();
    if (docType) query.append('doc_type', docType);
    if (processingStatus) query.append('processing_status', processingStatus);
    const qs = query.toString();
    return this.request<DocumentItem[]>(`/api/documents${qs ? `?${qs}` : ''}`);
  }

  async getDocument(id: string): Promise<DocumentItem> {
    return this.request<DocumentItem>(`/api/documents/${id}`);
  }

  async uploadDocument(file: File, docType: string, version?: string): Promise<DocumentItem> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('doc_type', docType);
    if (version) formData.append('version', version);

    return this.request<DocumentItem>('/api/documents', {
      method: 'POST',
      body: formData,
    });
  }

  async processDocument(id: string): Promise<DocumentItem> {
    return this.request<DocumentItem>(`/api/documents/${id}/process`, {
      method: 'POST',
    });
  }

  async analyzeDocument(id: string): Promise<AnalyzeDocumentResponse> {
    return this.request<AnalyzeDocumentResponse>(`/api/documents/${id}/analyze`, {
      method: 'POST',
    });
  }

  async getDocumentPage(docId: string, pageNum: number): Promise<DocumentPage> {
    return this.request<DocumentPage>(`/api/documents/${docId}/pages/${pageNum}`);
  }

  // ── Evidence ───────────────────────────────────────────────────────────────
  async getEvidence(controlId?: string, assessment?: string, reviewStatus?: string): Promise<Evidence[]> {
    const query = new URLSearchParams();
    if (controlId) query.append('control_id', controlId);
    if (assessment) query.append('assessment', assessment);
    if (reviewStatus) query.append('review_status', reviewStatus);
    const qs = query.toString();
    return this.request<Evidence[]>(`/api/evidence${qs ? `?${qs}` : ''}`);
  }

  async reviewEvidence(
    id: string,
    decision: 'accept' | 'reject' | 'Approved' | 'Rejected',
    assessment?: string,
    note?: string
  ): Promise<Evidence> {
    // Backend accepts 'Approved' | 'Rejected'
    const normalizedDecision = (decision.toLowerCase() === 'accept' || decision === 'Approved')
      ? 'Approved'
      : 'Rejected';

    return this.request<Evidence>(`/api/evidence/${id}/review`, {
      method: 'POST',
      body: JSON.stringify({
        decision: normalizedDecision,
        assessment,
        note,
      }),
    });
  }

  async mapEvidence(payload: {
    control_id: string;
    document_id: string;
    page_number?: number;
    excerpt?: string;
  }): Promise<Evidence> {
    return this.request<Evidence>('/api/evidence/map', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  // ── AI Assistant ───────────────────────────────────────────────────────────
  async chatAssistant(question: string, useHistory: boolean = true): Promise<ChatResponse> {
    return this.request<ChatResponse>('/api/assistant/chat', {
      method: 'POST',
      body: JSON.stringify({ question, use_history: useHistory }),
    });
  }

  // ── Analytics & Risks ──────────────────────────────────────────────────────
  async getAnalyticsSummary(): Promise<AnalyticsSummary> {
    return this.request<AnalyticsSummary>('/api/analytics/summary');
  }

  async getAnalyticsRisks(): Promise<RisksResponse> {
    return this.request<RisksResponse>('/api/analytics/risks');
  }

  // ── Audit History Timeline ─────────────────────────────────────────────────
  async getTimeline(params: { control_code?: string; control_id?: string }): Promise<TimelineResponse> {
    const query = new URLSearchParams();
    if (params.control_code) query.append('control_code', params.control_code);
    if (params.control_id) query.append('control_id', params.control_id);
    return this.request<TimelineResponse>(`/api/history/timeline?${query.toString()}`);
  }

  // ── Audit Cycles ───────────────────────────────────────────────────────────
  async getAuditCycles(): Promise<AuditCycle[]> {
    return this.request<AuditCycle[]>('/api/audit-cycles');
  }
}

export const api = new ApiClient();
export default api;
