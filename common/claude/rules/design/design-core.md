---
paths:
  - "**/*.tsx"
  - "**/*.jsx"
  - "**/*.css"
  - "**/*.scss"
  - "**/*.html"
  - "**/*.vue"
  - "**/*.svelte"
---

# Design Core

Apply whenever output changes appearance, interaction, or motion.

## Evidence hierarchy

Accessibility is a hard floor. Within it, resolve conflicts as explicit user direction → exact declared reference/Figma → repository truth → Apple foundation → selected specialist → Astryx fallback. Apple owns unresolved interaction behavior, not visual identity or a house style.

## Minimal quality floor

- Preserve the subject's identity; avoid generic AI landing-page defaults.
- For substantial new/redesigned UI, define only the tokens and layout needed by the implementation. Exact reproduction and tiny fixes inherit existing values.
- Reuse the repository spacing scale; otherwise use a coherent 4px-based scale. Keep related items tight and distinct groups separated. Block accidental overlap, clipping, horizontal overflow, and hit-area collisions; intentional overlap needs an explicit layer and must not obscure content or controls.
- Verify supported narrow, mid, and wide layouts with long/localized copy and 200% zoom before release.
- Reject an AI scaffold unless the subject truly calls for it: nested/identical card grids, repeated eyebrow or 01/02 markers, decorative gradient/glass, and hero-metric templates are not defaults.
- Keep hierarchy legible, controls direct, feedback immediate, and disclosure progressive. Direct manipulation uses 1:1 tracking and interruptible/reversible transitions; preserve velocity only when it clarifies continuity.
- Maintain WCAG AA contrast and visible focus. Use restrained springs/depth only to explain state, provide a no-motion equivalent, and honor `prefers-reduced-motion`.
- Icons come from an established icon library only — the project's existing library first; otherwise pick ONE of lucide / heroicons / phosphor / radix (SF Symbols on Apple platforms). Never emoji-as-icon, never hand-drawn or ad-hoc SVG icon paths; one icon library per project.
- Do not install or invoke a separate `taste` skill; the selected specialist owns aesthetic judgment.
