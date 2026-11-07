import React, { useEffect, useState, useMemo } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import { RemediationAction, Finding, Control, RemediationStatus } from '../api/types';
import { useUser } from '../context/UserContext';
import { useToast } from '../components/Toast';
import StatusBadge from '../components/StatusBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import ConfirmDialog from '../components/ConfirmDialog';
import {
  WrenchScrewdriverIcon,
  PlusIcon,
  FunnelIcon,
  ClockIcon,
  CheckCircleIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';

export const RemediationTracker: React.FC = () => {
  const { currentUser } = useUser();
  const { showToast } = useToast();
  const [searchParams] = useSearchParams();
  const findingIdParam = searchParams.get('finding_id');

  const [remediations, setRemediations] = useState<RemediationAction[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [controls, setControls] = useState<Control[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [overdueOnly, setOverdueOnly] = useState<boolean>(false);

  // Create Modal
  const [createModalOpen, setCreateModalOpen] = useState<boolean>(false);
  const [createFindingId, setCreateFindingId] = useState<string>(findingIdParam || '');
  const [createOwner, setCreateOwner] = useState<string>('Owen Owner');
  const [createAction, setCreateAction] = useState<string>('');
  const [createDueDate, setCreateDueDate] = useState<string>('');
  const [createEvidenceNote, setCreateEvidenceNote] = useState<string>('');
  const [submitting, setSubmitting] = useState<boolean>(false);

  // Status transition dialog
  const [transitionDialogOpen, setTransitionDialogOpen] = useState<boolean>(false);
  const [selectedAction, setSelectedAction] = useState<RemediationAction | null>(null);
  const [targetStatus, setTargetStatus] = useState<RemediationStatus | null>(null);
  const [transitionNote, setTransitionNote] = useState<string>('');

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [remsData, findingsData, controlsData] = await Promise.all([
        api.getRemediations(findingIdParam || undefined),
        api.getFindings(),
        api.getControls(),
      ]);
      setRemediations(remsData);
      setFindings(findingsData);
      setControls(controlsData);
      if (findingIdParam && !createFindingId) {
        setCreateFindingId(findingIdParam);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load remediation actions.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [findingIdParam]);

  const findingsMap = useMemo(() => {
    const map = new Map<string, Finding>();
    findings.forEach((f) => map.set(f.id, f));
    return map;
  }, [findings]);

  const controlsMap = useMemo(() => {
    const map = new Map<string, Control>();
    controls.forEach((c) => map.set(c.id, c));
    return map;
  }, [controls]);

  const filteredRemediations = useMemo(() => {
    return remediations.filter((rem) => {
      if (statusFilter !== 'all' && rem.status !== statusFilter) return false;
      if (overdueOnly && !rem.is_overdue) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesAction = rem.action.toLowerCase().includes(q);
        const matchesOwner = rem.owner?.toLowerCase().includes(q);
        const finding = findingsMap.get(rem.finding_id);
        const matchesFinding = finding?.description.toLowerCase().includes(q);
        if (!matchesAction && !matchesOwner && !matchesFinding) return false;
      }
      return true;
    });
  }, [remediations, statusFilter, overdueOnly, searchQuery, findingsMap]);

  const handleOpenCreate = () => {
    if (findings.length > 0 && !createFindingId) {
      setCreateFindingId(findings[0].id);
    }
    setCreateModalOpen(true);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createFindingId || !createAction.trim()) {
      showToast('Finding and Action description are required.', 'error');
      return;
    }

    setSubmitting(true);
    try {
      const created = await api.createRemediation({
        finding_id: createFindingId,
        owner: createOwner.trim() || 'Unassigned',
        action: createAction.trim(),
        due_date: createDueDate || null,
        evidence_note: createEvidenceNote.trim() || null,
      });
      showToast('Remediation action created successfully.', 'success');
      setCreateModalOpen(false);
      setCreateAction('');
      setCreateEvidenceNote('');
      setCreateDueDate('');
      setRemediations((prev) => [created, ...prev]);
    } catch (err: any) {
      showToast(err?.message || 'Failed to create remediation action.', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handlePromptTransition = (rem: RemediationAction, nextStatus: RemediationStatus) => {
    setSelectedAction(rem);
    setTargetStatus(nextStatus);
    setTransitionNote('');
    setTransitionDialogOpen(true);
  };

  const handleConfirmTransition = async () => {
    if (!selectedAction || !targetStatus) return;

    setSubmitting(true);
    try {
      const updated = await api.changeRemediationStatus(
        selectedAction.id,
        targetStatus,
        transitionNote.trim() || undefined
      );
      showToast(`Action updated to "${targetStatus}".`, 'success');
      setRemediations((prev) =>
        prev.map((r) => (r.id === updated.id ? updated : r))
      );
      setTransitionDialogOpen(false);
    } catch (err: any) {
      showToast(err?.message || 'Failed to update remediation status.', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const role = currentUser?.role || 'auditor';
  const isAuditor = role === 'auditor';
  const canComplete = role === 'admin' || role === 'compliance_officer';
  const canProgress = role === 'admin' || role === 'compliance_officer' || role === 'control_owner';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2.5">
            <WrenchScrewdriverIcon className="w-7 h-7 text-teal-600" />
            Remediation Tracker
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Track corrective actions, assignees, deadlines, and completion evidence linked to audit findings.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadData}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition shadow-xs"
          >
            <ArrowPathIcon className={clsx('w-4 h-4', loading && 'animate-spin')} />
            Refresh
          </button>
          {!isAuditor && (
            <button
              type="button"
              onClick={handleOpenCreate}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-700 transition shadow-xs"
            >
              <PlusIcon className="w-4 h-4" />
              New Action
            </button>
          )}
        </div>
      </div>

      {/* Overdue alert banner if any */}
      {remediations.some((r) => r.is_overdue) && (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-rose-100 rounded-lg text-rose-700">
              <ExclamationTriangleIcon className="w-5 h-5" />
            </div>
            <div>
              <p className="text-sm font-semibold text-rose-900">
                {remediations.filter((r) => r.is_overdue).length} Remediation Actions Overdue
              </p>
              <p className="text-xs text-rose-700 mt-0.5">
                Past due actions elevate the illustrative risk indicators for linked controls.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setOverdueOnly(!overdueOnly)}
            className={clsx(
              'text-xs font-semibold px-3 py-1.5 rounded-lg border transition',
              overdueOnly
                ? 'bg-rose-600 text-white border-rose-700'
                : 'bg-white text-rose-800 border-rose-300 hover:bg-rose-100/50'
            )}
          >
            {overdueOnly ? 'Show All' : 'Filter Overdue'}
          </button>
        </div>
      )}

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        <div className="flex flex-wrap gap-2 items-center flex-1">
          <div className="relative flex-1 min-w-[200px]">
            <MagnifyingGlassIcon className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            <input
              type="text"
              placeholder="Search actions, owner, finding..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
            />
          </div>

          <div className="flex items-center gap-1.5">
            <FunnelIcon className="w-4 h-4 text-slate-400" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-sm border border-slate-300 rounded-lg px-2.5 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-700"
            >
              <option value="all">All Statuses</option>
              <option value="Planned">Planned</option>
              <option value="In Progress">In Progress</option>
              <option value="Ready for Review">Ready for Review</option>
              <option value="Completed">Completed</option>
            </select>
          </div>

          <label className="flex items-center gap-2 text-xs font-medium text-slate-700 ml-2 cursor-pointer">
            <input
              type="checkbox"
              checked={overdueOnly}
              onChange={(e) => setOverdueOnly(e.target.checked)}
              className="rounded text-teal-600 focus:ring-teal-500"
            />
            Overdue only
          </label>
        </div>

        <div className="text-xs text-slate-500 font-medium">
          Showing {filteredRemediations.length} of {remediations.length} actions
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <LoadingSpinner message="Loading remediation actions..." />
      ) : error ? (
        <EmptyState title="Error Loading Actions" description={error} />
      ) : filteredRemediations.length === 0 ? (
        <EmptyState
          title="No Remediation Actions Found"
          description={
            searchQuery || statusFilter !== 'all' || overdueOnly
              ? 'No remediation actions match your current filters.'
              : 'There are no remediation actions recorded yet.'
          }
        />
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-600 uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3.5">Action & Finding</th>
                  <th className="px-5 py-3.5">Assignee</th>
                  <th className="px-5 py-3.5">Due Date</th>
                  <th className="px-5 py-3.5">Status</th>
                  <th className="px-5 py-3.5 text-right">Workflow Transition</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {filteredRemediations.map((rem) => {
                  const finding = findingsMap.get(rem.finding_id);
                  const control = finding?.control_id ? controlsMap.get(finding.control_id) : null;

                  return (
                    <tr key={rem.id} className="hover:bg-slate-50/70 transition">
                      <td className="px-5 py-4 max-w-md">
                        <div className="font-semibold text-slate-900">{rem.action}</div>
                        {rem.evidence_note && (
                          <p className="mt-1 text-xs text-slate-500 line-clamp-1 italic">
                            Evidence: {rem.evidence_note}
                          </p>
                        )}
                        {finding && (
                          <div className="mt-2 flex items-center gap-2 text-xs">
                            {control && (
                              <span className="font-mono font-medium text-teal-700 bg-teal-50 px-1.5 py-0.5 rounded border border-teal-200">
                                {control.control_code}
                              </span>
                            )}
                            <Link
                              to={`/findings?id=${finding.id}`}
                              className="text-slate-600 hover:text-teal-700 line-clamp-1 underline underline-offset-2"
                              title={finding.description}
                            >
                              Finding: {finding.description}
                            </Link>
                          </div>
                        )}
                      </td>

                      <td className="px-5 py-4 whitespace-nowrap">
                        <span className="font-medium text-slate-800">{rem.owner || 'Unassigned'}</span>
                      </td>

                      <td className="px-5 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <ClockIcon className="w-4 h-4 text-slate-400" />
                          <span
                            className={clsx(
                              'text-xs font-medium',
                              rem.is_overdue
                                ? 'text-rose-600 font-bold'
                                : rem.due_date
                                ? 'text-slate-700'
                                : 'text-slate-400 italic'
                            )}
                          >
                            {rem.due_date || 'No due date'}
                          </span>
                        </div>
                        {rem.is_overdue && (
                          <span className="inline-block mt-1 text-[10px] uppercase font-bold text-rose-700 bg-rose-100 px-1.5 py-0.2 rounded">
                            Overdue
                          </span>
                        )}
                      </td>

                      <td className="px-5 py-4 whitespace-nowrap">
                        <StatusBadge status={rem.status} />
                      </td>

                      <td className="px-5 py-4 whitespace-nowrap text-right">
                        {isAuditor ? (
                          <span className="text-xs text-slate-400 italic">Read-only role</span>
                        ) : (
                          <div className="inline-flex items-center gap-1.5">
                            {rem.status === 'Planned' && canProgress && (
                              <button
                                type="button"
                                onClick={() => handlePromptTransition(rem, 'In Progress')}
                                className="px-2.5 py-1 text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 rounded-md transition"
                              >
                                Start Work
                              </button>
                            )}

                            {rem.status === 'In Progress' && canProgress && (
                              <button
                                type="button"
                                onClick={() => handlePromptTransition(rem, 'Ready for Review')}
                                className="px-2.5 py-1 text-xs font-medium bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200 rounded-md transition"
                              >
                                Submit Review
                              </button>
                            )}

                            {rem.status === 'Ready for Review' && canComplete && (
                              <button
                                type="button"
                                onClick={() => handlePromptTransition(rem, 'Completed')}
                                className="px-2.5 py-1 text-xs font-medium bg-emerald-600 text-white hover:bg-emerald-700 rounded-md transition shadow-2xs"
                              >
                                Approve & Complete
                              </button>
                            )}

                            {rem.status === 'Completed' && (
                              <span className="inline-flex items-center gap-1 text-xs text-emerald-700 font-medium bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                                <CheckCircleIcon className="w-3.5 h-3.5" />
                                Done
                              </span>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Create Modal */}
      {createModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 animate-scale-up">
            <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <PlusIcon className="w-5 h-5 text-teal-600" />
              New Remediation Action
            </h3>
            <p className="mt-1 text-xs text-slate-500">
              Create a concrete corrective task linked to an existing audit finding.
            </p>

            <form onSubmit={handleCreateSubmit} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Target Finding *
                </label>
                <select
                  value={createFindingId}
                  onChange={(e) => setCreateFindingId(e.target.value)}
                  required
                  className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                >
                  <option value="">Select a finding...</option>
                  {findings.map((f) => {
                    const ctrl = f.control_id ? controlsMap.get(f.control_id) : null;
                    return (
                      <option key={f.id} value={f.id}>
                        {ctrl ? `[${ctrl.control_code}] ` : ''}
                        {f.description.substring(0, 75)}...
                      </option>
                    );
                  })}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Action Description *
                </label>
                <textarea
                  rows={3}
                  value={createAction}
                  onChange={(e) => setCreateAction(e.target.value)}
                  required
                  placeholder="e.g., Implement automated quarterly manager approval reviews in Okta"
                  className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Assignee / Owner
                  </label>
                  <input
                    type="text"
                    value={createOwner}
                    onChange={(e) => setCreateOwner(e.target.value)}
                    placeholder="e.g. Owen Owner"
                    className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Due Date
                  </label>
                  <input
                    type="date"
                    value={createDueDate}
                    onChange={(e) => setCreateDueDate(e.target.value)}
                    className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Evidence / Verification Note
                </label>
                <input
                  type="text"
                  value={createEvidenceNote}
                  onChange={(e) => setCreateEvidenceNote(e.target.value)}
                  placeholder="e.g. Exported Okta quarterly access certification report"
                  className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>

              <div className="mt-6 flex justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setCreateModalOpen(false)}
                  disabled={submitting}
                  className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 text-sm font-medium text-white bg-teal-600 rounded-lg hover:bg-teal-700 transition shadow-xs"
                >
                  {submitting ? 'Creating...' : 'Create Action'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Status Transition Dialog */}
      {transitionDialogOpen && selectedAction && targetStatus && (
        <ConfirmDialog
          isOpen={transitionDialogOpen}
          title={`Transition Status to "${targetStatus}"`}
          message={`Are you sure you want to transition this remediation action to "${targetStatus}"? This event will be logged in the immutable status history.`}
          confirmLabel={submitting ? 'Updating...' : `Set to ${targetStatus}`}
          cancelLabel="Cancel"
          isDestructive={false}
          onConfirm={handleConfirmTransition}
          onCancel={() => setTransitionDialogOpen(false)}
        >
          <div className="mt-3">
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Transition Note (Optional)
            </label>
            <input
              type="text"
              value={transitionNote}
              onChange={(e) => setTransitionNote(e.target.value)}
              placeholder="e.g., Reviewed Okta approval logs and verified full department coverage"
              className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-500"
            />
          </div>
        </ConfirmDialog>
      )}
    </div>
  );
};

export default RemediationTracker;
