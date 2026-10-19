'use client';

import React from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { useRouter, usePathname } from 'next/navigation';
import { Header, SupportedLocale } from '@/components/ui';
import { FileText, CheckCircle2, AlertTriangle, Truck, Scale } from 'lucide-react';

export function TermsClient() {
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
    <div className="min-h-screen bg-cream flex flex-col">
      <Header
        currentLocale={locale}
        onSelectLocale={handleLocaleChange}
        brandName={t('brand.name')}
      />

      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8">
        <div className="bg-white rounded-3xl border border-border p-6 sm:p-8 shadow-sm space-y-6">
          <div className="flex items-center gap-3 pb-4 border-b border-border">
            <div className="p-3 bg-deep-leaf/10 text-deep-leaf rounded-2xl">
              <FileText className="w-8 h-8" />
            </div>
            <div>
              <span className="text-xs font-bold text-deep-leaf uppercase tracking-wider">
                Fair Agricultural Trade &bull; Version 1.0
              </span>
              <h1 className="font-heading text-3xl font-extrabold text-ink">
                GrowCircle Terms of Use
              </h1>
            </div>
          </div>

          <div className="prose prose-slate max-w-none text-ink text-sm sm:text-base leading-relaxed space-y-6">
            <div className="bg-cream/60 p-4 rounded-2xl border border-border">
              <p className="font-bold text-ink mb-1">Zero Middlemen &bull; Zero Financial Custody:</p>
              <p className="text-muted text-sm">
                GrowCircle is a technology platform connecting farmers, buyers, and transporters. We do not charge commissions, hold funds in escrow, or intermediate payments. Commercial terms and payments are direct between parties.
              </p>
            </div>

            <section className="space-y-3">
              <h2 className="font-heading text-xl font-bold text-ink flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-deep-leaf" />
                1. Farmer Guidelines
              </h2>
              <ul className="list-disc pl-5 space-y-2 text-muted text-sm">
                <li><strong>Live In-App Photos:</strong> All listings require fresh live camera photos (whole lot, close-up, opened crate). Gallery uploads or recycled stock photos are strictly disallowed.</li>
                <li><strong>Honest Grading:</strong> Produce must be graded accurately as Grade A, B, or C according to visual standard guides.</li>
                <li><strong>Committed Harvest Date:</strong> Farmers commit to having the agreed lot crated and ready by the scheduled pickup date.</li>
              </ul>
            </section>

            <section className="space-y-3">
              <h2 className="font-heading text-xl font-bold text-ink flex items-center gap-2">
                <Scale className="w-5 h-5 text-deep-leaf" />
                2. Institutional Buyer Guidelines
              </h2>
              <ul className="list-disc pl-5 space-y-2 text-muted text-sm">
                <li><strong>Verified Registration:</strong> Hostels, colleges, hotels, and retail vendors must complete administrative verification (GSTIN or shop licence) before accessing farm listings.</li>
                <li><strong>OTP Release at Delivery:</strong> The 6-digit Delivery OTP must be released to the transporter upon physical inspection of crates at delivery.</li>
                <li><strong>Damage Photo Evidence:</strong> If transit damage occurs, buyers must capture clear photo proof at the delivery gate before raising an arbitration dispute.</li>
              </ul>
            </section>

            <section className="space-y-3">
              <h2 className="font-heading text-xl font-bold text-ink flex items-center gap-2">
                <Truck className="w-5 h-5 text-deep-leaf" />
                3. Transporter Guidelines
              </h2>
              <ul className="list-disc pl-5 space-y-2 text-muted text-sm">
                <li><strong>Document Compliance:</strong> Drivers must maintain valid DL, RC, Insurance, and Fitness Certificate. Vehicles with expired paperwork are automatically hidden from dispatch.</li>
                <li><strong>Indicative Guide Rates:</strong> Freight rates displayed are estimates calculated by distance and vehicle type. Final charges are agreed directly between driver and counterparty.</li>
              </ul>
            </section>

            <section className="space-y-3 pt-4 border-t border-border">
              <h2 className="font-heading text-xl font-bold text-ink flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-amber" />
                4. Mandi Price Disclaimer &amp; Jurisdiction
              </h2>
              <p className="text-muted text-sm">
                Mandi prices are aggregated directly from public Agmarknet auction records (data.gov.in) and provided for market guidance only. Governing law is the laws of India, subject to the jurisdiction of competent courts in Guntur, Andhra Pradesh.
              </p>
            </section>
          </div>
        </div>
      </main>

      <footer className="border-t border-border bg-white py-6 px-4 text-center text-xs text-muted">
        GrowCircle &bull; DPDP Act 2023 Aligned &bull; Farm to everyone, full circle
      </footer>
    </div>
  );
}
