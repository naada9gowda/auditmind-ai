import React, { useEffect, useState, useMemo } from 'react';
import { api } from '../api/client';
import { Evidence, Control, DocumentItem, EvidenceAssessment } from '../api/types';
import { useUser } from '../context/UserContext';
import { useToast } from '../components/Toast';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import SourceDrawer from '../components/SourceDrawer';
import VerifiedBadge from '../components/VerifiedBadge';
import {
  CheckBadgeIcon,
  CheckCircleIcon,
  XCircleIcon,
  DocumentMagnifyingGlassIcon,
  ArrowPathIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';

export const EvidenceVerifier: React.FC = () => {
  const { currentUser } = useUser();
  const { showToast } = useToast();

  const [controls, setControls] = useState<Control[]>([]);
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedControlId, setSelectedControlId] = useState<string>('all');
  const [assessmentFilter, setAssessmentFilter] = useState<string>('all');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Source drawer state
  const [sourceDrawerOpen, setSourceDrawerOpen] = useState<boolean>(false);
  const [drawerDocId, setDrawerDocId] = useState<string | null>(null);
  const [drawerPage, setDrawerPage] = useState<number | null>(null);
  const [drawerExcerpt, setDrawerExcerpt] = useState<string | null>(null);
  const [drawerControl, setDrawerControl] = useState<string | null>(null);

  // Reviewing item loading id
  const [reviewingId, setReviewingId] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [ctrls, evs, docs] = await Promise.all([
        api.getControls(),
        api.getEvidence(),
        api.getDocuments().catch(() => []),
      ]);
      setControls(ctrls);
      setEvidenceList(evs);
      setDocuments(docs);
    } catch (err: any) {
      setError(err.message || 'Failed to load evidence records.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const docMap = useMemo(() => {
    const map: Record<string, DocumentItem> = {};
    documents.forEach((d) => {
      map[d.id] = d;
    });
    return map;
  }, [documents]);

  const ctrlMap = useMemo(() => {
    const map: Record<string, Control> = {};
    controls.forEach((c) => {
      map[c.id] = c;
    });
    return map;
  }, [controls]);

  // Filtered evidence
  const filteredEvidence = useMemo(() => {
    return evidenceList.filter((ev) => {
      if (selectedControlId !== 'all' && ev.control_id !== selectedControlId) return false;
      if (assessmentFilter !== 'all' && ev.assessment !== assessmentFilter) return false;
      return true;
    });
  }, [evidenceList, selectedControlId, assessmentFilter]);

  // Handle Review (Accept / Reject)
  const handleReview = async (
    evidenceId: string,
    decision: 'Approved' | 'Rejected',
    assessmentOverride?: string
  ) => {
    setReviewingId(evidenceId);
    try {
      const updated = await api.reviewEvidence(evidenceId, decision, assessmentOverride);
      showToast(
        decision === 'Approved'
          ? 'Evidence assessment accepted and approved.'
          : 'Evidence assessment rejected.',
        'success'
      );
      setEvidenceList((prev) =>
        prev.map((ev) => (ev.id === evidenceId ? updated : ev))
      );
    } catch (err: any) {
      showToast(err.message || 'Failed to submit evidence review.', 'error');
    } finally {
      setReviewingId(null);
    }
  };

  const openSource = (ev: Evidence) => {
    const ctrl = ctrlMap[ev.control_id];
    setDrawerDocId(ev.document_id || null);
    setDrawerPage(ev.page_number || 1);
    setDrawerExcerpt(ev.excerpt || null);
    setDrawerControl(ctrl?.control_code || null);
    setSourceDrawerOpen(true);
  };

  const getAssessmentBadge = (assessment: EvidenceAssessment | string) => {
    switch (assessment) {
      case 'Candidate Match':
        return 'bg-emerald-50 text-emerald-800 border-emerald-300 ring-1 ring-emerald-500/20';
      case 'Missing':
        return 'bg-rose-50 text-rose-800 border-rose-300 ring-1 ring-rose-500/20';
      case 'Expired':
        return 'bg-orange-50 text-orange-800 border-orange-300 ring-1 ring-orange-500/20';
      case 'Incomplete':
        return 'bg-amber-50 text-amber-800 border-amber-300 ring-1 ring-amber-500/20';
      case 'Requires Human Review':
      default:
        return 'bg-slate-100 text-slate-700 border-slate-300';
    }
  };

  const isReviewerRole = currentUser?.role === 'compliance_officer' || currentUser?.role === 'auditor' || currentUser?.role === 'admin';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Evidence Verifier
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Automated document mapping verification with human audit assessment approvals
          </p>
        </div>
        <button
          type="button"
          onClick={loadData}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-xs self-start sm:self-auto"
        >
          <ArrowPathIcon className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      {/* Filter / Selector Bar */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex flex-wrap items-center gap-3 text-xs">
        <div className="flex items-center gap-1.5 text-slate-500 font-medium">
          <FunnelIcon className="w-4 h-4 text-slate-400" />
          <span>Control:</span>
        </div>

        {/* Control Selector Dropdown */}
        <select
          value={selectedControlId}
          onChange={(e) => setSelectedControlId(e.target.value)}
          className="rounded-lg border border-slate-300 py-1.5 px-3 text-xs text-slate-800 bg-white focus:ring-1 focus:ring-teal-500 max-w-xs truncate"
        >
          <option value="all">All Controls (Register Wide)</option>
          {controls.map((ctrl) => (
            <option key={ctrl.id} value={ctrl.id}>
              {ctrl.control_code}: {ctrl.title}
            </option>
          ))}
        </select>

        <div className="flex items-center gap-1.5 text-slate-500 font-medium ml-2">
          <span>Assessment:</span>
        </div>

        {/* Assessment Badge Filter */}
        <select
          value={assessmentFilter}
          onChange={(e) => setAssessmentFilter(e.target.value)}
          className="rounded-lg border border-slate-300 py-1.5 px-3 text-xs text-slate-800 bg-white focus:ring-1 focus:ring-teal-500"
        >
          <option value="all">All Assessments</option>
          <option value="Candidate Match">Candidate Match (Green)</option>
          <option value="Missing">Missing (Red)</option>
          <option value="Expired">Expired (Orange)</option>
          <option value="Incomplete">Incomplete (Amber)</option>
          <option value="Requires Human Review">Requires Human Review (Grey)</option>
        </select>

        <span className="ml-auto text-slate-400 text-[11px]">
          {filteredEvidence.length} evidence record(s) found
        </span>
      </div>

      {/* Role permission reminder banner */}
      {!isReviewerRole && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800 flex items-center justify-between">
          <span>
            Logged in as <strong>{currentUser?.name}</strong> ({currentUser?.role}). Evidence review and approvals require Compliance Officer or Auditor privileges.
          </span>
        </div>
      )}

      {/* Evidence List Cards */}
      {loading ? (
        <div className="py-24 flex items-center justify-center">
          <LoadingSpinner size="lg" message="Loading evidence verification records..." />
        </div>
      ) : error ? (
        <EmptyState title="Error Loading Evidence" message={error} onAction={loadData} actionLabel="Retry" />
      ) : filteredEvidence.length === 0 ? (
        <EmptyState
          title="No Evidence Records"
          message="No evidence items found matching the selected control and filters. Upload evidence documents in Document Centre to run mapping."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {filteredEvidence.map((ev) => {
            const ctrl = ctrlMap[ev.control_id];
            const doc = ev.document_id ? docMap[ev.document_id] : null;
            const isProcessing = reviewingId === ev.id;
            const isApproved = ev.review_status === 'Approved';

            return (
              <div
                key={ev.id}
                className={clsx(
                  'bg-white rounded-xl p-5 shadow-xs transition-all space-y-4',
                  isApproved
                    ? 'border-2 border-emerald-500/40'
                    : ev.review_status === 'Draft'
                    ? 'border-2 border-dashed border-amber-400'
                    : 'border border-slate-200'
                )}
              >
                {/* Header row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
                  <div className="flex items-center gap-2.5 flex-wrap">
                    <span className="font-mono font-bold text-xs bg-slate-900 text-white px-2 py-0.5 rounded">
                      {ctrl?.control_code || 'Control Ref'}
                    </span>
                    <span className="text-xs font-semibold text-slate-800">
                      {ctrl?.title || 'Unknown Control'}
                    </span>
                    <span
                      className={clsx(
                        'text-xs font-semibold px-2.5 py-0.5 rounded-full border',
                        getAssessmentBadge(ev.assessment)
                      )}
                    >
                      {ev.assessment}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    {isApproved ? (
                      <VerifiedBadge label="Approved Assessment" />
                    ) : (
                      <span className="text-[11px] font-semibold text-amber-700 bg-amber-50 border border-amber-300 px-2 py-0.5 rounded-full">
                        Draft AI Mapping
                      </span>
                    )}
                  </div>
                </div>

                {/* Body Details */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                  {/* Left Column: Source Document */}
                  <div className="space-y-1 bg-slate-50 p-3 rounded-lg border border-slate-100">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                      Source Document
                    </span>
                    <p className="font-semibold text-slate-800 truncate" title={doc?.filename || 'Uploaded Document'}>
                      {doc?.filename || (ev.document_id ? `Doc ID: ${ev.document_id.slice(0, 8)}...` : 'Manual mapping')}
                    </p>
                    <p className="text-[11px] text-slate-500">
                      {ev.page_number ? `Page ${ev.page_number}` : 'Full Document'} •{' '}
                      {ev.evidence_date ? `Recorded: ${ev.evidence_date}` : 'No date parsed'}
                    </p>
                  </div>

                  {/* Middle Column: Excerpt */}
                  <div className="md:col-span-2 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                        Extracted Verification Excerpt
                      </span>
                      {ev.document_id && (
                        <button
                          type="button"
                          onClick={() => openSource(ev)}
                          className="text-xs font-semibold text-teal-700 hover:text-teal-900 flex items-center gap-1 hover:underline"
                        >
                          <DocumentMagnifyingGlassIcon className="w-3.5 h-3.5" />
                          View Source Page
                        </button>
                      )}
                    </div>
                    {ev.excerpt ? (
                      <blockquote className="text-xs text-slate-700 italic border-l-2 border-teal-500 pl-3 py-1 bg-slate-50 rounded">
                        "{ev.excerpt}"
                      </blockquote>
                    ) : (
                      <p className="text-xs text-slate-400 italic bg-slate-50 p-2 rounded">
                        No text excerpt extracted for this evidence record.
                      </p>
                    )}
                  </div>
                </div>

                {/* Footer Review Controls */}
                <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-slate-100 text-xs">
                  <div className="text-[11px] text-slate-500">
                    {ev.reviewed_by ? (
                      <span>Reviewed by user: <code className="font-mono text-slate-700">{ev.reviewed_by.slice(0, 8)}...</code></span>
                    ) : (
                      <span>Awaiting compliance review decision</span>
                    )}
                  </div>

                  {/* Accept / Reject actions */}
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={isProcessing || !isReviewerRole}
                      onClick={() => handleReview(ev.id, 'Approved')}
                      className={clsx(
                        'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition shadow-xs',
                        isApproved
                          ? 'bg-slate-100 text-slate-400 cursor-default'
                          : 'bg-emerald-600 hover:bg-emerald-700 text-white'
                      )}
                    >
                      <CheckCircleIcon className="w-4 h-4" />
                      <span>{isApproved ? 'Approved' : 'Accept Assessment'}</span>
                    </button>

                    <button
                      type="button"
                      disabled={isProcessing || !isReviewerRole}
                      onClick={() => handleReview(ev.id, 'Rejected')}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200 transition shadow-xs"
                    >
                      <XCircleIcon className="w-4 h-4" />
                      <span>Reject Assessment</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

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

export default EvidenceVerifier;
