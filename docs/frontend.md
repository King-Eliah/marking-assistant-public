# Marking Assistant — Front-End Structure
## Screens, flows, modals, actions, settings, states

**Companion to:** the engineering specification
**Audience:** front-end developers, designers, and whoever writes the interface copy

---

## 0. How to read this

Every screen below is specified as:

- **Route** — the URL
- **Who** — roles that can reach it
- **Job** — the one thing this screen is for
- **Regions** — layout blocks
- **Data** — what it displays
- **Actions** — every button, with its permission
- **States** — loading, empty, error, offline, partial
- **Modals** — what it can open
- **Keys** — keyboard shortcuts

If a screen has more than one **Job**, split it into two screens.

**Totals:** 78 screens · 41 modals · 12 core flows · 4 settings levels.
The MVP subset is 26 screens — marked **[MVP]** throughout.

---

## 1. This is two products sharing one shell

Do not design one responsive app. Design two, and let them share auth, navigation, and design tokens.

| | **Capture** | **Review** |
|---|---|---|
| Device | Phone, held in one hand, script in the other | Desktop, two hands on a keyboard |
| Environment | Exam hall, corridor, poor light, weak signal | Office, stable connection |
| Session | 30 seconds, repeated 300 times | 90 minutes, sustained |
| Interaction | Thumb, one-handed, glanceable | Keyboard-first, dense, information-rich |
| Priority | Speed of capture, instant quality feedback, works offline | Speed of judgement, evidence visible at a glance |
| Failure cost | A retake (cheap, if caught immediately) | A wrong mark (expensive, and silent) |

**Consequences:**

- Capture screens are **mobile-only** and must work with no connection. Do not build a desktop version of the camera.
- The review workspace is **desktop-only** below 1280 px it shows a "this screen needs a wider display" notice rather than a cramped fallback. Marking on a phone produces bad marking; refusing is the correct behaviour.
- Everything else (exams, rubrics, results, admin) is responsive and works on both.

---

## 2. Sitemap

```
/                                  → redirect by role
/sign-in                        [MVP]
/forgot-password
/reset-password/:token
/mfa
/invite/:token
/session-expired
/maintenance

/home                           [MVP]  role-aware dashboard

/courses                        [MVP]
  /courses/new
  /courses/:id                  [MVP]
  /courses/:id/staff
  /courses/:id/settings

/exams                          [MVP]
  /exams/new                    [MVP]  wizard, 5 steps
  /exams/:id                    [MVP]  overview
  /exams/:id/questions          [MVP]
  /exams/:id/questions/:qid     [MVP]
  /exams/:id/rubric             [MVP]
  /exams/:id/rubric/versions
  /exams/:id/rubric/import
  /exams/:id/booklets
  /exams/:id/booklets/register
  /exams/:id/settings
  /exams/:id/upload             [MVP]
  /exams/:id/processing         [MVP]
  /exams/:id/marking            [MVP]  queue
  /exams/:id/marking/:scriptId  [MVP]  ← the review workspace
  /exams/:id/moderation
  /exams/:id/results            [MVP]
  /exams/:id/results/export
  /exams/:id/results/:scriptId  [MVP]  single script report
  /exams/:id/statistics
  /exams/:id/audit

/capture                        [MVP]  mobile only
  /capture/queue                [MVP]
  /capture/assemble

/transcribe/:scriptId           [MVP]

/integrity
  /integrity/:flagId

/analytics/accuracy
/analytics/rubric-health
/analytics/markers
/analytics/usage

/admin/users                    [MVP]
  /admin/users/:id
/admin/roles
/admin/institution
/admin/data
/admin/ai
/admin/spend
/admin/integrations
/admin/health
/admin/jobs                            failed-job triage

/settings/profile               [MVP]
/settings/security              [MVP]
/settings/notifications
/settings/display
/settings/shortcuts
/help
```

---

## 3. Navigation shell

### 3.1 Top bar (persistent)

```
┌────────────────────────────────────────────────────────────────────────┐
│ ☰  MarkAssist   [KNUST ▾]      ⌕ Search        🔔 3   ? Help   AM ▾  │
└────────────────────────────────────────────────────────────────────────┘
   │      │           │              │              │       │        │
   │      │           │              │              │       │        └ user menu
   │      │           │              │              │       └ help panel
   │      │           │              │              └ notification tray
   │      │           │              └ global search (exams, courses, booklet ID)
   │      │           └ institution switcher (only if user belongs to >1)
   │      └ product mark, links to /home
   └ sidebar toggle (collapses to icon rail)
```

**User menu items:** Profile · Security · Notifications · Display · Keyboard shortcuts · Help · Sign out

**Notification tray:** grouped by exam, unread badge, "Mark all read", link to notification settings. Real-time via SSE.

### 3.2 Sidebar (role-filtered)

| Item | Icon | Visible to |
|---|---|---|
| Home | house | all |
| Courses | book | all |
| Exams | file-text | all |
| Marking | pen | LECTURER, TA |
| Results | table | LECTURER, EXAMS_OFFICER, VIEWER |
| Integrity | shield-alert | LECTURER, EXAMS_OFFICER |
| Analytics | chart | LECTURER, EXAMS_OFFICER, ADMIN |
| Audit | history | EXAMS_OFFICER, AUDITOR, ADMIN |
| Admin | settings-2 | ADMIN |

Badge counts appear on **Marking** (scripts awaiting you) and **Integrity** (open flags). Nothing else gets a badge — badge inflation trains people to ignore them.

### 3.3 Exam sub-navigation

Once inside an exam, a horizontal tab strip replaces breadcrumb depth:

```
CSM 355 — End of Semester   ● MARKING
┌──────────┬───────────┬──────────┬────────┬──────────┬─────────┬────────┬───────┐
│ Overview │ Questions │ Booklets │ Upload │ Marking  │ Results │ Audit  │ ⚙     │
└──────────┴───────────┴──────────┴────────┴──────────┴─────────┴────────┴───────┘
                                              ▲ 47
```

Tabs disable with a tooltip explaining why, rather than disappearing — a disabled "Marking" tab saying *"Available once scripts finish processing"* teaches the workflow; a missing tab confuses.

### 3.4 The exam status pill (appears everywhere)

```
DRAFT → OPEN → MARKING → MODERATION → CLOSED
```

Colour-coded, always visible in the exam header. Clicking it opens the **Exam status** modal explaining what the current state permits and what the next transition requires.

---

## 4. Screen inventory

---

## A. Unauthenticated — 9 screens

### A1 · Sign in **[MVP]**
- **Route** `/sign-in` · **Who** public
- **Job** Get an authenticated session.
- **Regions** Left: brand panel with one line about the product. Right: form.
- **Fields** Institution email · Password · "Keep me signed in on this device" checkbox
- **Actions**
  - `Sign in` (primary)
  - `Forgot your password?` (link)
- **States**
  - Loading: button shows a spinner, form disabled
  - Error: *"That email and password don't match. Try again, or reset your password."* — identical message for unknown user and wrong password (no account enumeration)
  - Locked: *"Too many attempts. Try again in 4 minutes."* with a live countdown
  - Offline: *"You're offline. Sign-in needs a connection."*
- **Keys** `Enter` submits

### A2 · Forgot password
- **Route** `/forgot-password`
- **Actions** `Send reset link` · `Back to sign in`
- **Note** Always shows the same confirmation regardless of whether the email exists: *"If that address has an account, a reset link is on its way."*

### A3 · Reset password
- **Route** `/reset-password/:token`
- **Fields** New password with a live strength meter and explicit rules (12+ characters, not a common password)
- **Actions** `Set new password`
- **Error** Expired token → *"This link has expired. Request a new one."* with the request button inline

### A4 · MFA challenge
- **Route** `/mfa`
- **Fields** 6-digit code, auto-advancing inputs, paste-aware
- **Actions** `Verify` · `Use a recovery code` (reveals a second field)
- **Error** *"That code isn't valid. Codes change every 30 seconds — check your app for the current one."*

### A5 · MFA enrolment
- **Route** `/settings/security` (also forced on first sign-in for ADMIN and EXAMS_OFFICER)
- **Regions** QR code · manual entry key · verification field · recovery codes
- **Actions** `Verify and turn on` · `Download recovery codes` (must be acknowledged before continuing)

### A6 · Accept invitation
- **Route** `/invite/:token`
- Shows who invited you, to which institution, in which role. Then set password → MFA if required → land on `/home`.

### A7 · Session expired
- Modal-style full page. `Sign in again` returns to the exact route the user was on, with unsaved review state restored from local storage.

### A8 · Error pages (403 / 404 / 500)
- Each states what happened and offers one route out. 403: *"You don't have access to this. If you think you should, ask your exams officer."*

### A9 · Maintenance
- Static page with an estimated return time and a status link.

---

## B. Onboarding — 3 screens

### B1 · Institution setup wizard
- **Route** `/admin/institution/setup` · **Who** ADMIN, first run only
- **Steps** Institution details → Data region and retention → Invite your first users → AI budget cap → Done
- Each step is skippable except data region, which cannot be changed later without a migration. Say so on the step.

### B2 · Profile setup
- Name, display name, department, timezone. One screen, three fields, skippable.

### B3 · Guided tour
- Overlay coach-marks on `/home`, `/exams/:id/rubric` and the review workspace. Triggered once per role. Dismissible permanently. Re-runnable from Help.

---

## C. Home — 3 screens

### C1 · Lecturer dashboard **[MVP]**
- **Route** `/home` · **Job** Answer "what needs me today?"

```
┌──────────────────────────────────────────────────────────────────────┐
│  Good morning, Ama                                                    │
│                                                                       │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌───────────────┐ │
│  │ 47                  │  │ 12                  │  │ 3             │ │
│  │ scripts waiting     │  │ need your judgement │  │ flagged       │ │
│  │ for review          │  │ (low confidence)    │  │ for integrity │ │
│  │ [Start marking →]   │  │ [Review these →]    │  │ [Look →]      │ │
│  └─────────────────────┘  └─────────────────────┘  └───────────────┘ │
│                                                                       │
│  YOUR EXAMS                                                           │
│  ┌───────────────────────────────────────────────────────────────┐   │
│  │ CSM 355 End of Semester   ● MARKING   ████████░░ 78%  312 scr │   │
│  │ CSM 271 Mid-Semester      ● CLOSED    ██████████ 100% 288 scr │   │
│  │ CSM 483 Resit             ○ DRAFT     rubric not written      │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  RECENT ACTIVITY                                                      │
│  · You confirmed 24 marks in CSM 355            12 minutes ago        │
│  · 60 scripts finished processing               1 hour ago            │
│  · K. Osei added 3 exemplars to MP4 in CSM 355  yesterday             │
└──────────────────────────────────────────────────────────────────────┘
```

- **Actions** `Start marking` · `Review these` · `New exam` · per-exam row click
- **Empty state** *"No exams yet. Create one to get started."* with a single `New exam` button — an empty screen is an invitation to act, not an apology.

### C2 · Exams officer dashboard
- Institution-wide: exams by status, marking progress across departments, scripts stuck in processing, open integrity flags, month-to-date AI spend against cap, markers with unusually high accept-without-change rates.

### C3 · Admin dashboard
- System health, queue depth, provider error rates, spend, user count, failed jobs, audit chain status (green/red — this one is an alert, not a metric).

---

## D. Courses — 3 screens

### D1 · Course list **[MVP]**
- Table: code, title, academic year, exams count, your role. Filter by year and by "mine only". Search.
- **Actions** `New course` · row → detail

### D2 · Course detail **[MVP]**
- Header with code and title. Tabs: Exams · Staff · Settings.
- **Actions** `New exam` · `Edit course` · `Archive course`

### D3 · Course staff & roster
- Assign users to this course with a scoped role (LECTURER, TA, VIEWER). Import a student roster (CSV) used only at identity-reveal time.
- **Actions** `Add staff` · `Import roster` · `Remove` (with confirm modal)

---

## E. Exams — 4 screens

### E1 · Exam list **[MVP]**
- Filters: status, course, year, mine. Sort by date, progress.
- Columns: title, course, status pill, progress bar, scripts, last activity.

### E2 · Exam create wizard **[MVP]**
Five steps with a visible progress rail. Each step saves a draft — closing the browser loses nothing.

```
① Details      title · course · date · total marks · anonymous marking on/off
② Questions    add questions: number, prompt, max marks, answer type
③ Rubric       marking points per question (can be deferred)
④ Booklets     generate booklets? how many? pages per booklet
⑤ Review       summary + validation results + [Create exam]
```

- **Actions per step** `Back` · `Save draft and close` · `Continue`
- **Step 5 blocks creation** if marks don't add up, showing exactly which question is wrong.

### E3 · Exam overview **[MVP]**
- **Job** The exam's control room.

```
┌─────────────────────────────────────────────────────────────────────┐
│ CSM 355 — End of Semester Examination        ● MARKING    [⚙]       │
│ Operating Systems · 2025/26 · 8 questions · 80 marks                │
├─────────────────────────────────────────────────────────────────────┤
│  PROGRESS                                                            │
│  Uploaded    ████████████████████ 312 / 312                         │
│  Processed   ███████████████████░ 308 / 312   4 failed [triage →]   │
│  Reviewed    ██████████████░░░░░░ 241 / 308                         │
│  Finalised   ░░░░░░░░░░░░░░░░░░░░   0 / 308                         │
│                                                                      │
│  ROUTING BREAKDOWN                    NEEDS ATTENTION                │
│  Auto-suggest   198  (64%)            ⚠ 4 scripts failed processing │
│  Manual review   87  (28%)            ⚠ 3 integrity flags           │
│  Manual only     23  (8%)             ⚠ 11 lines need transcription │
│                                                                      │
│  [Continue marking →]   [Upload more]   [Export results]            │
└─────────────────────────────────────────────────────────────────────┘
```

- **Actions** `Continue marking` · `Upload more` · `Export results` · `Change status` (opens status modal) · `Exam settings`

### E4 · Exam settings
- Title, dates, anonymous marking, marking thresholds (bounded by platform floors), who can mark, moderation sampling rate, retention override.
- Dangerous actions in a separate, visually distinct block at the bottom: `Reopen exam` · `Delete exam` — both behind a type-to-confirm modal.

---

## F. Questions & rubric — 6 screens

### F1 · Question list **[MVP]**
- Table: number, prompt (truncated), max marks, answer type, marking points count, auto-markable ✓/✗, lint status.
- A running total against the exam's declared total, with a red mismatch warning.
- **Actions** `Add question` · `Reorder` (drag) · `Duplicate` · `Delete`

### F2 · Question editor **[MVP]**
- Fields: number, prompt, max marks, answer type (dropdown), auto-markable toggle.
- Selecting `DIAGRAM`, `MATH`, or `CODE` **auto-disables** auto-markable and shows an inline note: *"Answers of this type are always marked by hand. The system will show you the answer, not a suggestion."*

### F3 · Rubric builder **[MVP]**
The most important authoring screen. Bad rubrics are the largest source of bad suggestions, so this screen must actively teach.

```
┌────────────────────────────────────────────────────────────────────────┐
│ Q3(a) Explain the four Coffman conditions for deadlock.      6 marks   │
├──────────────────────────────────┬─────────────────────────────────────┤
│ MARKING POINTS      3 of 6 marks │  MP1                                │
│                     allocated    │  ┌───────────────────────────────┐  │
│                                  │  │ Statement                      │  │
│ ⠿ MP1  Mutual exclusion    2 ✓   │  │ States that at least one       │  │
│ ⠿ MP2  Hold and wait       1 ⚠   │  │ resource is held in a non-     │  │
│ ⠿ MP3  No pre-emption      0 ✗   │  │ shareable mode.                │  │
│                                  │  └───────────────────────────────┘  │
│ [+ Add marking point]            │  Marks  [ 2 ]                       │
│                                  │                                     │
│ ─────────────────────────────    │  Ways a student might phrase this   │
│ 3 marks not yet allocated        │  · only one process can use it      │
│                                  │  · the resource cannot be shared    │
│ CHECKS                           │  [+ Add another phrasing]           │
│ ✓ Statements are atomic          │                                     │
│ ⚠ MP2 has only 1 phrasing        │  Advanced ▾                         │
│ ✗ Marks don't total 6            │   Alternatives group   [ — ]        │
│                                  │   Only award if        [ — ]        │
│                                  │   Penalty point        [ ] off      │
│                                  │   Evidence can be shared  [ ] off   │
└──────────────────────────────────┴─────────────────────────────────────┘
```

- **Actions** `Add marking point` · `Add another phrasing` · `Reorder` (drag) · `Delete point` · `Test this rubric` · `Freeze rubric`
- **Live checks panel** runs the rubric linter on every keystroke (debounced). Blocking issues are red and disable `Freeze rubric`; warnings are amber and do not.
- **`Test this rubric`** opens the rubric test-drive modal (M14) — paste a sample answer, see which points it would satisfy and why. This is the single feature that will most improve rubric quality, because it makes the consequence of a vague statement immediate.
- **Copy rule:** never say "marking point statement". Say "What must the student say?" The interface names things by what people control.

### F4 · Rubric checks panel
Not a separate route — a persistent panel in F3. Listed separately because it needs its own design and its own copy:

| Severity | Example message |
|---|---|
| Blocking | *"MP2 says two things at once. Split it into one point per idea so marks can be awarded separately."* |
| Blocking | *"Marks total 5, but Q3(a) is worth 6. Allocate 1 more mark or reduce the question total."* |
| Blocking | *"MP1 and MP4 are nearly identical. They'll compete for the same evidence — merge or reword one."* |
| Warning | *"MP2 has one phrasing. Two or three makes matching much more reliable."* |
| Warning | *"MP5 is worth 4 of 6 marks. Consider splitting it for fairer partial credit."* |

### F5 · Rubric versions & diff
- Timeline of versions with author, date, frozen status, and how many scripts were marked against each.
- Side-by-side diff between any two versions.
- **Actions** `Compare` · `Duplicate as new version` · `View scripts marked with this version`
- A frozen version is read-only and says so with a lock icon and a line explaining why: *"Frozen on 12 June. 312 scripts were marked using this version, so it can't change."*

### F6 · Rubric import
- Paste from a document, upload CSV, or copy from a previous exam.
- Preview table with per-row lint results before committing.
- **Actions** `Preview` · `Import 14 points` · `Cancel`

---

## G. Booklets — 3 screens

### G1 · Booklet generation
- **Fields** How many booklets · pages per booklet · include a cover sheet · question layout (auto from questions, or blank pages)
- **Preview pane** showing page 1 with fiducials and QR
- **Actions** `Generate 320 booklets` · `Download PDF` · `Regenerate`
- **Warning modal** if booklets already exist: regenerating invalidates the previous set.

### G2 · Booklet PDF preview
- Paged preview, print-safety check (margins, DPI, marker contrast), print instructions block: *"Print at 100% scale. Do not fit to page — the corner markers must stay exactly where they are."*

### G3 · Booklet register
- Table of every booklet: ID, issued ✓, scanned ✓, pages received, status.
- **Filters** Not scanned · Incomplete · Duplicate detected
- **Job** answer "which scripts haven't come back?" — the question every exams officer asks.
- **Actions** `Mark as issued` · `Export register` · `Reconcile`

---

## H. Capture & upload — 7 screens

### H1 · Upload (desktop) **[MVP]**
- **Route** `/exams/:id/upload`
- **Job** Get a folder of scans into the system.
- **Regions** Drop zone · file list with per-file status · summary bar
- **Actions** `Choose files` · `Upload 312 files` · `Cancel remaining` · `Retry failed`
- **Per-file row states** Queued · Uploading (progress) · Checking quality · Accepted · Rejected (with reason and a `Replace` action)
- **Empty state** *"Drop scans here, or choose files. JPEG, PNG or PDF, up to 15 MB each."*
- **Warning** if a file's booklet ID already exists: inline, with `Keep the better one` / `Keep both` / `Skip`

### H2 · Capture (mobile) **[MVP]**
- **Route** `/capture` · **Mobile only, full screen, no chrome**

```
┌─────────────────────────┐
│ ✕            CSM 355    │
│                         │
│  ┌───────────────────┐  │
│  │ ▣               ▣ │  │  ← live overlay: guides turn
│  │                   │  │    green when all four corner
│  │   [camera feed]   │  │    markers are detected
│  │                   │  │
│  │ ▣               ▣ │  │
│  └───────────────────┘  │
│                         │
│  Booklet 4A1E · page 3  │  ← read live from the QR
│  ● Hold steady          │  ← live guidance, one line
│                         │
│   [ 12 ]      ◉      ⚡ │
│   queued   capture  flash│
└─────────────────────────┘
```

- **Live guidance line** — one message at a time, never a list:
  `Move closer` · `Hold steady` · `Too dark — find better light` · `Reflection on the page — tilt slightly` · `Ready`
- **Actions** Capture (large, thumb-reachable, bottom centre) · Flash toggle · Close · Queue count (taps through to H4)
- **Behaviour** Auto-capture when all four markers are locked and sharpness passes for 400 ms, with a manual override. Haptic feedback on capture.
- **Offline** Fully functional. Photos go to IndexedDB. A small cloud-with-slash icon appears; nothing else changes.

### H3 · Capture review **[MVP]**
- Shown for ~1.5 s after each capture, or held indefinitely if quality failed.
- **Pass** thumbnail with a green check, auto-advances to the next page
- **Fail** the photo with the problem named and a single `Retake` button:
  - *"Too blurred. Rest your phone on something solid and tap the screen to focus."*
  - *"Too dark. Move to brighter light and keep your shadow off the page."*
  - *"Reflection on the page. Tilt the page or move away from the direct light."*
  - *"Corners not visible. Include all four corners of the page in the frame."*
- **Actions** `Retake` (primary) · `Use anyway` (secondary, only above the hard-reject floor, and it stamps the page as degraded)

### H4 · Upload queue **[MVP]**
- **Route** `/capture/queue`
- Grouped by booklet. Per item: thumbnail, page number, size, status (Waiting for signal · Uploading · Done · Failed).
- **Header** *"12 photos waiting. They'll upload automatically when you're back online."*
- **Actions** `Upload now` · `Retry failed` · `Delete` (per item, with confirm) · `Clear completed`
- This screen must be reachable offline and must survive an app kill.

### H5 · Batch progress **[MVP]**
- A persistent, collapsible bar rather than a screen — visible on every route while a batch runs.
- `Processing 312 scripts — 208 done, 4 failed · [View] [Hide]`
- Live via SSE. Collapsing it keeps a small pill in the top bar.

### H6 · Page assembly (fallback path only)
- Used when QR codes are missing (legacy scripts on plain paper).
- Grid of thumbnails, drag to reorder, drag to group into scripts, assign a booklet or student reference per group.
- **Actions** `Auto-group by time` · `Split here` · `Merge` · `Confirm assembly`
- **Warning banner** *"These pages have no booklet codes, so the order is your responsibility. Check it before confirming."*

### H7 · Quality rejection review
- **Route** `/exams/:id/upload?filter=rejected`
- Every rejected page with its reason and thumbnail, grouped by reason so a lecturer can see a pattern ("everything from the afternoon batch is too dark").
- **Actions** `Replace` (opens file picker) · `Send retake list` (produces a printable list of booklet+page to re-scan)

---

## I. Processing — 3 screens

### I1 · Processing board **[MVP]**
- **Route** `/exams/:id/processing`
- Kanban-style columns matching the pipeline: Received · Preparing · Reading · Understanding · Scoring · Ready to review · Needs attention
- Cards show booklet ID, page count, and a stage spinner. Live updates.
- **Actions** per card: `View details` · `Retry` · `Cancel`
- **Filters** Failed only · Slow (>2 min) · Needs transcription

### I2 · Script pipeline detail
- **Route** `/exams/:id/processing/:scriptId`
- Vertical timeline of every stage with duration, provider used, cost, and confidence produced.
- Expandable per stage to show the raw artefact (processed image, transcript, verdicts, decision trace).
- **Actions** `Reprocess from this stage` (ADMIN) · `Download diagnostics` · `Open in review`
- This screen is how you answer "why did this script take four minutes?" and it will save the team many hours.

### I3 · Failed jobs triage
- **Route** `/admin/jobs` · **Who** ADMIN
- Dead-letter queue: job type, script, error class, attempt count, last error, first seen.
- Grouped by error class so one bad provider outage shows as one row, not 200.
- **Actions** `Retry selected` · `Retry all in group` · `Discard` (with reason) · `Copy error`

---

## J. Marking — 7 screens

### J1 · Marking queue **[MVP]**
- **Route** `/exams/:id/marking`
- **Job** Choose what to mark next, and let a lecturer clear the easy pile fast.

```
┌────────────────────────────────────────────────────────────────────────┐
│ CSM 355 · Marking                                    241 / 308 done    │
├────────────────────────────────────────────────────────────────────────┤
│ Show:  [ All ▾ ]  Routing: [ Any ▾ ]  Question: [ Any ▾ ]  ⌕          │
│                                                                        │
│  ○ Needs your judgement   87        ○ Ready to confirm   198          │
│  ○ Hand-marking only      23        ○ Flagged             3           │
│                                                                        │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ ☐ 4A1E   Q1–Q8   suggested 54/80   conf 0.91  ● ready       [Open] │ │
│ │ ☐ 7B2F   Q1–Q8   suggested 38/80   conf 0.72  ● review      [Open] │ │
│ │ ☐ 9C3D   Q1–Q8   — hand-marking     conf 0.44  ● manual     [Open] │ │
│ │ ☐ 2E8A   Q1–Q8   suggested 61/80   ⚠ flagged               [Open] │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│ 3 selected   [Confirm selected]  [Open first]                          │
└────────────────────────────────────────────────────────────────────────┘
```

- **Actions** `Open` · `Confirm selected` (only enabled for AUTO_SUGGEST rows) · `Open first` · `Mark by question` toggle
- **"Mark by question" mode** — a genuinely valuable option: instead of one script at a time, review Q3(a) across all 308 scripts. Markers are far more consistent this way, and it is how experienced examiners actually work. Same workspace, different iteration order.
- **Batch confirm guard** — selecting more than 20 opens M22 requiring the marker to spot-check a random sample first.

### J2 · Review workspace **[MVP]** — the screen everything else exists to serve

- **Route** `/exams/:id/marking/:scriptId?q=3a`
- **Desktop only** (≥1280 px). Below that: *"Marking needs a wider screen. Open this on a laptop or desktop."*

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ ← CSM 355 · Booklet 4A1E (anonymous) · Q3(a)          Script 27 of 308  ⌨ ?  │
│ Q1 ✓  Q2 ✓  [Q3a] Q3b  Q4  Q5 ✓  Q6  Q7  Q8            ← question rail       │
├─────────────────────────┬────────────────────────┬───────────────────────────┤
│ SCRIPT                  │ WHAT WE READ           │ MARKING SCHEME            │
│                         │                        │                           │
│ ┌─────────────────────┐ │ 1 Deadlock is a state  │ ✓ Mutual exclusion    2/2 │
│ │                     │ │   where processes wait │   from line 1             │
│ │  [page image,       │ │                        │                           │
│ │   evidence regions  │ │ 2 ▓Each process holds▓ │ ✓ Hold and wait       2/2 │
│ │   tinted to match   │ │   ▓a resource and    ▓ │   from line 2             │
│ │   the marking point │ │   ▓requests another  ▓ │                           │
│ │   colours]          │ │                        │ ✗ No pre-emption      0/2 │
│ │                     │ │ 3 ~~this is wrong~~    │   not found in the answer │
│ │  ⊕ ⊖ ⟲  fit         │ │   (crossed out —       │                           │
│ └─────────────────────┘ │    not counted)        │ ⚠ Circular wait       0/2 │
│                         │                        │   the answer says the     │
│ [Original] [Cleaned]    │ 4 [drawing — not read] │   opposite   from line 6  │
│                         │                        │                           │
│                         │ 5 ⚠ couldn't read this │ Total suggested     4 / 8 │
│                         │   [type what it says]  │                           │
├─────────────────────────┴────────────────────────┴───────────────────────────┤
│ Confidence   photo 0.94 · reading 0.91 · understanding 0.78 · overall 0.78   │
│ ⚠ Needs your judgement — the understanding step wasn't confident here        │
│                                                                              │
│ Your mark  [ 4.0 ] / 8    Why did you change it? [__________________]        │
│                                                                              │
│ [1 Confirm]  [2 Adjust]  [3 Send to moderation]  [4 Flag]   ← Prev  Next →   │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Interaction requirements — each is load-bearing:**

| Requirement | Why |
|---|---|
| Hovering a marking point tints its evidence in the transcript **and** on the page image | This is the "explain the decision" feature. Verification in under two seconds. |
| Clicking a transcript line scrolls and zooms the page image to that line | Lets a marker check the machine's reading against the handwriting instantly |
| Every marking point is individually clickable to award/withhold | Adjusting is per-point, not just a total. The total recalculates and is shown as *your* number, not the suggestion. |
| Struck-through and unread content shown, greyed, labelled | The marker must see what was deliberately ignored |
| Reason field required when the mark differs from the suggestion | Feeds rubric improvement; satisfies audit |
| When routing is MANUAL_ONLY, **no suggestion is shown at all** | A displayed number anchors the marker. Show the transcript and an empty mark field. |
| Question rail shows per-question state (✓ done, ● current, ⚠ flagged) | Orientation without leaving the screen |
| Zero mouse required | 300 scripts. The keyboard is the interface. |
| Auto-save every change to local storage | A dropped connection mid-script must never lose work |

**Keys** `1` confirm · `2` adjust · `3` moderation · `4` flag · `←/→` prev/next question · `Shift+←/→` prev/next script · `j/k` move between marking points · `Space` toggle the focused point · `+/-` zoom · `t` transcribe focused line · `e` show evidence overlay · `?` shortcut sheet · `Esc` back to queue

### J3 · Transcription correction **[MVP]**
- **Route** `/transcribe/:scriptId`
- A vertical list of only the lines the system could not read. Each row: cropped image of that line, a text field beneath, and the low-confidence guess pre-filled and selected.
- **Actions** `Save and next` (`Enter`) · `Can't read it either` · `Skip` · `Done`
- **Design note** the crop is the hero — large, sharp, no surrounding chrome. This screen should let a TA clear 100 lines in a few minutes.
- Completing it automatically re-runs understanding and scoring for the affected questions.

### J4 · Hand-marking sheet **[MVP]**
- For `MANUAL_ONLY` questions and for diagrams, mathematics, and code.
- Left: the page image or cropped region, large. Right: the marking scheme as a checklist with mark values, and a total field.
- **No suggestion anywhere on this screen.** The system's contribution is presentation and record-keeping.
- **Actions** per-point checkboxes · `Save mark` · `Next`

### J5 · Batch confirm
- Reached from J1 when confirming many scripts.
- Shows a random sample of 10% with their suggestions and evidence in a scroll-through. The marker must open each one before `Confirm all 198` enables.
- **Copy** *"Spot-check these 20 before confirming the rest. This keeps the batch defensible."*

### J6 · Moderation
- **Route** `/exams/:id/moderation` · **Who** LECTURER (lead), EXAMS_OFFICER
- Sampling rules (percentage, or all scripts above/below a mark boundary, or all overridden scripts).
- Table of sampled scripts with first marker's mark, moderator's mark, difference.
- **Actions** `Open` (loads the review workspace in moderation mode, showing the first marker's decisions) · `Agree` · `Change` · `Send back to marker`

### J7 · Marker comparison
- **Route** `/analytics/markers` (also linked from moderation)
- For double-marked sets: scatter of marker A vs marker B, disagreement list sorted by magnitude, per-question agreement stats, and the system's own agreement against both.
- This is the screen that produces the table for the dissertation.

---

## K. Results — 6 screens

### K1 · Results table **[MVP]**
- **Route** `/exams/:id/results`
- Columns: booklet (or student, if revealed), per-question marks, total, grade, status, marker, moderated ✓
- Sticky header, virtualised rows, column show/hide, sort, filter by status.
- **Actions** `Reveal identities` · `Export` · `Finalise all confirmed` · `Open script`
- **Guard** `Finalise` is disabled with a tooltip listing what's outstanding: *"11 scripts still need review."*

### K2 · Reveal identities
- A deliberate, audited step, not a toggle in a menu.
- Modal M31 explains: *"This links booklet codes to student names. It can't be undone and it's recorded in the audit log. Reveal identities for 308 scripts?"*
- After reveal, a banner sits on the results table: *"Identities revealed by A. Mensah on 14 June at 11:02."*

### K3 · Statistics
- Distribution histogram, mean/median/SD, per-question difficulty and discrimination, pass rate, comparison with previous sittings of the same course.
- **Actions** `Export chart` · `Download statistics`

### K4 · Export
- Choose format (CSV · XLSX · SIS format · annotated PDFs), choose columns, choose scope (all · finalised only · a filter).
- Preview of the first five rows before generating.
- **Actions** `Generate export` → job → download link + notification. Every export is audited and the record shows here.

### K5 · Student script report **[MVP]**
- **Route** `/exams/:id/results/:scriptId`
- The per-student view: page images with annotations, per-question marks with awarded and missed points, the marker's comments, total.
- **Actions** `Download PDF` · `Open in review` · `Build appeal bundle`

### K6 · Appeal bundle
- Generates a single signed PDF: original images, transcript with per-line confidence, rubric version used, every award with rule ID and evidence, complete event history, chain hash.
- **Actions** `Build bundle` · `Download` · `Copy verification hash`

---

## L. Integrity — 2 screens

### L1 · Flags queue
- **Route** `/integrity`
- Table: type, exam, booklet, detected at, severity, status.
- Types: `Suspected injection` · `Duplicate booklet` · `Possible screen photo` · `Answer under the wrong question` · `Identical answers across scripts` · `Missing pages`
- **Filters** Open · Reviewed · Dismissed · by exam
- **Actions** `Open` · `Dismiss` (reason required) · `Escalate to exams officer` · `Export report`

### L2 · Flag detail
- What was detected, the evidence (the exact transcript region highlighted on the page image), what the system did in response, and — stated plainly — what it did **not** do.
- For injection flags the copy matters: *"This script contains text that looks like an instruction to the system. It was recorded as written and changed no marks. You may want to look at it."*
- **Actions** `Dismiss` · `Escalate` · `Open script` · `Add note`

---

## M. Audit — 3 screens

### M1 · Audit log
- **Route** `/exams/:id/audit` and `/admin/audit`
- Filterable event stream: actor, action, object, before → after, reason, time, IP.
- Filters: actor, action type, date range, object.
- **Actions** `Export log` · `Verify chain`
- **No edit or delete actions exist on this screen.** Not disabled — absent.

### M2 · Script history
- A single script's complete life as a vertical timeline, mixing system and human events, with the decision trace expandable at each scoring event.
- This is what a lecturer opens when a student asks "why did I get 4?"

### M3 · Chain verification
- **Who** ADMIN, AUDITOR
- Runs the hash-chain check, shows the result as a single unambiguous statement: *"Verified. 48,201 records, chain intact, checked 2 minutes ago."* or a red failure naming the first broken record.
- **Actions** `Verify now` · `Download verification report`

---

## N. Analytics — 4 screens

### N1 · Accuracy dashboard
- Agreement between suggestions and final marks: QWK, exact agreement, within ±1, MAE.
- Confidence calibration curve (predicted vs actual agreement) — the plot that proves the thresholds are honest.
- Routing precision and recall.
- Filter by exam, question, date range.

### N2 · Rubric health
- Marking points sorted by override rate. High override rate = the rubric point is the problem.
- For each, the system proposes exemplars drawn from real student answers that markers accepted.
- **Actions** `Add this phrasing to MP4` · `Dismiss` · `Open rubric`
- This is the feedback loop made visible, and it is a strong demo moment.

### N3 · Marker consistency
- Per marker: scripts marked, mean mark, SD, accept-without-change rate, median time per script, agreement with moderators.
- **Purpose is support, not surveillance** — frame the copy accordingly and restrict access to EXAMS_OFFICER and above.

### N4 · Usage & cost
- Pages processed, AI spend month to date against the cap, cost per script trend, provider mix, Tier-2 trigger rate, cache hit rate.
- **Actions** `Export usage` · `Adjust cap` (ADMIN)

---

## O. Administration — 9 screens

### O1 · Users **[MVP]**
- Table: name, email, roles with their scopes, status, last active, MFA on/off.
- **Actions** `Invite user` · `Edit` · `Deactivate` · `Resend invitation` · `Force sign-out`

### O2 · User detail **[MVP]**
- Profile, scoped role assignments (role + scope pairs, added individually), session list with device and last-seen, recent activity.
- **Actions** `Add role` · `Remove role` · `Reset MFA` · `Revoke session` · `Deactivate`

### O3 · Roles & permissions
- Read-only matrix of the six roles against every permission. Not editable in v1 — custom roles are a v2 feature and saying so is better than a half-built role editor.

### O4 · Institution settings
- Name, logo, academic year, departments, contact, default grading scale.

### O5 · Data & retention
- Data region (read-only after setup, with an explanation), retention periods for images / marks / audit, deletion schedule with a dry-run preview, and a `Download all institution data` export.
- **Actions** `Run deletion preview` · `Apply retention` · `Export all data`

### O6 · AI providers & thresholds
- Which provider is primary, secondary, arbiter. Connection test per provider. Thresholds for routing, bounded by platform floors with the floor shown inline: *"Minimum 0.80 — set by the platform."*
- **Actions** `Test connection` · `Save` · `Reset to defaults`

### O7 · Spend caps
- Monthly cap, current spend, projected spend, behaviour at cap (stop and notify · queue and notify), alert thresholds.
- **Actions** `Set cap` · `Add alert`

### O8 · Integrations
- API keys (create, show once, revoke), webhook endpoints with a delivery log and replay, SIS export target.
- **Actions** `Create key` · `Revoke` · `Add webhook` · `Send test event` · `Replay delivery`

### O9 · System health
- Queue depth per stage, worker count, provider latency and error rate, database and storage status, last backup, backup restore test date, audit chain status.

---

## P. User settings & help — 6 screens

### P1 · Profile **[MVP]** — name, display name, department, timezone, language
### P2 · Security **[MVP]** — change password, MFA setup and recovery codes, active sessions with `Sign out everywhere`
### P3 · Notifications — per-event toggles for in-app and email (below), plus a daily digest option
### P4 · Display & accessibility — theme (system · light · dark), density (comfortable · compact), text size, reduce motion, high-contrast evidence colours (important: the default evidence tinting must not rely on colour alone)
### P5 · Keyboard shortcuts — the full reference, printable
### P6 · Help — photography guide, rubric writing guide, what the confidence numbers mean, contact support, restart the tour

---

## 5. Modal inventory — 41

Rules for all of them: one job each · title states the action, not the object · primary button repeats the verb from the trigger (a `Freeze rubric` button opens a modal whose primary button also says `Freeze rubric`) · `Esc` and the backdrop close non-destructive modals only · destructive modals need an explicit `Cancel` · focus is trapped and returns to the trigger on close.

### Session & safety
| # | Modal | Trigger | Primary | Notes |
|---|---|---|---|---|
| M1 | Sign out everywhere | Security settings | `Sign out everywhere` | Warns it ends this session too |
| M2 | Session ending soon | 2 min before expiry | `Stay signed in` | Countdown; auto-saves review state |
| M3 | Unsaved changes | Navigating away from an editor | `Keep editing` / `Discard` | Never auto-discard |
| M4 | Delete *X* | Any delete | `Delete` | Type the object's name to enable, for anything with dependents |

### Exams & rubric
| # | Modal | Trigger | Primary | Notes |
|---|---|---|---|---|
| M5 | Change exam status | Status pill | `Move to Marking` | Lists what the new status permits and what it prevents |
| M6 | Freeze rubric | Rubric builder | `Freeze rubric` | *"Once frozen this can't change. Scripts already marked stay on this version."* Blocked if lint errors exist |
| M7 | Test this rubric | Rubric builder | `Close` | Paste an answer → see which points it satisfies, with reasons. The teaching tool. |
| M8 | Duplicate rubric as new version | Version history | `Create version 5` | |
| M9 | Import rubric preview | Import screen | `Import 14 points` | Per-row lint results, bad rows highlighted |
| M10 | Regenerate booklets | Booklet screen | `Regenerate` | *"The 320 booklets you already printed will no longer work."* |
| M11 | Print instructions | Booklet preview | `Got it` | Scale 100%, no fit-to-page, plain paper |

### Capture & upload
| # | Modal | Trigger | Primary | Notes |
|---|---|---|---|---|
| M12 | Duplicate booklet page | Upload detects a repeat | `Keep the sharper one` | Also `Keep both` / `Skip` |
| M13 | Why was this rejected? | Rejected file row | `Replace file` | Shows the photo with the failing metric named |
| M14 | Send a retake list | Rejection review | `Download list` | Printable booklet+page list |
| M15 | Confirm page assembly | Fallback assembly | `Confirm order` | Restates that order is the user's responsibility |
| M16 | Reprocess script | Pipeline detail | `Reprocess` | Choose the stage to restart from; warns existing suggestions are replaced |

### Processing
| # | Modal | Trigger | Primary | Notes |
|---|---|---|---|---|
| M17 | Retry failed jobs | Triage screen | `Retry 14 jobs` | |
| M18 | Discard job | Triage screen | `Discard` | Reason required |

### Marking
| # | Modal | Trigger | Primary | Notes |
|---|---|---|---|---|
| M19 | Why the change? | Mark differs from suggestion | `Save mark` | Reason required; offers common reasons as one-tap chips |
| M20 | Flag this script | `4` in workspace | `Flag` | Type + note |
| M21 | Send to moderation | `3` in workspace | `Send` | Optional note to the moderator |
| M22 | Spot-check before confirming | Batch confirm > 20 | `Confirm all 198` | Disabled until the sample has been opened |
| M23 | Escalate to exams officer | Flag detail | `Escalate` | |
| M24 | Add a note | Several | `Add note` | |
| M25 | Dismiss flag | Flag detail | `Dismiss` | Reason required |
| M26 | How to transcribe | Transcription screen | `Got it` | What to do with unclear words, symbols, crossings-out |
| M27 | Reopen a finalised mark | Results table | `Reopen` | EXAMS_OFFICER only; reason required; creates a new attempt |

### Results
| # | Modal | Trigger | Primary | Notes |
|---|---|---|---|---|
| M28 | Reveal identities | Results table | `Reveal identities` | *"This can't be undone and it's recorded."* |
| M29 | Configure export | Export screen | `Generate export` | Format, columns, scope |
| M30 | Your export is ready | Job completion | `Download` | Also lands in notifications |
| M31 | Build appeal bundle | Script report | `Build bundle` | Explains what's included |

### Audit & admin
| # | Modal | Trigger | Primary | Notes |
|---|---|---|---|---|
| M32 | Chain verification result | Verify now | `Close` | Single clear statement, green or red |
| M33 | Invite a user | Users screen | `Send invitation` | Email + role + scope |
| M34 | Add a role | User detail | `Add role` | Role + scope selector |
| M35 | Remove a role | User detail | `Remove` | |
| M36 | Deactivate user | User detail | `Deactivate` | Explains their marks remain attributed |
| M37 | Reset MFA | User detail | `Reset` | Requires the admin's own MFA |
| M38 | Your new API key | Integrations | `I've copied it` | Shown once, never again |
| M39 | Revoke API key | Integrations | `Revoke` | |
| M40 | Set spend cap | Spend settings | `Set cap` | Shows projected spend against the new cap |
| M41 | Deletion preview | Data settings | `Run deletion` | Dry-run counts by object type first |

Plus one non-modal overlay: the **keyboard shortcut sheet** (`?`), which is a panel, not a dialog, so it can stay open while working.

---

## 6. Core flows

### Flow 1 · Set up the institution *(ADMIN, once)*
```
Accept invitation → set password → enrol MFA (forced) → institution wizard
  → details → data region → invite users → spend cap → /home
```
**Watch:** data region is irreversible. State that on the step, not in a tooltip.

### Flow 2 · Create an exam and write a rubric *(LECTURER)*
```
/home → New exam → wizard ①details ②questions ③rubric ④booklets ⑤review
  → exam overview → Questions tab → per question: Rubric builder
  → add marking points → add phrasings → checks pass → Test this rubric (M7)
  → paste 3 sample answers, confirm they behave → Freeze rubric (M6)
```
**Watch:** most users will try to skip step ③ in the wizard. Let them — but the exam cannot leave DRAFT until every auto-markable question has a frozen rubric, and the overview says exactly which questions are missing one.

### Flow 3 · Generate and print booklets *(LECTURER / EXAMS_OFFICER)*
```
Exam → Booklets → set count and pages → Generate → preview → print instructions (M11)
  → Download PDF → print → Booklet register shows 320 issued, 0 scanned
```

### Flow 4 · Capture scripts on a phone, offline *(LECTURER / TA)*
```
Sign in on phone (once; stays signed in) → open exam → Capture
  → point at page → markers lock green → auto-capture → quality pass ✓
  → next page … → queue shows "48 photos waiting"
  → walk into signal → queue drains automatically → notification "48 pages uploaded"
```
**Watch:** the whole flow must work with the phone in aeroplane mode. Test it that way.

### Flow 5 · Bulk upload from a scanner *(TA)*
```
Exam → Upload → drop 312 files → per-file quality check
  → 296 accepted, 16 rejected → Rejection review, grouped by reason
  → Send retake list (M14) → rescan those → Replace → all accepted
```

### Flow 6 · Triage processing failures *(LECTURER, then ADMIN)*
```
Processing board → "Needs attention" column → open a card → pipeline detail
  → see the stage that failed and the error
  → Retry (transient) or → escalate to /admin/jobs (systemic)
```

### Flow 7 · Fix unreadable lines *(TA)*
```
Exam overview → "11 lines need transcription" → /transcribe/:scriptId
  → crop + field, type, Enter, next … → Done
  → affected questions re-run understanding and scoring automatically
  → those scripts return to the marking queue with new confidence
```

### Flow 8 · Review and confirm a script *(LECTURER)* — the primary loop
```
Marking queue → Open first → workspace loads on Q1
  → glance at the marking scheme column → hover MP3 → evidence tints on the
    transcript and on the photograph → satisfied
  → press 1 (confirm) → auto-advances to Q2 …
  → on Q4 the suggestion looks wrong → press 2 → adjust MP2 from 2 to 0
    → reason chip "answer doesn't actually say this" → save
  → last question → script marked → Shift+→ next script
```
**Target:** a confident script confirmed in under 20 seconds, entirely on the keyboard.

### Flow 9 · Mark by question across the cohort *(LECTURER)*
```
Marking queue → toggle "Mark by question" → choose Q3(a)
  → workspace iterates the same question across 308 scripts
  → the marking scheme column never changes, so judgement stays consistent
  → finish Q3(a) → choose the next question
```

### Flow 10 · Handle an integrity flag *(LECTURER → EXAMS_OFFICER)*
```
Home "3 flagged" → Integrity queue → open a "Suspected injection" flag
  → see the exact text highlighted on the photograph
  → read the plain statement that no mark was changed
  → Escalate (M23) with a note → exams officer is notified
```

### Flow 11 · Moderate, reveal, export *(LECTURER + EXAMS_OFFICER)*
```
All scripts reviewed → Moderation → set sampling 10% + all overridden
  → moderator opens each, agrees or changes
  → Results table → Finalise all confirmed
  → Reveal identities (M28) → Export (M29) → download → SIS
```

### Flow 12 · Answer a student appeal *(LECTURER)*
```
Results → find booklet → Script report → Build appeal bundle (M31)
  → PDF containing images, transcript with confidence, rubric version,
    every award with its rule and evidence, full history, chain hash
  → send to the department
```
This flow is a genuine selling point. No manual marking process can produce this artefact at all.

---

## 7. Action inventory & permissions

Every button in the product, mapped to the permission that gates it. If a user lacks the permission, the control is **hidden**, not disabled — except where its absence would be confusing, in which case it is disabled with a tooltip naming the missing permission.

| Action | Permission | ADMIN | EXAMS_OFF | LECTURER | TA | VIEWER | AUDITOR |
|---|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Create course | `course.create` | | ✔ | ✔ | | | |
| Create exam | `exam.create` | | ✔ | ✔ | | | |
| Edit questions | `exam.edit` | | ✔ | ✔ | | | |
| Edit rubric | `rubric.edit` | | ✔ | ✔ | | | |
| Freeze rubric | `rubric.freeze` | | ✔ | ✔ | | | |
| Test rubric | `rubric.edit` | | ✔ | ✔ | | | |
| Generate booklets | `booklet.create` | | ✔ | ✔ | | | |
| Upload scripts | `script.upload` | | ✔ | ✔ | ✔ | | |
| Capture on mobile | `script.upload` | | ✔ | ✔ | ✔ | | |
| Reprocess script | `script.reprocess` | ✔ | ✔ | | | | |
| Correct transcription | `transcript.edit` | | ✔ | ✔ | ✔ | | |
| Confirm a mark | `marks.review` | | | ✔ | ✔¹ | | |
| Adjust a mark | `marks.review` | | | ✔ | ✔¹ | | |
| Batch confirm | `marks.review` | | | ✔ | | | |
| Send to moderation | `marks.review` | | ✔ | ✔ | ✔ | | |
| Moderate | `marks.moderate` | | ✔ | ✔² | | | |
| Finalise marks | `marks.finalise` | | ✔ | ✔ | | | |
| Reopen a finalised mark | `marks.reopen` | | ✔ | | | | |
| Flag for integrity | `integrity.flag` | | ✔ | ✔ | ✔ | | |
| Dismiss a flag | `integrity.resolve` | | ✔ | ✔ | | | |
| Reveal identities | `identity.reveal` | | ✔ | ✔² | | | |
| View results | `results.view` | | ✔ | ✔ | ✔ | ✔ | ✔ |
| Export results | `results.export` | | ✔ | ✔ | | | |
| Build appeal bundle | `results.export` | | ✔ | ✔ | | | |
| Read audit log | `audit.read` | ✔ | ✔ | | | | ✔ |
| Verify audit chain | `audit.verify` | ✔ | ✔ | | | | ✔ |
| Invite / edit users | `user.manage` | ✔ | | | | | |
| Assign roles | `role.assign` | ✔ | ✔³ | | | | |
| Change AI settings | `settings.ai` | ✔ | | | | | |
| Set spend cap | `settings.billing` | ✔ | | | | | |
| Change retention | `settings.data` | ✔ | | | | | |
| Manage API keys | `settings.integrations` | ✔ | | | | | |
| **Edit or delete audit records** | — | ✘ | ✘ | ✘ | ✘ | ✘ | ✘ |

¹ TA marks save as PROVISIONAL and need a lecturer's countersignature.
² Lecturer must be the lead marker on that exam.
³ Exams officer can assign course-scoped roles only, never tenant-scoped.

---

## 8. Settings inventory — four levels

Settings live at the narrowest level that makes sense. Each level can only override within bounds set by the level above.

### 8.1 Platform (Anthropic-of-this-product level; not in the UI, environment only)
`PLATFORM_MIN_AUTO_SUGGEST` · `MAX_UPLOAD_BYTES` · `MAX_BATCH_FILES` · provider allowlist · absolute retention ceiling · rate limit ceilings

### 8.2 Institution *(ADMIN, `/admin/*`)*

| Group | Settings |
|---|---|
| Identity | Name · logo · departments · academic year · contact email |
| Data | Region *(locked after setup)* · image retention days · marks retention days · audit retention days · deletion schedule |
| AI | Primary OCR provider · secondary · arbiter · entailment provider · connection tests · default routing thresholds *(bounded)* · Tier-2 trigger threshold |
| Budget | Monthly cap · behaviour at cap *(stop / queue)* · alert thresholds · per-exam cap |
| Security | Force MFA for roles · session length · password policy · IP allowlist *(optional)* · failed-attempt lockout |
| Marking defaults | Anonymous marking on/off · default moderation sample % · require reason on override · require spot-check for batch confirm |
| Grading | Grade boundaries · rounding · pass mark |
| Integrations | API keys · webhooks · SIS export target |
| Notifications | Institution-wide email sender · digest schedule |

### 8.3 Exam *(LECTURER / EXAMS_OFFICER, `/exams/:id/settings`)*

| Group | Settings |
|---|---|
| Basics | Title · course · date · total marks · status |
| Marking | Anonymous marking · who can mark · auto-suggest threshold *(bounded by institution)* · manual-only threshold · partial credit fraction · rounding · negative marking allowed |
| Moderation | Sampling rule · sample % · auto-sample overridden scripts · auto-sample near grade boundaries |
| Booklets | Pages per booklet · include cover sheet · question layout |
| Retention | Override institution default *(only shorter, never longer)* |
| Danger | Reopen exam · delete exam |

### 8.4 User *(`/settings/*`)*

| Group | Settings |
|---|---|
| Profile | Name · display name · department · timezone · language |
| Security | Password · MFA · recovery codes · active sessions |
| Notifications | Per-event in-app and email toggles · daily digest on/off and time |
| Display | Theme · density · text size · reduce motion · high-contrast evidence colours · default marking mode (by script / by question) |
| Marking preferences | Auto-advance after confirm · confirm requires two keys · show confidence numerals or bars |

---

## 9. Notifications

| Event | In-app | Email | Default |
|---|---|---|---|
| Your upload batch finished | ✔ | ✔ | on |
| Scripts failed to process | ✔ | ✔ | on |
| Lines need transcription | ✔ | | on |
| Scripts are ready for you to review | ✔ | ✔ | on |
| A script was flagged for integrity | ✔ | ✔ | on |
| A moderator changed your mark | ✔ | ✔ | on |
| A script was sent to you for moderation | ✔ | ✔ | on |
| Your export is ready | ✔ | ✔ | on |
| Exam status changed | ✔ | | on |
| Rubric health suggestions available | ✔ | | off |
| Spend reached 80% of cap | ✔ | ✔ | on *(ADMIN)* |
| Spend cap reached — processing stopped | ✔ | ✔ | forced on |
| Audit chain verification failed | ✔ | ✔ | forced on |
| New sign-in from a new device | ✔ | ✔ | forced on |

Two notifications cannot be turned off: the spend-cap stop and the audit chain failure. Both are conditions where silence is dangerous.

---

## 10. State matrix

Every list, table, and panel needs all six. Build them as components once, not per screen.

| State | Rule | Example copy |
|---|---|---|
| **Loading** | Skeletons that match the final layout, never a centred spinner on a full page. Tables show 5 skeleton rows. | — |
| **Empty (nothing yet)** | An invitation with exactly one action | *"No exams yet. Create one to get started."* |
| **Empty (filtered to nothing)** | Different from the above — offer to clear the filter | *"No scripts match these filters. Clear filters"* |
| **Error** | Name what happened and what to do. Never "Something went wrong." | *"Couldn't load the marking queue. Check your connection and try again."* + `Try again` |
| **Offline** | Say what still works | *"You're offline. You can keep capturing — photos will upload when you're back."* |
| **Partial** | Show what loaded, name what didn't | *"Showing 298 of 312 scripts. 14 couldn't be loaded. Retry"* |

**Additional workspace-specific states:**
- **Processing** — script opened before it finished: show the pipeline stage with live progress, not an error
- **Locked** — another marker has this script open: *"K. Osei is marking this script. Open read-only"*
- **Superseded** — the rubric changed since this was scored: *"This was scored on rubric v3. Version 4 is now active. Rescore this script"*

---

## 11. Component library

Build these once. Everything else composes from them.

**Primitives** — Button (primary/secondary/ghost/destructive) · IconButton · Input · Textarea · Select · Combobox · Checkbox · Radio · Switch · Slider · DatePicker · FileDrop · Badge · Pill · Tag · Avatar · Tooltip · Popover · Divider

**Feedback** — Toast · InlineAlert (info/warn/error/success) · Banner · ProgressBar · ProgressRing · Skeleton · Spinner · EmptyState · ErrorState

**Layout** — AppShell · Sidebar · TopBar · TabStrip · PageHeader · Card · Panel · SplitPane (draggable, used by the workspace) · Drawer · Modal · StickyFooterBar

**Data** — DataTable (virtualised, sortable, selectable, column toggle, sticky header) · DefinitionList · StatCard · Timeline · DiffView · KeyValueGrid

**Domain-specific — the ones that matter**
| Component | Used by |
|---|---|
| `ConfidenceMeter` | Four labelled segments plus an overall value. Never a single blended bar. |
| `RoutingBadge` | Ready to confirm · Needs judgement · Hand-marking only |
| `ExamStatusPill` | Everywhere an exam appears |
| `PageViewer` | Zoom, pan, fit, rotate, original/cleaned toggle, evidence overlay layer |
| `TranscriptPane` | Line numbers, confidence shading, strikethrough rendering, non-text placeholders, click-to-locate |
| `MarkingSchemePanel` | Per-point award state, evidence links, inline adjust |
| `EvidenceLink` | The tinted connection between a marking point, its transcript lines, and the page region — **the signature interaction** |
| `MarkInput` | Number field with keyboard stepping, bounded by max marks, showing suggested vs yours |
| `ReasonChips` | Common override reasons as one-tap options plus free text |
| `QuestionRail` | Per-question progress across the top of the workspace |
| `CaptureOverlay` | Live marker guides, guidance line, capture control |
| `UploadQueueItem` | Thumbnail, status, retry |
| `RubricPointEditor` | Statement, marks, phrasings, advanced options |
| `LintPanel` | Blocking vs advisory checks |
| `AuditTimeline` | Mixed system and human events, expandable decision traces |
| `DecisionTrace` | The ordered rule evaluation, human-readable |

---

## 12. Visual direction and tokens

**Subject:** an examiner's desk. The materials are photocopy paper under fluorescent light, a student's blue-black pen, ruled margins, and the marker's red. The interface should feel like a precise instrument, not an editorial page or a dashboard.

**The one idea to build everything around: colour encodes authorship.**

- **Indigo is the machine.** Every suggestion, confidence value, and system annotation.
- **Red belongs to the human.** The marker's own changes, and destructive actions. Nothing the system generates is ever red.
- **Green means settled.** Finalised only. Not "success", not "saved" — settled.

A marker can therefore tell at a glance, from colour alone, what the machine said and what a person did. That rule is doing real work, and it is the thing this interface will be remembered for.

### 12.1 Tokens

```css
:root {
  /* surface — cool paper, not cream. This is copier paper, not letterpress. */
  --paper:        #F7F8FA;
  --paper-raised: #FFFFFF;
  --paper-sunken: #EEF0F4;
  --rule:         #DDE1E8;   /* borders, dividers, the ruled line */
  --rule-strong:  #C3C9D4;

  /* ink */
  --ink:          #14181F;   /* primary text; blue-black, like a student's pen */
  --ink-muted:    #5A6472;
  --ink-faint:    #8B94A3;

  /* authorship */
  --machine:      #4C5BA8;   /* the system speaks in indigo */
  --machine-soft: #E8EAF6;
  --marker:       #C8382F;   /* the human's pen, and destructive actions ONLY */
  --marker-soft:  #FBE9E7;
  --settled:      #1F7A5C;   /* finalised */
  --settled-soft: #E3F2EC;
  --caution:      #B4700E;   /* needs judgement */
  --caution-soft: #FDF3E2;

  /* evidence tints — categorical, over photographs.
     Each is ALWAYS paired with a letter badge and a distinct outline dash,
     so the mapping never depends on colour alone. */
  --ev-a: #4C5BA8;  --ev-b: #1F7A5C;  --ev-c: #B4700E;
  --ev-d: #7A4CA8;  --ev-e: #0E7490;  --ev-f: #8A5A2B;
  --ev-fill-alpha: 0.18;

  /* type */
  --font-ui:   "Inter", system-ui, sans-serif;
  --font-data: "IBM Plex Mono", ui-monospace, monospace;

  --t-caption: 12px/16px;
  --t-small:   13px/18px;
  --t-body:    15px/22px;
  --t-lead:    17px/26px;
  --t-h3:      20px/26px;
  --t-h2:      26px/32px;
  --t-h1:      34px/40px;

  /* rhythm */
  --unit: 8px;
  --radius:       6px;
  --radius-lg:    10px;
  --row-comfort:  44px;
  --row-compact:  36px;

  --shadow-panel: 0 1px 2px rgba(20,24,31,.06), 0 4px 12px rgba(20,24,31,.05);
  --focus-ring:   0 0 0 2px var(--paper), 0 0 0 4px var(--machine);
}
```

### 12.2 Type rules

- **All marks, confidences, booklet IDs, and page numbers are set in the mono face with tabular figures.** Marks are data; digits must not shift as they change, and columns must align down a results table. This is not decoration — a jittering mark field during keyboard entry is genuinely distracting at volume.
- No serif display face. This is an instrument.
- **Never use a handwriting or script typeface anywhere.** It would be confusable with actual student writing on the same screen, which is a real functional hazard, not just a taste question.
- Sentence case everywhere, including buttons. No title case, no all-caps except in table column headers at `--t-caption` with `letter-spacing: .06em`.

### 12.3 Motion

Almost none. One orchestrated moment: hovering a marking point draws the **evidence link** — the transcript lines tint, then the page-image region tints 60 ms later, so the eye follows the connection from scheme to text to handwriting. 140 ms total, `cubic-bezier(.2,.8,.2,1)`.

Everything else is a 120 ms opacity or colour change, or nothing. No page transitions, no card lifts, no skeleton shimmer. A marker doing 300 scripts will see each animation 300 times; anything decorative becomes an irritant by script 40.

`prefers-reduced-motion` disables the staged link entirely — both tints appear at once.

### 12.4 Density

Two modes, user-selectable. Comfortable for authoring and admin; compact for the marking queue, results table, and audit log. The workspace itself is always compact — screen space there belongs to the script.

---

## 13. Keyboard shortcuts

Global:
| Key | Action |
|---|---|
| `?` | Shortcut panel |
| `/` or `⌘K` | Global search |
| `g h` | Home |
| `g e` | Exams |
| `g m` | Marking queue |
| `g r` | Results |
| `Esc` | Close panel / back to list |

Review workspace (the ones that matter):
| Key | Action |
|---|---|
| `1` | Confirm the suggested mark |
| `2` | Adjust |
| `3` | Send to moderation |
| `4` | Flag |
| `←` `→` | Previous / next question |
| `Shift+←` `Shift+→` | Previous / next script |
| `j` `k` | Move between marking points |
| `Space` | Toggle award on the focused point |
| `t` | Transcribe the focused line |
| `e` | Toggle the evidence overlay |
| `o` | Toggle original / cleaned image |
| `+` `-` `0` | Zoom in / out / fit |
| `n` | Jump to the next unresolved item on this script |

Transcription: `Enter` save and next · `⌘Enter` save and finish · `u` mark unreadable

Every shortcut is discoverable: the panel is one keypress away, and each button's tooltip shows its key.

---

## 14. Accessibility

Non-negotiable, and several items here have a direct functional payoff beyond compliance.

- **Contrast** ≥ 4.5:1 for text, ≥ 3:1 for UI boundaries and the evidence outlines over photographs
- **Evidence never depends on colour alone.** Each tint carries a letter badge (A–F) and a distinct outline dash pattern. A colour-blind marker must be able to trace a marking point to its evidence. There is also a high-contrast evidence mode in Display settings.
- **Full keyboard operation** for every flow, including the workspace, capture queue, and all modals. Visible focus rings everywhere; never `outline: none` without a replacement.
- **Focus management** — modals trap focus and return it; route changes move focus to the page heading; the workspace announces question changes politely.
- **Live regions** — processing progress, upload status, and save confirmations announce via `aria-live="polite"`; the spend-cap stop and chain-failure alerts use `assertive`.
- **Semantic structure** — one `h1` per screen, real landmarks, real `<table>` for tables, real `<button>` for buttons.
- **Images** — page images carry a meaningful label ("Booklet 4A1E page 3, question 3(a)"); decorative marks are hidden from assistive tech.
- **Text scaling** to 200% without horizontal scroll on everything except the workspace, which is exempted and says so.
- **Reduced motion** respected.
- **Target size** ≥ 44 px on mobile capture. The capture button is the largest element on the screen for a reason.

---

## 15. Copy rules

1. **Name things by what people control, not by how the system works.** "What must the student say?" not "marking point statement". "Photos waiting" not "upload queue depth".
2. **A verb keeps its name through the whole flow.** The button says `Freeze rubric` → the modal's primary says `Freeze rubric` → the toast says *"Rubric frozen."*
3. **Errors state what happened and what to do next.** They do not apologise and they are never vague. No "Oops", no "Something went wrong".
4. **Empty states are invitations,** with exactly one action.
5. **Never present a suggestion as a decision.** *"Suggested 7 of 8"*, never *"Score: 7/8"*. And the field the marker types into is labelled `Your mark`.
6. **Confidence is explained in words next to the numbers.** *"Needs your judgement — the understanding step wasn't confident here"* does more work than `0.78`.
7. **Sentence case. Active voice. No exclamation marks.**
8. **Say what the system did *not* do** when that is the reassuring part — especially on integrity flags.

### Key strings

| Where | String |
|---|---|
| Suggestion header | `Suggested 4 of 8` |
| Marker's field | `Your mark` |
| Low confidence | `Needs your judgement — the understanding step wasn't confident here` |
| No suggestion | `No suggestion for this one. The handwriting was too unclear to read reliably — here's the script and the marking scheme.` |
| Crossed out | `Crossed out — not counted` |
| Unread region | `Drawing — not read. Mark this by hand.` |
| Unreadable line | `Couldn't read this. Type what it says` |
| Injection flag | `This script contains text that looks like an instruction to the system. It was recorded as written and changed no marks.` |
| Frozen rubric | `Frozen on 12 June. 312 scripts were marked using this version, so it can't change.` |
| Offline capture | `You're offline. Keep capturing — photos will upload when you're back.` |
| Reveal identities | `This links booklet codes to student names. It can't be undone and it's recorded in the audit log.` |
| Spend cap reached | `Processing stopped. This month's AI budget is spent. Raise the cap to continue.` |
| Batch confirm gate | `Spot-check these 20 before confirming the rest. This keeps the batch defensible.` |
| Narrow screen | `Marking needs a wider screen. Open this on a laptop or desktop.` |

---

## 16. Real-time and offline

**Real-time (SSE, one connection per session):**
`script.state_changed` · `batch.progress` · `job.failed` · `flag.raised` · `export.ready` · `script.locked_by_other`
Reconnect with backoff; on reconnect, refetch rather than replay. A stale progress bar is worse than a refetch.

**Offline (service worker + IndexedDB):**

| Works offline | Does not |
|---|---|
| Camera capture and local quality check | Uploading |
| Upload queue view and management | Processing status |
| Viewing already-loaded scripts and transcripts | Loading new scripts |
| Drafting marks and reasons *(queued, applied on reconnect)* | Confirming marks |
| Shortcut panel, help guides | Anything in admin |

Queued mark changes are held locally and applied on reconnect **only if the script has not changed server-side**; if it has, the marker is shown a conflict and chooses. Never silently overwrite.

---

## 17. Build order

| Phase | Screens | Gate |
|---|---|---|
| **1 · Shell** | A1–A4, C1, navigation, design tokens, component primitives | A user can sign in and see an empty home |
| **2 · Authoring** | D1–D2, E1–E3, F1–F3, F4 | A lecturer can create an exam and freeze a rubric |
| **3 · Intake** | G1–G3, H1–H5, I1 | 300 scripts can be captured and uploaded |
| **4 · The loop** | J1, J2, J3, J4 | A lecturer can mark a full exam end to end |
| **5 · Close-out** | K1, K4, K5, M28–M31 | Results can be finalised and exported |
| **6 · Trust** | L1–L2, M1–M3, J5–J6 | Integrity, audit and moderation are usable |
| **7 · Operate** | O1–O9, I2–I3, N1–N4 | An admin can run the platform |
| **8 · Polish** | P1–P6, B3, H6–H7, remaining modals | |

**Phase 4 is the product.** Everything before it is setup, everything after is around it. Build a rough version of phases 1–3 quickly to get real data into phase 4 early, then come back and finish them. A perfect exam-creation wizard with an unusable marking workspace is a failed project; the reverse is a demo you can defend.

---

*Every screen listed here has a job, a state matrix, and a permission. If a new screen is proposed and cannot be given all three, it belongs inside an existing screen.*
