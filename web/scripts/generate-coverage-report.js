/**
 * Per-Language Coverage Report Generator (R5 Acceptance Criterion).
 * Produces structured JSON and Markdown coverage report comparing all 23 languages against en.json.
 * Lists:
 * - Total keys, translated keys, coverage percentage
 * - ui_ready, voice_stt_ready, voice_tts_ready, reviewed_by_native_speaker
 * - Untranslated strings that fall back to Hindi or English per string
 */

const fs = require('fs');
const path = require('path');

const MESSAGES_DIR = path.join(__dirname, '..', 'messages');
const REVIEWS_DIR = path.join(MESSAGES_DIR, 'reviews');
const REPORTS_DIR = path.join(__dirname, '..', 'reports');

if (!fs.existsSync(REPORTS_DIR)) {
  fs.mkdirSync(REPORTS_DIR, { recursive: true });
}

// Flatten nested object keys
function flattenKeys(obj, prefix = '') {
  let keys = {};
  for (const k of Object.keys(obj)) {
    const fullKey = prefix ? `${prefix}.${k}` : k;
    if (obj[k] && typeof obj[k] === 'object' && !Array.isArray(obj[k])) {
      Object.assign(keys, flattenKeys(obj[k], fullKey));
    } else {
      keys[fullKey] = obj[k];
    }
  }
  return keys;
}

const enMessages = JSON.parse(fs.readFileSync(path.join(MESSAGES_DIR, 'en.json'), 'utf8'));
const enFlat = flattenKeys(enMessages);
const totalEnKeys = Object.keys(enFlat).length;

const LANGUAGES = [
  { code: 'en', native: 'English', english: 'English', fallback: 'en', rtl: false },
  { code: 'te', native: 'తెలుగు', english: 'Telugu', fallback: 'en', rtl: false },
  { code: 'hi', native: 'हिंदी', english: 'Hindi', fallback: 'en', rtl: false },
  { code: 'gu', native: 'ગુજરાતી', english: 'Gujarati', fallback: 'hi', rtl: false },
  { code: 'as', native: 'অসমীয়া', english: 'Assamese', fallback: 'hi', rtl: false },
  { code: 'bn', native: 'বাংলা', english: 'Bengali', fallback: 'hi', rtl: false },
  { code: 'brx', native: 'बड़ो', english: 'Bodo', fallback: 'hi', rtl: false },
  { code: 'doi', native: 'डोगरी', english: 'Dogri', fallback: 'hi', rtl: false },
  { code: 'kn', native: 'ಕನ್ನಡ', english: 'Kannada', fallback: 'hi', rtl: false },
  { code: 'ks', native: 'کٲشُر', english: 'Kashmiri', fallback: 'hi', rtl: true },
  { code: 'kok', native: 'कोंकणी', english: 'Konkani', fallback: 'hi', rtl: false },
  { code: 'mai', native: 'मैथिली', english: 'Maithili', fallback: 'hi', rtl: false },
  { code: 'ml', native: 'മലയാളം', english: 'Malayalam', fallback: 'en', rtl: false },
  { code: 'mni', native: 'মৈতৈলোন্', english: 'Manipuri', fallback: 'hi', rtl: false },
  { code: 'mr', native: 'मराठी', english: 'Marathi', fallback: 'hi', rtl: false },
  { code: 'ne', native: 'नेपाली', english: 'Nepali', fallback: 'hi', rtl: false },
  { code: 'or', native: 'ଓଡ଼ିଆ', english: 'Odia', fallback: 'hi', rtl: false },
  { code: 'pa', native: 'ਪੰਜਾਬੀ', english: 'Punjabi', fallback: 'hi', rtl: false },
  { code: 'sa', native: 'संस्कृतम्', english: 'Sanskrit', fallback: 'hi', rtl: false },
  { code: 'sat', native: 'ᱥᱟᱱᱛᱟᱲᱤ', english: 'Santali', fallback: 'hi', rtl: false },
  { code: 'sd', native: 'سنڌي', english: 'Sindhi', fallback: 'hi', rtl: true },
  { code: 'ta', native: 'தமிழ்', english: 'Tamil', fallback: 'en', rtl: false },
  { code: 'ur', native: 'اردو', english: 'Urdu', fallback: 'hi', rtl: true },
];

console.log('=== GENERATING I18N COVERAGE REPORT ===');

const reportData = {
  generated_at: new Date().toISOString(),
  total_languages: LANGUAGES.length,
  total_base_keys: totalEnKeys,
  languages: [],
};

let mdReport = `# GrowCircle i18n & Honest Language Coverage Report\n\n`;
mdReport += `**Generated At:** ${new Date().toUTCString()}\n`;
mdReport += `**Total Supported Languages:** ${LANGUAGES.length} (22 Scheduled Indian Languages + English)\n`;
mdReport += `**Total Base Keys in English:** ${totalEnKeys}\n\n`;
mdReport += `| Code | Language | Script | UI Ready | Voice STT | Voice TTS | Native Reviewed | Coverage % | Status | Fallback |\n`;
mdReport += `| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- |\n`;

for (const lang of LANGUAGES) {
  const langFile = path.join(MESSAGES_DIR, `${lang.code}.json`);
  const reviewFile = path.join(REVIEWS_DIR, `${lang.code}.review.json`);

  let langMessages = {};
  if (fs.existsSync(langFile)) {
    langMessages = JSON.parse(fs.readFileSync(langFile, 'utf8'));
  }
  const langFlat = flattenKeys(langMessages);

  let reviewData = {};
  if (fs.existsSync(reviewFile)) {
    reviewData = JSON.parse(fs.readFileSync(reviewFile, 'utf8'));
  }

  const reviewedByNative = Boolean(reviewData.reviewed_by_native_speaker);
  const isInitialFour = ['en', 'te', 'hi', 'gu'].includes(lang.code);

  let translatedKeysCount = 0;
  let fallbackKeys = [];

  for (const [key, enVal] of Object.entries(enFlat)) {
    const val = langFlat[key];
    if (val && val !== enVal && val !== '') {
      translatedKeysCount++;
    } else if (lang.code === 'en') {
      translatedKeysCount++;
    } else {
      fallbackKeys.push({
        key,
        fallback_to: lang.fallback === 'hi' ? 'Hindi' : 'English',
        english_value: enVal,
      });
    }
  }

  const coveragePercent = Math.round((translatedKeysCount / totalEnKeys) * 100);
  const uiReady = isInitialFour;
  const voiceSttReady = isInitialFour;
  const voiceTtsReady = isInitialFour;
  const statusLabel = reviewedByNative ? 'Fully Translated & Reviewed' : 'Partly translated (First draft)';

  const langReport = {
    code: lang.code,
    name_english: lang.english,
    name_native: lang.native,
    is_rtl: lang.rtl,
    ui_ready: uiReady,
    voice_stt_ready: voiceSttReady,
    voice_tts_ready: voiceTtsReady,
    reviewed_by_native_speaker: reviewedByNative,
    total_keys: totalEnKeys,
    translated_keys: translatedKeysCount,
    fallback_keys_count: fallbackKeys.length,
    coverage_percentage: coveragePercent,
    status: statusLabel,
    fallback_per_string_to: lang.fallback === 'hi' ? 'Hindi' : 'English',
    untranslated_fallback_strings: fallbackKeys,
  };

  reportData.languages.push(langReport);

  const uiBadge = uiReady ? '✅ Yes' : '⏳ Partial';
  const sttBadge = voiceSttReady ? '✅ Yes' : '⏳ No';
  const ttsBadge = voiceTtsReady ? '✅ Yes' : '⏳ No';
  const reviewBadge = reviewedByNative ? '✅ Yes' : '⚠️ No (Machine Draft)';

  mdReport += `| \`${lang.code}\` | **${lang.native}** (${lang.english}) | ${reviewData.script || 'Indic'} | ${uiBadge} | ${sttBadge} | ${ttsBadge} | ${reviewBadge} | **${coveragePercent}%** | ${statusLabel} | ${lang.fallback.toUpperCase()} |\n`;
}

mdReport += `\n## Untranslated Strings & Fallback Mechanism\n\n`;
mdReport += `Languages with partial coverage fall back per string to **Hindi** (for Indic cognates) or **English**.\n`;
mdReport += `The table below summarizes untranslated keys that safely fall back per string:\n\n`;

for (const lang of reportData.languages) {
  if (lang.fallback_keys_count > 0) {
    mdReport += `### \`${lang.code}\` - ${lang.name_native} (${lang.name_english})\n`;
    mdReport += `- **Coverage:** ${lang.coverage_percentage}% (${lang.translated_keys}/${lang.total_keys} keys translated)\n`;
    mdReport += `- **Fallback Count:** ${lang.fallback_keys_count} strings fall back to ${lang.fallback_per_string_to}\n`;
    mdReport += `- **Sample Fallback Keys:**\n`;
    lang.untranslated_fallback_strings.slice(0, 5).forEach((item) => {
      mdReport += `  - \`${item.key}\` (falls back to ${item.fallback_to}: "${item.english_value}")\n`;
    });
    if (lang.fallback_keys_count > 5) {
      mdReport += `  - *...and ${lang.fallback_keys_count - 5} more keys.*\n`;
    }
    mdReport += `\n`;
  }
}

// Write reports
fs.writeFileSync(path.join(REPORTS_DIR, 'i18n-coverage-report.json'), JSON.stringify(reportData, null, 2), 'utf8');
fs.writeFileSync(path.join(REPORTS_DIR, 'i18n-coverage-report.md'), mdReport, 'utf8');

console.log('Successfully written:');
console.log(' - ' + path.join(REPORTS_DIR, 'i18n-coverage-report.json'));
console.log(' - ' + path.join(REPORTS_DIR, 'i18n-coverage-report.md'));
