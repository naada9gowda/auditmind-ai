import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import { Control, TimelineResponse, TimelineEntry } from '../api/types';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import StatusBadge from '../components/StatusBadge';
import {
  ClockIcon,
  ShieldCheckIcon,
  ArrowPathIcon,
  DocumentMagnifyingGlassIcon,
  WrenchScrewdriverIcon,
  ArrowRightCircleIcon,
  CalendarDaysIcon,
  SparklesIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';

export const AuditHistory: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialCode = searchParams.get('control_code') || 'SEC-014';

  const [controls, setControls] = useState<Control[]>([]);
  const [selectedControlCode, setSelectedControlCode] = useState<string>(initialCode);
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [timelineLoading, setTimelineLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [eventFilter, setEventFilter] = useState<string>('all');

  // Load controls list once
  useEffect(() => {
    async function loadControls() {
      setLoading(true);
      try {
        const data = await api.getControls();
        setControls(data);
        if (data.length > 0 && !selectedControlCode) {
          setSelectedControlCode(data[0].control_code);
        }
      } catch (err: any) {
        setError(err?.message || 'Failed to load controls.');
      } finally {
        setLoading(false);
      }
    }
    loadControls();
  }, []);

  // Load timeline whenever selected control changes
  useEffect(() => {
    if (!selectedControlCode) return;

    async function loadTimeline() {
      setTimelineLoading(true);
      setError(null);
      try {
        const res = await api.getTimeline({ control_code: selectedControlCode });
        setTimeline(res);
        setSearchParams({ control_code: selectedControlCode });
      } catch (err: any) {
        setError(err?.message || `Failed to load timeline for ${selectedControlCode}.`);
      } finally {
        setTimelineLoading(false);
      }
    }

    loadTimeline();
  }, [selectedControlCode]);

  const currentControl = controls.find((c) => c.control_code === selectedControlCode);

  const getEventBadge = (eventType: string) => {
    switch (eventType) {
      case 'audit_cycle':
        return {
          icon: CalendarDaysIcon,
          color: 'bg-purple-100 text-purple-800 border-purple-200',
          label: 'Audit Cycle',
        };
      case 'finding':
        return {
          icon: DocumentMagnifyingGlassIcon,
          color: 'bg-rose-100 text-rose-800 border-rose-200',
          label: 'Audit Finding',
        };
      case 'remediation':
        return {
          icon: WrenchScrewdriverIcon,
          color: 'bg-blue-100 text-blue-800 border-blue-200',
          label: 'Remediation',
        };
      case 'status_change':
        return {
          icon: ArrowRightCircleIcon,
          color: 'bg-teal-100 text-teal-800 border-teal-200',
          label: 'Status Change',
        };
      default:
        return {
          icon: ClockIcon,
          color: 'bg-slate-100 text-slate-800 border-slate-200',
          label: eventType,
        };
    }
  };

  const filteredEntries = (timeline?.entries || []).filter((entry) => {
    if (eventFilter === 'all') return true;
    return entry.event_type === eventFilter;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2.5">
            <ClockIcon className="w-7 h-7 text-teal-600" />
            Audit History Timeline
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Chronological audit intelligence across multi-cycle audit reviews, finding recurrences, and remediation proofs.
          </p>
        </div>

        <button
          type="button"
          onClick={() => {
            if (selectedControlCode) {
              setTimelineLoading(true);
              api.getTimeline({ control_code: selectedControlCode })
                .then(setTimeline)
                .finally(() => setTimelineLoading(false));
            }
          }}
          className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition shadow-xs self-start sm:self-auto"
        >
          <ArrowPathIcon className={clsx('w-4 h-4', timelineLoading && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {/* Control Selector Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
            Select Control:
          </label>
          <select
            value={selectedControlCode}
            onChange={(e) => setSelectedControlCode(e.target.value)}
            disabled={loading}
            className="text-sm font-medium border border-slate-300 rounded-lg px-3 py-2 bg-slate-50 focus:bg-white focus:outline-none focus:ring-2 focus:ring-teal-500 text-slate-900 min-w-[280px]"
          >
            {controls.map((c) => (
              <option key={c.id} value={c.control_code}>
                {c.control_code} — {c.title}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500 font-medium">Filter Events:</span>
          <select
            value={eventFilter}
            onChange={(e) => setEventFilter(e.target.value)}
            className="text-xs border border-slate-300 rounded-lg px-2.5 py-1.5 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-500"
          >
            <option value="all">All Events</option>
            <option value="audit_cycle">Audit Cycles</option>
            <option value="finding">Findings</option>
            <option value="remediation">Remediations</option>
            <option value="status_change">Status Changes</option>
          </select>
        </div>
      </div>

      {/* Control Overview Card */}
      {currentControl && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm font-bold text-teal-700 bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                {currentControl.control_code}
              </span>
              <h2 className="text-lg font-bold text-slate-900">{currentControl.title}</h2>
              <StatusBadge status={currentControl.status} />
            </div>
            {currentControl.description && (
              <p className="text-xs text-slate-600 max-w-2xl">{currentControl.description}</p>
            )}
          </div>

          <div className="flex items-center gap-6 border-t md:border-t-0 pt-3 md:pt-0 border-slate-100 text-xs text-slate-600">
            <div>
              <span className="block text-slate-400 font-medium">Cadence</span>
              <span className="font-semibold capitalize text-slate-800">{currentControl.cadence}</span>
            </div>
            <div>
              <span className="block text-slate-400 font-medium">Owner</span>
              <span className="font-semibold text-slate-800">{currentControl.owner || 'Owen Owner'}</span>
            </div>
            <div>
              <span className="block text-slate-400 font-medium">Total Timeline Events</span>
              <span className="font-semibold text-slate-800">{timeline?.entries.length || 0}</span>
            </div>
          </div>
        </div>
      )}

      {/* Recurrence Notice for SEC-014 */}
      {selectedControlCode === 'SEC-014' && (
        <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 flex items-start gap-3">
          <SparklesIcon className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
          <div className="text-xs text-amber-900 space-y-1">
            <p className="font-bold">
              Multi-Cycle Recurrence Pattern Flagged
            </p>
            <p>
              SEC-014 shows recurring access review gaps across January (AUD-2026-001) and April (AUD-2026-002) audit cycles. Our relational HistoryService links these findings with match reason: <span className="font-semibold">"Same control SEC-014, same department IT Operations, shared keywords: access, review, approval, missing"</span>.
            </p>
          </div>
        </div>
      )}

      {/* Timeline Content */}
      {timelineLoading ? (
        <LoadingSpinner message={`Loading timeline for ${selectedControlCode}...`} />
      ) : error ? (
        <EmptyState title="Timeline Unavailable" description={error} />
      ) : filteredEntries.length === 0 ? (
        <EmptyState
          title="No History Entries Found"
          description={`There are no recorded timeline entries for control ${selectedControlCode} matching your filter.`}
        />
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
          <div className="relative pl-6 sm:pl-8 border-l-2 border-slate-200 space-y-8">
            {filteredEntries.map((entry, idx) => {
              const badge = getEventBadge(entry.event_type);
              const Icon = badge.icon;

              return (
                <div key={idx} className="relative group">
                  {/* Dot on line */}
                  <div className="absolute -left-[31px] sm:-left-[39px] top-1 w-6 h-6 rounded-full bg-white border-2 border-teal-600 flex items-center justify-center shadow-xs">
                    <div className="w-2 h-2 rounded-full bg-teal-600" />
                  </div>

                  {/* Entry Card */}
                  <div className="bg-slate-50/70 hover:bg-slate-50 border border-slate-200/80 rounded-xl p-4 transition shadow-2xs">
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2">
                        <span
                          className={clsx(
                            'inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold border',
                            badge.color
                          )}
                        >
                          <Icon className="w-3.5 h-3.5" />
                          {badge.label}
                        </span>
                        <h4 className="text-sm font-bold text-slate-900">{entry.summary}</h4>
                      </div>

                      {entry.event_date && (
                        <span className="text-xs font-mono text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200">
                          {entry.event_date}
                        </span>
                      )}
                    </div>

                    {entry.detail && (
                      <p className="text-xs text-slate-600 leading-relaxed font-sans">
                        {entry.detail}
                      </p>
                    )}

                    <div className="mt-2.5 pt-2 border-t border-slate-200/60 flex items-center justify-between text-[11px] text-slate-400">
                      <span>Ref ID: {entry.entity_id.substring(0, 8)}...</span>
                      <span className="capitalize">{entry.entity_type} Record</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default AuditHistory;
