# Review — testing

## [SUY RA]
- Field-only references and multiplicities are inferred from identifier naming and static query/write evidence; MongoDB does not enforce these relationships.
- Missing type hints on extracted document keys default to `varchar(255)` as required by V6.
- Optionality defaults to nullable when a write path or annotation does not guarantee presence.

## Excluded from Domain Model
| Collection | Reason |
|---|---|
| `ai_run_outbox` | Technical/infrastructure collection excluded by V6 rule |
| `ai_request_audit` | Technical/infrastructure collection excluded by V6 rule |
| `defect_search_index_outbox` | Technical/infrastructure collection excluded by V6 rule |
| `audit_events` | Technical/infrastructure collection excluded by V6 rule |
| `document_summary_cache` | Technical/infrastructure collection excluded by V6 rule |
| `document_summary_chunk_cache` | Technical/infrastructure collection excluded by V6 rule |

## Code ambiguities / possible issues
- Dict-shaped and update-only fields are merged from static key evidence. The scanner cannot prove every runtime payload shape.
- Route registrations generated dynamically are represented from the `add_api_route` source pattern; inspect JSON `dynamic` flags if a template expands into multiple concrete routes.
- The scanner does not modify source application code.

## Extraction coverage
- Routes extracted: 369; dynamic route entries: 0.
- Collections extracted: 76; collections with no detected fields: 9.
- Separate vector stores extracted: 0.
- Check `spec.json` for file and line evidence; add service-specific cases to `overrides.json` if static extraction missed dynamic code.

## Reference-source attribution limitation

- The current extraction aggregates field-name evidence across schema and repository files, then associates a matching identifier field with each collection that contains that key. This can over-attach a reference to collections sharing common keys such as `project_id`; the generated reference list is a candidate list, not proof that every listed collection stores that reference. Validate each relationship against its collection-specific insert/update/query path before using the ERD.
