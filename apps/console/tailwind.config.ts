import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

/**
 * shadcn/ui — style: new-york, base colour: slate, CSS variables: yes.
 * Token values live in @marking/ui/tokens.css. See docs/design.md §2.
 */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
    "../../packages/ui/src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)"],
        cond: ["var(--font-cond)"],
        mono: ["var(--font-mono)"],
      },
      // design.md §3.2. Three weights only: 400, 500, 600.
      fontSize: {
        caption: ["11px", { lineHeight: "16px", fontWeight: "500" }],
        xs: ["12px", { lineHeight: "16px" }],
        sm: ["13px", { lineHeight: "18px" }],
        base: ["15px", { lineHeight: "22px" }],
        lead: ["17px", { lineHeight: "26px" }],
        h3: ["20px", { lineHeight: "26px", fontWeight: "600" }],
        h2: ["26px", { lineHeight: "32px", fontWeight: "600" }],
        h1: ["34px", { lineHeight: "40px", fontWeight: "600" }],
        mark: ["28px", { lineHeight: "32px", fontWeight: "500" }],
      },
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--card-foreground))" },
        popover: { DEFAULT: "hsl(var(--popover))", foreground: "hsl(var(--popover-foreground))" },
        primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
        accent: { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--accent-foreground))" },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        // authorship states — see .claude/rules/design-tokens.md
        settled: {
          DEFAULT: "hsl(var(--settled))",
          foreground: "hsl(var(--settled-foreground))",
          subtle: "hsl(var(--settled-subtle))",
        },
        caution: {
          DEFAULT: "hsl(var(--caution))",
          foreground: "hsl(var(--caution-foreground))",
          subtle: "hsl(var(--caution-subtle))",
        },
        "machine-subtle": "hsl(var(--machine-subtle))",
        "marker-subtle": "hsl(var(--marker-subtle))",
        "viewer-surround": "hsl(var(--viewer-surround))",
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        chart: {
          "1": "hsl(var(--chart-1))",
          "2": "hsl(var(--chart-2))",
          "3": "hsl(var(--chart-3))",
          "4": "hsl(var(--chart-4))",
          "5": "hsl(var(--chart-5))",
        },
        sidebar: {
          DEFAULT: "hsl(var(--sidebar-background))",
          foreground: "hsl(var(--sidebar-foreground))",
          primary: "hsl(var(--sidebar-primary))",
          "primary-foreground": "hsl(var(--sidebar-primary-foreground))",
          accent: "hsl(var(--sidebar-accent))",
          "accent-foreground": "hsl(var(--sidebar-accent-foreground))",
          border: "hsl(var(--sidebar-border))",
          ring: "hsl(var(--sidebar-ring))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [animate],
} satisfies Config;
