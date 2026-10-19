import { setRequestLocale } from 'next-intl/server';
import { locales } from '@/i18n';
import { TermsClient } from './TermsClient';

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default function TermsPage({
  params: { locale },
}: {
  params: { locale: string };
}) {
  setRequestLocale(locale);

  return <TermsClient />;
}
