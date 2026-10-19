import { setRequestLocale } from 'next-intl/server';
import { locales } from '@/i18n';
import { DashboardClient } from './DashboardClient';

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default function DashboardPage({
  params: { locale },
}: {
  params: { locale: string };
}) {
  setRequestLocale(locale);

  return <DashboardClient />;
}
