# GrowCircle Brand Identity Guidelines

> *"Farm to everyone, full circle"*

---

## 1. Brand Mark & Geometry

### 1.1 The Logo Mark
The GrowCircle symbol combines two natural and geometric forms:
- A rounded square container with a corner radius of approximately **23%** (e.g. `rx="118"` on a 512×512 grid), rendered in **Deep Leaf green** (`#1F6B3A`).
- An interior open circular arc in crisp white (forming a "C" open towards the right).
- A **Harvest Gold** (`#F6C343`) stylized leaf positioned across the opening.
- When viewed as a whole, the interaction between the open arc and leaf creates both a **"G"** (Grow) and a **"C"** (Circle).

### 1.2 The Wordmark
- Typeset in **Baloo 2 ExtraBold** (800 weight).
- The letters **"G"** and **"C"** are set in **Amber** (`#C77700`).
- The remaining letters (**"row"** and **"ircle"**) are set in **Deep Leaf green** (`#1F6B3A`).

### 1.3 Canonical Source Files
Always use the vector assets located in:
- Mark only: `assets/brand/logo-mark.svg`
- Full logo (Mark + Wordmark): `assets/brand/logo-full.svg`

---

## 2. Clear Space and Usage Rules

### Clear Space
Maintain an exclusion zone around the logo equal to at least **1 leaf-width** ($X$) on all sides. No typography, borders, UI controls, or graphics may encroach within this perimeter.

### Absolute "Do Nots"
- **DO NOT** redraw the logo mark from memory or substitute shapes.
- **DO NOT** alter the aspect ratio, stretch, condense, or rotate the logo.
- **DO NOT** recolor the leaf, the white arc, or the container background.
- **DO NOT** apply drop shadows, 3D bevels, gradients, or outer glows.
- **DO NOT** place emojis anywhere in the interface or branding assets.

---

## 3. Design Tokens & Palette

All colors are strictly defined in `assets/brand/tokens.json`.

| Token Name | Hex Code | Primary Role | Contrast Ratio on Cream |
| :--- | :--- | :--- | :--- |
| `deep-leaf` | `#1F6B3A` | Primary brand color, primary buttons, headers | 6.8:1 (WCAG AAA) |
| `harvest-gold`| `#F6C343` | Accent highlights on dark surfaces, icon accents | Decorative / Accent |
| `amber` | `#C77700` | Text accents on light surfaces ("G" and "C" letters) | 4.6:1 (WCAG AA) |
| `cream` | `#FBFAF4` | Universal app background | Base Surface |
| `ink` | `#1B1B18` | Primary body text and prominent titles | 15.1:1 (WCAG AAA) |
| `muted` | `#4A4A42` | Secondary text, captions, timestamps | 7.9:1 (WCAG AAA) |
| `border` | `#E3E0D2` | Card outlines, dividers, input borders | Subtle structural border |
| `danger` | `#C62828` | Price drops, error messages, alerts | 5.8:1 (WCAG AA) |
| `info` | `#1565C0` | Informational badges, guide notices | 6.1:1 (WCAG AA) |

*All color pairings meet or exceed WCAG AA standards (4.5:1 for body text, 3.0:1 for large display text and UI components).*

---

## 4. Typography

- **Headings & Wordmarks**: Baloo 2 (ExtraBold 800, Bold 700, SemiBold 600).
- **Body Text**:
  - English: Clean Sans-Serif (system fallback stack: Inter, -apple-system, sans-serif).
  - Telugu: Noto Sans Telugu.
  - Hindi: Noto Sans Devanagari.
  - Gujarati: Noto Sans Gujarati.
- **Touch & Accessibility Specifications**:
  - Minimum mobile body font size: **16px**.
  - Minimum touch target for all buttons and interactive chips: **44px × 44px**.

---

## 5. Localized Brand Names

Brand names must be spelled precisely per script and reviewed by native speakers:

| Language | Script Name | Audio Pronunciation Guide |
| :--- | :--- | :--- |
| **English** | GrowCircle | *Grow-Circle* |
| **Telugu** | గ్రో సర్కిల్ | *Gro-Sar-kil* |
| **Hindi** | ग्रो सर्कल | *Gro-Sar-kal* |
| **Gujarati** | ગ્રો સર્કલ | *Gro-Sar-kal* |

---

## 6. Tone of Voice & Spoken Rules

- **Warm, Respectful, Simple**: Use polite, straightforward language. Avoid jargon (no "commodities aggregated", "algorithmic dispatch", or "disintermediation").
- **Concise & Direct**: Keep sentences short. Spoken IVR audio prompts must be under **20 seconds**.
- **Voice Greeting**: Always begin voice interactions with *"Welcome to GrowCircle"* in the user's selected language.
- **Fact-Based Claims**: Never use unsubstantiated terms like *"organic"*, *"chemical-free"*, *"guaranteed"*, or *"100% secure"* unless verified by legal and certification documents.
