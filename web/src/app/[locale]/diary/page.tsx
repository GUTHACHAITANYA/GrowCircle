import { setRequestLocale } from 'next-intl/server';
import { locales, Locale } from '@/i18n';
import { DiaryClient } from './DiaryClient';

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default function DiaryPage({
  params: { locale },
}: {
  params: { locale: string };
}) {
  setRequestLocale(locale);

  return <DiaryClient />;
}
