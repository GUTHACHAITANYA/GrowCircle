import { setRequestLocale } from 'next-intl/server';
import { locales, Locale } from '@/i18n';
import { ShowcaseClient } from './ShowcaseClient';

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default function ShowcasePage({
  params: { locale },
}: {
  params: { locale: string };
}) {
  setRequestLocale(locale);

  return <ShowcaseClient />;
}
