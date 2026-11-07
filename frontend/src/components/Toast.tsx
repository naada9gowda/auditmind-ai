import React, { createContext, useContext, useState, useCallback } from 'react';
import { CheckCircleIcon, XCircleIcon, InformationCircleIcon, XMarkIcon } from '@heroicons/react/20/solid';
import clsx from 'clsx';

type ToastType = 'success' | 'error' | 'info';

interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
}

interface ToastContextType {
  showToast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback((message: string, type: ToastType = 'info') => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      removeToast(id);
    }, 4500);
  }, [removeToast]);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={clsx(
              'pointer-events-auto flex items-center justify-between gap-3 p-3.5 rounded-lg shadow-lg border text-xs font-medium transition-all duration-200 animate-slide-up',
              toast.type === 'success' && 'bg-emerald-50 text-emerald-900 border-emerald-300 ring-1 ring-emerald-500/20',
              toast.type === 'error' && 'bg-rose-50 text-rose-900 border-rose-300 ring-1 ring-rose-500/20',
              toast.type === 'info' && 'bg-slate-900 text-white border-slate-700 shadow-xl'
            )}
            role="status"
          >
            <div className="flex items-center gap-2">
              {toast.type === 'success' && <CheckCircleIcon className="w-4 h-4 text-emerald-600 shrink-0" />}
              {toast.type === 'error' && <XCircleIcon className="w-4 h-4 text-rose-600 shrink-0" />}
              {toast.type === 'info' && <InformationCircleIcon className="w-4 h-4 text-teal-400 shrink-0" />}
              <span>{toast.message}</span>
            </div>
            <button
              type="button"
              onClick={() => removeToast(toast.id)}
              className="p-1 hover:opacity-75 rounded"
            >
              <XMarkIcon className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = (): ToastContextType => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};
