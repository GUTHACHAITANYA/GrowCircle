'use client';

import React, { useState } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { useRouter, usePathname } from 'next/navigation';
import Image from 'next/image';
import {
  Header,
  Button,
  Card,
  Chip,
  PriceTile,
  MandiRow,
  LanguageSwitcher,
  VoiceButton,
  EmptyState,
  Toast,
  SupportedLocale,
} from '@/components/ui';
import {
  Sparkles,
  PhoneCall,
  Search,
  ShoppingCart,
} from 'lucide-react';
import { RoleGuard } from '@/components/auth/RoleGuard';

export function ShowcaseClient() {
  const t = useTranslations();
  const locale = useLocale() as SupportedLocale;
  const router = useRouter();
  const pathname = usePathname();

  // Interactive component states
  const [voiceState, setVoiceState] = useState<'idle' | 'listening' | 'processing'>('idle');
  const [selectedChip, setSelectedChip] = useState<string>('all');
  const [showToasts, setShowToasts] = useState({
    success: true,
    warning: true,
    error: true,
    info: true,
  });

  const handleLocaleChange = (newLocale: SupportedLocale) => {
    const segments = pathname.split('/');
    segments[1] = newLocale;
    router.push(segments.join('/'));
  };

  const toggleVoice = () => {
    if (voiceState === 'idle') setVoiceState('listening');
    else if (voiceState === 'listening') setVoiceState('processing');
    else setVoiceState('idle');
  };

  return (
    <div className="min-h-screen bg-cream flex flex-col">
      <Header
        currentLocale={locale}
        onSelectLocale={handleLocaleChange}
        brandName={t('brand.name')}
        activeNav="showcase"
      />

      <RoleGuard
        allowedRoles={['admin']}
        require2FA={false}
        fallbackTitle="Design System Access Restricted"
        fallbackMessage="The Storybook component showcase and raw design system tokens are restricted to administrators. Please sign in with an authorized account."
      >
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-16">
        {/* Showcase Header */}
        <div className="bg-white p-8 rounded-3xl border border-border shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-deep-leaf/10 text-deep-leaf text-xs font-bold mb-3">
                <Sparkles className="w-4 h-4" />
                <span>GROWCIRCLE DESIGN SYSTEM</span>
              </div>
              <h1 className="font-heading text-3xl sm:text-4xl font-extrabold text-ink">
                Storybook Component Showcase
              </h1>
              <p className="text-muted text-base mt-2 max-w-2xl">
                Every component strictly follows WCAG AA contrast standards, &ge; 44px accessible touch targets, and the canonical token system across all 22 scheduled Indian languages plus English with honest coverage tracking.
              </p>
            </div>

            {/* Language Switcher Bar */}
            <div className="flex flex-col items-start md:items-end gap-2">
              <span className="text-xs font-bold text-muted uppercase tracking-wider">
                Select a Language / భాషను ఎంచుకోండి
              </span>
              <LanguageSwitcher
                currentLocale={locale}
                onSelectLocale={handleLocaleChange}
              />
            </div>
          </div>
        </div>

        {/* SECTION 1: Brand Assets & Canonical Logos */}
        <section className="space-y-6">
          <div className="border-b border-border pb-3">
            <h2 className="font-heading text-2xl font-bold text-ink">
              1. Brand Identity & Canonical Logos
            </h2>
            <p className="text-sm text-muted">
              Loaded directly from assets/brand/logo-mark.svg and logo-full.svg. Proportions and colors are non-negotiable.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="p-6 bg-white flex flex-col items-center justify-center text-center">
              <div className="w-36 h-36 relative mb-4">
                <Image
                  src="/logo-mark.svg"
                  alt="GrowCircle Logo Mark"
                  width={144}
                  height={144}
                  className="w-full h-full object-contain"
                />
              </div>
              <h3 className="font-heading text-lg font-bold text-ink">
                Logo Mark (assets/brand/logo-mark.svg)
              </h3>
              <p className="text-xs text-muted max-w-xs mt-1">
                23% corner radius Deep Leaf container, white C arc, and Harvest Gold leaf creating the &quot;G&quot;.
              </p>
            </Card>

            <Card className="p-6 bg-white flex flex-col items-center justify-center text-center">
              <div className="w-full max-w-md h-28 relative mb-4">
                <Image
                  src="/logo-full.svg"
                  alt="GrowCircle Full Logo"
                  width={400}
                  height={110}
                  className="w-full h-full object-contain"
                />
              </div>
              <h3 className="font-heading text-lg font-bold text-ink">
                Full Logo & Wordmark (assets/brand/logo-full.svg)
              </h3>
              <p className="text-xs text-muted max-w-xs mt-1">
                Mark with Baloo 2 ExtraBold wordmark. &quot;G&quot; and &quot;C&quot; in Amber (#C77700), others in Deep Leaf (#1F6B3A).
              </p>
            </Card>
          </div>
        </section>

        {/* SECTION 2: Button Component */}
        <section className="space-y-6">
          <div className="border-b border-border pb-3">
            <h2 className="font-heading text-2xl font-bold text-ink">
              2. Button Component (Touch Target &ge; 44px)
            </h2>
            <p className="text-sm text-muted">
              Supports Primary, Secondary, Accent, Ghost, Danger, and Loading states with keyboard navigation.
            </p>
          </div>

          <div className="flex flex-wrap gap-4 items-center bg-white p-6 rounded-2xl border border-border">
            <Button
              variant="primary"
              size="md"
              leftIcon={<Search className="w-4 h-4" />}
            >
              {t('buttons.search')} (Primary)
            </Button>

            <Button
              variant="secondary"
              size="md"
              leftIcon={<PhoneCall className="w-4 h-4 text-deep-leaf" />}
            >
              {t('buttons.call')} (Secondary)
            </Button>

            <Button
              variant="accent"
              size="md"
              leftIcon={<ShoppingCart className="w-4 h-4" />}
            >
              {t('buttons.offer')} (Accent)
            </Button>

            <Button variant="ghost" size="md">
              {t('buttons.back')} (Ghost)
            </Button>

            <Button variant="danger" size="md">
              {t('buttons.close')} (Danger)
            </Button>

            <Button variant="primary" size="md" isLoading>
              Loading State
            </Button>

            <Button variant="secondary" size="md" disabled>
              Disabled
            </Button>
          </div>
        </section>

        {/* SECTION 3: PriceTile Component */}
        <section className="space-y-6">
          <div className="border-b border-border pb-3">
            <h2 className="font-heading text-2xl font-bold text-ink">
              3. PriceTile Component
            </h2>
            <p className="text-sm text-muted">
              Mandatory database prices with dates, last_updated timestamps, unit toggles, and &gt;24h stale warnings.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            <PriceTile
              commodityName={locale === 'te' ? 'టమాటా' : locale === 'hi' ? 'टमाटर' : locale === 'gu' ? 'ટામેટા' : 'Tomato'}
              variety="Hybrid Grade-A"
              modalPrice={28}
              unit="kg"
              trend="up"
              trendDiff={3}
              lastUpdated="Today, 08:30 AM"
              mandiName="Madanapalle Mandi"
              labels={{
                unitLabel: locale === 'te' ? '/కిలో' : locale === 'hi' ? '/किलो' : locale === 'gu' ? '/કિલો' : '/kg',
                modalPriceLabel: t('priceTile.modalPrice'),
                lastUpdatedPrefix: 'Updated',
                staleWarning: t('priceTile.staleWarning'),
              }}
            />

            <PriceTile
              commodityName={locale === 'te' ? 'ఉల్లిపాయ' : locale === 'hi' ? 'प्याज' : locale === 'gu' ? 'ડુંગળી' : 'Onion'}
              variety="Nashik Red"
              modalPrice={24}
              unit="kg"
              trend="down"
              trendDiff={-2}
              lastUpdated="Today, 09:15 AM"
              mandiName="Lasalgaon Mandi"
              labels={{
                unitLabel: locale === 'te' ? '/కిలో' : locale === 'hi' ? '/किलो' : locale === 'gu' ? '/કિલો' : '/kg',
                modalPriceLabel: t('priceTile.modalPrice'),
                lastUpdatedPrefix: 'Updated',
                staleWarning: t('priceTile.staleWarning'),
              }}
            />

            <PriceTile
              commodityName={locale === 'te' ? 'బంగాళాదుంప' : locale === 'hi' ? 'आलू' : locale === 'gu' ? 'બટાકા' : 'Potato'}
              variety="Jyoti Medium"
              modalPrice={19}
              unit="kg"
              trend="same"
              lastUpdated="Today, 07:45 AM"
              mandiName="Agra Mandi"
              labels={{
                unitLabel: locale === 'te' ? '/కిలో' : locale === 'hi' ? '/किलो' : locale === 'gu' ? '/કિલો' : '/kg',
                modalPriceLabel: t('priceTile.modalPrice'),
                lastUpdatedPrefix: 'Updated',
                staleWarning: t('priceTile.staleWarning'),
              }}
            />

            <PriceTile
              commodityName={locale === 'te' ? 'అరటిపండు' : locale === 'hi' ? 'केला' : locale === 'gu' ? 'કેળા' : 'Banana'}
              variety="Robusta"
              modalPrice={16}
              unit="kg"
              trend="same"
              lastUpdated="Yesterday, 11:00 AM"
              isStale={true}
              mandiName="Jalgaon Mandi"
              labels={{
                unitLabel: locale === 'te' ? '/కిలో' : locale === 'hi' ? '/किलो' : locale === 'gu' ? '/કિલો' : '/kg',
                modalPriceLabel: t('priceTile.modalPrice'),
                lastUpdatedPrefix: 'Updated',
                staleWarning: t('priceTile.staleWarning'),
              }}
            />
          </div>
        </section>

        {/* SECTION 4: MandiRow Component */}
        <section className="space-y-6">
          <div className="border-b border-border pb-3">
            <h2 className="font-heading text-2xl font-bold text-ink">
              4. MandiRow Component (3 Nearest Mandis)
            </h2>
            <p className="text-sm text-muted">
              Accurate straight-line distance calculations showing nearest mandi badges, arrival tonnage, and modal prices.
            </p>
          </div>

          <div className="space-y-3">
            <MandiRow
              mandiName="Madanapalle Mandi"
              district="Annamayya District, Andhra Pradesh"
              distanceKm={8.4}
              modalPrice={28}
              priceUnit="kg"
              arrivalDate="Today, 13 Oct"
              arrivalQtyQuintal={420}
              isNearest={true}
              onClick={() => alert('Selected Madanapalle Mandi')}
              labels={{
                distanceSuffix: locale === 'te' ? 'కి.మీ దూరం' : locale === 'hi' ? 'किमी दूर' : locale === 'gu' ? 'કિમી દૂર' : 'km away',
                nearestBadge: '1st Nearest',
                unitLabel: locale === 'te' ? '/కిలో' : locale === 'hi' ? '/किलो' : locale === 'gu' ? '/કિલો' : '/kg',
              }}
            />

            <MandiRow
              mandiName="Punganur Mandi"
              district="Chittoor District, Andhra Pradesh"
              distanceKm={22.1}
              modalPrice={26}
              priceUnit="kg"
              arrivalDate="Today, 13 Oct"
              arrivalQtyQuintal={180}
              onClick={() => alert('Selected Punganur Mandi')}
              labels={{
                distanceSuffix: locale === 'te' ? 'కి.మీ దూరం' : locale === 'hi' ? 'किमी दूर' : locale === 'gu' ? 'કિમી દૂર' : 'km away',
                nearestBadge: '2nd Nearest',
                unitLabel: locale === 'te' ? '/కిలో' : locale === 'hi' ? '/किलो' : locale === 'gu' ? '/કિલો' : '/kg',
              }}
            />

            <MandiRow
              mandiName="Kolar Mandi"
              district="Kolar District, Karnataka"
              distanceKm={48.6}
              modalPrice={27}
              priceUnit="kg"
              arrivalDate="Today, 13 Oct"
              arrivalQtyQuintal={650}
              onClick={() => alert('Selected Kolar Mandi')}
              labels={{
                distanceSuffix: locale === 'te' ? 'కి.మీ దూరం' : locale === 'hi' ? 'किमी दूर' : locale === 'gu' ? 'કિમી દૂર' : 'km away',
                nearestBadge: '3rd Nearest',
                unitLabel: locale === 'te' ? '/కిలో' : locale === 'hi' ? '/किलो' : locale === 'gu' ? '/કિલો' : '/kg',
              }}
            />
          </div>
        </section>

        {/* SECTION 5: VoiceButton Component */}
        <section className="space-y-6">
          <div className="border-b border-border pb-3">
            <h2 className="font-heading text-2xl font-bold text-ink">
              5. VoiceButton Component (Voice-First Engine)
            </h2>
            <p className="text-sm text-muted">
              Interactive voice action with concentric pulsing animations for low-literacy users. Tap to toggle states.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 bg-white p-8 rounded-2xl border border-border">
            <div className="flex flex-col items-center">
              <span className="text-xs font-bold text-muted mb-4 uppercase">Idle State</span>
              <VoiceButton
                state="idle"
                label={t('voice.speak')}
                sublabel={t('voice.prompt')}
              />
            </div>

            <div className="flex flex-col items-center">
              <span className="text-xs font-bold text-danger mb-4 uppercase">Listening State (Pulsing)</span>
              <VoiceButton
                state="listening"
                label={t('voice.listening')}
                sublabel="Microphone active"
              />
            </div>

            <div className="flex flex-col items-center">
              <span className="text-xs font-bold text-muted mb-4 uppercase">Interactive Live Button</span>
              <VoiceButton
                state={voiceState}
                onClick={toggleVoice}
                label={voiceState === 'idle' ? 'Tap to Test Voice' : voiceState === 'listening' ? 'Listening...' : 'Processing audio...'}
                sublabel="Tap to cycle states (Idle -> Listen -> Process)"
              />
            </div>
          </div>
        </section>

        {/* SECTION 6: Chip Component */}
        <section className="space-y-6">
          <div className="border-b border-border pb-3">
            <h2 className="font-heading text-2xl font-bold text-ink">
              6. Chip Component
            </h2>
            <p className="text-sm text-muted">
              Filter chips with touch target compliance (&ge; 44px when clickable).
            </p>
          </div>

          <div className="flex flex-wrap gap-3 bg-white p-6 rounded-2xl border border-border items-center">
            {['all', 'tomato', 'onion', 'potato', 'banana'].map((cropKey) => {
              const labels: Record<string, string> = {
                all: 'All Crops',
                tomato: locale === 'te' ? 'టమాటా' : locale === 'hi' ? 'टमाटर' : locale === 'gu' ? 'ટામેટા' : 'Tomato',
                onion: locale === 'te' ? 'ఉల్లిపాయ' : locale === 'hi' ? 'प्याज' : locale === 'gu' ? 'ડુંગળી' : 'Onion',
                potato: locale === 'te' ? 'బంగాళాదుంప' : locale === 'hi' ? 'आलू' : locale === 'gu' ? 'બટાકા' : 'Potato',
                banana: locale === 'te' ? 'అరటిపండు' : locale === 'hi' ? 'केला' : locale === 'gu' ? 'કેળા' : 'Banana',
              };
              return (
                <Chip
                  key={cropKey}
                  isClickable
                  selected={selectedChip === cropKey}
                  onClick={() => setSelectedChip(cropKey)}
                >
                  {labels[cropKey]}
                </Chip>
              );
            })}

            <div className="w-full my-2 border-t border-border" />

            <Chip variant="primary">Verified Buyer</Chip>
            <Chip variant="accent">3 Available Drivers</Chip>
            <Chip variant="danger">High Volatility</Chip>
            <Chip variant="info">Agmarknet Verified</Chip>
          </div>
        </section>

        {/* SECTION 7: EmptyState Component */}
        <section className="space-y-6">
          <div className="border-b border-border pb-3">
            <h2 className="font-heading text-2xl font-bold text-ink">
              7. EmptyState Component
            </h2>
            <p className="text-sm text-muted">
              Gracefully handles missing daily mandi reports or empty search results without blaming users.
            </p>
          </div>

          <EmptyState
            title={t('emptyState.noPricesTitle')}
            description={t('emptyState.noPricesDesc')}
            actionLabel={t('emptyState.actionRetry')}
            onAction={() => alert('Refreshing latest mandi arrivals...')}
          />
        </section>

        {/* SECTION 8: Toast Notifications */}
        <section className="space-y-6">
          <div className="border-b border-border pb-3">
            <h2 className="font-heading text-2xl font-bold text-ink">
              8. Toast Notifications (WCAG AA Compliant)
            </h2>
            <p className="text-sm text-muted">
              Accessible alert announcements with 44px dismiss touch targets.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {showToasts.success && (
              <Toast
                type="success"
                title={t('toasts.successTitle')}
                message="Farmer produce listing submitted with fresh photo verification."
                onDismiss={() => setShowToasts((s) => ({ ...s, success: false }))}
              />
            )}

            {showToasts.warning && (
              <Toast
                type="warning"
                title={t('toasts.warningTitle')}
                message="Mandi arrival report is 26 hours old. Showing last reported prices."
                onDismiss={() => setShowToasts((s) => ({ ...s, warning: false }))}
              />
            )}

            {showToasts.error && (
              <Toast
                type="error"
                title={t('toasts.errorTitle')}
                message="Driver OTP mismatch. Please re-enter the 4-digit code provided by farmer."
                onDismiss={() => setShowToasts((s) => ({ ...s, error: false }))}
              />
            )}

            {showToasts.info && (
              <Toast
                type="info"
                title={t('toasts.infoTitle')}
                message="Masked call routing initialized. Direct numbers will not be exposed."
                onDismiss={() => setShowToasts((s) => ({ ...s, info: false }))}
              />
            )}
          </div>
        </section>

        {/* SECTION 9: WCAG AA Accessibility Contrast Checklist */}
        <section className="space-y-6">
          <div className="border-b border-border pb-3">
            <h2 className="font-heading text-2xl font-bold text-ink">
              9. WCAG AA Contrast Proof & Verification
            </h2>
            <p className="text-sm text-muted">
              Mathematical proof of contrast ratios validated across every token pairing.
            </p>
          </div>

          <Card className="p-6 overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-border text-xs uppercase text-muted font-bold">
                  <th className="py-3 px-4">Color Pairing</th>
                  <th className="py-3 px-4">Role</th>
                  <th className="py-3 px-4">Calculated Ratio</th>
                  <th className="py-3 px-4">Requirement</th>
                  <th className="py-3 px-4">Result</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                <tr>
                  <td className="py-3 px-4 font-semibold text-ink">Ink (#1B1B18) on Cream (#FBFAF4)</td>
                  <td className="py-3 px-4 text-muted">Primary Body Text</td>
                  <td className="py-3 px-4 font-mono font-bold text-deep-leaf">16.51:1</td>
                  <td className="py-3 px-4 text-muted">&ge; 4.5:1</td>
                  <td className="py-3 px-4"><span className="px-2 py-0.5 rounded bg-deep-leaf/10 text-deep-leaf font-bold text-xs">PASS (AAA)</span></td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-semibold text-ink">Muted (#4A4A42) on Cream (#FBFAF4)</td>
                  <td className="py-3 px-4 text-muted">Secondary Text / Timestamps</td>
                  <td className="py-3 px-4 font-mono font-bold text-deep-leaf">8.55:1</td>
                  <td className="py-3 px-4 text-muted">&ge; 4.5:1</td>
                  <td className="py-3 px-4"><span className="px-2 py-0.5 rounded bg-deep-leaf/10 text-deep-leaf font-bold text-xs">PASS (AAA)</span></td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-semibold text-ink">Deep Leaf (#1F6B3A) on Cream (#FBFAF4)</td>
                  <td className="py-3 px-4 text-muted">Brand Accents & Links</td>
                  <td className="py-3 px-4 font-mono font-bold text-deep-leaf">6.23:1</td>
                  <td className="py-3 px-4 text-muted">&ge; 4.5:1</td>
                  <td className="py-3 px-4"><span className="px-2 py-0.5 rounded bg-deep-leaf/10 text-deep-leaf font-bold text-xs">PASS (AA)</span></td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-semibold text-ink">White (#FFFFFF) on Deep Leaf (#1F6B3A)</td>
                  <td className="py-3 px-4 text-muted">Primary Button Text</td>
                  <td className="py-3 px-4 font-mono font-bold text-deep-leaf">6.52:1</td>
                  <td className="py-3 px-4 text-muted">&ge; 4.5:1</td>
                  <td className="py-3 px-4"><span className="px-2 py-0.5 rounded bg-deep-leaf/10 text-deep-leaf font-bold text-xs">PASS (AA)</span></td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-semibold text-ink">Ink (#1B1B18) on Harvest Gold (#F6C343)</td>
                  <td className="py-3 px-4 text-muted">Accent Button Text</td>
                  <td className="py-3 px-4 font-mono font-bold text-deep-leaf">10.53:1</td>
                  <td className="py-3 px-4 text-muted">&ge; 4.5:1</td>
                  <td className="py-3 px-4"><span className="px-2 py-0.5 rounded bg-deep-leaf/10 text-deep-leaf font-bold text-xs">PASS (AAA)</span></td>
                </tr>
                <tr>
                  <td className="py-3 px-4 font-semibold text-ink">Amber (#C77700) on Cream (#FBFAF4)</td>
                  <td className="py-3 px-4 text-muted">Wordmark Large Text (&quot;G&quot; &amp; &quot;C&quot;)</td>
                  <td className="py-3 px-4 font-mono font-bold text-deep-leaf">3.31:1</td>
                  <td className="py-3 px-4 text-muted">&ge; 3.0:1 (Large/Bold)</td>
                  <td className="py-3 px-4"><span className="px-2 py-0.5 rounded bg-deep-leaf/10 text-deep-leaf font-bold text-xs">PASS (AA Large)</span></td>
                </tr>
              </tbody>
            </table>
          </Card>
        </section>
      </main>
      </RoleGuard>

      <footer className="border-t border-border bg-white py-6 text-center text-xs text-muted">
        GrowCircle Design System &bull; Phase 0 Foundation Complete
      </footer>
    </div>
  );
}
