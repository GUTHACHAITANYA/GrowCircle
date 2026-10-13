import React from 'react';
import { clsx } from 'clsx';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'accent' | 'ghost' | 'danger';
  size?: 'md' | 'lg';
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      className,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      disabled = false,
      leftIcon,
      rightIcon,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      'inline-flex items-center justify-center font-semibold rounded-xl transition-all duration-150 select-none focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100 min-h-[44px] min-w-[44px]';

    const variantStyles = {
      primary:
        'bg-deep-leaf text-white hover:bg-[#18552e] active:bg-[#124022] focus-visible:ring-deep-leaf shadow-sm',
      secondary:
        'bg-cream text-ink border border-border hover:bg-[#f3f0e2] active:bg-[#eae6d4] focus-visible:ring-deep-leaf',
      accent:
        'bg-harvest-gold text-ink hover:bg-[#e6b334] active:bg-[#d4a329] focus-visible:ring-harvest-gold font-bold',
      ghost:
        'bg-transparent text-ink hover:bg-black/5 active:bg-black/10 focus-visible:ring-deep-leaf',
      danger:
        'bg-danger text-white hover:bg-[#ad2020] active:bg-[#911b1b] focus-visible:ring-danger shadow-sm',
    };

    const sizeStyles = {
      md: 'px-4 py-2.5 text-base gap-2',
      lg: 'px-6 py-3.5 text-lg gap-2.5 min-h-[48px]',
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={clsx(
          baseStyles,
          variantStyles[variant],
          sizeStyles[size],
          className
        )}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="w-5 h-5 animate-spin" aria-hidden="true" />
        ) : (
          leftIcon && <span className="flex-shrink-0">{leftIcon}</span>
        )}
        <span>{children}</span>
        {!isLoading && rightIcon && (
          <span className="flex-shrink-0">{rightIcon}</span>
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';
