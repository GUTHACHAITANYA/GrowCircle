import type { Metadata, Viewport } from 'next';
import { NextIntlClientProvider } from 'next-intl';
import { getMessages, setRequestLocale } from 'next-intl/server';
import { notFound } from 'next/navigation';
import { locales, Locale } from '@/i18n';
import '../globals.css';

export const viewport: Viewport = {
  themeColor: '#1F6B3A',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
};

export const metadata: Metadata = {
  metadataBase: new URL('https://growcircle.app'),
  title: 'GrowCircle | Farm to everyone, full circle',
  description:
    'GrowCircle is a voice-first platform connecting farmers, buyers, drivers, and consumers in India with real-time mandi prices and verified logistics.',
  manifest: '/manifest.json',
  icons: {
    icon: [
      { url: '/icons/favicon.svg', type: 'image/svg+xml' },
      { url: '/icons/favicon.ico', sizes: 'any' },
    ],
    apple: [{ url: '/icons/icon-192.png' }],
  },
  openGraph: {
    title: 'GrowCircle - Farm to everyone, full circle',
    description:
      'Voice-first fruit-and-vegetable ecosystem in India connecting farmers, buyers, drivers, and everyday consumers.',
    images: [{ url: '/icons/og-image.png', width: 1200, height: 630 }],
  },
};

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params: { locale },
}: {
  children: React.ReactNode;
  params: { locale: string };
}) {
  if (!locales.includes(locale as Locale)) {
    notFound();
  }

  // Enable static rendering
  setRequestLocale(locale);

  const messages = await getMessages();

  return (
    <html lang={locale}>
      <body className="min-h-screen bg-cream text-ink antialiased selection:bg-harvest-gold selection:text-ink">
        <NextIntlClientProvider locale={locale} messages={messages}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
