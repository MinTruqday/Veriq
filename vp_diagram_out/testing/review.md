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
- Identifier fields are attached to the collection where their write/query evidence was extracted; the relationship remains inferred from field naming, not a MongoDB-enforced foreign key.
- Route registrations generated dynamically are represented from the `add_api_route` source pattern; inspect JSON `dynamic` flags if a template expands into multiple concrete routes.
- Frontend boundaries include pages and `*Panel` components whose static import closure reaches a service module. API function/path lists are based on imported symbols; dynamically assembled requests may be missing. BCE links are emitted only when literal paths match extracted backend route paths.
- `overrides.json` is not yet applied by the extractor; dynamic route/collection corrections require code changes to the extractor or a later override implementation.
- The scanner does not modify source application code.

## Extraction coverage
- Routes extracted: 369; dynamic route entries: 0.
- Collections extracted: 76; collections with no detected fields: 9.
- Frontend boundaries extracted: 37 (route pages plus statically linked pages/panels).
- Separate vector stores extracted: 0.
- Check `spec.json` for file and line evidence; add service-specific cases to `overrides.json` if static extraction missed dynamic code.

## Reference and frontend extraction limits

- Each inferred identifier relationship now takes its source field and evidence list from that specific collection's extracted field record; `evidence` is listed in `spec.json`. The relationship itself is inferred from the identifier field name and matching target collection, so it is not proof of enforced referential integrity.
- Frontend boundaries include route pages and statically linked page/panel components whose import closure reaches a service module. API-to-controller links are generated only when an extracted literal path and HTTP method match a backend route path after parameter normalization. Template-built paths and cases where page code invokes service objects indirectly may be absent or need review.
