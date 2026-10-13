/**
 * WCAG AA Contrast Ratio Automated Verification Test
 * Calculates the relative luminance of colors from assets/brand/tokens.json
 * and asserts compliance with WCAG AA:
 * - Normal text (< 18pt / 24px): requires >= 4.5:1
 * - Large text (>= 18pt or >= 14pt bold, such as Wordmark "G" & "C"): requires >= 3.0:1
 * - UI components & graphical elements: requires >= 3.0:1
 */

const fs = require('fs');
const path = require('path');

const tokensPath = path.join(__dirname, '..', '..', 'assets', 'brand', 'tokens.json');
const tokens = JSON.parse(fs.readFileSync(tokensPath, 'utf8'));

function hexToRgb(hex) {
  const cleanHex = hex.replace('#', '');
  return {
    r: parseInt(cleanHex.substring(0, 2), 16),
    g: parseInt(cleanHex.substring(2, 4), 16),
    b: parseInt(cleanHex.substring(4, 6), 16),
  };
}

function getLuminance({ r, g, b }) {
  const [rs, gs, bs] = [r, g, b].map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

function getContrastRatio(hex1, hex2) {
  const lum1 = getLuminance(hexToRgb(hex1));
  const lum2 = getLuminance(hexToRgb(hex2));
  const brightest = Math.max(lum1, lum2);
  const darkest = Math.min(lum1, lum2);
  return (brightest + 0.05) / (darkest + 0.05);
}

const colors = {
  deepLeaf: tokens.color['deep-leaf'].value,
  harvestGold: tokens.color['harvest-gold'].value,
  amber: tokens.color['amber'].value,
  cream: tokens.color['cream'].value,
  ink: tokens.color['ink'].value,
  muted: tokens.color['muted'].value,
  border: tokens.color['border'].value,
  danger: tokens.color['danger'].value,
  info: tokens.color['info'].value,
  white: '#FFFFFF',
};

const checks = [
  // Normal body text (WCAG AA >= 4.5:1)
  { name: 'Ink body text on Cream background', fg: colors.ink, bg: colors.cream, min: 4.5, type: 'Normal Text' },
  { name: 'Ink body text on White surface', fg: colors.ink, bg: colors.white, min: 4.5, type: 'Normal Text' },
  { name: 'Muted text on Cream background', fg: colors.muted, bg: colors.cream, min: 4.5, type: 'Normal Text' },
  { name: 'Muted text on White surface', fg: colors.muted, bg: colors.white, min: 4.5, type: 'Normal Text' },
  { name: 'Deep Leaf text on Cream background', fg: colors.deepLeaf, bg: colors.cream, min: 4.5, type: 'Normal Text' },
  { name: 'White text on Deep Leaf button', fg: colors.white, bg: colors.deepLeaf, min: 4.5, type: 'Normal Text' },
  { name: 'Danger text on Cream background', fg: colors.danger, bg: colors.cream, min: 4.5, type: 'Normal Text' },
  { name: 'White text on Danger button', fg: colors.white, bg: colors.danger, min: 4.5, type: 'Normal Text' },
  { name: 'Info text on Cream background', fg: colors.info, bg: colors.cream, min: 4.5, type: 'Normal Text' },
  { name: 'Ink text on Harvest Gold accent button', fg: colors.ink, bg: colors.harvestGold, min: 4.5, type: 'Normal Text' },

  // Large display text & Wordmark (WCAG AA >= 3.0:1)
  { name: 'Amber "G" & "C" large wordmark text on Cream', fg: colors.amber, bg: colors.cream, min: 3.0, type: 'Large Text (>=18pt/bold)' },
  { name: 'Amber large wordmark text on White', fg: colors.amber, bg: colors.white, min: 3.0, type: 'Large Text (>=18pt/bold)' },
];

console.log('=== GROWCIRCLE WCAG AA CONTRAST RATIO VERIFICATION ===\n');
let failed = false;

checks.forEach(({ name, fg, bg, min, type }) => {
  const ratio = getContrastRatio(fg, bg);
  const passed = ratio >= min;
  const status = passed ? 'PASS' : 'FAIL';
  console.log(`[${status}] ${name} [${type}]: ${ratio.toFixed(2)}:1 (Required >= ${min}:1)`);
  if (!passed) failed = true;
});

if (failed) {
  console.error('\nContrast checks failed! WCAG AA requirements not met.');
  process.exit(1);
} else {
  console.log('\nAll color combinations pass WCAG AA contrast standards!\n');
}
