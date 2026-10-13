import React from 'react';
import { clsx } from 'clsx';
import { Sprout, RefreshCw } from 'lucide-react';
import { Button } from './Button';

export interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon,
  actionLabel,
  onAction,
  className,
}) => {
  return (
    <div
      className={clsx(
        'flex flex-col items-center justify-center p-8 sm:p-12 text-center bg-white border border-border rounded-2xl max-w-lg mx-auto',
        className
      )}
    >
      <div className="w-16 h-16 rounded-2xl bg-cream border border-border flex items-center justify-center text-deep-leaf mb-4 shadow-sm">
        {icon || <Sprout className="w-8 h-8 text-deep-leaf" />}
      </div>

      <h3 className="font-heading text-xl sm:text-2xl font-bold text-ink mb-2">
        {title}
      </h3>

      <p className="text-base text-muted max-w-md mb-6 leading-relaxed">
        {description}
      </p>

      {actionLabel && onAction && (
        <Button
          variant="secondary"
          size="md"
          onClick={onAction}
          leftIcon={<RefreshCw className="w-4 h-4 text-deep-leaf" />}
        >
          {actionLabel}
        </Button>
      )}
    </div>
  );
};
