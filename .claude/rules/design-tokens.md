---
name: design-tokens
description: Colour encodes authorship. Token usage rules for all UI code.
globs: "packages/ui/**,**/globals.css,**/*.tsx,**/*.css"
alwaysApply: false
source: docs/design.md §2
---

# Colour encodes authorship

This is the organising idea of the entire interface, and every colour decision derives from it.

| Hue | Means | Used for |
|---|---|---|
| **Indigo** | The machine said this | Suggestions, confidence, system annotations, evidence links, primary actions |
| **Red** | A person did this | Marker overrides, human annotations, destructive actions only |
| **Green** | Settled | Finalised marks only. Not "success", not "saved". |
| **Amber** | Needs a person | Low confidence, routed for review, pending |
| **Neutral** | Everything else | Surfaces, text, chrome |

**Nothing the system generates is ever red.** A marker must be able to tell, from colour alone
across the whole screen, what the machine proposed and what a human decided. Violating this rule
is the single most damaging thing you can do to this interface.

## Usage rules

- **One accent hue.** Indigo. Everything else is a state, not decoration.
- **Green appears exactly once per flow** — on a finalised mark. Never for toasts, checkmarks, or
  "saved". Those are neutral.
- **Amber is not an alarm.** It means "a person needs to look at this", which is routine and
  expected. Style it calmly. No warning triangles.
- **Subtle variants** (`--*-subtle`) are for backgrounds behind text of the same hue. Never put
  full-strength state colour behind body text.
- **Never tint a whole surface.** Cards are `--card`. State is a 2px left border, a pill, or an
  icon — never a coloured panel.
- **Red is reserved.** Form validation uses `--destructive` for text and border, never a red fill
  on a non-destructive control.

## Evidence tints

Six categorical tints (`--ev-a` … `--ev-f`), used only over page photographs and their matching
transcript lines.

1. **Never rely on hue alone.** Each tint always pairs with a letter badge (A–F) and a distinct
   outline dash pattern: `solid`, `4 2`, `2 2`, `6 2 2 2`, `1 3`, `8 3`.
2. Fill at `--ev-fill` alpha; outline full strength, 2px.
3. Assignment is by marking-point order within the question, **stable across renders**. A point
   that is A on first load is A forever.
4. Beyond six visible points, reuse tints but never adjacent; the badge disambiguates.
5. High-contrast mode drops fills to 0 and raises outlines to 3px.

## Theme

Light is the default, with full dark parity. This is functional, not aesthetic: the marking
workspace sits beside a photograph of white paper, and a dark UI around a bright page image
creates a glare halo over a 90-minute session. **The page-viewer surround (`--viewer-surround`)
stays neutral in both themes.**

## Do not hand-roll shadcn primitives

Use the official `sidebar` component — collapse, rail, mobile sheet, keyboard shortcut, and
cookie-persisted state are already solved. Take visual details from references; do not rebuild
behaviour.

Radius is `0.375rem`. The mark is solid single-colour, square line caps, no gradient — round
caps read as consumer software, square reads as a stamp. See [[clients]].
