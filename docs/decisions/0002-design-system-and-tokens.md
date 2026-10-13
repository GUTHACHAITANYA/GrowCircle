# ADR 0002: Token-Driven Design System and Multilingual Accessibility

## Status
Accepted

## Context
GrowCircle serves users across diverse literacy levels and multilingual backgrounds in India (Telugu, Hindi, Gujarati, English). The interface must:
- Meet strict WCAG AA contrast standards across all lighting conditions.
- Guarantee at least 44px touch targets on mobile devices.
- Prevent hardcoded strings and maintain brand names properly translated into regional scripts.
- Avoid emojis in UI controls while providing clear agricultural iconography.

## Decision
1. **Design Tokens as Source of Truth**: Centralize tokens in `assets/brand/tokens.json`. Web Tailwind configuration imports tokens directly.
2. **Localization Layer**: Enforce `next-intl` with keys for every user-facing label. Never use hardcoded English strings.
3. **Typography**: Baloo 2 for headings and brand marks; Google Noto Sans family for regional scripts.
4. **Accessible Components**: Enforce 44px minimum touch targets and automated contrast validation.

## Consequences
- **Positive**: Strict visual consistency across all doors, high readability for farmers and drivers, guaranteed compliance with accessibility rules.
- **Negative**: Requires maintaining synchronized message bundles across four languages.
- **Mitigation**: CI pipeline tests enforce that missing translation keys fail the build.
