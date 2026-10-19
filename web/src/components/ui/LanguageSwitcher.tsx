'use client';

import React, { useState, useEffect, useRef, useId } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { clsx } from 'clsx';
import { Globe, ChevronDown, Check, Search, X, Sparkles } from 'lucide-react';
import {
  ALL_LANGUAGES,
  SupportedLocale,
  LanguageInfo,
  getLanguageInfo,
  isRtlLocale,
} from '@/lib/languages';
import { loadScriptFont, applyLayoutDirection } from '@/lib/fontLoader';

export type { SupportedLocale, LanguageInfo };
export { ALL_LANGUAGES as LANGUAGES };
export type LanguageOption = LanguageInfo;

export interface LanguageSwitcherProps {
  currentLocale: SupportedLocale;
  onSelectLocale?: (locale: SupportedLocale) => void;
  className?: string;
  compact?: boolean;
}

const COOKIE_EXPIRY_DAYS = 365;

function setCookie(name: string, value: string, days: number = COOKIE_EXPIRY_DAYS) {
  if (typeof document === 'undefined') return;
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
}

function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const matches = document.cookie.match(
    new RegExp('(?:^|; )' + name.replace(/([\.$?*|{}\(\)\[\]\\\/\+^])/g, '\\$1') + '=([^;]*)')
  );
  return matches ? decodeURIComponent(matches[1]) : null;
}

export const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({
  currentLocale,
  onSelectLocale,
  className,
  compact = false,
}) => {
  const t = useTranslations();
  const router = useRouter();
  const pathname = usePathname();

  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState(0);

  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const listboxId = useId();
  const currentLang = getLanguageInfo(currentLocale);

  // Filter languages by native name, english name, or code
  const filteredLanguages = ALL_LANGUAGES.filter((lang) => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return true;
    return (
      lang.englishLabel.toLowerCase().includes(q) ||
      lang.nativeLabel.toLowerCase().includes(q) ||
      lang.code.toLowerCase().includes(q)
    );
  });

  // First Visit Check: Automatically open language selector on first visit
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const hasChosen =
      localStorage.getItem('growcircle_locale_selected') ||
      getCookie('growcircle_locale_selected');

    if (!hasChosen) {
      setIsOpen(true);
    }
  }, []);

  // When dropdown opens, focus search input and reset highlight
  useEffect(() => {
    if (isOpen) {
      setSearchQuery('');
      const currentIndex = filteredLanguages.findIndex((l) => l.code === currentLocale);
      setHighlightedIndex(currentIndex >= 0 ? currentIndex : 0);
      setTimeout(() => {
        searchInputRef.current?.focus();
      }, 50);
    }
  }, [isOpen, currentLocale]);

  // Click outside listener
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  // Handle switching language
  const handleSelectLanguage = (newLocale: SupportedLocale) => {
    // 1. Remember choice in cookie (1-year expiry) & localStorage
    setCookie('NEXT_LOCALE', newLocale);
    setCookie('growcircle_locale', newLocale);
    setCookie('growcircle_locale_selected', 'true');

    if (typeof window !== 'undefined') {
      localStorage.setItem('growcircle_locale', newLocale);
      localStorage.setItem('growcircle_locale_selected', 'true');
    }

    // 2. Load script font on demand and apply layout direction (RTL/LTR)
    loadScriptFont(newLocale);
    applyLayoutDirection(newLocale);

    // 3. Sync to user profile if logged in (non-blocking)
    try {
      fetch('/api/languages/preference', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language: newLocale }),
      }).catch(() => {
        // Fallback silently if unauthenticated or offline
      });
    } catch {
      // Ignore network errors on preference sync
    }

    // 4. Update page without full reload (client-side SPA navigation)
    if (onSelectLocale) {
      onSelectLocale(newLocale);
    } else {
      const segments = pathname.split('/');
      segments[1] = newLocale;
      router.push(segments.join('/'));
    }

    setIsOpen(false);
    triggerRef.current?.focus();
  };

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        setIsOpen(true);
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex((prev) =>
          prev < filteredLanguages.length - 1 ? prev + 1 : 0
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex((prev) =>
          prev > 0 ? prev - 1 : filteredLanguages.length - 1
        );
        break;
      case 'Enter':
        e.preventDefault();
        if (filteredLanguages[highlightedIndex]) {
          handleSelectLanguage(filteredLanguages[highlightedIndex].code);
        }
        break;
      case 'Escape':
        e.preventDefault();
        setIsOpen(false);
        triggerRef.current?.focus();
        break;
      case 'Tab':
        setIsOpen(false);
        break;
    }
  };

  // Keep highlighted item scrolled into view
  useEffect(() => {
    if (isOpen && listRef.current) {
      const highlightedEl = listRef.current.children[highlightedIndex] as HTMLElement;
      if (highlightedEl) {
        highlightedEl.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [highlightedIndex, isOpen]);

  // Translated control label
  const controlLabel = t('languages.selectLanguage') || 'Select a language';
  const searchPlaceholder = t('languages.searchPlaceholder') || 'Search languages...';
  const partlyTranslatedLabel = t('languages.partlyTranslated') || 'Partly translated';
  const reviewedLabel = t('languages.reviewed') || 'Native reviewed';
  const noResultsLabel = t('languages.noResults') || 'No matching languages found';

  return (
    <div
      ref={containerRef}
      className={clsx('relative inline-block text-left', className)}
      onKeyDown={handleKeyDown}
    >
      {/* R5 Requirement 1: Single control labelled "Select a language" (itself translated) */}
      <button
        ref={triggerRef}
        type="button"
        id="language-selector-button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={listboxId}
        aria-label={`${controlLabel}: ${currentLang.nativeLabel} (${currentLang.englishLabel})`}
        className={clsx(
          'min-h-[44px] px-3.5 py-2 rounded-2xl border border-border bg-white hover:bg-cream',
          'text-ink font-semibold text-sm transition-all duration-150 inline-flex items-center gap-2.5',
          'shadow-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-deep-leaf active:scale-[0.98]',
          isOpen && 'border-deep-leaf ring-2 ring-deep-leaf/20'
        )}
      >
        <div className="w-6 h-6 rounded-lg bg-deep-leaf/10 text-deep-leaf flex items-center justify-center flex-shrink-0">
          <Globe className="w-4 h-4" aria-hidden="true" />
        </div>

        <div className="flex flex-col items-start leading-tight text-left">
          {!compact && (
            <span className="text-[10px] font-bold uppercase tracking-wider text-muted">
              {controlLabel}
            </span>
          )}
          <span className="font-bold text-ink">
            {currentLang.nativeLabel}
            <span className="text-muted font-normal ml-1.5 text-xs">
              ({currentLang.englishLabel})
            </span>
          </span>
        </div>

        <ChevronDown
          className={clsx(
            'w-4 h-4 text-muted transition-transform duration-200 ml-1',
            isOpen && 'rotate-180 text-deep-leaf'
          )}
          aria-hidden="true"
        />
      </button>

      {/* Dropdown Menu / First Visit Searchable Dialog */}
      {isOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={controlLabel}
          className={clsx(
            'absolute right-0 mt-2 w-80 sm:w-96 rounded-3xl bg-white border border-border shadow-2xl z-50 overflow-hidden',
            'animate-in fade-in-0 zoom-in-95 duration-150 flex flex-col',
            'max-h-[85vh] sm:max-h-[520px]'
          )}
        >
          {/* Header & Search Bar */}
          <div className="p-3.5 bg-cream/80 border-b border-border space-y-2">
            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-deep-leaf">
                  {controlLabel}
                </span>
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-deep-leaf/10 text-deep-leaf">
                  23 Languages
                </span>
              </div>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                aria-label="Close language selector"
                className="w-8 h-8 rounded-full flex items-center justify-center text-muted hover:text-ink hover:bg-black/5"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Search Input */}
            <div className="relative flex items-center">
              <Search className="w-4 h-4 text-muted absolute left-3 pointer-events-none" />
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setHighlightedIndex(0);
                }}
                placeholder={searchPlaceholder}
                aria-label={searchPlaceholder}
                className={clsx(
                  'w-full pl-9 pr-8 py-2.5 bg-white border border-border rounded-xl text-sm text-ink',
                  'placeholder:text-muted/70 focus:outline-none focus:border-deep-leaf focus:ring-2 focus:ring-deep-leaf/20'
                )}
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery('');
                    searchInputRef.current?.focus();
                  }}
                  aria-label="Clear search"
                  className="absolute right-2.5 text-muted hover:text-ink p-1 rounded-full"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* Languages List: all 22 scheduled + English (23 total) */}
          <ul
            id={listboxId}
            ref={listRef}
            role="listbox"
            aria-label="Supported Languages"
            className="overflow-y-auto divide-y divide-border/40 py-1 flex-1 focus:outline-none"
          >
            {filteredLanguages.length === 0 ? (
              <li className="px-4 py-8 text-center text-sm text-muted">
                {noResultsLabel}
              </li>
            ) : (
              filteredLanguages.map((lang, index) => {
                const isSelected = lang.code === currentLocale;
                const isHighlighted = index === highlightedIndex;

                return (
                  <li
                    key={lang.code}
                    role="option"
                    id={`lang-opt-${lang.code}`}
                    aria-selected={isSelected}
                    onClick={() => handleSelectLanguage(lang.code)}
                    onMouseEnter={() => setHighlightedIndex(index)}
                    className={clsx(
                      'min-h-[44px] px-4 py-2.5 cursor-pointer flex items-center justify-between transition-colors',
                      isHighlighted && 'bg-deep-leaf/5',
                      isSelected && 'bg-deep-leaf/10 font-bold'
                    )}
                  >
                    <div className="flex flex-col text-left">
                      <div className="flex items-center gap-2">
                        {/* Requirement 1: native script name and English name */}
                        <span className="text-sm font-bold text-ink">
                          {lang.nativeLabel}
                        </span>
                        <span className="text-xs text-muted font-normal">
                          ({lang.englishLabel})
                        </span>

                        {/* Requirement 2: Honest coverage badge */}
                        {!lang.reviewed_by_native_speaker && (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-900 border border-amber-300">
                            {partlyTranslatedLabel}
                          </span>
                        )}
                        {lang.reviewed_by_native_speaker && (
                          <span className="hidden sm:inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-deep-leaf/10 text-deep-leaf">
                            <Sparkles className="w-2.5 h-2.5" />
                            {reviewedLabel}
                          </span>
                        )}
                      </div>

                      {/* Script & fallback note for partly translated */}
                      {!lang.reviewed_by_native_speaker && (
                        <span className="text-[11px] text-muted/80 mt-0.5">
                          Falls back to {lang.fallbackLocale === 'hi' ? 'Hindi' : 'English'} per string
                        </span>
                      )}
                    </div>

                    {isSelected && (
                      <div className="w-6 h-6 rounded-full bg-deep-leaf text-white flex items-center justify-center flex-shrink-0 ml-2">
                        <Check className="w-3.5 h-3.5 stroke-[3]" />
                      </div>
                    )}
                  </li>
                );
              })
            )}
          </ul>

          {/* Footer note for honest coverage */}
          <div className="p-2.5 bg-cream/90 border-t border-border text-[11px] text-muted text-center flex items-center justify-center gap-2">
            <span>22 Scheduled Languages + English</span>
            <span>&bull;</span>
            <span>WCAG 44px Touch Targets</span>
          </div>
        </div>
      )}
    </div>
  );
};
