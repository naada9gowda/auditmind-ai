import React from 'react';
import clsx from 'clsx';
import { FindingSeverity } from '../api/types';

interface SeverityBadgeProps {
  severity: FindingSeverity | string;
  className?: string;
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({ severity, className }) => {
  const norm = severity?.toLowerCase();

  let badgeClass = 'bg-slate-100 text-slate-700 border-slate-300';
  let dotClass = 'bg-slate-500';

  if (norm === 'high') {
    badgeClass = 'bg-red-50 text-red-800 border-red-300 ring-1 ring-red-600/20';
    dotClass = 'bg-red-600';
  } else if (norm === 'medium') {
    badgeClass = 'bg-amber-50 text-amber-800 border-amber-300 ring-1 ring-amber-600/20';
    dotClass = 'bg-amber-600';
  } else if (norm === 'low') {
    badgeClass = 'bg-blue-50 text-blue-800 border-blue-300 ring-1 ring-blue-600/20';
    dotClass = 'bg-blue-600';
  }

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border',
        badgeClass,
        className
      )}
      aria-label={`Severity: ${severity}`}
    >
      <span className={clsx('w-1.5 h-1.5 rounded-full shrink-0', dotClass)} aria-hidden="true" />
      <span>{severity}</span>
    </span>
  );
};

export default SeverityBadge;
