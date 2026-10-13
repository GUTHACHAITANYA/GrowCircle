import type { Config } from 'tailwindcss';
import tokens from '../assets/brand/tokens.json';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'deep-leaf': tokens.color['deep-leaf'].value,
        'harvest-gold': tokens.color['harvest-gold'].value,
        'amber': tokens.color['amber'].value,
        'cream': tokens.color['cream'].value,
        'ink': tokens.color['ink'].value,
        'muted': tokens.color['muted'].value,
        'border': tokens.color['border'].value,
        'danger': tokens.color['danger'].value,
        'info': tokens.color['info'].value,
      },
      fontFamily: {
        heading: ['var(--font-baloo)', 'Baloo 2', 'cursive', 'sans-serif'],
        body: ['var(--font-sans)', 'system-ui', '-apple-system', 'sans-serif'],
        telugu: ['var(--font-noto-telugu)', 'Noto Sans Telugu', 'sans-serif'],
        hindi: ['var(--font-noto-devanagari)', 'Noto Sans Devanagari', 'sans-serif'],
        gujarati: ['var(--font-noto-gujarati)', 'Noto Sans Gujarati', 'sans-serif'],
      },
      minHeight: {
        touch: tokens.spacing.touchMin.value,
        voice: tokens.spacing.voiceButton.value,
      },
      minWidth: {
        touch: tokens.spacing.touchMin.value,
        voice: tokens.spacing.voiceButton.value,
      },
      borderRadius: {
        mark: tokens.borderRadius.mark,
      },
    },
  },
  plugins: [],
};

export default config;
