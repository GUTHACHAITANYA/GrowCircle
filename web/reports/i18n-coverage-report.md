# GrowCircle i18n & Honest Language Coverage Report

**Generated At:** Fri, 16 Oct 2026 08:00:03 GMT
**Total Supported Languages:** 23 (22 Scheduled Indian Languages + English)
**Total Base Keys in English:** 95

| Code | Language | Script | UI Ready | Voice STT | Voice TTS | Native Reviewed | Coverage % | Status | Fallback |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- |
| `en` | **English** (English) | Latin | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | **100%** | Fully Translated & Reviewed | EN |
| `te` | **తెలుగు** (Telugu) | Telugu | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | **96%** | Fully Translated & Reviewed | EN |
| `hi` | **हिंदी** (Hindi) | Devanagari | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | **96%** | Fully Translated & Reviewed | EN |
| `gu` | **ગુજરાતી** (Gujarati) | Gujarati | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | **96%** | Fully Translated & Reviewed | HI |
| `as` | **অসমীয়া** (Assamese) | Bengali | ⏳ Partial | ⏳ No | ⏳ No | ⚠️ No (Machine Draft) | **94%** | Partly translated (First draft) | HI |
| `bn` | **বাংলা** (Bengali) | Bengali | ⏳ Partial | ⏳ No | ⏳ No | ⚠️ No (Machine Draft) | **96%** | Partly translated (First draft) | HI |
| `brx` | **बड़ो** (Bodo) | Devanagari | ⏳ Partial | ⏳ No | ⏳ No | ⚠️ No (Machine Draft) | **91%** | Partly translated (First draft) | HI |
| `doi` | **डोगरी** (Dogri) | Devanagari | ⏳ Partial | ⏳ No | ⏳ No | ⚠️ No (Machine Draft) | **91%** | Partly translated (First draft) | HI |
| `kn` | **ಕನ್ನಡ** (Kannada) | Kannada | ⏳ Partial | ⏳ No | ⏳ No | ⚠️ No (Machine Draft) | **96%** | Partly translated (First draft) | HI |
| `ks` | **کٲشُر** (Kashmiri) | Arabic | ⏳ Partial | ⏳ No | ⏳ No | ⚠️ No (Machine Draft) | **93%** | Partly translated (First draft) | HI |
| `kok` | **कोंकणी** (Konkani) | Devanagari | ⏳ Partial | ⏳ No | ⏳ No | ⚠️ No (Machine Draft) | **91%** | Partly translated (First draft) | HI |
| `mai` | **मैथिली** (Maithili) | Devanagari | ⏳ Partial | ⏳ No | ⏳ No | ⚠️ No (Machine Draft) | **91%** | Partly translated (First draft) | HI |
| `ml` | **മലയാളം** (Malayalam) | Malayalam | ⏳ Partial | ⏳ No | ⏳ No | ⚠️ No (Machine Draft) | **36%** | Partly translated (First draft) | EN |
| `mni` | **মৈতৈলোন্** (Manipuri) | Bengali | ⏳ Partial | ⏳ No | ⏳ No | ⚠️ No (Machine Draft) | **91%** | Partly translated (First draft) | HI |
| `mr` | **मराठी** (Marathi) | Devanagari | ⏳ Partial | ⏳ No | ⏳ No | ⚠️ No (Machine Draft) | **96%** | Partly translated (First draft) | HI |
| `ne` | **नेपाली** (Nepali) | Devanagari | ⏳ Partial | ⏳ No | ⏳ No | ⚠️ No (Machine Draft) | **94%** | Partly translated (First draft) | HI |
| `or` | **ଓଡ଼ିଆ** (Odia) | Odia | ⏳ Partial | ⏳ No | ⏳ No | ⚠️ No (Machine Draft) | **94%** | Partly translated (First draft) | HI |
| `pa` | **ਪੰਜਾਬੀ** (Punjabi) | Gurmukhi | ⏳ Partial | ⏳ No | ⏳ No | ⚠️ No (Machine Draft) | **96%** | Partly translated (First draft) | HI |
| `sa` | **संस्कृतम्** (Sanskrit) | Devanagari | ⏳ Partial | ⏳ No | ⏳ No | ⚠️ No (Machine Draft) | **91%** | Partly translated (First draft) | HI |
| `sat` | **ᱥᱟᱱᱛᱟᱲᱤ** (Santali) | Ol Chiki | ⏳ Partial | ⏳ No | ⏳ No | ⚠️ No (Machine Draft) | **91%** | Partly translated (First draft) | HI |
| `sd` | **سنڌي** (Sindhi) | Arabic | ⏳ Partial | ⏳ No | ⏳ No | ⚠️ No (Machine Draft) | **91%** | Partly translated (First draft) | HI |
| `ta` | **தமிழ்** (Tamil) | Tamil | ⏳ Partial | ⏳ No | ⏳ No | ⚠️ No (Machine Draft) | **36%** | Partly translated (First draft) | EN |
| `ur` | **اردو** (Urdu) | Arabic | ⏳ Partial | ⏳ No | ⏳ No | ⚠️ No (Machine Draft) | **96%** | Partly translated (First draft) | HI |

## Untranslated Strings & Fallback Mechanism

Languages with partial coverage fall back per string to **Hindi** (for Indic cognates) or **English**.
The table below summarizes untranslated keys that safely fall back per string:

### `te` - తెలుగు (Telugu)
- **Coverage:** 96% (91/95 keys translated)
- **Fallback Count:** 4 strings fall back to English
- **Sample Fallback Keys:**
  - `languages.en` (falls back to English: "English")
  - `languages.te` (falls back to English: "తెలుగు")
  - `languages.hi` (falls back to English: "हिंदी")
  - `languages.gu` (falls back to English: "ગુજરાતી")

### `hi` - हिंदी (Hindi)
- **Coverage:** 96% (91/95 keys translated)
- **Fallback Count:** 4 strings fall back to English
- **Sample Fallback Keys:**
  - `languages.en` (falls back to English: "English")
  - `languages.te` (falls back to English: "తెలుగు")
  - `languages.hi` (falls back to English: "हिंदी")
  - `languages.gu` (falls back to English: "ગુજરાતી")

### `gu` - ગુજરાતી (Gujarati)
- **Coverage:** 96% (91/95 keys translated)
- **Fallback Count:** 4 strings fall back to Hindi
- **Sample Fallback Keys:**
  - `languages.en` (falls back to Hindi: "English")
  - `languages.te` (falls back to Hindi: "తెలుగు")
  - `languages.hi` (falls back to Hindi: "हिंदी")
  - `languages.gu` (falls back to Hindi: "ગુજરાતી")

### `as` - অসমীয়া (Assamese)
- **Coverage:** 94% (89/95 keys translated)
- **Fallback Count:** 6 strings fall back to Hindi
- **Sample Fallback Keys:**
  - `languages.firstVisitDesc` (falls back to Hindi: "GrowCircle is available across 22 scheduled Indian languages plus English.")
  - `languages.noResults` (falls back to Hindi: "No matching languages found")
  - `languages.en` (falls back to Hindi: "English")
  - `languages.te` (falls back to Hindi: "తెలుగు")
  - `languages.hi` (falls back to Hindi: "हिंदी")
  - *...and 1 more keys.*

### `bn` - বাংলা (Bengali)
- **Coverage:** 96% (91/95 keys translated)
- **Fallback Count:** 4 strings fall back to Hindi
- **Sample Fallback Keys:**
  - `languages.en` (falls back to Hindi: "English")
  - `languages.te` (falls back to Hindi: "తెలుగు")
  - `languages.hi` (falls back to Hindi: "हिंदी")
  - `languages.gu` (falls back to Hindi: "ગુજરાતી")

### `brx` - बड़ो (Bodo)
- **Coverage:** 91% (86/95 keys translated)
- **Fallback Count:** 9 strings fall back to Hindi
- **Sample Fallback Keys:**
  - `languages.partlyTranslated` (falls back to Hindi: "Partly translated")
  - `languages.reviewed` (falls back to Hindi: "Native reviewed")
  - `languages.firstVisitTitle` (falls back to Hindi: "Select your language")
  - `languages.firstVisitDesc` (falls back to Hindi: "GrowCircle is available across 22 scheduled Indian languages plus English.")
  - `languages.noResults` (falls back to Hindi: "No matching languages found")
  - *...and 4 more keys.*

### `doi` - डोगरी (Dogri)
- **Coverage:** 91% (86/95 keys translated)
- **Fallback Count:** 9 strings fall back to Hindi
- **Sample Fallback Keys:**
  - `languages.partlyTranslated` (falls back to Hindi: "Partly translated")
  - `languages.reviewed` (falls back to Hindi: "Native reviewed")
  - `languages.firstVisitTitle` (falls back to Hindi: "Select your language")
  - `languages.firstVisitDesc` (falls back to Hindi: "GrowCircle is available across 22 scheduled Indian languages plus English.")
  - `languages.noResults` (falls back to Hindi: "No matching languages found")
  - *...and 4 more keys.*

### `kn` - ಕನ್ನಡ (Kannada)
- **Coverage:** 96% (91/95 keys translated)
- **Fallback Count:** 4 strings fall back to Hindi
- **Sample Fallback Keys:**
  - `languages.en` (falls back to Hindi: "English")
  - `languages.te` (falls back to Hindi: "తెలుగు")
  - `languages.hi` (falls back to Hindi: "हिंदी")
  - `languages.gu` (falls back to Hindi: "ગુજરાતી")

### `ks` - کٲشُر (Kashmiri)
- **Coverage:** 93% (88/95 keys translated)
- **Fallback Count:** 7 strings fall back to Hindi
- **Sample Fallback Keys:**
  - `languages.firstVisitTitle` (falls back to Hindi: "Select your language")
  - `languages.firstVisitDesc` (falls back to Hindi: "GrowCircle is available across 22 scheduled Indian languages plus English.")
  - `languages.noResults` (falls back to Hindi: "No matching languages found")
  - `languages.en` (falls back to Hindi: "English")
  - `languages.te` (falls back to Hindi: "తెలుగు")
  - *...and 2 more keys.*

### `kok` - कोंकणी (Konkani)
- **Coverage:** 91% (86/95 keys translated)
- **Fallback Count:** 9 strings fall back to Hindi
- **Sample Fallback Keys:**
  - `languages.partlyTranslated` (falls back to Hindi: "Partly translated")
  - `languages.reviewed` (falls back to Hindi: "Native reviewed")
  - `languages.firstVisitTitle` (falls back to Hindi: "Select your language")
  - `languages.firstVisitDesc` (falls back to Hindi: "GrowCircle is available across 22 scheduled Indian languages plus English.")
  - `languages.noResults` (falls back to Hindi: "No matching languages found")
  - *...and 4 more keys.*

### `mai` - मैथिली (Maithili)
- **Coverage:** 91% (86/95 keys translated)
- **Fallback Count:** 9 strings fall back to Hindi
- **Sample Fallback Keys:**
  - `languages.partlyTranslated` (falls back to Hindi: "Partly translated")
  - `languages.reviewed` (falls back to Hindi: "Native reviewed")
  - `languages.firstVisitTitle` (falls back to Hindi: "Select your language")
  - `languages.firstVisitDesc` (falls back to Hindi: "GrowCircle is available across 22 scheduled Indian languages plus English.")
  - `languages.noResults` (falls back to Hindi: "No matching languages found")
  - *...and 4 more keys.*

### `ml` - മലയാളം (Malayalam)
- **Coverage:** 36% (34/95 keys translated)
- **Fallback Count:** 61 strings fall back to English
- **Sample Fallback Keys:**
  - `brand.tagline` (falls back to English: "Farm to everyone, full circle")
  - `brand.greeting` (falls back to English: "Welcome to GrowCircle")
  - `languages.en` (falls back to English: "English")
  - `languages.te` (falls back to English: "తెలుగు")
  - `languages.hi` (falls back to English: "हिंदी")
  - *...and 56 more keys.*

### `mni` - মৈতৈলোন্ (Manipuri)
- **Coverage:** 91% (86/95 keys translated)
- **Fallback Count:** 9 strings fall back to Hindi
- **Sample Fallback Keys:**
  - `languages.partlyTranslated` (falls back to Hindi: "Partly translated")
  - `languages.reviewed` (falls back to Hindi: "Native reviewed")
  - `languages.firstVisitTitle` (falls back to Hindi: "Select your language")
  - `languages.firstVisitDesc` (falls back to Hindi: "GrowCircle is available across 22 scheduled Indian languages plus English.")
  - `languages.noResults` (falls back to Hindi: "No matching languages found")
  - *...and 4 more keys.*

### `mr` - मराठी (Marathi)
- **Coverage:** 96% (91/95 keys translated)
- **Fallback Count:** 4 strings fall back to Hindi
- **Sample Fallback Keys:**
  - `languages.en` (falls back to Hindi: "English")
  - `languages.te` (falls back to Hindi: "తెలుగు")
  - `languages.hi` (falls back to Hindi: "हिंदी")
  - `languages.gu` (falls back to Hindi: "ગુજરાતી")

### `ne` - नेपाली (Nepali)
- **Coverage:** 94% (89/95 keys translated)
- **Fallback Count:** 6 strings fall back to Hindi
- **Sample Fallback Keys:**
  - `languages.firstVisitDesc` (falls back to Hindi: "GrowCircle is available across 22 scheduled Indian languages plus English.")
  - `languages.noResults` (falls back to Hindi: "No matching languages found")
  - `languages.en` (falls back to Hindi: "English")
  - `languages.te` (falls back to Hindi: "తెలుగు")
  - `languages.hi` (falls back to Hindi: "हिंदी")
  - *...and 1 more keys.*

### `or` - ଓଡ଼ିଆ (Odia)
- **Coverage:** 94% (89/95 keys translated)
- **Fallback Count:** 6 strings fall back to Hindi
- **Sample Fallback Keys:**
  - `languages.firstVisitDesc` (falls back to Hindi: "GrowCircle is available across 22 scheduled Indian languages plus English.")
  - `languages.noResults` (falls back to Hindi: "No matching languages found")
  - `languages.en` (falls back to Hindi: "English")
  - `languages.te` (falls back to Hindi: "తెలుగు")
  - `languages.hi` (falls back to Hindi: "हिंदी")
  - *...and 1 more keys.*

### `pa` - ਪੰਜਾਬੀ (Punjabi)
- **Coverage:** 96% (91/95 keys translated)
- **Fallback Count:** 4 strings fall back to Hindi
- **Sample Fallback Keys:**
  - `languages.en` (falls back to Hindi: "English")
  - `languages.te` (falls back to Hindi: "తెలుగు")
  - `languages.hi` (falls back to Hindi: "हिंदी")
  - `languages.gu` (falls back to Hindi: "ગુજરાતી")

### `sa` - संस्कृतम् (Sanskrit)
- **Coverage:** 91% (86/95 keys translated)
- **Fallback Count:** 9 strings fall back to Hindi
- **Sample Fallback Keys:**
  - `languages.partlyTranslated` (falls back to Hindi: "Partly translated")
  - `languages.reviewed` (falls back to Hindi: "Native reviewed")
  - `languages.firstVisitTitle` (falls back to Hindi: "Select your language")
  - `languages.firstVisitDesc` (falls back to Hindi: "GrowCircle is available across 22 scheduled Indian languages plus English.")
  - `languages.noResults` (falls back to Hindi: "No matching languages found")
  - *...and 4 more keys.*

### `sat` - ᱥᱟᱱᱛᱟᱲᱤ (Santali)
- **Coverage:** 91% (86/95 keys translated)
- **Fallback Count:** 9 strings fall back to Hindi
- **Sample Fallback Keys:**
  - `languages.partlyTranslated` (falls back to Hindi: "Partly translated")
  - `languages.reviewed` (falls back to Hindi: "Native reviewed")
  - `languages.firstVisitTitle` (falls back to Hindi: "Select your language")
  - `languages.firstVisitDesc` (falls back to Hindi: "GrowCircle is available across 22 scheduled Indian languages plus English.")
  - `languages.noResults` (falls back to Hindi: "No matching languages found")
  - *...and 4 more keys.*

### `sd` - سنڌي (Sindhi)
- **Coverage:** 91% (86/95 keys translated)
- **Fallback Count:** 9 strings fall back to Hindi
- **Sample Fallback Keys:**
  - `languages.partlyTranslated` (falls back to Hindi: "Partly translated")
  - `languages.reviewed` (falls back to Hindi: "Native reviewed")
  - `languages.firstVisitTitle` (falls back to Hindi: "Select your language")
  - `languages.firstVisitDesc` (falls back to Hindi: "GrowCircle is available across 22 scheduled Indian languages plus English.")
  - `languages.noResults` (falls back to Hindi: "No matching languages found")
  - *...and 4 more keys.*

### `ta` - தமிழ் (Tamil)
- **Coverage:** 36% (34/95 keys translated)
- **Fallback Count:** 61 strings fall back to English
- **Sample Fallback Keys:**
  - `brand.tagline` (falls back to English: "Farm to everyone, full circle")
  - `brand.greeting` (falls back to English: "Welcome to GrowCircle")
  - `languages.en` (falls back to English: "English")
  - `languages.te` (falls back to English: "తెలుగు")
  - `languages.hi` (falls back to English: "हिंदी")
  - *...and 56 more keys.*

### `ur` - اردو (Urdu)
- **Coverage:** 96% (91/95 keys translated)
- **Fallback Count:** 4 strings fall back to Hindi
- **Sample Fallback Keys:**
  - `languages.en` (falls back to Hindi: "English")
  - `languages.te` (falls back to Hindi: "తెలుగు")
  - `languages.hi` (falls back to Hindi: "हिंदी")
  - `languages.gu` (falls back to Hindi: "ગુજરાતી")

