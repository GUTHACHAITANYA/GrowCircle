'use client';

import React from 'react';
import { clsx } from 'clsx';
import { Globe } from 'lucide-react';

export type SupportedLocale = 'en' | 'te' | 'hi' | 'gu';

export interface LanguageOption {
  code: SupportedLocale;
  nativeLabel: string;
  englishLabel: string;
}

export const LANGUAGES: LanguageOption[] = [
  { code: 'en', nativeLabel: 'English', englishLabel: 'English' },
  { code: 'te', nativeLabel: 'తెలుగు', englishLabel: 'Telugu' },
  { code: 'hi', nativeLabel: 'हिंदी', englishLabel: 'Hindi' },
  { code: 'gu', nativeLabel: 'ગુજરાતી', englishLabel: 'Gujarati' },
];

export interface LanguageSwitcherProps {
  currentLocale: SupportedLocale;
  onSelectLocale: (locale: SupportedLocale) => void;
  className?: string;
  compact?: boolean;
}

export const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({
  currentLocale,
  onSelectLocale,
  className,
  compact = false,
}) => {
  return (
    <div
      className={clsx(
        'inline-flex items-center p-1 bg-cream border border-border rounded-2xl gap-1',
        className
      )}
      role="group"
      aria-label="Language selection"
    >
      {!compact && (
        <div className="hidden sm:flex items-center pl-2 pr-1 text-muted">
          <Globe className="w-4 h-4" aria-hidden="true" />
        </div>
      )}

      {LANGUAGES.map((lang) => {
        const isActive = lang.code === currentLocale;
        return (
          <button
            key={lang.code}
            type="button"
            onClick={() => onSelectLocale(lang.code)}
            aria-pressed={isActive}
            className={clsx(
              'min-h-[44px] min-w-[44px] px-3 py-2 rounded-xl text-sm font-semibold transition-all duration-150 flex items-center justify-center focus:outline-none focus-visible:ring-2 focus-visible:ring-deep-leaf',
              isActive
                ? 'bg-deep-leaf text-white shadow-sm'
                : 'text-ink hover:bg-black/5 hover:text-deep-leaf'
            )}
          >
            <span className="leading-none">{lang.nativeLabel}</span>
          </button>
        );
      })}
    </div>
  );
};
