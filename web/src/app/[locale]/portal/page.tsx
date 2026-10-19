import { setRequestLocale } from 'next-intl/server';
import { locales } from '@/i18n';
import { PortalClient } from './PortalClient';

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default function PortalPage({
  params: { locale },
}: {
  params: { locale: string };
}) {
  setRequestLocale(locale);

  return <PortalClient />;
}
