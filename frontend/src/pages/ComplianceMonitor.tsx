import React, { useEffect, useState, useMemo } from 'react';
import { api } from '../api/client';
import { Control, Evidence, Finding, ControlStatus } from '../api/types';
import { useUser } from '../context/UserContext';
import { useToast } from '../components/Toast';
import StatusBadge from '../components/StatusBadge';
import SeverityBadge from '../components/SeverityBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import SourceDrawer from '../components/SourceDrawer';
import {
  ShieldCheckIcon,
  FunnelIcon,
  ArrowPathIcon,
  PlusIcon,
  XMarkIcon,
  DocumentTextIcon,
  ExclamationCircleIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';

export const ComplianceMonitor: React.FC = () => {
  const { currentUser } = useUser();
  const { showToast } = useToast();

  const [controls, setControls] = useState<Control[]>([]);
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Search
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Selected Control for Detail Drawer
  const [selectedControl, setSelectedControl] = useState<Control | null>(null);

  // Remediation / Review Task Modal state
  const [taskModalOpen, setTaskModalOpen] = useState<boolean>(false);
  const [taskFindingId, setTaskFindingId] = useState<string>('');
  const [taskAction, setTaskAction] = useState<string>('');
  const [taskDueDate, setTaskDueDate] = useState<string>('');
  const [taskEvidenceNote, setTaskEvidenceNote] = useState<string>('');
  const [taskSubmitting, setTaskSubmitting] = useState<boolean>(false);

  // Source drawer
  const [sourceDrawerOpen, setSourceDrawerOpen] = useState<boolean>(false);
  const [sourceDocId, setSourceDocId] = useState<string | null>(null);
  const [sourcePage, setSourcePage] = useState<number | null>(null);
  const [sourceExcerpt, setSourceExcerpt] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [ctrls, evs, fnds] = await Promise.all([
        api.getControls(),
        api.getEvidence().catch(() => []),
        api.getFindings().catch(() => []),
      ]);
      setControls(ctrls);
      setEvidenceList(evs);
      setFindings(fnds);
    } catch (err: any) {
      setError(err.message || 'Failed to load control register.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Filtered controls
  const filteredControls = useMemo(() => {
    return controls.filter((c) => {
      if (statusFilter !== 'all' && c.status !== statusFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesCode = c.control_code.toLowerCase().includes(q);
        const matchesTitle = c.title.toLowerCase().includes(q);
        const matchesOwner = c.owner.toLowerCase().includes(q);
        if (!matchesCode && !matchesTitle && !matchesOwner) return false;
      }
      return true;
    });
  }, [controls, statusFilter, searchQuery]);

  // Last evidence date map
  const lastEvidenceMap = useMemo(() => {
    const map: Record<string, string> = {};
    evidenceList.forEach((ev) => {
      if (ev.evidence_date) {
        if (!map[ev.control_id] || ev.evidence_date > map[ev.control_id]) {
          map[ev.control_id] = ev.evidence_date;
        }
      }
    });
    return map;
  }, [evidenceList]);

  // Handle Control Status Transition (e.g. Compliant / Needs Review)
  const handleUpdateStatus = async (controlId: string, newStatus: string) => {
    try {
      const updated = await api.updateControlStatus(controlId, newStatus);
      showToast(`Control status updated to ${newStatus}.`, 'success');
      setControls((prev) => prev.map((c) => (c.id === controlId ? updated : c)));
      if (selectedControl && selectedControl.id === controlId) {
        setSelectedControl(updated);
      }
    } catch (err: any) {
      showToast(err.message || 'Failed to update control status.', 'error');
    }
  };

  // Handle Create Review Task (Remediation)
  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedControl) return;

    // Use finding id or fallback to finding for this control
    const targetFinding =
      findings.find((f) => f.id === taskFindingId) ||
      findings.find((f) => f.control_id === selectedControl.id) ||
      findings[0];

    if (!targetFinding) {
      showToast('A finding is required to attach a remediation action.', 'error');
      return;
    }

    setTaskSubmitting(true);
    try {
      await api.createRemediation({
        finding_id: targetFinding.id,
        owner: selectedControl.owner,
        action: taskAction || `Conduct quarterly review for ${selectedControl.control_code}`,
        due_date: taskDueDate || null,
        evidence_note: taskEvidenceNote || null,
      });

      showToast(`Review task assigned to ${selectedControl.owner}.`, 'success');
      setTaskModalOpen(false);
      setTaskAction('');
      setTaskDueDate('');
      setTaskEvidenceNote('');
    } catch (err: any) {
      showToast(err.message || 'Failed to create remediation task.', 'error');
    } finally {
      setTaskSubmitting(false);
    }
  };

  const openSourceForEvidence = (ev: Evidence) => {
    if (!ev.document_id) {
      showToast('No document ID attached to this evidence.', 'info');
      return;
    }
    setSourceDocId(ev.document_id);
    setSourcePage(ev.page_number || 1);
    setSourceExcerpt(ev.excerpt || null);
    setSourceDrawerOpen(true);
  };

  // Control details when drawer is open
  const controlEvidence = selectedControl
    ? evidenceList.filter((ev) => ev.control_id === selectedControl.id)
    : [];
  const controlFindings = selectedControl
    ? findings.filter((f) => f.control_id === selectedControl.id && f.status !== 'Closed')
    : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Continuous Compliance Monitor
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            ISO/IEC 27001-inspired control register with real-time audit evidence verification
          </p>
        </div>
        <button
          type="button"
          onClick={loadData}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-xs self-start sm:self-auto"
        >
          <ArrowPathIcon className="w-3.5 h-3.5" />
          Refresh Register
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 text-slate-500 font-medium">
            <FunnelIcon className="w-4 h-4 text-slate-400" />
            <span>Filter Status:</span>
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-slate-300 py-1.5 px-2.5 text-xs text-slate-700 bg-white focus:ring-1 focus:ring-teal-500"
          >
            <option value="all">All Control Statuses</option>
            <option value="Compliant">Compliant</option>
            <option value="Needs Review">Needs Review</option>
            <option value="Gap Identified">Gap Identified</option>
            <option value="Not Assessed">Not Assessed</option>
          </select>
        </div>

        <div className="w-full sm:w-72">
          <input
            type="text"
            placeholder="Search code, title, owner..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-slate-300 py-1.5 px-3 text-xs bg-slate-50 focus:bg-white focus:ring-1 focus:ring-teal-500"
          />
        </div>
      </div>

      {/* Control Register Table */}
      {loading ? (
        <div className="py-24 flex items-center justify-center">
          <LoadingSpinner size="lg" message="Loading control register..." />
        </div>
      ) : error ? (
        <EmptyState title="Error Loading Controls" message={error} actionLabel="Retry" onAction={loadData} />
      ) : filteredControls.length === 0 ? (
        <EmptyState
          title="No Controls Found"
          message="No controls match your search criteria. Try modifying your filters."
        />
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50/75 border-b border-slate-200 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  <th className="py-3 px-4">Code</th>
                  <th className="py-3 px-4">Title & Description</th>
                  <th className="py-3 px-4">Owner</th>
                  <th className="py-3 px-4">Cadence</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Last Evidence</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {filteredControls.map((ctrl) => {
                  const lastEv = lastEvidenceMap[ctrl.id];
                  return (
                    <tr
                      key={ctrl.id}
                      onClick={() => setSelectedControl(ctrl)}
                      className={clsx(
                        'hover:bg-teal-50/30 transition cursor-pointer',
                        selectedControl?.id === ctrl.id && 'bg-teal-50/50'
                      )}
                    >
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <span className="font-mono font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded text-xs border border-slate-200">
                          {ctrl.control_code}
                        </span>
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="font-bold text-slate-900 text-xs">
                          {ctrl.title}
                        </div>
                        {ctrl.description && (
                          <div className="text-[11px] text-slate-500 truncate max-w-md mt-0.5">
                            {ctrl.description}
                          </div>
                        )}
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap text-slate-600 font-medium">
                        {ctrl.owner}
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap capitalize text-slate-600">
                        {ctrl.cadence}
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap">
                        <StatusBadge status={ctrl.status} />
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap text-slate-500 font-mono text-[11px]">
                        {lastEv ? new Date(lastEv).toLocaleDateString() : '—'}
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap text-right">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedControl(ctrl);
                          }}
                          className="text-xs font-semibold text-teal-600 hover:text-teal-800 hover:underline"
                        >
                          View Details →
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Control Detail Drawer */}
      {selectedControl && (
        <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs transition-opacity animate-fade-in">
          <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
            <div className="w-screen max-w-xl bg-white shadow-2xl flex flex-col border-l border-slate-200">
              {/* Drawer Header */}
              <div className="p-5 bg-slate-900 text-white flex items-center justify-between border-b border-slate-800">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-teal-500/20 text-teal-400">
                    <ShieldCheckIcon className="w-6 h-6" />
                  </div>
                  <div>
                    <h2 className="text-base font-semibold text-white">
                      {selectedControl.control_code}: {selectedControl.title}
                    </h2>
                    <p className="text-xs text-slate-300">
                      Owner: {selectedControl.owner} • Cadence: {selectedControl.cadence}
                    </p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedControl(null)}
                  className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-slate-800"
                >
                  <XMarkIcon className="w-6 h-6" />
                </button>
              </div>

              {/* Status & Transitions */}
              <div className="px-6 py-3.5 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3 text-xs">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-slate-600">Current Status:</span>
                  <StatusBadge status={selectedControl.status} />
                </div>

                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] text-slate-400 font-semibold mr-1">Set Status:</span>
                  {(['Compliant', 'Needs Review', 'Gap Identified', 'Not Assessed'] as ControlStatus[]).map(
                    (st) => (
                      <button
                        key={st}
                        type="button"
                        onClick={() => handleUpdateStatus(selectedControl.id, st)}
                        disabled={selectedControl.status === st}
                        className={clsx(
                          'text-[10px] font-semibold px-2 py-0.5 rounded transition',
                          selectedControl.status === st
                            ? 'bg-slate-300 text-slate-600 cursor-default'
                            : 'bg-white border border-slate-300 text-slate-700 hover:bg-slate-100'
                        )}
                      >
                        {st}
                      </button>
                    )
                  )}
                </div>
              </div>

              {/* Drawer Content */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {/* Description & Evidence Expectation */}
                <div className="space-y-3 bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs">
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-0.5">
                      Description
                    </span>
                    <p className="text-slate-800 leading-relaxed font-medium">
                      {selectedControl.description || 'No description provided.'}
                    </p>
                  </div>
                  <div>
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-0.5">
                      Evidence Expectation
                    </span>
                    <p className="text-slate-600 leading-relaxed italic">
                      {selectedControl.evidence_expectation || 'Standard periodic documentation.'}
                    </p>
                  </div>
                </div>

                {/* Evidence items with assessment badges */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                      Attached Evidence Items ({controlEvidence.length})
                    </h3>
                  </div>

                  {controlEvidence.length === 0 ? (
                    <div className="p-4 rounded-lg bg-slate-50 border border-dashed border-slate-200 text-center text-xs text-slate-400">
                      No evidence records currently mapped to this control.
                    </div>
                  ) : (
                    <div className="space-y-2.5">
                      {controlEvidence.map((ev) => (
                        <div
                          key={ev.id}
                          className="p-3.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 transition flex flex-col gap-2"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span
                              className={clsx(
                                'text-[10px] font-semibold px-2 py-0.5 rounded-full border',
                                ev.assessment === 'Candidate Match'
                                  ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                                  : ev.assessment === 'Missing'
                                  ? 'bg-rose-50 text-rose-800 border-rose-300'
                                  : ev.assessment === 'Expired'
                                  ? 'bg-orange-50 text-orange-800 border-orange-300'
                                  : 'bg-amber-50 text-amber-800 border-amber-300'
                              )}
                            >
                              {ev.assessment}
                            </span>
                            <span className="text-[11px] text-slate-400">
                              {ev.evidence_date ? `Date: ${ev.evidence_date}` : 'Undated'}
                            </span>
                          </div>

                          {ev.excerpt && (
                            <blockquote className="text-xs text-slate-700 italic border-l-2 border-slate-300 pl-2.5 py-0.5">
                              "{ev.excerpt}"
                            </blockquote>
                          )}

                          <div className="flex items-center justify-between pt-1 text-[11px]">
                            <span className="text-slate-400">
                              Review: <strong className="text-slate-700">{ev.review_status}</strong>
                            </span>
                            {ev.document_id && (
                              <button
                                type="button"
                                onClick={() => openSourceForEvidence(ev)}
                                className="text-teal-700 font-semibold hover:underline flex items-center gap-1"
                              >
                                <DocumentTextIcon className="w-3.5 h-3.5" />
                                Inspect Source
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Open Findings for this control */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                      Active Open Findings ({controlFindings.length})
                    </h3>
                  </div>

                  {controlFindings.length === 0 ? (
                    <div className="p-4 rounded-lg bg-emerald-50/60 border border-emerald-200 text-xs text-emerald-800 flex items-center gap-2">
                      <ShieldCheckIcon className="w-4 h-4 text-emerald-600" />
                      <span>No active open findings for this control.</span>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {controlFindings.map((f) => (
                        <div
                          key={f.id}
                          className="p-3 rounded-lg border border-slate-200 bg-white flex items-start justify-between gap-3"
                        >
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <SeverityBadge severity={f.severity} />
                              <span className="text-[10px] text-slate-500 font-medium">
                                Status: {f.status}
                              </span>
                              {f.is_recurrence && (
                                <span className="text-[10px] text-amber-700 font-semibold bg-amber-50 px-1 rounded">
                                  Recurring
                                </span>
                              )}
                            </div>
                            <p className="text-xs text-slate-800 font-medium">{f.description}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Drawer Footer Actions */}
              <div className="p-4 bg-white border-t border-slate-200 flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => {
                    const matchedFinding = controlFindings[0] || findings[0];
                    setTaskFindingId(matchedFinding?.id || '');
                    setTaskAction(`Execute quarterly access review for ${selectedControl.control_code}`);
                    setTaskModalOpen(true);
                  }}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-teal-600 rounded-lg hover:bg-teal-700 transition shadow-xs"
                >
                  <PlusIcon className="w-4 h-4" />
                  Create Review Task
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedControl(null)}
                  className="px-4 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition shadow-2xs"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create Review Task Modal */}
      {taskModalOpen && selectedControl && (
        <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 border border-slate-200 animate-slide-up">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900">
                Create Remediation Task for {selectedControl.control_code}
              </h3>
              <button
                type="button"
                onClick={() => setTaskModalOpen(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateTask} className="mt-4 space-y-4 text-xs">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Assignee (Control Owner)
                </label>
                <input
                  type="text"
                  disabled
                  value={selectedControl.owner}
                  className="w-full rounded-lg border border-slate-200 bg-slate-100 p-2 text-xs text-slate-700 cursor-not-allowed"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Target Finding
                </label>
                <select
                  value={taskFindingId}
                  onChange={(e) => setTaskFindingId(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 p-2 text-xs bg-white focus:ring-1 focus:ring-teal-500"
                  required
                >
                  {findings.map((f) => (
                    <option key={f.id} value={f.id}>
                      [{f.severity}] {f.description.slice(0, 50)}...
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Remediation Action
                </label>
                <textarea
                  rows={2}
                  required
                  value={taskAction}
                  onChange={(e) => setTaskAction(e.target.value)}
                  placeholder="e.g. Schedule and conduct role-based access reviews..."
                  className="w-full rounded-lg border border-slate-300 p-2 text-xs bg-white focus:ring-1 focus:ring-teal-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Due Date
                </label>
                <input
                  type="date"
                  value={taskDueDate}
                  onChange={(e) => setTaskDueDate(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 p-2 text-xs bg-white focus:ring-1 focus:ring-teal-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Evidence Requirement Note
                </label>
                <input
                  type="text"
                  value={taskEvidenceNote}
                  onChange={(e) => setTaskEvidenceNote(e.target.value)}
                  placeholder="e.g. Upload signed PDF extract from HR system"
                  className="w-full rounded-lg border border-slate-300 p-2 text-xs bg-white focus:ring-1 focus:ring-teal-500"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setTaskModalOpen(false)}
                  className="px-3 py-1.5 rounded-lg border border-slate-300 bg-white text-slate-700 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={taskSubmitting}
                  className="px-3.5 py-1.5 rounded-lg bg-teal-600 text-white font-semibold hover:bg-teal-700 shadow-xs"
                >
                  {taskSubmitting ? 'Creating Task...' : 'Assign Remediation Task'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Source Drawer for Evidence Text */}
      <SourceDrawer
        isOpen={sourceDrawerOpen}
        onClose={() => setSourceDrawerOpen(false)}
        documentId={sourceDocId}
        pageNumber={sourcePage}
        highlightExcerpt={sourceExcerpt}
        controlCode={selectedControl?.control_code}
      />
    </div>
  );
};

export default ComplianceMonitor;
