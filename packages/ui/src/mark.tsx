/**
 * The mark. design.md §2.6.
 *
 * Solid, single colour, no gradient. Square line caps, not round — round caps
 * read as friendly consumer software, square reads as a stamp, which is the
 * correct register for an examinations instrument.
 */
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
