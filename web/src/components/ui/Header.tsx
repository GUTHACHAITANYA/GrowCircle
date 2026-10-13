'use client';

import React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { clsx } from 'clsx';
import { LanguageSwitcher, SupportedLocale } from './LanguageSwitcher';

export interface HeaderProps {
  currentLocale: SupportedLocale;
  onSelectLocale: (locale: SupportedLocale) => void;
  brandName?: string;
  className?: string;
  activeNav?: string;
}

export const Header: React.FC<HeaderProps> = ({
  currentLocale,
  onSelectLocale,
  brandName = 'GrowCircle',
  className,
  activeNav,
}) => {
  return (
    <header
      role="banner"
      className={clsx(
        'sticky top-0 z-40 bg-white/95 backdrop-blur border-b border-border transition-shadow',
        className
      )}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-20 gap-4">
          {/* Logo & Brand Name */}
          <Link
            href={`/${currentLocale}`}
            className="flex items-center gap-3 focus:outline-none focus-visible:ring-2 focus-visible:ring-deep-leaf rounded-xl p-1 -ml-1 group"
            aria-label={`${brandName} Home`}
          >
            {/* Logo Mark directly from canonical SVG file */}
            <div className="w-12 h-12 relative flex-shrink-0">
              <Image
                src="/logo-mark.svg"
                alt=""
                width={48}
                height={48}
                priority
                className="w-full h-full object-contain"
              />
            </div>

            {/* Wordmark with G and C in Amber #C77700 and others in Deep Leaf #1F6B3A */}
            <div className="flex flex-col">
              <span className="font-heading text-2xl sm:text-3xl font-extrabold tracking-tight leading-none">
                <span className="text-amber">G</span>
                <span className="text-deep-leaf">row</span>
                <span className="text-amber">C</span>
                <span className="text-deep-leaf">ircle</span>
              </span>
              {currentLocale !== 'en' && (
                <span className="text-xs font-semibold text-muted leading-tight mt-0.5">
                  {brandName}
                </span>
              )}
            </div>
          </Link>

          {/* Navigation links & Language Switcher */}
          <div className="flex items-center gap-3 sm:gap-6">
            <nav className="hidden md:flex items-center gap-2">
              <Link
                href={`/${currentLocale}/prices`}
                className={clsx(
                  'px-3.5 py-2 rounded-xl text-sm font-semibold transition-colors min-h-[44px] inline-flex items-center',
                  activeNav === 'prices'
                    ? 'bg-deep-leaf text-white shadow-sm'
                    : 'text-ink hover:text-deep-leaf hover:bg-black/5'
                )}
              >
                Price Today
              </Link>
              <Link
                href={`/${currentLocale}/showcase`}
                className={clsx(
                  'px-3.5 py-2 rounded-xl text-sm font-semibold transition-colors min-h-[44px] inline-flex items-center',
                  activeNav === 'showcase'
                    ? 'bg-deep-leaf/10 text-deep-leaf'
                    : 'text-ink hover:text-deep-leaf hover:bg-black/5'
                )}
              >
                Design System
              </Link>
            </nav>

            <LanguageSwitcher
              currentLocale={currentLocale}
              onSelectLocale={onSelectLocale}
              compact
            />
          </div>
        </div>
      </div>
    </header>
  );
};
