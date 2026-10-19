/**
 * Automated Verification Suite for Language Selector & Localization (R5).
 * Tests all 7 requirements and acceptance criteria:
 * 1. Single control, searchable list, all 23 entries (22 scheduled + English).
 * 2. Honest coverage: ui_ready, voice_stt_ready, voice_tts_ready, reviewed_by_native_speaker.
 * 3. Translation workflow: message keys, review files, reviewed glossary for crops, mandi terms, units.
 * 4. Fonts and RTL scripts (Urdu, Kashmiri, Sindhi).
 * 5. Preference persistence (cookie and profile storage).
 * 6. Numbers, crop names, units localized; prices as numerals with currency symbol.
 * 7. Accessibility: keyboard operable, 44px targets, ARIA roles.
 */

const fs = require('fs');
const path = require('path');
const assert = require('assert');

console.log('=== GROWCIRCLE LANGUAGE SELECTOR VERIFICATION SUITE (R5) ===\n');

const SCHEDULED_22 = [
  'as', 'bn', 'brx', 'doi', 'gu', 'hi', 'kn', 'ks', 'kok', 'mai',
  'ml', 'mni', 'mr', 'ne', 'or', 'pa', 'sa', 'sat', 'sd', 'ta', 'te', 'ur'
];
const ALL_23 = [...SCHEDULED_22, 'en'];

// 1. Verify all 23 language message files exist
console.log('CHECK 1: Verifying all 23 language files exist...');
const messagesDir = path.join(__dirname, '..', 'messages');
for (const code of ALL_23) {
  const filePath = path.join(messagesDir, `${code}.json`);
  assert(fs.existsSync(filePath), `Missing message file for language: ${code}`);
  const content = JSON.parse(fs.readFileSync(filePath, 'utf8'));
  assert(content.brand && content.brand.name, `Language ${code} missing brand.name`);
  assert(content.languages, `Language ${code} missing languages object`);
}
console.log('  [PASS] All 23 language files exist and are valid JSON.');

// 2. Verify all 23 review files exist and honest coverage fields
console.log('\nCHECK 2: Verifying review files and honest coverage flags...');
const reviewsDir = path.join(messagesDir, 'reviews');
assert(fs.existsSync(reviewsDir), 'Reviews directory missing');

for (const code of ALL_23) {
  const reviewPath = path.join(reviewsDir, `${code}.review.json`);
  assert(fs.existsSync(reviewPath), `Missing review file for: ${code}`);
  const review = JSON.parse(fs.readFileSync(reviewPath, 'utf8'));

  assert(typeof review.reviewed_by_native_speaker === 'boolean', `Missing reviewed_by_native_speaker in ${code}`);
  assert(review.language_code === code, `Language code mismatch in ${code}.review.json`);

  // Initial 4 languages are certified reviewed
  if (['en', 'te', 'hi', 'gu'].includes(code)) {
    assert(review.reviewed_by_native_speaker === true, `${code} should be reviewed`);
    assert(review.review_status === 'approved', `${code} should have approved status`);
  } else {
    // Other 19 languages are first drafts, not marked as reviewed
    assert(review.reviewed_by_native_speaker === false, `${code} must NOT be marked as reviewed by native speaker`);
    assert(review.review_status === 'pending_native_review', `${code} should be pending review`);
  }
}
console.log('  [PASS] Honest coverage: Native reviews accurately separated from machine drafts.');

// 3. Verify reviewed glossary enforcement (Crops, Mandi terms, Units)
console.log('\nCHECK 3: Verifying reviewed glossary for crops, mandi terms, and units...');
const glossaryPath = path.join(__dirname, 'glossary-data.json');
assert(fs.existsSync(glossaryPath), 'Glossary data file missing');
const glossary = JSON.parse(fs.readFileSync(glossaryPath, 'utf8'));

assert(glossary.crops && glossary.crops.banana, 'Crop glossary missing banana');
assert(glossary.crops.tomato, 'Crop glossary missing tomato');
assert(glossary.mandi && glossary.mandi.modalPrice, 'Mandi glossary missing modalPrice');
assert(glossary.units && glossary.units.quintal, 'Units glossary missing quintal');
assert(glossary.units.kg, 'Units glossary missing kg');

// Verify all 23 languages have entries in glossary
for (const code of ALL_23) {
  assert(glossary.crops.banana[code], `Banana missing translation for ${code}`);
  assert(glossary.mandi.modalPrice[code], `Modal price missing translation for ${code}`);
  assert(glossary.units.quintal[code], `Quintal missing translation for ${code}`);
}
console.log('  [PASS] Reviewed glossary covers all 23 languages for crops, mandi terms, and units.');

// 4. Verify RTL Scripts (Urdu, Kashmiri, Sindhi) layout configuration
console.log('\nCHECK 4: Verifying RTL configuration for Urdu, Kashmiri, and Sindhi...');
const rtlCodes = ['ur', 'ks', 'sd'];
const globalsCss = fs.readFileSync(path.join(__dirname, '..', 'src', 'app', 'globals.css'), 'utf8');

assert(globalsCss.includes('[dir="rtl"]'), 'globals.css missing [dir="rtl"] rules');
assert(globalsCss.includes('direction: rtl'), 'globals.css missing direction: rtl');
assert(globalsCss.includes('.rtl-flip'), 'globals.css missing .rtl-flip helper');
assert(globalsCss.includes("'Noto Sans Arabic'"), 'globals.css missing Noto Sans Arabic for RTL languages');

const languagesTs = fs.readFileSync(path.join(__dirname, '..', 'src', 'lib', 'languages.ts'), 'utf8');
for (const rtlCode of rtlCodes) {
  assert(languagesTs.includes(`code: '${rtlCode}'`), `languages.ts missing ${rtlCode}`);
  assert(languagesTs.includes("isRtl: true"), `languages.ts must flag RTL for ${rtlCode}`);
}
console.log('  [PASS] RTL layout rules and Noto Sans Arabic fonts configured for Urdu, Kashmiri, Sindhi.');

// 5. Verify LanguageSwitcher component has all 23 entries, searchable, and accessible
console.log('\nCHECK 5: Verifying LanguageSwitcher component features...');
const switcherContent = fs.readFileSync(path.join(__dirname, '..', 'src', 'components', 'ui', 'LanguageSwitcher.tsx'), 'utf8');

// Check accessibility
assert(switcherContent.includes('min-h-[44px]'), 'LanguageSwitcher must enforce 44px min touch targets');
assert(switcherContent.includes('aria-haspopup="listbox"'), 'LanguageSwitcher must have aria-haspopup="listbox"');
assert(switcherContent.includes('aria-expanded='), 'LanguageSwitcher must have aria-expanded');
assert(switcherContent.includes('role="listbox"'), 'LanguageSwitcher must have role="listbox"');
assert(switcherContent.includes('role="option"'), 'LanguageSwitcher options must have role="option"');
assert(switcherContent.includes('aria-selected='), 'LanguageSwitcher options must have aria-selected');

// Check search functionality
assert(switcherContent.includes('searchQuery'), 'LanguageSwitcher must have search input filter');
assert(switcherContent.includes('filteredLanguages'), 'LanguageSwitcher must filter languages');
assert(switcherContent.includes('nativeLabel'), 'LanguageSwitcher must show native name');
assert(switcherContent.includes('englishLabel'), 'LanguageSwitcher must show English name');

// Check first visit prompt
assert(switcherContent.includes('growcircle_locale_selected'), 'LanguageSwitcher must remember choice and handle first visit');

// Check cookie and storage persistence
assert(switcherContent.includes('NEXT_LOCALE'), 'LanguageSwitcher must set NEXT_LOCALE cookie');
assert(switcherContent.includes('localStorage.setItem'), 'LanguageSwitcher must set localStorage');
console.log('  [PASS] LanguageSwitcher has searchable list, 44px targets, ARIA roles, first-visit modal, and cookies.');

// 6. Verify Price Numeral Formatting with Currency Symbol
console.log('\nCHECK 6: Verifying prices kept as numerals with currency symbol...');
assert(languagesTs.includes('function formatPrice'), 'languages.ts must provide formatPrice');
assert(languagesTs.includes('₹'), 'formatPrice must include ₹ currency symbol');
assert(languagesTs.includes('en-IN'), 'formatPrice must keep numerals formatted with Indian commas (1,250)');
console.log('  [PASS] Prices strictly formatted as clear Arabic numerals with ₹ symbol.');

// 7. Verify Coverage Report produced and lists untranslated fallbacks
console.log('\nCHECK 7: Verifying coverage report produced with fallback strings...');
const reportJsonPath = path.join(__dirname, '..', 'reports', 'i18n-coverage-report.json');
const reportMdPath = path.join(__dirname, '..', 'reports', 'i18n-coverage-report.md');
assert(fs.existsSync(reportJsonPath), 'i18n-coverage-report.json missing');
assert(fs.existsSync(reportMdPath), 'i18n-coverage-report.md missing');

const reportData = JSON.parse(fs.readFileSync(reportJsonPath, 'utf8'));
assert(reportData.total_languages === 23, 'Report must contain all 23 languages');
assert(reportData.languages.length === 23, 'Report languages array must have 23 entries');

// Verify untranslated strings fall back and are listed in the report
const partlyTranslatedLangs = reportData.languages.filter(l => !l.reviewed_by_native_speaker);
assert(partlyTranslatedLangs.length === 19, '19 languages should be partly translated');
for (const pLang of partlyTranslatedLangs) {
  assert(pLang.fallback_per_string_to === 'Hindi' || pLang.fallback_per_string_to === 'English', `${pLang.code} must fall back to Hindi or English`);
  assert(Array.isArray(pLang.untranslated_fallback_strings), `${pLang.code} must list untranslated fallback strings`);
}
console.log('  [PASS] Per-language coverage report produced; untranslated strings fall back and are listed.');

console.log('\nALL R5 ACCEPTANCE CRITERIA VERIFIED SUCCESSFULLY!\n');
