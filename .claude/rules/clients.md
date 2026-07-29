---
name: clients
description: The two client apps — console (desktop) and capture (mobile). Shell rules and screen discipline.
globs: "apps/console/**,apps/capture/**"
alwaysApply: false
source: docs/frontend.md §0, §1; docs/design.md §0
---

# Two products, one system

Do not build one responsive app. Build two that share auth, tokens, icons, voice, and
`components/ui` primitives. Shells, navigation, and layout density are **not** shared.

| | **console** | **capture** |
|---|---|---|
| Platform | Desktop web, 1280px and up | Mobile PWA, 360–430px |
| User | Lecturer, TA, exams officer, admin | Lecturer, TA |
| Context | Office, sustained 90-minute sessions | Exam hall, one hand, poor light, weak signal |
| Shell | Sidebar + top bar | Full-bleed, no chrome |
| Input | Keyboard-first | Thumb-first |
| Failure cost | A wrong mark — expensive and silent | A retake — cheap if caught immediately |

**Resolved contradiction:** frontend.md §1 says the non-marking screens are responsive and work
on both; design.md §0 says the shells are separate and console is desktop-only. **design.md
wins.** Console is desktop ≥1280 for every screen it owns; capture is mobile-only. Below 1280
console shows "this screen needs a wider display" rather than a cramped fallback. Marking on a
phone produces bad marking; refusing is correct behaviour.

Do not build a desktop version of the camera.

## Screen discipline

Every screen is specified with: route, who (roles), job, regions, data, actions with
permissions, states (loading/empty/error/offline/partial), modals, keys.

- **If a screen has more than one job, split it into two screens.**
- A proposed screen that cannot be given a job, a state matrix, and a permission belongs inside
  an existing screen.
- Totals for reference: 78 screens, 41 modals, 12 core flows, 4 settings levels. MVP is 26 screens.

## Offline

Capture must work with no connection. IndexedDB upload queue survives connection loss and
process death. Quality pre-check runs on-device before upload — catching a bad photograph in the
exam hall is worth more than any server-side check.

## Never show a bare number

`Suggested 7/10 · needs your confirmation`, never `7/10`. The system reports its own uncertainty
prominently rather than burying it. See [[design-tokens]] for how authorship is coloured.

TypeScript strict. No `any`. Routes are links with `aria-current`, not Radix `Tabs` — the exam
strip switches routes, and Tabs breaks the back button, deep links, and screen-reader semantics.
