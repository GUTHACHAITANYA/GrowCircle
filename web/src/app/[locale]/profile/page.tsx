import { setRequestLocale } from 'next-intl/server';
import { locales, Locale } from '@/i18n';
import { ProfileClient } from './ProfileClient';

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default function ProfilePage({
  params: { locale },
}: {
  params: { locale: string };
}) {
  setRequestLocale(locale);

  return <ProfileClient />;
}
