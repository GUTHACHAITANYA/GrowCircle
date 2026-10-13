import { setRequestLocale } from 'next-intl/server';
import { locales, Locale } from '@/i18n';
import { PricesClient } from './PricesClient';

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default function PricesPage({
  params: { locale },
}: {
  params: { locale: string };
}) {
  setRequestLocale(locale);

  return <PricesClient />;
}
