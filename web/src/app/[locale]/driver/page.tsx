import { setRequestLocale } from 'next-intl/server';
import { locales, Locale } from '@/i18n';
import { DriverClient } from './DriverClient';

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default function DriverPage({
  params: { locale },
}: {
  params: { locale: string };
}) {
  setRequestLocale(locale);

  return <DriverClient />;
}
