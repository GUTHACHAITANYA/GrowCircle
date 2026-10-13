import React from 'react';
import { clsx } from 'clsx';

export interface ChipProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'primary' | 'accent' | 'danger' | 'info';
  size?: 'sm' | 'md';
  selected?: boolean;
  isClickable?: boolean;
  icon?: React.ReactNode;
  onRemove?: () => void;
}

export const Chip = React.forwardRef<HTMLDivElement, ChipProps>(
  (
    {
      children,
      className,
      variant = 'default',
      size = 'md',
      selected = false,
      isClickable = false,
      icon,
      onRemove,
      onClick,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      'inline-flex items-center justify-center font-medium rounded-full select-none transition-colors border';

    const variantStyles = {
      default: selected
        ? 'bg-deep-leaf text-white border-deep-leaf'
        : 'bg-white text-ink border-border hover:bg-cream',
      primary: 'bg-deep-leaf/10 text-deep-leaf border-deep-leaf/20 font-semibold',
      accent: 'bg-harvest-gold/25 text-ink border-harvest-gold/50 font-semibold',
      danger: 'bg-danger/10 text-danger border-danger/20 font-semibold',
      info: 'bg-info/10 text-info border-info/20 font-semibold',
    };

    const sizeStyles = {
      sm: 'px-3 py-1 text-xs gap-1.5 min-h-[32px]',
      // md adheres to the >= 44px accessible touch target when clickable
      md: isClickable
        ? 'px-4 py-2 text-sm gap-2 min-h-[44px]'
        : 'px-3.5 py-1.5 text-sm gap-2 min-h-[36px]',
    };

    const interactiveStyles = isClickable
      ? 'cursor-pointer active:scale-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-deep-leaf'
      : '';

    return (
      <div
        ref={ref}
        role={isClickable ? 'button' : undefined}
        tabIndex={isClickable ? 0 : undefined}
        onClick={onClick}
        className={clsx(
          baseStyles,
          variantStyles[variant],
          sizeStyles[size],
          interactiveStyles,
          className
        )}
        {...props}
      >
        {icon && <span className="flex-shrink-0">{icon}</span>}
        <span>{children}</span>
        {onRemove && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onRemove();
            }}
            className="ml-1 p-0.5 rounded-full hover:bg-black/10 focus:outline-none"
            aria-label="Remove"
          >
            <span aria-hidden="true">&times;</span>
          </button>
        )}
      </div>
    );
  }
);

Chip.displayName = 'Chip';
