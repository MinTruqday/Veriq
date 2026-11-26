# Design System UI/UX Refactor

Refactor uses the existing tokens and components. It does not introduce a second visual system or new brand palette.

| Purpose | Current source |
|---|---|
| Brand and surfaces | `frontend/app/globals.css`: `--brand`, `--brand-hover`, `--brand-soft`, `--surface`, `--surface-quiet`, `--surface-raised` |
| Text and borders | `--ink`, `--ink-muted`, `--ink-faint`, `--border`, `--border-strong` |
| Utility mapping | `frontend/tailwind.config.js` |
| Shared layout and panels | `WorkspacePage`, `Panel`, `StatusPill`, `Metric`, `LoadingState`, `ErrorState` in `WorkspacePrimitives.jsx` |
| Navigation and access | `navigation.js`, `navigationAccess.mjs`, project route helpers |
| Form controls and buttons | existing `apple-input`, `apple-button`, `secondary-button`, `danger-button`, `icon-button` styles in `globals.css` |

## Rules for this refactor

- Keep current logo, font, colors, tokens, shell and navigation model.
- Use the existing spacing, border and control tokens. Avoid decorative gradients, nested panels and excess cards.
- Choose the layout per task: grid/list for projects, dashboard for overview, split view for repositories, document workspace for plans, execution workspace for runs, kanban/list for defects, reader for documents, grouped settings for configuration.
- Keep current permission gates, backend states and real API values. No frontend-only fake metrics or workflow actions.
- Support loading, empty and error states. Keep keyboard focus visible and use accessible labels for icon buttons/charts.
- Check 1280×720, 1440×900, 1920×1080 and narrower layouts.
