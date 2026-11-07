import React from 'react';
import { Dialog, DialogBackdrop, DialogPanel, DialogTitle } from '@headlessui/react';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import clsx from 'clsx';

interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'warning' | 'primary';
  loading?: boolean;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'primary',
  loading = false,
}) => {
  return (
    <Dialog open={isOpen} onClose={onClose} className="relative z-50">
      <DialogBackdrop className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs transition-opacity" />

      <div className="fixed inset-0 z-10 w-screen overflow-y-auto">
        <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
          <DialogPanel className="relative transform overflow-hidden rounded-xl bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-md sm:p-6 border border-slate-200">
            <div className="sm:flex sm:items-start">
              <div
                className={clsx(
                  'mx-auto flex h-12 w-12 shrink-0 items-center justify-center rounded-full sm:mx-0 sm:h-10 sm:w-10',
                  variant === 'danger'
                    ? 'bg-red-100 text-red-600'
                    : variant === 'warning'
                    ? 'bg-amber-100 text-amber-600'
                    : 'bg-teal-100 text-teal-600'
                )}
              >
                <ExclamationTriangleIcon className="h-6 w-6" aria-hidden="true" />
              </div>
              <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left">
                <DialogTitle as="h3" className="text-base font-semibold leading-6 text-slate-900">
                  {title}
                </DialogTitle>
                <div className="mt-2">
                  <p className="text-xs text-slate-500 leading-relaxed">{message}</p>
                </div>
              </div>
            </div>
            <div className="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse gap-2">
              <button
                type="button"
                disabled={loading}
                onClick={onConfirm}
                className={clsx(
                  'inline-flex w-full justify-center rounded-lg px-3 py-2 text-xs font-semibold text-white shadow-xs sm:w-auto transition',
                  variant === 'danger'
                    ? 'bg-rose-600 hover:bg-rose-500'
                    : variant === 'warning'
                    ? 'bg-amber-600 hover:bg-amber-500'
                    : 'bg-teal-600 hover:bg-teal-500',
                  loading && 'opacity-60 cursor-not-allowed'
                )}
              >
                {loading ? 'Processing...' : confirmLabel}
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={onClose}
                className="mt-3 inline-flex w-full justify-center rounded-lg bg-white px-3 py-2 text-xs font-semibold text-slate-700 shadow-xs ring-1 ring-inset ring-slate-300 hover:bg-slate-50 sm:mt-0 sm:w-auto transition"
              >
                {cancelLabel}
              </button>
            </div>
          </DialogPanel>
        </div>
      </div>
    </Dialog>
  );
};

export default ConfirmDialog;
