import React from 'react';
import { clsx } from 'clsx';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'elevated' | 'bordered';
  isClickable?: boolean;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  (
    {
      children,
      className,
      variant = 'default',
      isClickable = false,
      ...props
    },
    ref
  ) => {
    const baseStyles = 'rounded-2xl transition-all duration-200 overflow-hidden';

    const variantStyles = {
      default: 'bg-white border border-border shadow-[0_2px_8px_rgba(27,27,24,0.04)]',
      elevated: 'bg-white border border-border/80 shadow-[0_8px_24px_rgba(27,27,24,0.08)]',
      bordered: 'bg-cream border-2 border-border',
    };

    const clickableStyles = isClickable
      ? 'cursor-pointer hover:border-deep-leaf/40 hover:shadow-[0_6px_20px_rgba(31,107,58,0.12)] active:scale-[0.99]'
      : '';

    return (
      <div
        ref={ref}
        className={clsx(
          baseStyles,
          variantStyles[variant],
          clickableStyles,
          className
        )}
        {...props}
      >
        {children}
      </div>
    );
  }
);

Card.displayName = 'Card';
