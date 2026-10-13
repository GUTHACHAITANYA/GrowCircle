import React from 'react';
import { clsx } from 'clsx';
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastProps {
  id?: string;
  type: ToastType;
  title: string;
  message?: string;
  onDismiss?: () => void;
  className?: string;
}

export const Toast: React.FC<ToastProps> = ({
  type = 'info',
  title,
  message,
  onDismiss,
  className,
}) => {
  const typeConfig = {
    success: {
      icon: <CheckCircle2 className="w-5 h-5 text-deep-leaf" />,
      containerStyles: 'bg-white border-l-4 border-l-deep-leaf border-border text-ink',
    },
    error: {
      icon: <AlertCircle className="w-5 h-5 text-danger" />,
      containerStyles: 'bg-white border-l-4 border-l-danger border-border text-ink',
    },
    warning: {
      icon: <AlertTriangle className="w-5 h-5 text-amber" />,
      containerStyles: 'bg-white border-l-4 border-l-amber border-border text-ink',
    },
    info: {
      icon: <Info className="w-5 h-5 text-info" />,
      containerStyles: 'bg-white border-l-4 border-l-info border-border text-ink',
    },
  };

  const { icon, containerStyles } = typeConfig[type];

  return (
    <div
      role="alert"
      aria-live="assertive"
      className={clsx(
        'flex items-start justify-between gap-3 p-4 rounded-xl shadow-lg border max-w-md w-full transition-all duration-200',
        containerStyles,
        className
      )}
    >
      <div className="flex items-start gap-3 flex-1">
        <span className="flex-shrink-0 mt-0.5">{icon}</span>
        <div>
          <h4 className="text-base font-bold text-ink leading-tight">{title}</h4>
          {message && (
            <p className="text-sm text-muted mt-1 leading-snug">{message}</p>
          )}
        </div>
      </div>

      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="flex-shrink-0 min-h-[44px] min-w-[44px] -mr-2 -mt-2 p-2.5 rounded-lg text-muted hover:text-ink hover:bg-black/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-deep-leaf flex items-center justify-center"
          aria-label="Dismiss notification"
        >
          <X className="w-5 h-5" />
        </button>
      )}
    </div>
  );
};
