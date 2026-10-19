import { setRequestLocale } from 'next-intl/server';
import { locales } from '@/i18n';
import { AdminClient } from './AdminClient';

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default function AdminPage({
  params: { locale },
}: {
  params: { locale: string };
}) {
  setRequestLocale(locale);

  return <AdminClient />;
}
