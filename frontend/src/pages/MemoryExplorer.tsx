import React, { useState } from 'react';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import {
  CpuChipIcon,
  MagnifyingGlassIcon,
  SparklesIcon,
  ArrowDownTrayIcon,
  LightBulbIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';

interface MemoryItem {
  id: string;
  category: string;
  audit_period: string;
  control_id: string;
  department: string;
  summary: string;
  narrative: string;
  source_ref: string;
  reflection: string;
}

const SEED_MEMORIES: MemoryItem[] = [
  {
    id: 'mem-001',
    category: 'Audit finding',
    audit_period: 'January 2026 (Cycle 1)',
    control_id: 'SEC-014',
    department: 'IT Operations',
    summary: 'Employee access reviews incomplete in IT Operations; approval sign-offs missing.',
    narrative: 'Audit 1 flagged SEC-014 because 14 privileged database accounts were uncertified. Manager sign-offs were missing from Q4 records.',
    source_ref: 'AUD-2026-001, page 4',
    reflection: 'Root cause identified as lack of automated quarterly calendar reminders and absence of designated review coordinator.'
  },
  {
    id: 'mem-002',
    category: 'Remediation',
    audit_period: 'February 2026',
    control_id: 'SEC-014',
    department: 'IT Operations',
    summary: 'Control owner submitted review spreadsheet; marked action ready for review.',
    narrative: 'Owen Owner submitted ad-hoc spreadsheet recertifying database access. Reviewer accepted evidence but required scheduled recurrence.',
    source_ref: 'REM-2026-014-01',
    reflection: 'Corrective action addressed symptom (clearing current backlog) rather than establishing institutionalized cadence.'
  },
  {
    id: 'mem-003',
    category: 'Risk pattern',
    audit_period: 'April 2026 (Cycle 2)',
    control_id: 'SEC-014',
    department: 'IT Operations',
    summary: 'Recurrence confirmed: similar access-review gap detected in same department.',
    narrative: 'Audit 2 confirmed access review overdue again. System recalled January memory and highlighted systemic process weakness.',
    source_ref: 'AUD-2026-002, page 11',
    reflection: 'High risk early-warning triggered due to recurrence pattern in consecutive audit cycles.'
  },
  {
    id: 'mem-004',
    category: 'Audit finding',
    audit_period: 'July 2026 (Cycle 3)',
    control_id: 'SEC-014',
    department: 'IT Operations',
    summary: 'Current cycle: quarterly database access review overdue by 45 days.',
    narrative: 'New evidence indicates 45 entries reviewed, but missing HR sign-off on 3 terminated contractors. Ongoing recurrence alert.',
    source_ref: '2026_Q2_Access_Audit_Report.pdf, page 14',
    reflection: 'Recommended remediation: enforce automated PAM/IAM integration rather than manual spreadsheet verification.'
  }
];

export const MemoryExplorer: React.FC = () => {
  const [memories] = useState<MemoryItem[]>(SEED_MEMORIES);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  const filteredMemories = memories.filter((m) => {
    if (selectedCategory !== 'all' && m.category !== selectedCategory) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        m.summary.toLowerCase().includes(q) ||
        m.narrative.toLowerCase().includes(q) ||
        m.control_id.toLowerCase().includes(q) ||
        m.department.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="pb-2 border-b border-slate-200 flex flex-wrap justify-between items-center gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <CpuChipIcon className="w-6 h-6 text-teal-600" />
            Hindsight Memory Explorer
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Transparent inspection of retained audit memories, reflections, and cross-cycle organizational recall
          </p>
        </div>
        <span className="text-xs font-mono font-bold bg-teal-50 text-teal-800 px-3 py-1 rounded-lg border border-teal-300">
          Memory Bank: abctech-audit-memory
        </span>
      </div>

      {/* Retain, Recall, Reflect Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs space-y-1">
          <div className="font-extrabold text-teal-800 uppercase text-[11px] flex items-center gap-1.5">
            <ArrowDownTrayIcon className="w-4 h-4 text-teal-600" />
            Hindsight Retain
          </div>
          <p className="text-slate-600 leading-relaxed">
            Stores approved findings, remediation outcomes, and policy changes with rich metadata tags (organisation_id, control_id, department, audit_period).
          </p>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs space-y-1">
          <div className="font-extrabold text-blue-800 uppercase text-[11px] flex items-center gap-1.5">
            <MagnifyingGlassIcon className="w-4 h-4 text-blue-600" />
            Hindsight Recall
          </div>
          <p className="text-slate-600 leading-relaxed">
            When a new finding or question arises, recalls past audit memories matching control ID, department, or issue context across prior cycles.
          </p>
        </div>

        <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-xs space-y-1">
          <div className="font-extrabold text-purple-800 uppercase text-[11px] flex items-center gap-1.5">
            <LightBulbIcon className="w-4 h-4 text-purple-600" />
            Hindsight Reflect
          </div>
          <p className="text-slate-600 leading-relaxed">
            Synthesizes retrieved history to detect recurring patterns and advise human reviewers whether an issue was truly resolved or merely patched.
          </p>
        </div>
      </div>

      {/* Filter / Search Bar */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3">
          <span className="font-bold text-slate-700">Filter Category:</span>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="rounded-lg border border-slate-300 py-1.5 px-3 text-xs bg-white focus:ring-1 focus:ring-teal-500"
          >
            <option value="all">All Categories</option>
            <option value="Audit finding">Audit finding</option>
            <option value="Remediation">Remediation</option>
            <option value="Risk pattern">Risk pattern</option>
          </select>
        </div>

        <div className="w-full sm:w-64">
          <input
            type="text"
            placeholder="Search memories..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-slate-300 py-1.5 px-3 text-xs bg-slate-50 focus:bg-white focus:ring-1 focus:ring-teal-500"
          />
        </div>
      </div>

      {/* Retained Memories List */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-700 flex justify-between">
          <span>Retained Memory Records ({filteredMemories.length})</span>
          <span className="text-[11px] text-slate-400">Scoped to tenant ABC Technologies</span>
        </div>

        <div className="divide-y divide-slate-100">
          {filteredMemories.map((mem) => (
            <div key={mem.id} className="p-5 hover:bg-slate-50 transition space-y-2">
              <div className="flex flex-wrap justify-between items-center gap-2">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold bg-slate-900 text-white px-2 py-0.5 rounded">
                    {mem.control_id}
                  </span>
                  <span className="text-xs font-bold text-slate-900">{mem.summary}</span>
                  <span className="text-[10px] uppercase font-bold text-teal-800 bg-teal-50 px-2 py-0.5 rounded border border-teal-200">
                    {mem.category}
                  </span>
                </div>
                <span className="text-[11px] font-mono text-slate-500 font-semibold">{mem.audit_period}</span>
              </div>

              <p className="text-xs text-slate-700 leading-relaxed font-medium">
                {mem.narrative}
              </p>

              <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 text-[11px] space-y-1">
                <div className="text-purple-900 font-bold">Reflected Context:</div>
                <div className="text-slate-600 italic">"{mem.reflection}"</div>
                <div className="text-slate-400 pt-1 font-mono">Source Reference: {mem.source_ref}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default MemoryExplorer;
