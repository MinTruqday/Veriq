# VP diagram extraction progress

Generated from the current repository by `vp_diagram_out/tools/extract.py`. No application source code was modified.

## Current inventory

Service | Mongo collections | Routes | Frontend boundaries | Domain classes | ERD fields | BCE prompt groups
---|---:|---:|---:|---:|---:|---:
authentication | 12 | 107 | 9 | 1 | 132 | 22
content | 7 | 41 | 0 | 6 | 30 | 17
cloud | 5 | 77 | 3 | 5 | 33 | 35
notification | 2 | 9 | 2 | 2 | 3 | 4
testing | 76 | 369 | 37 | 70 | 481 | 125
worker | 2 | 9 | 0 | 0 | 28 | 1
ai | 12 plus 1 separate vector store | 35 | 0 | 5 | 87 Mongo fields | 31

## Completed in this pass

- Fixed local/external reference candidates to use each collection's own extracted field evidence rather than copying a global name match across all collections.
- Followed frontend relative and alias imports through service files. Captured page and panel boundaries with direct service dependencies, including auth admin panels and cloud upload use in testing pages.
- Linked literal frontend path + HTTP method pairs to matching backend route controls when a static route path matched. The BCE frontend prompt declares those controls and their operations.
- Excluded generic dynamic routes such as `/{event}` from path matching. Recorded import/path extraction limits in each service `review.md`.
- Kept AI `long_term_memory` because code has active index, read, and write paths; Qdrant remains listed separately from Mongo.

## Still requires human review against runtime behavior

- FastAPI routers may receive prefixes from `main.py`; the extractor matches path suffixes and normalizes `{parameter}` names, so check cross-router collisions and route-prefix cases in `P3_bce_frontend_pages.txt`.
- Import-closure analysis cannot prove that every transitively imported API is exercised in every UI state. Review the boundary links against the component code where exact UI behavior matters.
- Static field and optionality inference cannot prove runtime payload shape or requiredness. Use `spec.json` evidence and per-service `review.md` for ambiguous/update-only fields.
- `overrides.json` is still a notes file and is not applied by the extractor. Dynamic route/collection corrections are not automated.

## Output

All generated artifacts are under `vp_diagram_out/`; regenerate them with `python3 vp_diagram_out/tools/extract.py`.
