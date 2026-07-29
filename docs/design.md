# DESIGN.md
## Marking Assistant — design system

**Owner:** design
**Consumers:** front-end engineers building Console and Capture
**Stack:** React + TypeScript + Tailwind + shadcn/ui + Lucide

This document is the single source of truth for colour, type, spacing, components, and copy. If something on screen is not derivable from this file, it is a bug in this file or a bug in the build. Raise it, don't improvise.

---

## 0. Two apps, one system

| | **Console** | **Capture** |
|---|---|---|
| Platform | Desktop web, 1280px and up | Mobile PWA, 360–430px |
| User | Lecturer, TA, exams officer, admin | Lecturer, TA |
| Context | Office, sustained 90-minute sessions | Exam hall, one hand, poor light, weak signal |
| Shell | Sidebar + top bar | Full-bleed, no chrome |
| Input | Keyboard-first | Thumb-first |
| Shared | Auth, design tokens, icon set, writing voice, all `components/ui` primitives | |
| Not shared | Shell, navigation, layout density, most patterns | |

Build the token layer and `components/ui` once. Build the shells twice. Do not attempt one responsive layout that serves both — the marking workspace and the camera have nothing structurally in common, and forcing them together produces a bad version of each.

---

## 1. Corrections to the references you sent

Recorded here so the decisions are traceable.

**1. `navbar-1` is a marketing component, not an app shell.** The floating pill with a centred nav is right for a public landing page and wrong for a product with 78 screens and role-based navigation. Use it on the marketing site only. Console uses sidebar + top bar (§6.2).

**2. Its logo mark uses a `#FF9966 → #FF5E62` gradient.** Removed. That coral-orange gradient is one of the most common generative-design tells, and it carries no meaning here. Replaced with a solid mark in the primary hue (§2.6).

**3. `dashboard-sidebar` is a good visual reference but should not be hand-rolled.** shadcn ships an official `sidebar` component with collapse, rail, mobile sheet, keyboard shortcut, and cookie-persisted state already solved. Take the *visual* details from your reference — the workspace switcher, the tucked keyboard hints, the tree indent guides — and apply them to the official primitive. Do not rebuild collapse behaviour by hand.

**4. Your tab-strip reference should not use Radix `Tabs`.** Radix Tabs is for switching panels within a page. The exam strip switches *routes*. Build it as a list of links with `aria-current="page"` (§6.4). Using Tabs here breaks the back button, deep links, and screen-reader semantics.

**5. Your reference screenshots are all dark.** Light is the default here, with full dark parity. The reason is functional, not aesthetic: the marking workspace sits next to a photograph of white paper. A dark UI wrapped around a bright page image creates a glare halo and measurable eye strain over a 90-minute session. Dark mode is fully specified and supported — the *page viewer surround stays neutral in both themes* (§3.4).

---

## 2. Colour

### 2.1 The organising idea: colour encodes authorship

This is the one rule that makes the product legible at a glance, and every colour decision derives from it.

| Hue | Means | Used for |
|---|---|---|
| **Indigo** | The machine said this | Suggestions, confidence, system annotations, evidence links, primary actions |
| **Red** | A person did this | Marker overrides, human annotations, and destructive actions only |
| **Green** | Settled | Finalised marks only. Not "success", not "saved". |
| **Amber** | Needs a person | Low confidence, routed for review, pending |
| **Neutral** | Everything else | Surfaces, text, chrome |

**Nothing the system generates is ever red.** A marker can tell, from colour alone across the whole screen, what the machine proposed and what a human decided. Violating this rule is the single most damaging thing you can do to this interface.

### 2.2 Tokens — light (default)

Paste into `globals.css`. shadcn HSL triplet format.

```css
@layer base {
  :root {
    /* surfaces — cool paper, not cream */
    --background:            220 23% 97%;   /* #F7F8FA */
    --foreground:            218 22% 10%;   /* #14181F */
    --card:                  0 0% 100%;     /* #FFFFFF */
    --card-foreground:       218 22% 10%;
    --popover:               0 0% 100%;
    --popover-foreground:    218 22% 10%;
    --muted:                 220 21% 95%;   /* #EEF0F4 */
    --muted-foreground:      215 12% 40%;   /* #5A6472 */
    --accent:                220 21% 95%;
    --accent-foreground:     218 22% 10%;
    --border:                218 19% 89%;   /* #DDE1E8 */
    --input:                 218 19% 89%;
    --ring:                  230 38% 48%;

    /* authorship */
    --primary:               230 38% 48%;   /* #4C5BA8  machine / indigo */
    --primary-foreground:    0 0% 100%;
    --secondary:             220 21% 95%;
    --secondary-foreground:  218 22% 10%;
    --destructive:           4 62% 48%;     /* #C8382F  marker red */
    --destructive-foreground:0 0% 100%;

    /* semantic states */
    --settled:               160 59% 30%;   /* #1F7A5C  finalised */
    --settled-foreground:    0 0% 100%;
    --settled-subtle:        160 40% 94%;
    --caution:               35 86% 38%;    /* #B4700E  needs judgement */
    --caution-foreground:    0 0% 100%;
    --caution-subtle:        38 78% 95%;
    --machine-subtle:        230 45% 95%;
    --marker-subtle:         4 60% 96%;

    /* page viewer surround — neutral in BOTH themes */
    --viewer-surround:       220 12% 88%;

    /* evidence tints — categorical, drawn over photographs */
    --ev-a: 230 38% 48%;   /* indigo  */
    --ev-b: 160 59% 30%;   /* green   */
    --ev-c: 35 86% 38%;    /* amber   */
    --ev-d: 275 38% 48%;   /* violet  */
    --ev-e: 190 78% 30%;   /* teal    */
    --ev-f: 25 52% 36%;    /* umber   */
    --ev-fill: 0.18;       /* fill alpha over an image */

    /* charts — same family, no rainbow */
    --chart-1: 230 38% 48%;
    --chart-2: 190 78% 30%;
    --chart-3: 160 59% 30%;
    --chart-4: 35 86% 38%;
    --chart-5: 275 38% 48%;

    /* sidebar (shadcn sidebar tokens) */
    --sidebar-background:        220 21% 96%;
    --sidebar-foreground:        218 22% 10%;
    --sidebar-primary:           230 38% 48%;
    --sidebar-primary-foreground:0 0% 100%;
    --sidebar-accent:            220 21% 92%;
    --sidebar-accent-foreground: 218 22% 10%;
    --sidebar-border:            218 19% 89%;
    --sidebar-ring:              230 38% 48%;

    --radius: 0.375rem;   /* 6px — controls */
  }
}
```

### 2.3 Tokens — dark

```css
@layer base {
  .dark {
    --background:            220 18% 8%;
    --foreground:            220 20% 96%;
    --card:                  220 16% 11%;
    --card-foreground:       220 20% 96%;
    --popover:               220 16% 12%;
    --popover-foreground:    220 20% 96%;
    --muted:                 220 14% 16%;
    --muted-foreground:      217 12% 62%;
    --accent:                220 14% 18%;
    --accent-foreground:     220 20% 96%;
    --border:                218 14% 20%;
    --input:                 218 14% 22%;
    --ring:                  230 60% 68%;

    --primary:               230 60% 68%;   /* indigo lifts on dark */
    --primary-foreground:    220 25% 10%;
    --secondary:             220 14% 18%;
    --secondary-foreground:  220 20% 96%;
    --destructive:           4 72% 62%;
    --destructive-foreground:220 25% 10%;

    --settled:               160 48% 48%;
    --settled-foreground:    220 25% 10%;
    --settled-subtle:        160 30% 16%;
    --caution:               38 82% 58%;
    --caution-foreground:    220 25% 10%;
    --caution-subtle:        38 40% 16%;
    --machine-subtle:        230 30% 20%;
    --marker-subtle:         4 32% 20%;

    --viewer-surround:       220 10% 24%;

    --ev-a: 230 60% 68%;
    --ev-b: 160 48% 52%;
    --ev-c: 38 82% 58%;
    --ev-d: 275 55% 68%;
    --ev-e: 190 60% 52%;
    --ev-f: 25 45% 56%;
    --ev-fill: 0.26;

    --chart-1: 230 60% 68%;
    --chart-2: 190 60% 52%;
    --chart-3: 160 48% 52%;
    --chart-4: 38 82% 58%;
    --chart-5: 275 55% 68%;

    --sidebar-background:        220 18% 10%;
    --sidebar-foreground:        220 20% 96%;
    --sidebar-primary:           230 60% 68%;
    --sidebar-primary-foreground:220 25% 10%;
    --sidebar-accent:            220 14% 16%;
    --sidebar-accent-foreground: 220 20% 96%;
    --sidebar-border:            218 14% 20%;
    --sidebar-ring:              230 60% 68%;
  }
}
```

### 2.4 Usage rules

- **One accent hue.** Indigo. Everything else is a state, not decoration.
- **Red is reserved.** Marker annotations and destructive actions. Never for errors in form validation — those use `--destructive` text and border, which is the same token used intentionally, but never a red *fill* on a non-destructive control.
- **Green appears exactly once per flow:** on a finalised mark. Do not use it for toasts, checkmarks, or "saved" states — those are neutral.
- **Amber is not a warning triangle.** It means "a person needs to look at this", which is a routine, expected state, not an alarm. Style it calmly.
- **Subtle variants** (`--*-subtle`) are for backgrounds behind text of the same hue. Never put full-strength state colour behind body text.
- **Never tint a whole surface.** Cards are `--card`. State is communicated by a 2px left border, a pill, or an icon — not by a coloured panel.

### 2.5 Evidence tints

Six categorical tints, used only over page photographs and their matching transcript lines.

Rules:
1. **Never rely on hue alone.** Each tint is always paired with a letter badge (A–F) and a distinct outline dash pattern (`solid`, `4 2`, `2 2`, `6 2 2 2`, `1 3`, `8 3`).
2. Fill at `--ev-fill` alpha; outline at full strength, 2px.
3. Assignment is by marking-point order within the question, stable across renders. A point that is A on first load is A forever.
4. More than six marking points visible at once: reuse tints but never adjacent, and the letter badge disambiguates.
5. High-contrast mode (user setting) drops fills to 0 and raises outlines to 3px.

### 2.6 The mark

Solid, single colour, no gradient. A rounded square with a diagonal rule through it — the marker's tick abstracted, at 32px it reads as a stamped page corner.

```tsx
export function Mark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <rect x="2" y="2" width="28" height="28" rx="7" fill="hsl(var(--primary))" />
      <path
        d="M10 16.5l4.2 4.2L22 12"
        stroke="hsl(var(--primary-foreground))"
        strokeWidth="2.6"
        strokeLinecap="square"
        fill="none"
      />
    </svg>
  );
}
```

Square line caps, not round. Round caps read as friendly consumer software; square reads as a stamp. That is the correct register for an examinations instrument.

---

## 3. Typography

### 3.1 Faces

| Role | Face | Why |
|---|---|---|
| UI, body, headings | **IBM Plex Sans** | Institutional rather than startup-neutral. Designed as a corporate/technical face, so it carries the right register for an examinations product without being characterless. Deliberately not Inter — Inter is the default everyone reaches for. |
| Marks, IDs, confidences, timestamps, code | **IBM Plex Mono** | Every number in this product is data. Tabular figures mean marks don't jitter as they change and columns align down a results table. |
| Table column headers | IBM Plex Sans Condensed, 11px, `letter-spacing: .06em`, uppercase | Buys horizontal room in dense tables without shrinking the type further |

**Never use a handwriting, script, or "friendly" rounded face anywhere.** Beyond taste, it would appear on the same screen as actual student handwriting. That is a functional hazard.

```css
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {
  --font-sans: "IBM Plex Sans", ui-sans-serif, system-ui, sans-serif;
  --font-cond: "IBM Plex Sans Condensed", var(--font-sans);
  --font-mono: "IBM Plex Mono", ui-monospace, "SF Mono", monospace;
}

body { font-family: var(--font-sans); }

/* every numeral in the product */
.tabular, table, [data-numeric] {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
```

Self-host in production. Google Fonts adds a third-party request and a privacy question a university will ask about.

### 3.2 Scale

| Token | Size / line | Weight | Use |
|---|---|---|---|
| `text-caption` | 11 / 16 | 500 | Table headers, metadata, keyboard hints |
| `text-xs` | 12 / 16 | 400 | Timestamps, helper text |
| `text-sm` | 13 / 18 | 400 | Sidebar items, table cells, dense UI |
| `text-base` | 15 / 22 | 400 | Body, form fields, most interface text |
| `text-lead` | 17 / 26 | 400 | Auth card body, empty-state descriptions |
| `text-h3` | 20 / 26 | 600 | Card and section titles |
| `text-h2` | 26 / 32 | 600 | Page titles |
| `text-h1` | 34 / 40 | 600 | Auth card headings, dashboard greeting |
| `text-mark` | 28 / 32 | 500, mono | The mark itself in the workspace |

Three weights only: 400, 500, 600. No 300, no 700, no 800. Weight range is where interfaces start to look assembled rather than designed.

### 3.3 Rules

- Sentence case everywhere, including buttons and headings. No Title Case.
- No all-caps except `text-caption` table headers.
- Measure caps at 68 characters for prose; the transcript pane is exempt because it must match the physical line breaks of the script.
- Never centre body text. Auth card headings are the only centred type in the product, and only at `text-h1`.
- No letter-spacing adjustments except the condensed table header.

### 3.4 The page viewer surround

`--viewer-surround` is a mid-neutral in both themes. Reason: a page photograph judged against a pure white background reads as darker than it is, and against pure black reads as blown out. A mid-neutral surround is standard practice in any tool where you assess an image, and here the assessment is whether handwriting is legible. This token does not follow the theme.

---

## 4. Space, shape, elevation

### 4.1 Spacing

8px base. Permitted values only: `2 4 6 8 12 16 20 24 32 40 48 64`. Nothing else. If a layout needs 18px, it needs 16 or 20.

| Context | Padding |
|---|---|
| Control internal (button, input) | 8 / 12 |
| Card | 20, or 16 in compact density |
| Page gutter, Console | 24 |
| Page gutter, Capture | 16 |
| Section gap | 24 |
| Related item gap | 8 |
| Form field gap | 16 |

### 4.2 Radius

| Token | Value | Use |
|---|---|---|
| `rounded-sm` | 4px | Badges, keyboard hints, tags |
| `rounded` (`--radius`) | 6px | Buttons, inputs, selects, menu items |
| `rounded-lg` | 8px | Cards, panels, dialogs |
| `rounded-full` | — | Status pills, avatars, stepper nodes only |

**Ceiling is 8px on containers.** Larger radii read as consumer software and, at this density, waste corner space. No `rounded-xl`, no `rounded-2xl`, no `rounded-3xl` anywhere in Console.

### 4.3 Elevation

Three levels. Borders do most of the work; shadows are a last resort.

```css
--shadow-1: 0 1px 2px hsl(220 20% 12% / .06);                                  /* raised card */
--shadow-2: 0 2px 4px hsl(220 20% 12% / .06), 0 8px 16px hsl(220 20% 12% / .06); /* popover, dropdown */
--shadow-3: 0 8px 24px hsl(220 20% 12% / .12), 0 2px 6px hsl(220 20% 12% / .08); /* dialog, sheet */
```

- Cards in a list: **border only, no shadow.** Twelve shadowed cards in a grid is the most reliable tell of a templated design.
- Dark theme: shadows barely register. Use a 1px lighter top border on raised surfaces instead.
- No inner shadows, no coloured shadows, no glow.

### 4.4 Density

Two modes, user-selectable in Display settings.

| | Comfortable | Compact |
|---|---|---|
| Table row | 44px | 36px |
| Control height | 36px | 32px |
| Card padding | 20px | 16px |
| Base type | 15px | 14px |

Authoring and admin default to comfortable. Marking queue, results table, and audit log default to compact. The review workspace is always compact — space there belongs to the script.

---

## 5. Motion

Almost none, on purpose. A marker sees each transition 300 times per exam. Anything decorative becomes an irritant by script 40.

| Token | Duration | Curve | Use |
|---|---|---|---|
| `--m-instant` | 0ms | — | State that must feel like a physical switch: checkbox, mark award toggle |
| `--m-quick` | 120ms | `ease-out` | Hover, focus, colour change, tooltip |
| `--m-panel` | 180ms | `cubic-bezier(.2,.8,.2,1)` | Sheets, dropdowns, sidebar collapse |
| `--m-evidence` | 140ms staged | `cubic-bezier(.2,.8,.2,1)` | The one signature moment, below |

**The evidence link — the only orchestrated animation in the product.** Hovering or focusing a marking point:

1. `0ms` — the marking point's row raises to `--machine-subtle`
2. `0ms` — matching transcript lines fill with their evidence tint
3. `60ms` — the region on the page photograph fills and outlines

The 60ms offset is deliberate: the eye follows the connection from scheme, to text, to handwriting. It is the moment that turns "the system says 7" into "I can see why." Under `prefers-reduced-motion` both tints appear together at 0ms.

**Banned:** page transitions, card lift on hover, skeleton shimmer, parallax, scroll-triggered reveals, spring physics anywhere in Console, staggered list entrance, number count-up. Capture may use a single spring on the capture-confirm haptic pulse.

Do not install `motion` in Console. It is a dependency for the marketing site only.

---

## 6. Icons

**Lucide**, exclusively. One pack, no exceptions, no custom SVGs except the mark and the fiducial guide overlay.

```
strokeWidth  1.5 default · 2 for 14px and below
size         14 inline · 16 dense UI · 18 buttons and sidebar · 20 page headers · 24 empty states
colour       inherits currentColor; never coloured independently of its label
```

- Icons never appear alone without an accessible label.
- Icons in buttons only where the icon *is* the object of the action (`Download`, `Upload`, `Trash`). Never as decoration on a text button.
- **No sparkle, wand, star, or robot iconography anywhere.** The entire thesis of this product is that its suggestions are auditable rather than magical. A sparkle icon contradicts the thing you are trying to prove, and it is the single most common visual tell of AI-adjacent software.

### 6.1 Domain icon map

| Concept | Icon |
|---|---|
| Home | `LayoutDashboard` |
| Course | `BookMarked` |
| Exam | `FileText` |
| Question | `ListOrdered` |
| Rubric / marking scheme | `ClipboardList` |
| Marking point | `Check` / `X` / `AlertTriangle` (contradicted) |
| Booklet | `Files` |
| Upload | `Upload` |
| Capture | `Camera` |
| Processing | `Loader` (animated) / `Cpu` |
| Marking | `PenLine` |
| Transcription | `Type` |
| Moderation | `UsersRound` |
| Results | `Table2` |
| Statistics | `BarChart3` |
| Integrity flag | `ShieldAlert` |
| Audit | `History` |
| Chain verified | `ShieldCheck` |
| Analytics | `Activity` |
| Admin | `Settings2` |
| Confidence | no icon — a meter, never a symbol |
| Suggestion | no icon — the word "Suggested" |

---

## 7. Component library

### 7.1 Setup

```bash
npx shadcn@latest init
# style: new-york · base colour: slate · CSS variables: yes
```

Then replace the generated `:root` and `.dark` blocks with §2.2 and §2.3.

```bash
npx shadcn@latest add \
  alert alert-dialog avatar badge breadcrumb button calendar card checkbox \
  collapsible command dialog dropdown-menu form hover-card input input-otp \
  label pagination popover progress radio-group resizable scroll-area select \
  separator sheet sidebar skeleton slider sonner switch table tabs textarea \
  toggle toggle-group tooltip chart
```

```bash
npm i lucide-react class-variance-authority clsx tailwind-merge \
      react-hook-form @hookform/resolvers zod \
      @tanstack/react-table @tanstack/react-virtual \
      date-fns sonner vaul
```

| Package | For | Where |
|---|---|---|
| `@tanstack/react-table` + `react-virtual` | Results table, marking queue, audit log — 300+ rows must virtualise | Console |
| `react-hook-form` + `zod` | Every form. Validation schemas mirror the API's Pydantic models. | Both |
| `vaul` | Bottom sheets in Capture | Capture |
| `sonner` | Toasts | Both |
| `chart` (recharts) | Analytics screens only | Console |

**Not installed:** `motion` / `framer-motion` (marketing site only), any icon pack other than Lucide, any component library other than shadcn.

### 7.2 File structure

```
src/
  components/
    ui/                shadcn primitives — do not edit except to apply tokens
    shell/             AppShell · AppSidebar · TopBar · NavTabs · CommandPalette
    auth/              AuthLayout · AuthCard · ProviderButtons · OtpField
    common/            StatusPill · Stepper · ConfidenceMeter · EmptyState
                       ErrorState · PageHeader · DataTable · ReasonChips
    marking/           ReviewWorkspace · PageViewer · TranscriptPane
                       MarkingSchemePanel · EvidenceLink · MarkInput
                       QuestionRail · DecisionTrace
    rubric/            RubricPointEditor · LintPanel · RubricTestDrive
    capture/           CaptureOverlay · CaptureGuidance · UploadQueueItem
    marketing/         MarketingNav · Hero          (the only place motion lives)
  lib/
    utils.ts           cn()
    permissions.ts     usePermission() — one source for every gated control
```

**Rule:** never edit `components/ui/*` beyond token wiring. Extensions live in `common/`. This keeps `npx shadcn@latest add` upgradeable.

### 7.3 Buttons — the full matrix

One primary action per view. Never two adjacent.

| Variant | Appearance | Use | Example |
|---|---|---|---|
| `default` | Indigo fill, white text | The single main action | `Confirm mark`, `Create exam` |
| `secondary` | Muted fill, ink text | Common alternative to the primary | `Save draft` |
| `outline` | Border, transparent | Neutral actions in a group | `Retake`, `Export` |
| `ghost` | No border, hover fill | Toolbar, table rows, low-emphasis | `Open`, `Edit` |
| `destructive` | Red fill | Irreversible only | `Delete exam`, `Revoke key` |
| `link` | Indigo underline on hover | Inline navigation inside prose | `Forgot your password?` |

| Size | Height | Padding | Type | Use |
|---|---|---|---|---|
| `sm` | 32 | 12 | 13 | Table rows, toolbars |
| `default` | 36 | 16 | 14 | Everywhere |
| `lg` | 44 | 20 | 15 | Auth card, Capture, mobile |
| `icon` | 36×36 | — | — | Icon-only, always with `aria-label` |

Rules:
- Loading state keeps the button's width and swaps the label for `Loader2` spinning plus the present-participle label (`Confirming…`). Never let a button change width mid-action.
- Destructive buttons never sit in the primary position of a dialog unless the dialog exists solely to destroy something.
- Full-width buttons only in Capture, the auth card, and mobile sheets.
- No icon on a `default` button unless the icon is the object of the verb.

### 7.4 Form fields

```
Label            13px / 500 / --foreground, above the field, 6px gap
Field            36px (32 compact), 1px --input border, 6px radius
Focus            2px --ring offset 2px. Never remove the outline.
Helper           12px / --muted-foreground, below, 6px gap
Error            12px / --destructive, replaces helper, with a 14px AlertCircle
Error field      --destructive border, no red fill
Required         no asterisk — mark OPTIONAL fields "(optional)" instead
Disabled         50% opacity, --muted background, cursor not-allowed
```

Marking asterisks on required fields means the eye has to scan for exceptions in the common case. Marking the optional ones inverts that, and there are always fewer of them.

---

## 8. The requested components

### 8.1 `StatusPill`

Small, calm, always the same shape. Reference: your "In progress" screenshot, with the spinner reserved for genuinely live states.

```tsx
// components/common/status-pill.tsx
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

const pill = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 h-[22px] " +
  "text-[11px] font-medium whitespace-nowrap select-none",
  {
    variants: {
      tone: {
        neutral: "border-border bg-muted text-muted-foreground",
        machine: "border-primary/25 bg-[hsl(var(--machine-subtle))] text-primary",
        caution: "border-[hsl(var(--caution))]/25 bg-[hsl(var(--caution-subtle))] text-[hsl(var(--caution))]",
        settled: "border-[hsl(var(--settled))]/25 bg-[hsl(var(--settled-subtle))] text-[hsl(var(--settled))]",
        marker:  "border-destructive/25 bg-[hsl(var(--marker-subtle))] text-destructive",
      },
    },
    defaultVariants: { tone: "neutral" },
  }
);

type Status =
  | "draft" | "open" | "marking" | "moderation" | "closed"
  | "processing" | "ready" | "review" | "manual" | "flagged" | "failed";

const MAP: Record<Status, { label: string; tone: VariantProps<typeof pill>["tone"]; live?: boolean }> = {
  draft:      { label: "Draft",              tone: "neutral" },
  open:       { label: "Open",               tone: "machine" },
  marking:    { label: "Marking",            tone: "machine" },
  moderation: { label: "Moderation",         tone: "caution" },
  closed:     { label: "Closed",             tone: "settled" },
  processing: { label: "Processing",         tone: "machine", live: true },
  ready:      { label: "Ready to confirm",   tone: "machine" },
  review:     { label: "Needs judgement",    tone: "caution" },
  manual:     { label: "Hand-marking only",  tone: "neutral" },
  flagged:    { label: "Flagged",            tone: "marker" },
  failed:     { label: "Failed",             tone: "marker" },
};

export function StatusPill({ status, className }: { status: Status; className?: string }) {
  const s = MAP[status];
  return (
    <span className={cn(pill({ tone: s.tone }), className)}>
      {s.live
        ? <Loader2 className="h-3 w-3 animate-spin" aria-hidden />
        : <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" aria-hidden />}
      {s.label}
    </span>
  );
}
```

Rules: the dot inherits `currentColor` so hue never has to be maintained twice. The spinner appears only when work is genuinely in flight — a spinner on a static state is a lie the user will notice.

### 8.2 `Stepper` — exam creation wizard

Reference: your numbered/checkmark screenshot. Five steps, horizontal on desktop, condensed to a counter on mobile.

```tsx
// components/common/stepper.tsx
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export function Stepper({ steps, current }: { steps: string[]; current: number }) {
  return (
    <>
      {/* mobile */}
      <div className="sm:hidden">
        <p className="text-caption uppercase tracking-wide text-muted-foreground">
          Step {current + 1} of {steps.length}
        </p>
        <p className="text-h3 mt-1">{steps[current]}</p>
      </div>

      {/* desktop */}
      <ol className="hidden sm:flex items-start" aria-label="Progress">
        {steps.map((label, i) => {
          const done = i < current;
          const active = i === current;
          return (
            <li key={label} className={cn("flex items-start", i < steps.length - 1 && "flex-1")}>
              <div className="flex flex-col items-center gap-2 shrink-0">
                <span
                  aria-current={active ? "step" : undefined}
                  className={cn(
                    "flex h-7 w-7 items-center justify-center rounded-full border text-[12px] font-mono transition-colors",
                    done   && "border-primary bg-primary text-primary-foreground",
                    active && "border-primary bg-background text-primary font-semibold",
                    !done && !active && "border-border bg-background text-muted-foreground"
                  )}
                >
                  {done ? <Check className="h-3.5 w-3.5" strokeWidth={2.5} aria-hidden /> : i + 1}
                </span>
                <span className={cn(
                  "text-caption max-w-[104px] text-center leading-tight",
                  active ? "text-foreground font-medium" : "text-muted-foreground"
                )}>
                  {label}
                </span>
              </div>
              {i < steps.length - 1 && (
                <span className={cn("mt-3.5 h-px flex-1 mx-2", done ? "bg-primary" : "bg-border")} />
              )}
            </li>
          );
        })}
      </ol>
    </>
  );
}
```

Used by: exam creation wizard, institution setup, MFA enrolment. Nowhere else — a stepper on a two-step flow is theatre.

### 8.3 `Breadcrumb` — Console top bar

Use shadcn `breadcrumb`. Rules:

- **Breadcrumb and tab strip never occupy the same level.** Breadcrumb lives in the top bar and expresses *where you are in the hierarchy* (Institution → Course → Exam). The tab strip lives under the exam header and expresses *which part of this exam*. They answer different questions.
- Maximum four levels. Beyond that, collapse the middle with `BreadcrumbEllipsis` into a dropdown.
- The last crumb is the current page: `--foreground`, weight 500, not a link.
- Separator is `ChevronRight` at 14px, `--muted-foreground` at 60%.
- On mobile, show only the last two crumbs.

```tsx
<Breadcrumb>
  <BreadcrumbList>
    <BreadcrumbItem><BreadcrumbLink href="/courses">Courses</BreadcrumbLink></BreadcrumbItem>
    <BreadcrumbSeparator />
    <BreadcrumbItem><BreadcrumbLink href="/courses/csm355">CSM 355</BreadcrumbLink></BreadcrumbItem>
    <BreadcrumbSeparator />
    <BreadcrumbItem><BreadcrumbPage>End of Semester</BreadcrumbPage></BreadcrumbItem>
  </BreadcrumbList>
</Breadcrumb>
```

### 8.4 `NavTabs` — the exam strip

**Not Radix `Tabs`.** These are routes. Links with `aria-current`, horizontally scrollable, disabled states carry a tooltip explaining the condition rather than disappearing.

```tsx
// components/shell/nav-tabs.tsx
import { NavLink } from "react-router-dom";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

export type NavTab = {
  to: string;
  label: string;
  count?: number;
  disabled?: boolean;
  disabledReason?: string;
};

export function NavTabs({ tabs }: { tabs: NavTab[] }) {
  return (
    <nav className="border-b border-border" aria-label="Exam sections">
      <ul className="flex gap-1 overflow-x-auto px-1 [&::-webkit-scrollbar]:hidden">
        {tabs.map((t) => {
          const inner = (
            <span className="inline-flex items-center gap-2">
              {t.label}
              {typeof t.count === "number" && t.count > 0 && (
                <span className="rounded-sm bg-muted px-1.5 py-px font-mono text-[11px] text-muted-foreground tabular-nums">
                  {t.count}
                </span>
              )}
            </span>
          );

          if (t.disabled) {
            return (
              <li key={t.to}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span
                      aria-disabled="true"
                      className="inline-flex h-10 cursor-not-allowed items-center border-b-2 border-transparent px-3 text-sm text-muted-foreground/50"
                    >
                      {inner}
                    </span>
                  </TooltipTrigger>
                  <TooltipContent>{t.disabledReason}</TooltipContent>
                </Tooltip>
              </li>
            );
          }

          return (
            <li key={t.to}>
              <NavLink
                to={t.to}
                end
                className={({ isActive }) =>
                  cn(
                    "inline-flex h-10 items-center border-b-2 px-3 text-sm transition-colors",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                    isActive
                      ? "border-primary font-medium text-foreground"
                      : "border-transparent text-muted-foreground hover:border-border hover:text-foreground"
                  )
                }
              >
                {inner}
              </NavLink>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
```

Disabled copy examples — always state the condition, never just "unavailable":
`Available once scripts finish processing` · `Add at least one question first` · `Freeze the rubric to start marking`

### 8.5 `AppSidebar` — Console shell

Built on shadcn `sidebar`. Take these visual details from your reference: the institution switcher at the top, keyboard hints revealed on hover, badge counts on the right, indent guides for nested items.

```tsx
// components/shell/app-sidebar.tsx  (abridged — structure and rules)
<Sidebar collapsible="icon">
  <SidebarHeader>
    <InstitutionSwitcher />   {/* your WorkspaceSwitcher, renamed and re-scoped */}
  </SidebarHeader>

  <SidebarContent>
    <SidebarGroup>
      <SidebarMenu>
        <Item to="/home"    icon={LayoutDashboard} label="Home" />
        <Item to="/courses" icon={BookMarked}      label="Courses" />
        <Item to="/exams"   icon={FileText}        label="Exams" />
      </SidebarMenu>
    </SidebarGroup>

    <SidebarGroup>
      <SidebarGroupLabel>Marking</SidebarGroupLabel>
      <SidebarMenu>
        <Item to="/marking"   icon={PenLine}    label="Marking"  badge={47} />
        <Item to="/results"   icon={Table2}     label="Results" />
        <Item to="/integrity" icon={ShieldAlert} label="Integrity" badge={3} />
      </SidebarMenu>
    </SidebarGroup>

    <SidebarGroup>
      <SidebarGroupLabel>Oversight</SidebarGroupLabel>
      <SidebarMenu>
        <Item to="/analytics" icon={Activity} label="Analytics" />
        <Item to="/audit"     icon={History}  label="Audit" />
      </SidebarMenu>
    </SidebarGroup>
  </SidebarContent>

  <SidebarFooter>
    <Item to="/admin"            icon={Settings2} label="Admin" />
    <Item to="/settings/profile" icon={UserRound} label="Settings" shortcut="⌘," />
    <UserMenu />
  </SidebarFooter>
</Sidebar>
```

Rules:
1. **Groups are filtered by permission, not hidden per item.** If a role has no items in "Oversight", the whole group and its label disappear. A group heading with one orphan item under it looks broken.
2. **Badges on two items only:** Marking (scripts awaiting you) and Integrity (open flags). Badge inflation trains people to ignore badges. Use `--primary` fill for counts, never red — a queue is not an error.
3. **Item height 32px, icon 16px at stroke 1.5, label 13px.** Active state is a `--sidebar-accent` fill with 500 weight, not a coloured left bar; the bar competes with the evidence colour language elsewhere.
4. Keyboard hints render in a `kbd` at 10px mono, revealed on hover, `--muted-foreground` at 60%.
5. Collapsed (icon) mode shows a tooltip on every item. `⌘B` toggles. State persists via cookie — shadcn's sidebar does this already; don't reimplement it.
6. Nested items indent 12px with a 1px `--border` guide line at the parent's icon centre.

### 8.6 `MarketingNav` — public site only

Your `navbar-1`, with the gradient removed and reduced motion. This component does **not** appear in Console or Capture.

```tsx
// components/marketing/marketing-nav.tsx
"use client";
import { useState } from "react";
import { Menu, X } from "lucide-react";
import { Mark } from "@/components/common/mark";
import { Button } from "@/components/ui/button";

const LINKS = [
  { label: "How it works", href: "/how-it-works" },
  { label: "Security",     href: "/security" },
  { label: "For institutions", href: "/institutions" },
  { label: "Docs",         href: "/docs" },
];

export function MarketingNav() {
  const [open, setOpen] = useState(false);
  return (
    <header className="w-full px-4 py-5">
      <div className="mx-auto flex h-14 w-full max-w-5xl items-center justify-between rounded-lg border border-border bg-card px-5 shadow-[var(--shadow-1)]">
        <a href="/" className="flex items-center gap-2.5">
          <Mark className="h-7 w-7" />
          <span className="text-sm font-semibold tracking-tight">Marking Assistant</span>
        </a>

        <nav className="hidden items-center gap-7 md:flex">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href}
               className="text-sm text-muted-foreground transition-colors hover:text-foreground">
              {l.label}
            </a>
          ))}
        </nav>

        <div className="hidden md:block">
          <Button asChild size="sm"><a href="/sign-in">Sign in</a></Button>
        </div>

        <button className="md:hidden" onClick={() => setOpen(true)} aria-label="Open menu">
          <Menu className="h-5 w-5" />
        </button>
      </div>

      {open && (
        <div className="fixed inset-0 z-50 bg-background px-6 pt-6 md:hidden">
          <div className="flex justify-end">
            <button onClick={() => setOpen(false)} aria-label="Close menu">
              <X className="h-5 w-5" />
            </button>
          </div>
          <nav className="mt-8 flex flex-col gap-6">
            {LINKS.map((l) => (
              <a key={l.href} href={l.href} onClick={() => setOpen(false)} className="text-lead">
                {l.label}
              </a>
            ))}
            <Button asChild size="lg" className="mt-2 w-full"><a href="/sign-in">Sign in</a></Button>
          </nav>
        </div>
      )}
    </header>
  );
}
```

Changes from your reference and why: gradient mark replaced with the solid mark; `rounded-full` pill replaced with `rounded-lg` to match the product's 8px ceiling; per-link entrance animations removed (four staggered fades on page load is decoration, not information); `Get Started` replaced with `Sign in`, because institutions are onboarded by agreement, not self-serve, and a button should promise something the product can deliver.

### 8.7 `OtpField` — MFA

Reference: your segmented input screenshot. shadcn `input-otp`, six digits in two groups of three.

```tsx
// components/auth/otp-field.tsx
import { InputOTP, InputOTPGroup, InputOTPSeparator, InputOTPSlot } from "@/components/ui/input-otp";
import { cn } from "@/lib/utils";

export function OtpField({
  value, onChange, onComplete, error,
}: {
  value: string;
  onChange: (v: string) => void;
  onComplete?: (v: string) => void;
  error?: string;
}) {
  return (
    <div className="flex flex-col items-center gap-2">
      <InputOTP
        maxLength={6}
        value={value}
        onChange={onChange}
        onComplete={onComplete}
        aria-label="Six digit verification code"
        aria-invalid={!!error}
      >
        <InputOTPGroup>
          {[0, 1, 2].map((i) => (
            <InputOTPSlot key={i} index={i}
              className={cn("h-12 w-11 font-mono text-lg tabular-nums", error && "border-destructive")} />
          ))}
        </InputOTPGroup>
        <InputOTPSeparator />
        <InputOTPGroup>
          {[3, 4, 5].map((i) => (
            <InputOTPSlot key={i} index={i}
              className={cn("h-12 w-11 font-mono text-lg tabular-nums", error && "border-destructive")} />
          ))}
        </InputOTPGroup>
      </InputOTP>
      {error && <p className="text-xs text-destructive" role="alert">{error}</p>}
    </div>
  );
}
```

Behaviour: auto-advance on entry, backspace moves back, paste fills all six, auto-submit on the sixth digit, focus returns to slot one on error and the value clears. Never disable paste — people copy codes from a password manager.

Error copy: `That code isn't valid. Codes change every 30 seconds — check your app for the current one.`

---

## 9. The auth surface — one layout, five states

Sign in, sign up, reset request, set new password, and MFA all share one card. Only the heading, the body, and the fields change. Same width, same rhythm, same button, same footer. Anyone who signs in once knows how to reset.

### 9.1 Layout

```
┌──────────────────────────────┬───────────────────────────────────────┐
│                              │                                       │
│   [mark]                     │                                       │
│                              │      ┌─────────────────────────┐      │
│   Marking that shows          │      │                         │      │
│   its work.                  │      │   Sign in                │      │
│                              │      │   Use your institution   │      │
│   Every mark this system     │      │   email.                 │      │
│   suggests comes with the    │      │                          │      │
│   sentence it came from.     │      │   [ Microsoft ]          │      │
│                              │      │   [ Google    ]          │      │
│                              │      │   [ SSO       ]          │      │
│                              │      │   ─────  or  ─────       │      │
│                              │      │   Email                  │      │
│                              │      │   [___________________]  │      │
│   KNUST · Department of      │      │   Password    Forgot?    │      │
│   Computer Science           │      │   [___________________]  │      │
│                              │      │                          │      │
│                              │      │   [     Sign in      ]   │      │
│                              │      │                          │      │
│                              │      └─────────────────────────┘      │
│                              │      Terms · Privacy                  │
└──────────────────────────────┴───────────────────────────────────────┘
   40% — brand panel                60% — card, max-width 400px
   hidden below 900px
```

The left panel is a solid `--muted` surface with the mark, one sentence of positioning, and the institution name. No photograph, no illustration, no gradient, no abstract shapes. If it has nothing true to say, it is empty.

### 9.2 Shared card

```tsx
// components/auth/auth-card.tsx
export function AuthCard({
  title, description, children, footer,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <div className="w-full max-w-[400px]">
      <div className="rounded-lg border border-border bg-card p-8 shadow-[var(--shadow-1)]">
        <h1 className="text-h1 tracking-tight">{title}</h1>
        {description && (
          <p className="mt-2 text-lead text-muted-foreground">{description}</p>
        )}
        <div className="mt-7 flex flex-col gap-4">{children}</div>
      </div>
      {footer && (
        <p className="mt-5 text-center text-xs text-muted-foreground">{footer}</p>
      )}
    </div>
  );
}
```

### 9.3 The five states

| Route | Title | Description | Fields | Primary | Footer |
|---|---|---|---|---|---|
| `/sign-in` | Sign in | Use your institution email. | Providers · email · password | `Sign in` | Terms · Privacy |
| `/invite/:token` | Set up your account | K. Osei invited you to KNUST as a lecturer. | Name · password | `Create account` | Terms · Privacy |
| `/forgot-password` | Reset your password | We'll email you a link to set a new one. | Email | `Send reset link` | `Back to sign in` |
| `/reset-password/:t` | Set a new password | Choose something you haven't used here before. | Password · confirm | `Set new password` | `Back to sign in` |
| `/mfa` | Enter your code | Open your authenticator app and enter the six-digit code. | `OtpField` | `Verify` | `Use a recovery code` |

Notes:
- There is **no public sign-up.** Accounts are created by invitation from an exams officer or admin. Institutions are onboarded by agreement. A "Create account" link on the sign-in page would be a lie about how the product is sold.
- After `Send reset link`, the card is replaced in place — same card, no navigation — with `Check your email` and `We sent a link to ama@knust.edu.gh. It expires in 30 minutes.` plus a `Send it again` link disabled for 60 seconds.

### 9.4 Identity providers

```
Microsoft   — most Ghanaian and international universities run Microsoft 365
Google      — common for smaller departments and Google Workspace institutions
SSO         — SAML / OIDC for institutions with their own IdP
```

Apple sign-in is removed from your reference — no institution issues Apple IDs to staff.

Provider buttons are `outline` variant, `lg` size, full width, stacked, with the provider's official mark at 18px and a plain label (`Continue with Microsoft`). Never restyle a provider's logo, never recolour it, never put it in a coloured button — most providers' brand terms forbid it.

**Security note that affects the backend spec:** offering institutional SSO changes the auth model. When SSO is used, MFA is enforced by the institution's IdP, not by us, and our own MFA screen is skipped for those accounts. Roles still come from our `user_roles` table, never from IdP claims. Record this in the auth section of the engineering spec before building.

### 9.5 Password field

- `type="password"` with an eye toggle at 16px on the right, `aria-label="Show password"` / `"Hide password"`.
- `Forgot your password?` sits on the label row, right-aligned, `link` variant, 12px. Not below the field — below the field it competes with the error message for the same space.
- Strength meter appears only on *setting* a password, never on entering one. Four segments, `--muted` to `--settled`, with a plain-language rule beneath: `At least 12 characters.`

---

## 10. The two shells

### 10.1 Console

```
┌────────────┬──────────────────────────────────────────────────────────┐
│            │  Courses › CSM 355 › End of Semester        ⌕  ⌥  AM ▾  │ 52px
│  Sidebar   ├──────────────────────────────────────────────────────────┤
│  260px     │  CSM 355 — End of Semester        [Marking]   [Actions]  │ 72px
│  (56px     │  Operating Systems · 2025/26 · 8 questions · 80 marks    │
│  collapsed)├──────────────────────────────────────────────────────────┤
│            │  Overview │ Questions │ Booklets │ Upload │ Marking │ …  │ 40px
│            ├──────────────────────────────────────────────────────────┤
│            │                                                          │
│            │  Content, 24px gutter, max-width 1440px                  │
│            │                                                          │
└────────────┴──────────────────────────────────────────────────────────┘
```

- Top bar: breadcrumb left; search (`⌘K`), notifications, user menu right. 52px, `--card` background, 1px bottom border.
- Page header: title, `StatusPill`, primary action. 72px. Scrolls away; the top bar does not.
- The review workspace replaces everything below the top bar and runs full-bleed. It has no page header and no tab strip — the question rail serves that role, and screen space belongs to the script.

### 10.2 Capture

```
┌─────────────────────┐
│ ✕      CSM 355   ⚡ │  48px, transparent over the viewfinder
├─────────────────────┤
│                     │
│   viewfinder,       │
│   full bleed,       │
│   fiducial overlay  │
│                     │
├─────────────────────┤
│  Booklet 4A1E · p3  │  read live from the QR
│  Hold steady        │  one guidance line, never a list
│                     │
│   [12]    ( ● )     │  capture button 72px, thumb zone
│  queued             │
└─────────────────────┘
```

- No sidebar, no breadcrumb, no tab strip. Navigation is `←` back and the queue count.
- Every touch target 44px minimum; the capture button is 72px and is the largest element on screen.
- Bottom sheets (`vaul`) for the queue, exam picker, and settings. Never a centred dialog on mobile — it fights the keyboard and the thumb.
- Guidance line: one message, `text-base`, on a translucent `--foreground` at 70% backdrop so it stays readable over any scene. This is the only backdrop blur permitted in the product.

---

## 11. Domain components

Visual specifications. Behaviour is in the front-end structure document.

### `ConfidenceMeter`
Four labelled segments plus an overall value. Never a single blended bar — a mean hides which stage is uncertain, and that is the actionable information.

```
Photo     ████████░░  0.94
Reading   ████████░░  0.91
Meaning   ██████░░░░  0.78   ← lowest, tinted --caution
Overall               0.78   ← the minimum, not the mean, in mono
```
Segments are `--primary` above 0.85, `--caution` from 0.70 to 0.85, `--destructive` below. The lowest segment carries the tint; the others stay neutral, so the eye lands on the problem.

### `MarkInput`
```
Suggested 4 of 8          ← 13px, --muted-foreground, mono numerals
Your mark  [ 4.0 ] / 8    ← 28px mono, 72px-wide field, arrow keys step by 0.5
```
When the value differs from the suggestion, the field border turns `--destructive` and a `ReasonChips` row appears beneath. Red here is correct and meaningful: a human changed it.

### `EvidenceLink`
The signature interaction (§5). Not a component so much as a coordinated state: `hoveredMarkingPointId` lives in the workspace store; the marking scheme row, the transcript lines, and the page viewer overlay all subscribe. No prop drilling, no DOM measurement, no drawn connector lines — tint and offset alone carry the connection.

### `PageViewer`
Surround `--viewer-surround`. Controls bottom-right in a floating `--card` group at 32px: zoom out, zoom in, fit, rotate, original/cleaned toggle. Scroll to pan, `⌘`+scroll to zoom, double-click to zoom to a region. Evidence overlay is an SVG layer in image coordinates, transformed with the image so it never drifts.

### `TranscriptPane`
Line numbers in mono at 11px, `--muted-foreground`, 32px gutter. Line confidence shown as a 2px left bar, `--border` above 0.9 and `--caution` below — never as text colour, which would make low-confidence lines harder to read at exactly the moment they most need reading.
Struck-through lines: 50% opacity with `line-through`, followed by `Crossed out — not counted` at 11px.
Non-text regions: a dashed `--border` box with `Drawing — not read` at 12px.

### `MarkingSchemePanel`
One row per marking point. Left: award state icon (`Check` in `--settled`, `X` in `--muted-foreground`, `AlertTriangle` in `--caution` for contradicted). Centre: statement at 13px. Right: `2/2` in mono. Below, at 11px `--muted-foreground`: `from line 2` as a link that scrolls the transcript and the page image.
Row hover raises `--machine-subtle` and fires the evidence link.

### `QuestionRail`
Horizontal strip above the workspace. One chip per question, 28px tall, showing the number and a state dot. Current question has a `--primary` bottom border. `←`/`→` move between them. Same construction as `NavTabs` but at chip scale.

### `DecisionTrace`
A monospaced, indented list of rule evaluations, collapsed by default behind `Show how this was calculated`. Each line: rule id, inputs, output. This is the artefact that answers an appeal — style it as a record, not as a debug dump: `--card` surface, 12px mono, generous line height, no syntax colouring.

---

## 12. Patterns

### 12.1 Empty, loading, error

| State | Construction |
|---|---|
| **Loading** | Skeletons matching the final layout. Tables show five skeleton rows at the real row height. Never a centred spinner on a full page. Never a shimmer animation. |
| **Empty (nothing yet)** | 24px icon in `--muted-foreground`, `text-h3` line, one `text-base` sentence, one primary button. Centred in the content area, max-width 360px. |
| **Empty (filtered out)** | Different component. Same layout, but the action is `Clear filters` and the copy names the filters. |
| **Error** | `AlertCircle` at 20px in `--destructive`, what happened, what to do, a `Try again` button. Never a stack trace, never an error code alone — a code may accompany plain language for support. |
| **Offline** | A `--caution-subtle` bar under the top bar. Says what still works. |
| **Partial** | Content renders; a `--caution-subtle` inline alert above names what is missing and offers `Retry`. |

### 12.2 Tables

- `@tanstack/react-table`, virtualised above 100 rows.
- Sticky header, `--card` background, `text-caption` uppercase condensed labels.
- Row height 44 comfortable / 36 compact. Zebra striping is **not** used — a 1px `--border` bottom rule is enough and stripes fight the status pills.
- Numeric columns right-aligned, mono, tabular.
- Row hover: `--muted` fill. Selected: `--machine-subtle` fill with a 2px `--primary` left border.
- Actions in the last column as a `ghost` `icon` button opening a dropdown. Never more than one visible action per row.
- Bulk selection reveals a sticky footer bar with the count and available actions, not a floating toolbar.

### 12.3 Dialogs and sheets

- Console: `Dialog`, max-width 480 (confirm) / 640 (form) / 800 (rubric test-drive). Sheet from the right for anything with a form longer than six fields.
- Capture: `vaul` bottom sheet. Never `Dialog`.
- Title states the action, primary button repeats the same verb: trigger `Freeze rubric` → dialog title `Freeze rubric` → primary `Freeze rubric` → toast `Rubric frozen.`
- Destructive dialogs: `AlertDialog`, `Cancel` on the left, destructive primary on the right, and for anything with dependents, a type-to-confirm field.
- One dialog at a time. Never a dialog opened from a dialog.

### 12.4 Toasts

`sonner`, bottom-right in Console, top in Capture. Neutral surface, no colour fill. Success toasts get no icon and no green — completing an action is the expected case, not a celebration. Errors get `AlertCircle` in `--destructive`.

Duration: 4s default, 8s if it carries an action, indefinite for errors with a retry.
Never toast something the user can already see happen on screen.

### 12.5 Permission-gated controls

```tsx
const can = usePermission();
{can("marks.finalise") && <Button>Finalise marks</Button>}
```
Hidden by default. Disabled-with-tooltip only where absence would be confusing — a `Finalise marks` button that vanishes for a TA is fine; a `Marking` tab that vanishes makes the workflow incomprehensible.

---

## 13. Writing

Words are design material here, not decoration. The product's whole claim is that it is honest about what it knows, and the copy is where that claim is kept or broken.

### 13.1 Voice

Plain, exact, unhurried. A capable colleague explaining something, not a brand talking. No enthusiasm, no apology, no jokes. The subject is someone's degree classification.

### 13.2 Rules

1. **Name things by what people control.** "What must the student say?" not "marking point statement". "Photos waiting" not "upload queue depth".
2. **A verb keeps its name across the whole flow.** Button, dialog title, primary button, toast — the same word.
3. **Never present a suggestion as a decision.** `Suggested 4 of 8`, never `Score: 4/8`. The marker's field is labelled `Your mark`.
4. **Errors say what happened and what to do.** No "Oops", no "Something went wrong", no apology, no exclamation marks.
5. **Empty states are invitations**, with exactly one action.
6. **Say what the system did not do** when that is the reassuring part — especially on integrity flags.
7. **Explain confidence in words next to the number.** `Needs your judgement — the meaning step wasn't confident here` does more work than `0.78`.
8. **Sentence case. Active voice. Present tense. Second person.**
9. **No emoji anywhere**, including in toasts, empty states, and notification emails.
10. **Numbers as numerals** from zero up, because they are all data: `4 of 8`, `3 flagged`, `0 failed`.

### 13.3 Button labels

| Never | Always |
|---|---|
| Submit | `Send reset link`, `Create exam`, `Confirm mark` |
| OK | The verb the dialog is about |
| Yes / No | `Freeze rubric` / `Cancel` |
| Save | `Save changes`, `Save draft`, `Save mark` |
| Learn more | `How confidence works` |
| Get started | `Sign in` |
| Continue | `Continue` is fine in a wizard, nowhere else |

### 13.4 The string table

Ship these exactly. They carry the product's position.

| Where | String |
|---|---|
| Suggestion header | `Suggested 4 of 8` |
| Marker's field label | `Your mark` |
| Low confidence | `Needs your judgement — the meaning step wasn't confident here` |
| No suggestion offered | `No suggestion for this one. The handwriting was too unclear to read reliably — here's the script and the marking scheme.` |
| Crossed-out text | `Crossed out — not counted` |
| Non-text region | `Drawing — not read. Mark this by hand.` |
| Unreadable line | `Couldn't read this. Type what it says` |
| Integrity flag | `This script contains text that looks like an instruction to the system. It was recorded as written and changed no marks.` |
| Frozen rubric | `Frozen on 12 June. 312 scripts were marked using this version, so it can't change.` |
| Offline capture | `You're offline. Keep capturing — photos will upload when you're back.` |
| Reveal identities | `This links booklet codes to student names. It can't be undone and it's recorded in the audit log.` |
| Spend cap reached | `Processing stopped. This month's AI budget is spent. Raise the cap to continue.` |
| Batch confirm gate | `Spot-check these 20 before confirming the rest. This keeps the batch defensible.` |
| Narrow screen | `Marking needs a wider screen. Open this on a laptop or desktop.` |
| Sign-in failure | `That email and password don't match. Try again, or reset your password.` |
| Account locked | `Too many attempts. Try again in 4 minutes.` |
| Reset sent | `We sent a link to ama@knust.edu.gh. It expires in 30 minutes.` |
| Empty exams | `No exams yet. Create one to get started.` |
| Empty after filter | `No scripts match these filters.` + `Clear filters` |
| Generic load failure | `Couldn't load the marking queue. Check your connection and try again.` |

### 13.5 Words we do not use

`AI` in the interface (say *the system*, or name the step: *reading*, *meaning*) · `smart` · `magic` · `automatically graded` · `powered by` · `seamless` · `effortless` · `simply` · `just` · `oops` · `whoops` · `awesome` · `great!`

The reason for the first one is substantive. This product's defence is that its output is traceable, deterministic, and human-confirmed. Labelling things "AI" in the interface invites exactly the mistrust the architecture was built to avoid, and it obscures which step is responsible when something goes wrong.

---

## 14. Accessibility floor

Non-negotiable. Several items have direct functional payoff beyond compliance.

- Contrast 4.5:1 for text, 3:1 for control boundaries and evidence outlines over photographs. Verify `--muted-foreground` on `--muted` specifically; it is the pairing most likely to fail.
- **Evidence never depends on hue alone.** Letter badge plus outline dash pattern, always. High-contrast evidence mode in Display settings.
- Full keyboard operation for every flow including the workspace, capture queue, and all dialogs. Visible focus ring everywhere. Never `outline: none` without a replacement.
- Focus management: dialogs trap and restore; route changes move focus to the `h1`; the workspace announces question changes politely.
- Live regions: processing progress and save confirmations `polite`; the spend-cap stop and audit-chain failure `assertive`.
- One `h1` per screen. Real landmarks. Real `<table>`. Real `<button>`.
- Page images carry a meaningful label: `Booklet 4A1E page 3, question 3(a)`.
- 200% text scaling without horizontal scroll everywhere except the review workspace, which is explicitly exempt and says so.
- `prefers-reduced-motion` disables the staged evidence link and all transitions above 0ms.
- Touch targets 44px minimum in Capture.

---

## 15. Anti-generic checklist

Run this before any screen ships. Each line exists because it is a common tell.

**Colour**
- [ ] No gradients anywhere — not on the logo, buttons, text, backgrounds, or borders
- [ ] Exactly one accent hue; everything else is a semantic state
- [ ] No purple-to-pink, no coral-to-orange, no terracotta accent
- [ ] Red appears only for human annotations and destructive actions
- [ ] No coloured panel backgrounds behind body text

**Shape and depth**
- [ ] No radius above 8px on containers
- [ ] No shadows on cards inside a list or grid
- [ ] No glassmorphism or backdrop blur except the command palette scrim and the Capture guidance line
- [ ] No decorative blobs, orbs, mesh, noise, or dot-grid backgrounds

**Type**
- [ ] Three weights only
- [ ] No Title Case
- [ ] Every numeral in mono with tabular figures
- [ ] No centred body text

**Motion**
- [ ] No entrance animations on lists, cards, or nav items
- [ ] No hover lift or scale on cards
- [ ] No skeleton shimmer
- [ ] No count-up numbers

**Icons and imagery**
- [ ] Lucide only
- [ ] No sparkle, wand, star, brain, or robot icons
- [ ] No stock photography, no 3D renders, no isometric illustrations
- [ ] Empty states use a single line icon, not an illustration

**Copy**
- [ ] No emoji
- [ ] No exclamation marks
- [ ] The word "AI" does not appear in the interface
- [ ] No "Oops", "Simply", "Just", "Seamless", "Powered by"
- [ ] Every button label is a verb phrase naming its own outcome

---

## 16. Handoff and QA

**Before a screen is called done:**

- [ ] Light and dark both correct, including the `--viewer-surround` exception
- [ ] Comfortable and compact density both correct
- [ ] All six states built: loading, empty, filtered-empty, error, offline, partial
- [ ] Keyboard path complete; focus order matches visual order
- [ ] Every gated control checked against `usePermission()`
- [ ] Copy matches §13.4 verbatim where a string appears there
- [ ] Anti-generic checklist passed
- [ ] Contrast checked on the actual rendered colours, not the token names
- [ ] 200% text scale, or an explicit documented exemption
- [ ] Tested at 1280px (Console minimum) and 360px (Capture minimum)

**Build order for the design system itself:**

1. Tokens, fonts, `globals.css`, `cn()` — half a day, unblocks everyone
2. shadcn install, button matrix, form fields — one day
3. `AuthLayout` + `AuthCard` + `OtpField` — the five auth states, one day
4. `AppShell`, `AppSidebar`, `TopBar`, `NavTabs`, `Breadcrumb`, `StatusPill` — two days
5. `DataTable`, `EmptyState`, `ErrorState`, `Stepper` — one day
6. Marking domain components — the rest of the time

Steps 1–5 are two days of work that unblock every screen in the product. Do them first and do not let feature work start before step 4 is merged, or you will spend the project reconciling six different sidebars.

---

*Anything not derivable from this file is a gap in this file. Raise it here rather than deciding locally — a design system survives on the fact that there is exactly one answer to each question.*
