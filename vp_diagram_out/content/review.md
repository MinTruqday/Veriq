# Review — content

## [SUY RA]
- Field-only references and multiplicities are inferred from identifier naming and static query/write evidence; MongoDB does not enforce these relationships.
- Missing type hints on extracted document keys default to `varchar(255)` as required by V6.
- Optionality defaults to nullable when a write path or annotation does not guarantee presence.

## Excluded from Domain Model
| Collection | Reason |
|---|---|
| `document_ingestion_outbox` | Technical/infrastructure collection excluded by V6 rule |

## Code ambiguities / possible issues
- Dict-shaped and update-only fields are merged from static key evidence. The scanner cannot prove every runtime payload shape.
- Route registrations generated dynamically are represented from the `add_api_route` source pattern; inspect JSON `dynamic` flags if a template expands into multiple concrete routes.
- The scanner does not modify source application code.

## Extraction coverage
- Routes extracted: 41; dynamic route entries: 4.
- Collections extracted: 7; collections with no detected fields: 6.
- Separate vector stores extracted: 0.
- Check `spec.json` for file and line evidence; add service-specific cases to `overrides.json` if static extraction missed dynamic code.
