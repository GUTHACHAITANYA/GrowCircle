import { setRequestLocale } from 'next-intl/server';
import { locales, Locale } from '@/i18n';
import { HomePageClient } from './HomePageClient';

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default function HomePage({
  params: { locale },
}: {
  params: { locale: string };
}) {
  setRequestLocale(locale);

  return <HomePageClient />;
}
