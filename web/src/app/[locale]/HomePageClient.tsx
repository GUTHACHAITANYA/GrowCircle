'use client';

import React from 'react';
import Link from 'next/link';
import { useTranslations, useLocale } from 'next-intl';
import { useRouter, usePathname } from 'next/navigation';
import { Header } from '@/components/ui/Header';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { VoiceButton } from '@/components/ui/VoiceButton';
import { SupportedLocale } from '@/components/ui/LanguageSwitcher';
import {
  TrendingUp,
  Store,
  Truck,
  Users,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
} from 'lucide-react';

export function HomePageClient() {
  const t = useTranslations();
  const locale = useLocale() as SupportedLocale;
  const router = useRouter();
  const pathname = usePathname();

  const handleLocaleChange = (newLocale: SupportedLocale) => {
    const segments = pathname.split('/');
    segments[1] = newLocale;
    router.push(segments.join('/'));
  };

  return (
    <div className="min-h-screen flex flex-col bg-cream">
      <Header
        currentLocale={locale}
        onSelectLocale={handleLocaleChange}
        brandName={t('brand.name')}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
        {/* Hero Section */}
        <div className="text-center max-w-3xl mx-auto mb-12 sm:mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-deep-leaf/10 text-deep-leaf border border-deep-leaf/20 mb-6 text-sm font-semibold">
            <ShieldCheck className="w-4 h-4" />
            <span>{t('brand.tagline')}</span>
          </div>

          <h1 className="font-heading text-4xl sm:text-6xl font-extrabold text-ink tracking-tight mb-4 leading-tight">
            {t('brand.greeting')}
          </h1>

          <p className="text-lg sm:text-xl text-muted leading-relaxed mb-8">
            The voice-first fruit and vegetable circle in India. Real-time mandi prices,
            verified institutional buyers, and transparent transport dispatch for everyone.
          </p>

          {/* Voice Prompt Action */}
          <div className="bg-white p-6 sm:p-8 rounded-3xl border border-border shadow-sm max-w-md mx-auto mb-8">
            <VoiceButton
              state="idle"
              label={t('voice.speak')}
              sublabel={t('voice.prompt')}
            />
          </div>

          <div className="flex flex-wrap items-center justify-center gap-4">
            <Link href={`/${locale}/showcase`}>
              <Button
                variant="primary"
                size="lg"
                rightIcon={<ArrowRight className="w-5 h-5" />}
              >
                {t('nav.showcase')}
              </Button>
            </Link>
          </div>
        </div>

        {/* The Four Core Doors / Roles */}
        <div className="mb-16">
          <div className="text-center mb-8">
            <h2 className="font-heading text-2xl sm:text-3xl font-bold text-ink">
              One Engine, Four Core Doors
            </h2>
            <p className="text-muted text-base mt-1">
              Every door calls the exact same single-source-of-truth API.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card className="p-6 flex flex-col justify-between">
              <div>
                <div className="w-12 h-12 rounded-2xl bg-deep-leaf/10 text-deep-leaf flex items-center justify-center mb-4">
                  <TrendingUp className="w-6 h-6" />
                </div>
                <h3 className="font-heading text-xl font-bold text-ink mb-1">
                  {t('roles.farmer')}
                </h3>
                <p className="text-sm text-muted">
                  Voice-first queries, nearest mandis, fair crop listing, and masked calls with buyers.
                </p>
              </div>
              <div className="mt-4 pt-4 border-t border-border flex items-center text-xs text-deep-leaf font-bold">
                <CheckCircle2 className="w-4 h-4 mr-1.5" />
                Always 100% Free
              </div>
            </Card>

            <Card className="p-6 flex flex-col justify-between">
              <div>
                <div className="w-12 h-12 rounded-2xl bg-harvest-gold/30 text-ink flex items-center justify-center mb-4">
                  <Store className="w-6 h-6" />
                </div>
                <h3 className="font-heading text-xl font-bold text-ink mb-1">
                  {t('roles.buyer')}
                </h3>
                <p className="text-sm text-muted">
                  Colleges, hostels, schools, hotels & shops post weekly requirements and negotiate directly.
                </p>
              </div>
              <div className="mt-4 pt-4 border-t border-border flex items-center text-xs text-muted font-bold">
                <CheckCircle2 className="w-4 h-4 mr-1.5 text-deep-leaf" />
                Verified Supply
              </div>
            </Card>

            <Card className="p-6 flex flex-col justify-between">
              <div>
                <div className="w-12 h-12 rounded-2xl bg-info/10 text-info flex items-center justify-center mb-4">
                  <Truck className="w-6 h-6" />
                </div>
                <h3 className="font-heading text-xl font-bold text-ink mb-1">
                  {t('roles.driver')}
                </h3>
                <p className="text-sm text-muted">
                  Goods autos & mini-trucks receive trip requests post-deal with secure OTP verification.
                </p>
              </div>
              <div className="mt-4 pt-4 border-t border-border flex items-center text-xs text-muted font-bold">
                <CheckCircle2 className="w-4 h-4 mr-1.5 text-deep-leaf" />
                Two-way Ratings
              </div>
            </Card>

            <Card className="p-6 flex flex-col justify-between">
              <div>
                <div className="w-12 h-12 rounded-2xl bg-amber/10 text-amber flex items-center justify-center mb-4">
                  <Users className="w-6 h-6" />
                </div>
                <h3 className="font-heading text-xl font-bold text-ink mb-1">
                  {t('roles.consumer')}
                </h3>
                <p className="text-sm text-muted">
                  No login required. Today&apos;s mandi prices, regional price trends, and consumer alerts.
                </p>
              </div>
              <div className="mt-4 pt-4 border-t border-border flex items-center text-xs text-deep-leaf font-bold">
                <CheckCircle2 className="w-4 h-4 mr-1.5" />
                No Login Needed
              </div>
            </Card>
          </div>
        </div>
      </main>

      <footer className="border-t border-border bg-white py-8 px-4 text-center text-sm text-muted">
        <p className="font-semibold text-ink">
          GrowCircle ({t('brand.name')}) &bull; {t('brand.tagline')}
        </p>
        <p className="text-xs text-muted mt-1">
          WCAG AA Compliant &bull; DPDP Act Aligned &bull; Real Mandi Data
        </p>
      </footer>
    </div>
  );
}
