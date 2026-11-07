import React from 'react';
import clsx from 'clsx';
import { ControlStatus } from '../api/types';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  MinusCircleIcon,
} from '@heroicons/react/20/solid';

interface StatusBadgeProps {
  status: ControlStatus | string;
  className?: string;
  showIcon?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  className,
  showIcon = true,
}) => {
  const normalized = status?.trim() || 'Not Assessed';

  let bgClass = 'bg-slate-100 text-slate-700 border-slate-300';
  let IconComponent = MinusCircleIcon;

  switch (normalized) {
    case 'Compliant':
      bgClass = 'bg-emerald-50 text-emerald-800 border-emerald-300 ring-1 ring-emerald-600/20';
      IconComponent = CheckCircleIcon;
      break;
    case 'Needs Review':
      bgClass = 'bg-amber-50 text-amber-800 border-amber-300 ring-1 ring-amber-600/20';
      IconComponent = ExclamationTriangleIcon;
      break;
    case 'Gap Identified':
      bgClass = 'bg-rose-50 text-rose-800 border-rose-300 ring-1 ring-rose-600/20';
      IconComponent = XCircleIcon;
      break;
    case 'Not Assessed':
    default:
      bgClass = 'bg-slate-100 text-slate-700 border-slate-300 ring-1 ring-slate-600/10';
      IconComponent = MinusCircleIcon;
      break;
  }

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border',
        bgClass,
        className
      )}
      aria-label={`Status: ${normalized}`}
    >
      {showIcon && <IconComponent className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />}
      <span>{normalized}</span>
    </span>
  );
};

export default StatusBadge;
