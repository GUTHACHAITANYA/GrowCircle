import { setRequestLocale } from 'next-intl/server';
import { locales } from '@/i18n';
import { PrivacyClient } from './PrivacyClient';

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default function PrivacyPage({
  params: { locale },
}: {
  params: { locale: string };
}) {
  setRequestLocale(locale);

  return <PrivacyClient />;
}
