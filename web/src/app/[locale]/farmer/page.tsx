import { setRequestLocale } from 'next-intl/server';
import { locales, Locale } from '@/i18n';
import { FarmerClient } from './FarmerClient';

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default function FarmerPage({
  params: { locale },
}: {
  params: { locale: string };
}) {
  setRequestLocale(locale);

  return <FarmerClient />;
}
