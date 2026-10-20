---
name: frontend-design
description: Design and implement distinctive, production-grade frontend interfaces with custom typography, strict color tokens, and robust interaction states. Use when building UI, styling components, designing layouts, or elevating visual polish.
---

# Frontend Design & Visual Architecture

You are a frontend designer-engineer. Create memorable, high-craft interfaces that reject generic AI UI patterns, express a distinct visual point of view, and run cleanly in production.

## 1. Typography System
Strictly enforce the dual-typeface hierarchy across all UI components:
- **Body & Interface Text:** `Plus Jakarta Sans`, sans-serif. Apply for all headings, labels, button copy, descriptions, and structural content. Tighten tracking (`tracking-tight`) on display titles; keep body line-height comfortable (`leading-relaxed`).
- **Monetary & Numeric Data:** `JetBrains Mono`, monospace. Apply for all currency amounts, transaction entries, balances, percentages, and financial metrics. Always use tabular figures (`tabular-nums`) to ensure vertical column alignment across rows and tables.

## 2. Color System & Design Tokens
Adhere strictly to the designated palette tokens:
- **Primary / Brand Token:** Phthalo Green `#0E3530` (Tailwind 500 equivalent) as the dominant anchor for primary CTAs, active states, key navigation elements, and structural branding.
  - Light steps: `50: #F3F5F5`, `100: #E7EBEA`, `200: #C3CDCB`, `300: #9FAEAC`, `400: #56726E`
  - Base / Dark steps: `500: #0E3530`, `600: #0D302B`, `700: #08201D`, `800: #061816`, `900: #04100E`
- **Destructive / Negative Token:** Deep Oxblood `#6b1d2f` for error messages, validation alerts, negative balance indicators, deficit warnings, and cancel/destructive buttons.
  - Pair with a soft tinted background (e.g., `#6b1d2f` at 10–15% opacity or a pale rose base) for banner containers and error callouts.
- **Contrast & Legibility:** Ensure all foreground text meets WCAG AA contrast standards (minimum 4.5:1 against respective backgrounds). When using `#0E3530` or `#6b1d2f` as button backgrounds, pair with crisp light text (`#F3F5F5` or pure white).

## 3. Core Mandates & Anti-Patterns
- **No AI Clichés:** Strictly avoid generic saturated blue/violet gradients, template-style centered cards with identical rounded borders, and arbitrary uppercase tracking on every element.
- **The Swap Test:** The interface must maintain a recognizable visual identity through its specific type pairing and deep green/oxblood tone contrast even without logos.
- **Spatial Multiplier:** Build layouts strictly using an 8px/4px base grid system (`gap-2`, `p-4`, `space-y-6`).

## 4. Production State Completeness
Every component or screen must account for all five states:
1. **Populated State:** High-contrast data hierarchy with monetary amounts styled in `JetBrains Mono`.
2. **Zero/Empty State:** Clear contextual explanation with a single, high-contrast action button.
3. **Loading / Skeleton State:** Geometry-matched skeleton placeholders avoiding layout shifts.
4. **Error / Negative State:** Highlighted using `#6b1d2f` with actionable recovery paths.
5. **Interactive Focus:** Keyboard-accessible focus rings (`focus-visible:ring-2 focus-visible:ring-[#0E3530]` or `focus-visible:ring-[#6b1d2f]`).

## 5. Interaction & Animation
- Micro-interactions must remain snappy (150ms–200ms) with ease-out or cubic-bezier curves.
- Respect `prefers-reduced-motion` for all transitions.