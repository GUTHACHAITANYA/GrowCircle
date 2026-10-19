import { setRequestLocale } from 'next-intl/server';
import { locales } from '@/i18n';
import { CropPlanClient } from './CropPlanClient';

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default function CropPlanPage({
  params: { locale },
}: {
  params: { locale: string };
}) {
  setRequestLocale(locale);

  return <CropPlanClient />;
}
