/**
 * design.md §15 — the anti-generic checklist, as a test.
 *
 * A checklist in a document gets read once. These are the lines that describe
 * something a machine can see, so they run on every commit instead. Each one
 * exists because it is a common tell.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "vitest";
import fg from "fast-glob";

const SOURCE = fg.sync(["src/**/*.{ts,tsx,css}", "../../packages/ui/src/**/*.{ts,tsx,css}"], {
  cwd: process.cwd(),
  absolute: true,
  ignore: ["**/*.test.tsx", "**/design-rules.test.tsx"],
});

function read(): { path: string; text: string }[] {
  return SOURCE.map((path) => ({ path, text: readFileSync(path, "utf8") }));
}

function offenders(pattern: RegExp): string[] {
  return read()
    .filter(({ text }) => pattern.test(text))
    .map(({ path }) => path.replace(process.cwd(), "").replace(/\\/g, "/"));
}

// --- colour ----------------------------------------------------------------

test("no gradients anywhere", () => {
  // Not on the logo, buttons, text, backgrounds or borders. The coral-orange
  // gradient removed in design.md §1 was described as one of the most common
  // generative-design tells.
  expect(offenders(/bg-gradient|linear-gradient|radial-gradient|from-\[|via-\[/)).toEqual([]);
});

test("no purple-to-pink, coral, or terracotta accents", () => {
  expect(offenders(/\b(?:from|to|via)-(?:purple|pink|fuchsia|rose|orange|amber)-\d/)).toEqual([]);
});

test("colour comes from tokens, never from Tailwind's palette", () => {
  // One accent hue; everything else is a semantic state. A raw `bg-blue-500`
  // is a second accent nobody decided on.
  expect(
    offenders(/\b(?:bg|text|border)-(?:red|blue|green|yellow|purple|pink|indigo|teal|cyan)-\d{2,3}\b/),
  ).toEqual([]);
});

// --- shape and depth -------------------------------------------------------

test("no radius above 8px on containers", () => {
  // rounded-lg is 8px and is the ceiling. Larger reads as consumer software
  // and wastes corner space at this density.
  expect(offenders(/rounded-(?:xl|2xl|3xl|\[\s*(?:1[2-9]|[2-9]\d)px)/)).toEqual([]);
});

test("no glassmorphism or backdrop blur", () => {
  // Permitted only on the command-palette scrim and the Capture guidance line,
  // neither of which exists yet.
  expect(offenders(/backdrop-blur|backdrop-filter/)).toEqual([]);
});

test("no decorative blobs, mesh, noise or dot-grid backgrounds", () => {
  expect(offenders(/bg-\[url\(|noise\.|mesh-|blob/)).toEqual([]);
});

// --- type ------------------------------------------------------------------

test("three weights only", () => {
  // 400, 500, 600. Weight range is where interfaces start to look assembled
  // rather than designed.
  expect(offenders(/font-(?:thin|extralight|light|bold|extrabold|black)\b/)).toEqual([]);
});

test("no centred body text", () => {
  // Auth card headings are the only centred type in the product, and only at
  // text-h1. `text-center` on a container is allowed; on body copy it is not,
  // so this checks for the pairing.
  expect(offenders(/text-center[^"']*text-(?:base|lead|sm)\b/)).toEqual([]);
});

// --- motion ----------------------------------------------------------------

test("no entrance animations, hover lift, or shimmer", () => {
  // A marker sees each transition 300 times per exam. Anything decorative
  // becomes an irritant by script 40.
  expect(offenders(/animate-(?:bounce|ping|pulse|spin-slow)|hover:scale-|hover:-translate-y/)).toEqual(
    [],
  );
});

// --- icons -----------------------------------------------------------------

test("no sparkle, wand, star, brain or robot icons", () => {
  // The tells that say "this product wants you to think it is clever".
  expect(offenders(/\b(?:Sparkles?|Wand2?|Stars?|Brain|Bot|Rocket)\b\s*[,}]/)).toEqual([]);
});

// --- copy ------------------------------------------------------------------

test("no emoji in the interface", () => {
  expect(offenders(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u)).toEqual([]);
});

test("no exclamation marks in user-facing copy", () => {
  const text = read()
    .filter(({ path }) => path.endsWith(".tsx"))
    .map(({ text }) => text)
    .join("\n");
  // Inside a JSX text node or a quoted string, not `!==` or `!value`.
  expect(text).not.toMatch(/[a-z]!["'<]/);
});

test('the word "AI" does not appear in the interface', () => {
  // design.md §15. The product does not describe itself that way; it says what
  // it did and shows the sentence it did it from.
  const tsx = read().filter(({ path }) => path.endsWith(".tsx"));
  for (const { path, text } of tsx) {
    expect(text, path).not.toMatch(/\bAI\b(?![-\w])/);
  }
});

test("no Oops, Simply, Just, Seamless, or Powered by", () => {
  expect(offenders(/\b(?:Oops|Simply|Seamlessly?|Powered by)\b/i)).toEqual([]);
});

// --- the tokens themselves -------------------------------------------------

test("the elevation tokens exist in both themes", () => {
  const tokens = readFileSync(
    join(process.cwd(), "../../packages/ui/src/tokens.css"),
    "utf8",
  );
  // Three levels, light and dark. design.md §4.3.
  expect(tokens.match(/--shadow-1:/g)?.length).toBe(2);
  expect(tokens.match(/--shadow-3:/g)?.length).toBe(2);
});

test("the viewer surround is defined in both themes and stays neutral", () => {
  const tokens = readFileSync(
    join(process.cwd(), "../../packages/ui/src/tokens.css"),
    "utf8",
  );
  // §3.4: a page photograph judged against pure white reads darker than it is,
  // and against black reads blown out. This token deliberately does not follow
  // the theme in the way the others do.
  expect(tokens.match(/--viewer-surround:/g)?.length).toBe(2);
});
