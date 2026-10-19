'use client';

import React from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { useRouter, usePathname } from 'next/navigation';
import { Header, SupportedLocale } from '@/components/ui';
import { ShieldCheck, Lock, PhoneCall, Download, Trash2, Mail, MapPin } from 'lucide-react';

export function PrivacyClient() {
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
              <ShieldCheck className="w-8 h-8" />
            </div>
            <div>
              <span className="text-xs font-bold text-deep-leaf uppercase tracking-wider">
                DPDP Act 2023 Aligned &bull; Version 1.0
              </span>
              <h1 className="font-heading text-3xl font-extrabold text-ink">
                GrowCircle Privacy Policy
              </h1>
            </div>
          </div>

          <div className="prose prose-slate max-w-none text-ink text-sm sm:text-base leading-relaxed space-y-6">
            <div className="bg-cream/60 p-4 rounded-2xl border border-border">
              <p className="font-bold text-ink mb-1">Our Simple Promise to Every User:</p>
              <p className="text-muted text-sm">
                GrowCircle was built to connect farmers, buyers, drivers, and consumers directly. Your data is yours. We do not sell your personal numbers or records to advertisers or third parties.
              </p>
            </div>

            <section className="space-y-3">
              <h2 className="font-heading text-xl font-bold text-ink flex items-center gap-2">
                <Lock className="w-5 h-5 text-deep-leaf" />
                1. What Information We Collect and Why
              </h2>
              <ul className="list-disc pl-5 space-y-2 text-muted text-sm">
                <li><strong>Phone Number:</strong> Used solely for OTP authentication, daily mandi price drop alerts you opt into, and connecting you to verified counterparties.</li>
                <li><strong>District &amp; Preferred Language:</strong> Used to display the 3 nearest mandis and speak or text in Telugu, Hindi, Gujarati, or English.</li>
                <li><strong>Farm Diary Records:</strong> Stored securely and privately to calculate your break-even price and profit/loss per acre.</li>
                <li><strong>Buyer Proof Documents:</strong> GST/trade licence uploads are encrypted using AES-256 and only decrypted in-memory for authorized admin verification.</li>
              </ul>
            </section>

            <section className="space-y-3">
              <h2 className="font-heading text-xl font-bold text-ink flex items-center gap-2">
                <PhoneCall className="w-5 h-5 text-deep-leaf" />
                2. Privacy Safeguards
              </h2>
              <ul className="list-disc pl-5 space-y-2 text-muted text-sm">
                <li><strong>Masked Phone Calls:</strong> When negotiating, a virtual telephony bridge protects both farmer and buyer numbers until a deal is finalized.</li>
                <li><strong>No Continuous GPS Tracking:</strong> Driver location is only verified at pickup and delivery gates. Live tracking ceases immediately once delivery OTP is entered.</li>
                <li><strong>No Financial Custody:</strong> GrowCircle never holds payments or bank credentials; all transactions occur directly between parties.</li>
              </ul>
            </section>

            <section className="space-y-3">
              <h2 className="font-heading text-xl font-bold text-ink flex items-center gap-2">
                <Download className="w-5 h-5 text-deep-leaf" />
                3. Your Rights Under DPDP Act 2023
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="p-4 bg-cream rounded-xl border border-border">
                  <h4 className="font-bold text-ink text-sm flex items-center gap-1.5 mb-1">
                    <Download className="w-4 h-4 text-deep-leaf" /> Right to Data Portability
                  </h4>
                  <p className="text-xs text-muted">
                    Download all your listings, farm diary expenses, and trip histories anytime via CSV/JSON exports with zero vendor lock-in.
                  </p>
                </div>
                <div className="p-4 bg-cream rounded-xl border border-border">
                  <h4 className="font-bold text-ink text-sm flex items-center gap-1.5 mb-1">
                    <Trash2 className="w-4 h-4 text-danger" /> Right to Erasure
                  </h4>
                  <p className="text-xs text-muted">
                    Request complete account deletion anytime. Your phone number is permanently hashed and identifying records are wiped.
                  </p>
                </div>
              </div>
            </section>

            <section className="space-y-3 pt-4 border-t border-border">
              <h2 className="font-heading text-xl font-bold text-ink flex items-center gap-2">
                <Mail className="w-5 h-5 text-deep-leaf" />
                4. Statutory Grievance Redressal Officer
              </h2>
              <div className="bg-deep-leaf/5 p-4 sm:p-5 rounded-2xl border border-deep-leaf/20 text-xs sm:text-sm space-y-2">
                <div className="flex items-center justify-between font-bold text-ink">
                  <span>Name: Smt. Radhika Varma</span>
                  <span className="text-xs bg-deep-leaf text-white px-2 py-0.5 rounded-full">DPO &amp; Grievance Officer</span>
                </div>
                <div className="text-muted">
                  Email: <strong>grievance@growcircle.in</strong> &bull; Helpline: <strong>+91 863 294 5678</strong>
                </div>
                <div className="text-muted flex items-start gap-1">
                  <MapPin className="w-4 h-4 text-deep-leaf flex-shrink-0 mt-0.5" />
                  <span>4th Floor, Agriculture Innovation Hub, Ring Road, Guntur, Andhra Pradesh - 522002</span>
                </div>
                <p className="text-[11px] text-muted pt-1">
                  Statutory SLA: Acknowledgment within <strong>72 hours</strong>, resolution within <strong>30 days</strong>. Escalation: Data Protection Board of India.
                </p>
              </div>
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
