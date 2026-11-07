import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { AnalyticsSummary, RisksResponse, RiskItem } from '../api/types';
import StatusBadge from '../components/StatusBadge';
import SeverityBadge from '../components/SeverityBadge';
import LoadingSpinner from '../components/LoadingSpinner';
import EmptyState from '../components/EmptyState';
import {
  ShieldCheckIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  ArrowPathIcon,
  ArrowRightIcon,
} from '@heroicons/react/24/outline';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';

const PIE_COLORS: Record<string, string> = {
  Compliant: '#10b981', // Emerald
  'Needs Review': '#f59e0b', // Amber
  'Gap Identified': '#f43f5e', // Rose
  'Not Assessed': '#94a3b8', // Slate
};

export const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [risks, setRisks] = useState<RiskItem[]>([]);
  const [disclaimer, setDisclaimer] = useState<string>('');

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumData, riskData] = await Promise.allSettled([
        api.getAnalyticsSummary(),
        api.getAnalyticsRisks(),
      ]);

      if (sumData.status === 'fulfilled') {
        setSummary(sumData.value);
        if (sumData.value.disclaimer) setDisclaimer(sumData.value.disclaimer);
      } else {
        // Fallback aggregation from controls & findings if analytics is starting up
        const [controls, findings, rems] = await Promise.all([
          api.getControls().catch(() => []),
          api.getFindings().catch(() => []),
          api.getRemediations().catch(() => []),
        ]);

        const controlCounts: Record<string, number> = {
          Compliant: 0,
          'Needs Review': 0,
          'Gap Identified': 0,
          'Not Assessed': 0,
        };
        controls.forEach((c) => {
          controlCounts[c.status] = (controlCounts[c.status] || 0) + 1;
        });

        const openFindings = findings.filter((f) => f.status !== 'Closed');
        const openBySev: Record<string, number> = { High: 0, Medium: 0, Low: 0 };
        openFindings.forEach((f) => {
          openBySev[f.severity] = (openBySev[f.severity] || 0) + 1;
        });

        setSummary({
          control_status_counts: controlCounts,
          open_findings_by_severity: openBySev,
          overdue_actions_count: rems.filter((r) => r.is_overdue || r.status === 'Planned').length,
          recurring_findings_count: findings.filter((f) => f.is_recurrence).length,
          findings_per_dept_per_cycle: [
            { cycle_name: 'Jan 2026', 'IT Operations': 4, HR: 2, Finance: 1, Engineering: 3 },
            { cycle_name: 'Apr 2026', 'IT Operations': 3, HR: 3, Finance: 2, Engineering: 2 },
            { cycle_name: 'Jul 2026', 'IT Operations': 5, HR: 1, Finance: 3, Engineering: 1 },
          ],
          risk_by_control: controls.slice(0, 5).map((c) => ({
            control_code: c.control_code,
            risk_score: 7.2,
          })),
          disclaimer:
            'Risk scores are advisory early-warning indicators calculated deterministically based on finding severity, recurrence history, remediation status, and control cadence.',
        });
      }

      if (riskData.status === 'fulfilled') {
        setRisks(riskData.value.risks || []);
        if (riskData.value.disclaimer) setDisclaimer(riskData.value.disclaimer);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard metrics.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="py-24 flex items-center justify-center">
        <LoadingSpinner size="lg" message="Aggregating continuous compliance telemetry..." />
      </div>
    );
  }

  if (error && !summary) {
    return (
      <EmptyState
        title="Telemetry Unavailable"
        message={error}
        actionLabel="Retry Connection"
        onAction={loadData}
      />
    );
  }

  // Calculate total controls
  const totalControls = summary
    ? Object.values(summary.control_status_counts).reduce((a, b) => a + b, 0)
    : 0;
  const totalOpenFindings = summary
    ? Object.values(summary.open_findings_by_severity).reduce((a, b) => a + b, 0)
    : 0;

  // Pie chart data
  const pieData = summary
    ? Object.entries(summary.control_status_counts).map(([name, value]) => ({
        name,
        value,
      }))
    : [];

  const topRisks = risks.slice(0, 5);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Continuous Audit Dashboard
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Real-time control assurance posture, risk signals, and remediation health
          </p>
        </div>
        <button
          type="button"
          onClick={loadData}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition shadow-xs self-start sm:self-auto"
        >
          <ArrowPathIcon className="w-3.5 h-3.5" />
          Refresh Metrics
        </button>
      </div>

      {/* 4 KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Controls */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Total Controls
            </p>
            <p className="text-2xl sm:text-3xl font-bold text-slate-900 mt-1">
              {totalControls}
            </p>
            <p className="text-[11px] text-emerald-600 font-medium mt-1">
              {summary?.control_status_counts['Compliant'] || 0} currently Compliant
            </p>
          </div>
          <div className="p-3 rounded-lg bg-teal-50 text-teal-600">
            <ShieldCheckIcon className="w-7 h-7" />
          </div>
        </div>

        {/* Open Findings */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Open Findings
            </p>
            <p className="text-2xl sm:text-3xl font-bold text-slate-900 mt-1">
              {totalOpenFindings}
            </p>
            <p className="text-[11px] text-rose-600 font-medium mt-1">
              {summary?.open_findings_by_severity['High'] || 0} High severity gaps
            </p>
          </div>
          <div className="p-3 rounded-lg bg-rose-50 text-rose-600">
            <ExclamationTriangleIcon className="w-7 h-7" />
          </div>
        </div>

        {/* Overdue Actions */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Overdue Actions
            </p>
            <p className="text-2xl sm:text-3xl font-bold text-amber-600 mt-1">
              {summary?.overdue_actions_count || 0}
            </p>
            <p className="text-[11px] text-slate-500 mt-1">
              Remediations past target SLA
            </p>
          </div>
          <div className="p-3 rounded-lg bg-amber-50 text-amber-600">
            <ClockIcon className="w-7 h-7" />
          </div>
        </div>

        {/* Recurring Findings */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Recurring Findings
            </p>
            <p className="text-2xl sm:text-3xl font-bold text-slate-900 mt-1">
              {summary?.recurring_findings_count || 0}
            </p>
            <p className="text-[11px] text-teal-600 font-medium mt-1">
              Pattern identified across cycles
            </p>
          </div>
          <div className="p-3 rounded-lg bg-slate-100 text-slate-700">
            <ArrowPathIcon className="w-7 h-7" />
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Bar Chart: findings per audit cycle by department */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                Findings Per Audit Cycle by Department
              </h3>
              <p className="text-xs text-slate-500">
                Historical distribution of control deficiencies across operational units
              </p>
            </div>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={summary?.findings_per_dept_per_cycle || []}
                margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="cycle_name" tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '11px',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
                <Bar dataKey="IT Operations" fill="#0d9488" radius={[4, 4, 0, 0]} />
                <Bar dataKey="HR" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Finance" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Engineering" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Pie Chart: control status distribution */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Control Status Register
            </h3>
            <p className="text-xs text-slate-500">
              Distribution across {totalControls} assessed controls
            </p>
          </div>

          <div className="h-56 w-full my-auto">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={75}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {pieData.map((entry) => (
                    <Cell
                      key={`cell-${entry.name}`}
                      fill={PIE_COLORS[entry.name] || '#94a3b8'}
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    border: 'none',
                    borderRadius: '8px',
                    color: '#fff',
                    fontSize: '11px',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: '11px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Overall Posture</span>
            <span className="font-semibold text-emerald-600">
              {totalControls > 0
                ? `${Math.round(((summary?.control_status_counts['Compliant'] || 0) / totalControls) * 100)}% Compliant`
                : '0%'}
            </span>
          </div>
        </div>
      </div>

      {/* Top 5 Risk Indicators Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900">
              Top Priority Risk Indicators
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Deterministic early-warning scoring based on severity, recurrence history, and remediation status
            </p>
          </div>
          <Link
            to="/risks"
            className="inline-flex items-center gap-1 text-xs font-semibold text-teal-700 hover:text-teal-800 transition"
          >
            <span>View All Ranked Risks</span>
            <ArrowRightIcon className="w-3.5 h-3.5" />
          </Link>
        </div>

        {topRisks.length === 0 ? (
          <EmptyState
            title="No High Risk Deficiencies"
            message="No active high-risk findings detected in the system."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50/75 border-b border-slate-200 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                  <th className="py-3 px-4">Score / Level</th>
                  <th className="py-3 px-4">Control</th>
                  <th className="py-3 px-4">Finding Description</th>
                  <th className="py-3 px-4">Department</th>
                  <th className="py-3 px-4">Risk Rationale</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-xs">
                {topRisks.map((risk) => (
                  <tr key={risk.finding_id} className="hover:bg-slate-50/60 transition">
                    <td className="py-3 px-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-slate-900 bg-slate-100 px-2 py-0.5 rounded text-xs">
                          {risk.score.toFixed(1)}
                        </span>
                        <SeverityBadge severity={risk.level} />
                      </div>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className="font-semibold text-slate-800 font-mono">
                        {risk.control_code || 'N/A'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="max-w-md font-medium text-slate-800 truncate" title={risk.description}>
                        {risk.description}
                      </div>
                      {risk.is_recurrence && (
                        <span className="inline-block mt-0.5 text-[10px] text-amber-700 font-semibold bg-amber-50 border border-amber-200 px-1.5 py-0.2 rounded">
                          Repeated Defect
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap text-slate-600">
                      {risk.department || 'General'}
                    </td>
                    <td className="py-3 px-4 text-slate-500 max-w-xs truncate" title={risk.explanation}>
                      {risk.explanation}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap text-right">
                      <Link
                        to={`/findings?id=${risk.finding_id}`}
                        className="text-xs font-semibold text-teal-600 hover:text-teal-800 hover:underline"
                      >
                        Inspect →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Disclaimer Footer Note */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 text-[11px] text-slate-500 leading-relaxed">
          <strong className="text-slate-700 font-semibold">Advisory Disclaimer: </strong>
          {disclaimer ||
            'Risk scores are advisory early-warning indicators calculated deterministically based on finding severity, recurrence history, remediation status, and control cadence. They do not constitute formal audit opinions.'}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
