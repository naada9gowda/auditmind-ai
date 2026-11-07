import React from 'react';
import clsx from 'clsx';
import { ShieldCheckIcon } from '@heroicons/react/20/solid';

interface VerifiedBadgeProps {
  label?: string;
  className?: string;
}

export const VerifiedBadge: React.FC<VerifiedBadgeProps> = ({
  label = 'Approved record',
  className,
}) => {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-800 border-2 border-emerald-600 shadow-sm',
        className
      )}
      title="This record has been confirmed and approved by an authorized reviewer."
    >
      <ShieldCheckIcon className="w-3.5 h-3.5 text-emerald-700 shrink-0" aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
};

export default VerifiedBadge;
