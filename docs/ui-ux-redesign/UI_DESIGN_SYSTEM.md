# Veriq UI design system notes

## Foundation

Continue the existing Veriq identity and CSS custom properties in `frontend/app/globals.css`; do not add a competing palette or replace the app shell.

- Brand: `--brand`, `--brand-hover`, `--brand-soft`.
- Surfaces: `--canvas`, `--surface`, `--surface-quiet`, `--surface-raised`.
- Text and borders: `--ink`, `--ink-muted`, `--ink-faint`, `--border`, `--border-strong`.
- Typography: existing app font stack; use clear page, section, body and helper-text hierarchy. Keep dense data readable.
- Spacing: use the current 4/8/12/16/24px rhythm and existing utility classes.
- Corners: use current shared radius utilities; avoid nested bordered containers and heavy shadows.

## Layout and components

- Reuse `WorkspacePage`, `Panel`, `StatusPill`, `Metric`, loading/error/empty states and existing form controls in `WorkspacePrimitives.jsx` and shared UI.
- Use cards for project selection, split view for selecting and inspecting records, tables for sortable/filterable/bulk data, and focused workspaces for execution and document tasks.
- Keep primary actions in the page header or adjacent to the content they affect. Make icon-only controls accessible with labels.
- Keep state colors consistent with existing status semantics. Do not invent new workflow states or show metrics without API evidence.
- On narrow screens, allow headers and toolbars to wrap, preserve access to row actions, and avoid horizontal page overflow.

## Interaction

- Preserve route behavior, permissions, validation, confirmation flows, loading/error feedback and keyboard focus.
- Forms should state required fields and validation errors beside the relevant controls.
- Use a dedicated route/page for substantial create/edit work where the current implementation supports it; retain dialogs for brief confirmations or contextual actions.
- Lists, filters, tabs, dialogs and drawers must keep their existing behavior unless explicitly refactored without changing business semantics.
