import React from 'react';
import clsx from 'clsx';
import { SparklesIcon, ExclamationTriangleIcon } from '@heroicons/react/20/solid';

interface AiSuggestionBannerProps {
  message?: string;
  sourceDoc?: string | null;
  sourcePage?: number | null;
  onViewSource?: () => void;
  className?: string;
  children?: React.ReactNode;
}

export const AiSuggestionBanner: React.FC<AiSuggestionBannerProps> = ({
  message = 'AI suggestion — needs human review',
  sourceDoc,
  sourcePage,
  onViewSource,
  className,
  children,
}) => {
  return (
    <div
      className={clsx(
        'rounded-lg border-2 border-dashed border-amber-400 bg-amber-50/70 p-3 text-amber-900 transition-all',
        className
      )}
      role="alert"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5">
          <span className="p-1 rounded bg-amber-200/80 text-amber-800 shrink-0 mt-0.5">
            <SparklesIcon className="w-4 h-4" aria-hidden="true" />
          </span>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold tracking-wide uppercase text-amber-800">
                {message}
              </span>
              <span className="inline-flex items-center gap-0.5 text-[11px] text-amber-700 font-medium bg-amber-100/90 px-1.5 py-0.5 rounded">
                <ExclamationTriangleIcon className="w-3 h-3" /> Draft Status
              </span>
            </div>
            {sourceDoc && (
              <p className="mt-1 text-xs text-amber-800/90">
                Extracted from: <span className="font-semibold">{sourceDoc}</span>
                {sourcePage ? ` (Page ${sourcePage})` : ''}
              </p>
            )}
          </div>
        </div>

        {onViewSource && (
          <button
            type="button"
            onClick={onViewSource}
            className="shrink-0 text-xs font-semibold text-amber-900 bg-amber-200/90 hover:bg-amber-300 px-2.5 py-1 rounded transition shadow-sm border border-amber-400/50"
          >
            View Source
          </button>
        )}
      </div>

      {children && <div className="mt-2.5 pt-2 border-t border-amber-200/70">{children}</div>}
    </div>
  );
};

export default AiSuggestionBanner;
