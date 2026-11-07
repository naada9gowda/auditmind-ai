import React, { useEffect, useState, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import {
  Finding,
  Control,
  FindingHistoryResponse,
  ApproveFindingResponse,
  FindingSeverity,
} from '../api/types';
import { useUser } from '../context/UserContext';
import { useToast } from '../components/Toast';
import SeverityBadge from '../components/SeverityBadge';
import VerifiedBadge from '../components/VerifiedBadge';
import AiSuggestionBanner from '../components/AiSuggestionBanner';
import SourceDrawer from '../components/SourceDrawer';
import ConfirmDialog from '../components/ConfirmDialog';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import {
  FunnelIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowPathIcon,
  DocumentMagnifyingGlassIcon,
  ChevronRightIcon,
  PencilSquareIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';

export const FindingsReview: React.FC = () => {
  const { currentUser } = useUser();
  const { showToast } = useToast();
  const [searchParams] = useSearchParams();
  const preselectedId = searchParams.get('id');

  const [findings, setFindings] = useState<Finding[]>([]);
  const [controls, setControls] = useState<Control[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [reviewFilter, setReviewFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [deptFilter, setDeptFilter] = useState<string>('all');

  // Selected Finding Detail
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null);
  const [findingHistory, setFindingHistory] = useState<FindingHistoryResponse | null>(null);
  const [historyLoading, setHistoryLoading] = useState<boolean>(false);

  // Approve dialog state
  const [approveDialogOpen, setApproveDialogOpen] = useState<boolean>(false);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [approvalResult, setApprovalResult] = useState<ApproveFindingResponse | null>(null);

  // Source drawer state
  const [sourceDrawerOpen, setSourceDrawerOpen] = useState<boolean>(false);
  const [drawerDocId, setDrawerDocId] = useState<string | null>(null);
  const [drawerPage, setDrawerPage] = useState<number | null>(null);
  const [drawerExcerpt, setDrawerExcerpt] = useState<string | null>(null);
  const [drawerControl, setDrawerControl] = useState<string | null>(null);

  // Edit Mode state
  const [editMode, setEditMode] = useState<boolean>(false);
  const [editForm, setEditForm] = useState<{
    control_id: string;
    department: string;
    severity: FindingSeverity;
    description: string;
  }>({
    control_id: '',
    department: '',
    severity: 'Medium',
    description: '',
  });

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [fetchedFindings, fetchedControls] = await Promise.all([
        api.getFindings(),
        api.getControls().catch(() => []),
      ]);
      setFindings(fetchedFindings);
      setControls(fetchedControls);

      if (preselectedId) {
        const found = fetchedFindings.find((f) => f.id === preselectedId);
        if (found) {
          selectFinding(found);
        }
      } else if (fetchedFindings.length > 0 && !selectedFinding) {
        selectFinding(fetchedFindings[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load audit findings.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const selectFinding = async (finding: Finding) => {
    setSelectedFinding(finding);
    setEditMode(false);
    setApprovalResult(null);
    setEditForm({
      control_id: finding.control_id || '',
      department: finding.department || '',
      severity: finding.severity || 'Medium',
      description: finding.description || '',
    });

    // Load finding history and related findings
    setHistoryLoading(true);
    try {
      const hist = await api.getFindingHistory(finding.id);
      setFindingHistory(hist);
    } catch {
      setFindingHistory(null);
    } finally {
      setHistoryLoading(false);
    }
  };

  // Filtered list
  const filteredFindings = useMemo(() => {
    return findings.filter((f) => {
      if (reviewFilter !== 'all' && f.review_status !== reviewFilter) return false;
      if (severityFilter !== 'all' && f.severity !== severityFilter) return false;
      if (deptFilter !== 'all' && f.department !== deptFilter) return false;
      return true;
    });
  }, [findings, reviewFilter, severityFilter, deptFilter]);

  // Unique departments for filter
  const departments = useMemo(() => {
    const set = new Set<string>();
    findings.forEach((f) => {
      if (f.department) set.add(f.department);
    });
    return Array.from(set);
  }, [findings]);

  // Handle Approve
  const handleApprove = async () => {
    if (!selectedFinding) return;
    setActionLoading(true);
    try {
      const res = await api.approveFinding(selectedFinding.id);
      setApprovalResult(res);
      showToast(res.message, 'success');

      // Update finding in list
      setFindings((prev) =>
        prev.map((f) => (f.id === selectedFinding.id ? res.finding : f))
      );
      setSelectedFinding(res.finding);

      // Refresh history
      const hist = await api.getFindingHistory(selectedFinding.id);
      setFindingHistory(hist);
      setApproveDialogOpen(false);
    } catch (err: any) {
      showToast(err.message || 'Failed to approve finding', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Review Related Suggestion
  const handleReviewRelated = async (relatedId: string, decision: 'confirmed' | 'rejected') => {
    if (!selectedFinding) return;
    try {
      await api.reviewRelatedFinding(selectedFinding.id, relatedId, decision);
      showToast(
        decision === 'confirmed'
          ? 'Related recurrence confirmed and flagged on record.'
          : 'Related recurrence dismissed.',
        'info'
      );
      // Reload history & finding
      const [updatedFinding, hist] = await Promise.all([
        api.getFinding(selectedFinding.id),
        api.getFindingHistory(selectedFinding.id),
      ]);
      setSelectedFinding(updatedFinding);
      setFindingHistory(hist);
      setFindings((prev) =>
        prev.map((f) => (f.id === updatedFinding.id ? updatedFinding : f))
      );
    } catch (err: any) {
      showToast(err.message || 'Failed to review related finding', 'error');
    }
  };

  // Handle Update Finding Fields (PATCH)
  const handleSaveEdit = async () => {
    if (!selectedFinding) return;
    setActionLoading(true);
    try {
      const updated = await api.updateFinding(selectedFinding.id, {
        control_id: editForm.control_id || null,
        department: editForm.department || null,
        severity: editForm.severity,
        description: editForm.description,
      });
      showToast('Finding metadata updated successfully.', 'success');
      setSelectedFinding(updated);
      setFindings((prev) => prev.map((f) => (f.id === updated.id ? updated : f)));
      setEditMode(false);
    } catch (err: any) {
      showToast(err.message || 'Failed to update finding', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Finding Status Change (e.g. Open -> In Remediation -> Ready for Review -> Closed)
  const handleStatusChange = async (newStatus: string) => {
    if (!selectedFinding) return;
    try {
      const updated = await api.changeFindingStatus(selectedFinding.id, newStatus);
      showToast(`Finding status changed to ${newStatus}.`, 'success');
      setSelectedFinding(updated);
      setFindings((prev) => prev.map((f) => (f.id === updated.id ? updated : f)));
      const hist = await api.getFindingHistory(selectedFinding.id);
      setFindingHistory(hist);
    } catch (err: any) {
      showToast(err.message || 'Status transition denied.', 'error');
    }
  };

  const openSourceViewer = (docId?: string | null, page?: number | null, excerpt?: string | null, ctrlCode?: string | null) => {
    setDrawerDocId(docId || null);
    setDrawerPage(page || 1);
    setDrawerExcerpt(excerpt || null);
    setDrawerControl(ctrlCode || null);
    setSourceDrawerOpen(true);
  };

  const isControlOwner = currentUser?.role === 'control_owner';
  const canApprove = currentUser?.role === 'admin' || currentUser?.role === 'compliance_officer';

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Findings Review & Verification
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Human-in-the-loop review queue for AI-extracted audit deficiencies and recurrence checks
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadData}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-xs"
          >
            <ArrowPathIcon className="w-3.5 h-3.5" />
            Refresh
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex flex-wrap items-center gap-3 text-xs">
        <div className="flex items-center gap-1.5 text-slate-500 font-medium mr-1">
          <FunnelIcon className="w-4 h-4 text-slate-400" />
          <span>Filters:</span>
        </div>

        {/* Review Status Filter */}
        <select
          value={reviewFilter}
          onChange={(e) => setReviewFilter(e.target.value)}
          className="rounded-lg border border-slate-300 py-1.5 px-2.5 text-xs text-slate-700 bg-white focus:ring-1 focus:ring-teal-500"
        >
          <option value="all">All Review Statuses</option>
          <option value="Draft">Draft (AI Suggestions)</option>
          <option value="Approved">Approved Records</option>
          <option value="Rejected">Rejected</option>
        </select>

        {/* Severity Filter */}
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="rounded-lg border border-slate-300 py-1.5 px-2.5 text-xs text-slate-700 bg-white focus:ring-1 focus:ring-teal-500"
        >
          <option value="all">All Severities</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>

        {/* Department Filter */}
        <select
          value={deptFilter}
          onChange={(e) => setDeptFilter(e.target.value)}
          className="rounded-lg border border-slate-300 py-1.5 px-2.5 text-xs text-slate-700 bg-white focus:ring-1 focus:ring-teal-500"
        >
          <option value="all">All Departments</option>
          {departments.map((dept) => (
            <option key={dept} value={dept}>
              {dept}
            </option>
          ))}
        </select>

        <span className="ml-auto text-slate-400 text-[11px]">
          Showing {filteredFindings.length} of {findings.length} findings
        </span>
      </div>

      {loading ? (
        <div className="py-24 flex items-center justify-center">
          <LoadingSpinner size="lg" message="Loading findings repository..." />
        </div>
      ) : error ? (
        <EmptyState title="Error Loading Findings" message={error} onAction={loadData} actionLabel="Retry" />
      ) : findings.length === 0 ? (
        <EmptyState
          title="No Findings Registered"
          message="No findings have been extracted or registered yet. Upload an audit report in Document Centre to extract findings."
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Findings List (Left column) */}
          <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden max-h-[800px] flex flex-col">
            <div className="p-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-xs font-semibold text-slate-700">
              <span>Audit Findings List</span>
              <span className="text-[11px] text-slate-400 font-normal">Click to review details</span>
            </div>

            <div className="divide-y divide-slate-100 overflow-y-auto flex-1">
              {filteredFindings.map((finding) => {
                const isSelected = selectedFinding?.id === finding.id;
                const isAiDraft = finding.review_status === 'Draft' && finding.ai_generated;
                const ctrl = controls.find((c) => c.id === finding.control_id);

                return (
                  <div
                    key={finding.id}
                    onClick={() => selectFinding(finding)}
                    className={clsx(
                      'p-4 cursor-pointer transition text-left flex flex-col gap-2 relative',
                      isSelected ? 'bg-teal-50/50 ring-2 ring-teal-500/20' : 'hover:bg-slate-50/70',
                      isAiDraft && 'border-l-4 border-l-amber-400'
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="font-mono text-[11px] font-bold text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded">
                          {ctrl?.control_code || 'General'}
                        </span>
                        <SeverityBadge severity={finding.severity} />
                        {finding.is_recurrence && (
                          <span className="text-[10px] bg-amber-50 text-amber-800 border border-amber-300 px-1.5 py-0.2 rounded font-semibold">
                            Recurrence
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] font-medium text-slate-500">
                        {finding.status}
                      </span>
                    </div>

                    <p className="text-xs font-semibold text-slate-900 line-clamp-2 leading-relaxed">
                      {finding.description}
                    </p>

                    <div className="flex items-center justify-between text-[11px] text-slate-500 mt-1">
                      <span>{finding.department || 'All Departments'}</span>
                      {finding.review_status === 'Approved' ? (
                        <VerifiedBadge label="Approved" className="text-[10px] py-0 px-2" />
                      ) : (
                        <span className="text-[10px] text-amber-700 bg-amber-100/80 px-1.5 py-0.5 rounded font-medium border border-dashed border-amber-300">
                          Draft AI
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Finding Detail & Verification Panel (Right column) */}
          <div className="lg:col-span-7 space-y-4">
            {selectedFinding ? (
              <div
                className={clsx(
                  'bg-white rounded-xl shadow-xs overflow-hidden transition-all',
                  selectedFinding.review_status === 'Approved'
                    ? 'border-2 border-emerald-500/40'
                    : selectedFinding.ai_generated
                    ? 'border-2 border-dashed border-amber-400'
                    : 'border border-slate-200'
                )}
              >
                {/* Header status banner */}
                <div className="p-4 sm:p-5 border-b border-slate-100 bg-slate-50/50 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    {selectedFinding.review_status === 'Approved' ? (
                      <VerifiedBadge label="Approved Record" />
                    ) : (
                      <AiSuggestionBanner
                        message="AI Extracted Finding — Pending Verification"
                        className="py-1 px-2.5 text-xs"
                      />
                    )}
                    <span className="text-xs font-mono text-slate-400">
                      ID: {selectedFinding.id.slice(0, 8)}
                    </span>
                  </div>

                  {/* Actions / Edit toggle */}
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setEditMode(!editMode)}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 px-2.5 py-1.5 rounded-lg shadow-2xs transition"
                    >
                      <PencilSquareIcon className="w-3.5 h-3.5 text-slate-500" />
                      <span>{editMode ? 'Cancel Edit' : 'Edit Metadata'}</span>
                    </button>

                    {/* Approve button for Draft findings */}
                    {selectedFinding.review_status === 'Draft' && (
                      <button
                        type="button"
                        disabled={isControlOwner || actionLoading}
                        onClick={() => setApproveDialogOpen(true)}
                        className={clsx(
                          'inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white rounded-lg shadow-xs transition',
                          isControlOwner
                            ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
                            : 'bg-emerald-600 hover:bg-emerald-700'
                        )}
                        title={
                          isControlOwner
                            ? 'Control owners cannot approve audit findings. Compliance Officer or Admin review required.'
                            : 'Approve finding and check historic recurrences'
                        }
                      >
                        <CheckCircleIcon className="w-4 h-4" />
                        <span>Approve Finding</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Edit Notice if control_owner */}
                {isControlOwner && selectedFinding.review_status === 'Draft' && (
                  <div className="bg-amber-50 px-5 py-2 text-[11px] text-amber-800 border-b border-amber-200 flex items-center gap-1.5">
                    <span>Role restriction: As a Control Owner, you cannot approve findings. Approval is restricted to Compliance Officers and Admins.</span>
                  </div>
                )}

                {/* Finding Body */}
                <div className="p-5 sm:p-6 space-y-5 text-xs">
                  {editMode ? (
                    /* Edit Form */
                    <div className="space-y-4 bg-slate-50 p-4 rounded-xl border border-slate-200">
                      <div>
                        <label className="block text-xs font-bold text-slate-700 mb-1">
                          Mapped Control
                        </label>
                        <select
                          value={editForm.control_id}
                          onChange={(e) => setEditForm({ ...editForm, control_id: e.target.value })}
                          className="w-full rounded-lg border border-slate-300 p-2 text-xs bg-white focus:ring-1 focus:ring-teal-500"
                        >
                          <option value="">-- No Control Assigned --</option>
                          {controls.map((c) => (
                            <option key={c.id} value={c.id}>
                              {c.control_code}: {c.title}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs font-bold text-slate-700 mb-1">
                            Department
                          </label>
                          <input
                            type="text"
                            value={editForm.department}
                            onChange={(e) => setEditForm({ ...editForm, department: e.target.value })}
                            className="w-full rounded-lg border border-slate-300 p-2 text-xs bg-white focus:ring-1 focus:ring-teal-500"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-bold text-slate-700 mb-1">
                            Severity
                          </label>
                          <select
                            value={editForm.severity}
                            onChange={(e) =>
                              setEditForm({ ...editForm, severity: e.target.value as FindingSeverity })
                            }
                            className="w-full rounded-lg border border-slate-300 p-2 text-xs bg-white focus:ring-1 focus:ring-teal-500"
                          >
                            <option value="High">High</option>
                            <option value="Medium">Medium</option>
                            <option value="Low">Low</option>
                          </select>
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs font-bold text-slate-700 mb-1">
                          Deficiency Description
                        </label>
                        <textarea
                          rows={3}
                          value={editForm.description}
                          onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                          className="w-full rounded-lg border border-slate-300 p-2 text-xs bg-white focus:ring-1 focus:ring-teal-500"
                        />
                      </div>

                      <div className="flex justify-end gap-2 pt-2">
                        <button
                          type="button"
                          onClick={() => setEditMode(false)}
                          className="px-3 py-1.5 rounded-lg border border-slate-300 bg-white text-slate-700 font-semibold"
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          onClick={handleSaveEdit}
                          disabled={actionLoading}
                          className="px-3 py-1.5 rounded-lg bg-teal-600 text-white font-semibold hover:bg-teal-700 shadow-xs"
                        >
                          {actionLoading ? 'Saving...' : 'Save Changes'}
                        </button>
                      </div>
                    </div>
                  ) : (
                    /* Display Mode */
                    <div className="space-y-4">
                      <div>
                        <h3 className="text-sm font-bold text-slate-900 leading-snug">
                          {selectedFinding.description}
                        </h3>
                      </div>

                      {/* Metadata Chips */}
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 p-3.5 rounded-xl border border-slate-100">
                        <div>
                          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                            Control
                          </span>
                          <span className="font-semibold text-slate-800 font-mono">
                            {controls.find((c) => c.id === selectedFinding.control_id)?.control_code ||
                              'Unassigned'}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                            Department
                          </span>
                          <span className="font-semibold text-slate-800">
                            {selectedFinding.department || 'General'}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                            Severity
                          </span>
                          <SeverityBadge severity={selectedFinding.severity} />
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider block">
                            Status
                          </span>
                          <span className="font-semibold text-slate-800">
                            {selectedFinding.status}
                          </span>
                        </div>
                      </div>

                      {/* Source Document Excerpt Callout */}
                      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                            <DocumentMagnifyingGlassIcon className="w-4 h-4 text-teal-600" />
                            Original Source Reference
                          </span>
                          {selectedFinding.source_document_id && (
                            <button
                              type="button"
                              onClick={() =>
                                openSourceViewer(
                                  selectedFinding.source_document_id,
                                  selectedFinding.source_page,
                                  selectedFinding.source_excerpt,
                                  controls.find((c) => c.id === selectedFinding.control_id)?.control_code
                                )
                              }
                              className="text-xs font-semibold text-teal-700 hover:text-teal-900 bg-white border border-teal-200 hover:border-teal-300 px-2.5 py-1 rounded-lg transition shadow-2xs"
                            >
                              Open Source Drawer →
                            </button>
                          )}
                        </div>

                        {selectedFinding.source_excerpt ? (
                          <blockquote className="text-xs text-slate-700 italic border-l-2 border-teal-500 pl-3 py-1 bg-white/70 rounded">
                            "{selectedFinding.source_excerpt}"
                          </blockquote>
                        ) : (
                          <p className="text-xs text-slate-400 italic">
                            No specific page excerpt recorded for this finding.
                          </p>
                        )}

                        <div className="text-[11px] text-slate-400 flex items-center gap-3 pt-1">
                          {selectedFinding.source_document_id && (
                            <span>Doc ID: {selectedFinding.source_document_id.slice(0, 8)}...</span>
                          )}
                          {selectedFinding.source_page && (
                            <span>Page Number: {selectedFinding.source_page}</span>
                          )}
                        </div>
                      </div>

                      {/* Status Transition Options */}
                      <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-600">
                          Workflow Transition:
                        </span>
                        <div className="flex items-center gap-2">
                          {['Open', 'In Remediation', 'Ready for Review', 'Closed'].map((st) => (
                            <button
                              key={st}
                              type="button"
                              onClick={() => handleStatusChange(st)}
                              disabled={selectedFinding.status === st}
                              className={clsx(
                                'text-xs px-2.5 py-1 rounded-md font-semibold transition',
                                selectedFinding.status === st
                                  ? 'bg-slate-200 text-slate-700 cursor-default'
                                  : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-50'
                              )}
                            >
                              {st}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Related Findings Suggestions (Post-Approval or from History) */}
                  <div className="pt-4 border-t border-slate-200 space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                        Possible Related Past Findings (History Retrieval)
                      </h4>
                      {selectedFinding.is_recurrence && (
                        <span className="text-[11px] font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">
                          Recurrence Confirmed
                        </span>
                      )}
                    </div>

                    {historyLoading ? (
                      <LoadingSpinner size="sm" message="Searching audit historical records..." />
                    ) : findingHistory?.related_findings && findingHistory.related_findings.length > 0 ? (
                      <div className="space-y-2.5">
                        {findingHistory.related_findings.map((rf) => (
                          <div
                            key={rf.id || rf.related_finding_id}
                            className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/75 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                          >
                            <div className="space-y-1">
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-bold text-slate-900 font-mono">
                                  ID: {rf.related_finding_id.slice(0, 8)}...
                                </span>
                                <span className="text-[10px] bg-teal-100 text-teal-800 px-1.5 py-0.2 rounded font-semibold">
                                  Match Score: {rf.match_score}
                                </span>
                                {rf.reviewed_by ? (
                                  <span className="text-[10px] text-slate-500 italic">
                                    (Reviewed by {rf.reviewed_by.slice(0, 6)}...)
                                  </span>
                                ) : (
                                  <span className="text-[10px] text-amber-700 bg-amber-100 px-1.5 py-0.2 rounded font-semibold">
                                    Needs Confirmation
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-slate-600 font-medium">
                                {rf.match_reason}
                              </p>
                            </div>

                            {!rf.reviewed_by && (
                              <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">
                                <button
                                  type="button"
                                  onClick={() => handleReviewRelated(rf.id || rf.related_finding_id, 'confirmed')}
                                  className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-white bg-teal-600 hover:bg-teal-700 rounded-lg shadow-2xs"
                                >
                                  <CheckCircleIcon className="w-3.5 h-3.5" />
                                  Confirm Recurrence
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleReviewRelated(rf.id || rf.related_finding_id, 'rejected')}
                                  className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg shadow-2xs"
                                >
                                  <XCircleIcon className="w-3.5 h-3.5" />
                                  Dismiss
                                </button>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="p-3 bg-slate-50 rounded-lg text-slate-400 text-xs italic">
                        No relevant history found in prior audit cycles.
                      </div>
                    )}
                  </div>

                  {/* Status History Audit Trail */}
                  {findingHistory?.status_history && findingHistory.status_history.length > 0 && (
                    <div className="pt-3 border-t border-slate-200">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                        Status Transition Audit Log
                      </h4>
                      <div className="space-y-1.5">
                        {findingHistory.status_history.map((sh) => (
                          <div
                            key={sh.id}
                            className="text-[11px] text-slate-600 flex items-center justify-between py-1 border-b border-slate-100 last:border-none"
                          >
                            <span>
                              Changed from <strong className="text-slate-800">{sh.old_status}</strong> →{' '}
                              <strong className="text-slate-800">{sh.new_status}</strong>
                              {sh.note ? ` (${sh.note})` : ''}
                            </span>
                            <span className="text-slate-400 font-mono">
                              {new Date(sh.changed_at).toLocaleString()}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <EmptyState title="Select a Finding" message="Choose an audit finding from the list on the left to inspect its details." />
            )}
          </div>
        </div>
      )}

      {/* Confirmation Dialog for Approving Findings */}
      <ConfirmDialog
        isOpen={approveDialogOpen}
        onClose={() => setApproveDialogOpen(false)}
        onConfirm={handleApprove}
        loading={actionLoading}
        title="Approve AI Audit Finding"
        message="Approving this finding will transition it from 'Draft' to 'Approved' official record and immediately trigger audit history retrieval to check for similar recurring defects across prior audit cycles."
        confirmLabel="Approve Finding"
        variant="primary"
      />

      {/* Source Drawer for Page Context */}
      <SourceDrawer
        isOpen={sourceDrawerOpen}
        onClose={() => setSourceDrawerOpen(false)}
        documentId={drawerDocId}
        pageNumber={drawerPage}
        highlightExcerpt={drawerExcerpt}
        controlCode={drawerControl}
      />
    </div>
  );
};

export default FindingsReview;
