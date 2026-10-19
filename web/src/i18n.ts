import { getRequestConfig } from 'next-intl/server';
import { ALL_LANGUAGES, SupportedLocale, getLanguageInfo } from './lib/languages';

export const locales = [
  'en', 'te', 'hi', 'gu', 'as', 'bn', 'brx', 'doi', 'kn', 'ks',
  'kok', 'mai', 'ml', 'mni', 'mr', 'ne', 'or', 'pa', 'sa', 'sat',
  'sd', 'ta', 'ur'
] as const;

export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = 'en';

function deepMerge(...objects: any[]) {
  const result: any = {};
  for (const obj of objects) {
    if (!obj) continue;
    for (const key of Object.keys(obj)) {
      if (
        obj[key] &&
        typeof obj[key] === 'object' &&
        !Array.isArray(obj[key])
      ) {
        result[key] = deepMerge(result[key] || {}, obj[key]);
      } else if (obj[key] !== undefined && obj[key] !== null && obj[key] !== '') {
        result[key] = obj[key];
      }
    }
  }
  return result;
}

export default getRequestConfig(async ({ requestLocale }) => {
  let locale = await requestLocale;
  if (!locale || !locales.includes(locale as Locale)) {
    locale = defaultLocale;
  }

  const langInfo = getLanguageInfo(locale);
  const fallbackLocale = langInfo.fallbackLocale || 'en';

  // Load English base messages
  const enMessages = (await import('../messages/en.json')).default;

  // Load intermediate fallback messages if different (e.g. Hindi for Indic cognates)
  let fallbackMessages = {};
  if (fallbackLocale !== 'en') {
    try {
      fallbackMessages = (await import(`../messages/${fallbackLocale}.json`)).default;
    } catch {
      fallbackMessages = {};
    }
  }

  // Load target locale messages
  let localeMessages = {};
  try {
    localeMessages = (await import(`../messages/${locale}.json`)).default;
  } catch {
    localeMessages = {};
  }

  // Per-string fallback: English -> Intermediate Fallback (Hindi/English) -> Target Locale
  const mergedMessages = deepMerge(enMessages, fallbackMessages, localeMessages);

  return {
    locale,
    messages: mergedMessages,
  };
});
