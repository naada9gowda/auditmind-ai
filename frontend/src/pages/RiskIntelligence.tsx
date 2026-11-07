import React, { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { RisksResponse, RiskItem } from '../api/types';
import SeverityBadge from '../components/SeverityBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import {
  ExclamationCircleIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  ArrowPathIcon,
  ArrowRightIcon,
  ShieldAlertIcon,
} from '@heroicons/react/24/outline';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import clsx from 'clsx';

export const RiskIntelligence: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [risks, setRisks] = useState<RiskItem[]>([]);
  const [disclaimer, setDisclaimer] = useState<string>('');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data: RisksResponse = await api.getAnalyticsRisks();
      setRisks(data.risks || []);
      setDisclaimer(
        data.disclaimer ||
          'Risk scores are advisory early-warning indicators calculated deterministically based on finding severity, recurrence history, remediation status, and control cadence.'
      );
    } catch (err: any) {
      setError(err.message || 'Failed to calculate risk indicators.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const toggleExpand = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  // Recurring findings subset
  const recurringRisks = useMemo(() => {
    return risks.filter((r) => r.is_recurrence);
  }, [risks]);

  // Department scores for Bar chart
  const deptChartData = useMemo(() => {
    const deptTotals: Record<string, { totalScore: number; count: number }> = {};
    risks.forEach((r) => {
      const d = r.department || 'General';
      if (!deptTotals[d]) {
        deptTotals[d] = { totalScore: 0, count: 0 };
      }
      deptTotals[d].totalScore += r.score;
      deptTotals[d].count += 1;
    });

    return Object.entries(deptTotals).map(([department, val]) => ({
      department,
      averageScore: Number((val.totalScore / val.count).toFixed(1)),
      findingCount: val.count,
    }));
  }, [risks]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Risk Intelligence & Early-Warning Scores
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Transparent 0-10 risk scoring algorithm with breakdown of point contributions and recurrence penalties
          </p>
        </div>
        <button
          type="button"
          onClick={loadData}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-xs self-start sm:self-auto"
        >
          <ArrowPathIcon className="w-3.5 h-3.5" />
          Recalculate Scores
        </button>
      </div>

      {/* Prominent Disclaimer Notice */}
      <div className="rounded-xl border border-teal-200 bg-teal-50/70 p-4 text-xs text-teal-900 flex items-start gap-3">
        <ExclamationCircleIcon className="w-5 h-5 text-teal-700 shrink-0 mt-0.5" />
        <div>
          <h4 className="font-bold text-teal-950 uppercase tracking-wide text-[11px]">
            Auditor Advisory Notice & Scoring Methodology
          </h4>
          <p className="mt-0.5 text-teal-900/90 leading-relaxed">
            {disclaimer}
          </p>
        </div>
      </div>

      {loading ? (
        <div className="py-24 flex items-center justify-center">
          <LoadingSpinner size="lg" message="Computing deterministic risk models..." />
        </div>
      ) : error ? (
        <EmptyState title="Scoring Error" message={error} onAction={loadData} actionLabel="Retry" />
      ) : (
        <>
          {/* Department Trend Chart */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5">
            <div className="mb-4">
              <h3 className="text-sm font-bold text-slate-900">
                Average Risk Score by Department
              </h3>
              <p className="text-xs text-slate-500">
                Comparative severity and recurrence impact across organisational units
              </p>
            </div>

            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={deptChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                  <XAxis dataKey="department" tick={{ fontSize: 11, fill: '#64748b' }} />
                  <YAxis domain={[0, 10]} tick={{ fontSize: 11, fill: '#64748b' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      border: 'none',
                      borderRadius: '8px',
                      color: '#fff',
                      fontSize: '11px',
                    }}
                  />
                  <Bar
                    dataKey="averageScore"
                    name="Avg Risk Score (0-10)"
                    fill="#0f766e"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Ranked Risks Table with Expandable Component Rows */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="p-4 sm:p-5 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Ranked Finding Risk Register ({risks.length})
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Click any row to reveal transparent point contributions and score decomposition
                </p>
              </div>
            </div>

            {risks.length === 0 ? (
              <EmptyState title="No Risk Deficiencies" message="No active findings requiring risk scoring." />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-50/75 border-b border-slate-200 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                      <th className="py-3 px-4">Rank / Score</th>
                      <th className="py-3 px-4">Level</th>
                      <th className="py-3 px-4">Control</th>
                      <th className="py-3 px-4">Deficiency Description</th>
                      <th className="py-3 px-4">Department</th>
                      <th className="py-3 px-4">Audit Rationale</th>
                      <th className="py-3 px-4 text-right">Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-xs">
                    {risks.map((risk, index) => {
                      const isExpanded = expandedId === risk.finding_id;

                      return (
                        <React.Fragment key={risk.finding_id}>
                          <tr
                            onClick={() => toggleExpand(risk.finding_id)}
                            className={clsx(
                              'hover:bg-slate-50/75 transition cursor-pointer',
                              isExpanded && 'bg-slate-50/80 font-medium'
                            )}
                          >
                            <td className="py-3.5 px-4 whitespace-nowrap">
                              <div className="flex items-center gap-2">
                                <span className="font-mono text-xs text-slate-400 font-semibold w-4">
                                  #{index + 1}
                                </span>
                                <span className="font-mono font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded text-xs border border-slate-200">
                                  {risk.score.toFixed(1)} / 10
                                </span>
                              </div>
                            </td>

                            <td className="py-3.5 px-4 whitespace-nowrap">
                              <SeverityBadge severity={risk.level} />
                            </td>

                            <td className="py-3.5 px-4 whitespace-nowrap">
                              <span className="font-mono font-bold text-slate-800">
                                {risk.control_code || 'N/A'}
                              </span>
                            </td>

                            <td className="py-3.5 px-4">
                              <div className="max-w-md font-semibold text-slate-900 truncate" title={risk.description}>
                                {risk.description}
                              </div>
                              {risk.is_recurrence && (
                                <span className="inline-block mt-0.5 text-[10px] text-amber-700 bg-amber-50 border border-amber-300 px-1.5 py-0.2 rounded font-semibold">
                                  Repeat Defect
                                </span>
                              )}
                            </td>

                            <td className="py-3.5 px-4 whitespace-nowrap text-slate-600">
                              {risk.department || 'General'}
                            </td>

                            <td className="py-3.5 px-4 text-slate-500 max-w-xs truncate" title={risk.explanation}>
                              {risk.explanation}
                            </td>

                            <td className="py-3.5 px-4 whitespace-nowrap text-right">
                              <button
                                type="button"
                                className="text-slate-400 hover:text-slate-700 p-1"
                              >
                                {isExpanded ? (
                                  <ChevronUpIcon className="w-4 h-4" />
                                ) : (
                                  <ChevronDownIcon className="w-4 h-4" />
                                )}
                              </button>
                            </td>
                          </tr>

                          {/* Expandable Score Breakdown Components Row */}
                          {isExpanded && (
                            <tr className="bg-slate-100/50">
                              <td colSpan={7} className="p-4 sm:px-8 border-b border-slate-200">
                                <div className="space-y-3 bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
                                  <div className="flex items-center justify-between">
                                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                                      Transparent Scoring Component Breakdown
                                    </h4>
                                    <Link
                                      to={`/findings?id=${risk.finding_id}`}
                                      className="text-xs font-semibold text-teal-600 hover:text-teal-800 hover:underline flex items-center gap-1"
                                    >
                                      <span>Open Finding Review</span>
                                      <ArrowRightIcon className="w-3.5 h-3.5" />
                                    </Link>
                                  </div>

                                  <div className="overflow-x-auto">
                                    <table className="w-full text-left text-xs border border-slate-200 rounded-lg overflow-hidden">
                                      <thead className="bg-slate-50 text-[10px] font-semibold text-slate-500 uppercase">
                                        <tr>
                                          <th className="py-2 px-3">Component Factor</th>
                                          <th className="py-2 px-3">Points Assigned</th>
                                          <th className="py-2 px-3">Scoring Rationale</th>
                                        </tr>
                                      </thead>
                                      <tbody className="divide-y divide-slate-100">
                                        {risk.components && risk.components.length > 0 ? (
                                          risk.components.map((comp, ci) => (
                                            <tr key={ci} className="hover:bg-slate-50">
                                              <td className="py-2 px-3 font-semibold text-slate-800">
                                                {comp.name}
                                              </td>
                                              <td className="py-2 px-3 font-mono font-bold text-teal-700">
                                                +{comp.points.toFixed(1)}
                                              </td>
                                              <td className="py-2 px-3 text-slate-600">
                                                {comp.reason}
                                              </td>
                                            </tr>
                                          ))
                                        ) : (
                                          <tr>
                                            <td colSpan={3} className="py-2 px-3 text-slate-400 italic">
                                              Baseline calculation based on severity rating.
                                            </td>
                                          </tr>
                                        )}
                                      </tbody>
                                    </table>
                                  </div>

                                  <p className="text-[11px] text-slate-400 italic">
                                    Total raw score capped at 10.0 maximum severity ceiling.
                                  </p>
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Dedicated Recurring Findings Section */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5 space-y-4">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
              <div className="p-1.5 rounded-lg bg-amber-100 text-amber-800">
                <ShieldAlertIcon className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900">
                  Recurring Findings Watchlist (is_recurrence = True)
                </h3>
                <p className="text-xs text-slate-500">
                  Deficiencies that have recurred across multiple audit cycles, indicating systemic process lapses
                </p>
              </div>
            </div>

            {recurringRisks.length === 0 ? (
              <div className="p-4 bg-slate-50 rounded-lg text-slate-400 text-xs italic text-center">
                No repeat recurring findings currently identified.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {recurringRisks.map((rec) => (
                  <div
                    key={rec.finding_id}
                    className="p-4 rounded-xl border-2 border-amber-300/80 bg-amber-50/40 space-y-2 flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <span className="font-mono text-xs font-bold text-slate-900 bg-amber-100 px-2 py-0.5 rounded">
                          {rec.control_code || 'Control Ref'}
                        </span>
                        <SeverityBadge severity={rec.severity} />
                      </div>
                      <p className="text-xs font-bold text-slate-900">{rec.description}</p>
                      <p className="text-[11px] text-slate-600 mt-1">
                        Dept: <span className="font-semibold">{rec.department}</span> • Score:{' '}
                        <span className="font-mono font-bold text-amber-900">{rec.score}</span>
                      </p>
                    </div>

                    <div className="pt-2 border-t border-amber-200/60 flex items-center justify-between">
                      <span className="text-[10px] text-amber-800 font-semibold uppercase">
                        Requires Remediation Attention
                      </span>
                      <Link
                        to={`/findings?id=${rec.finding_id}`}
                        className="text-xs font-semibold text-teal-700 hover:text-teal-900 hover:underline"
                      >
                        Inspect finding →
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};

export default RiskIntelligence;
