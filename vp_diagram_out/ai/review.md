# Review — ai

## [SUY RA]
- Field-only references and multiplicities are inferred from identifier naming and static query/write evidence; MongoDB does not enforce these relationships.
- Missing type hints on extracted document keys default to `varchar(255)` as required by V6.
- Optionality defaults to nullable when a write path or annotation does not guarantee presence.

## Excluded from Domain Model
| Collection | Reason |
|---|---|
| `ai_run_checkpoints` | Technical/infrastructure collection excluded by V6 rule |
| `agent_traces` | Technical/infrastructure collection excluded by V6 rule |
| `dead_letter_recovery_audit` | Technical/infrastructure collection excluded by V6 rule |
| `retrieval_audit` | Technical/infrastructure collection excluded by V6 rule |
| `document_ingestion_page_checkpoints` | Technical/infrastructure collection excluded by V6 rule |
| `ai_run_derivation_receipts` | Technical/infrastructure collection excluded by V6 rule |
| `ai_run_source_facts` | Technical/infrastructure collection excluded by V6 rule |

## Code ambiguities / possible issues
- Dict-shaped and update-only fields are merged from static key evidence. The scanner cannot prove every runtime payload shape.
- Identifier fields are attached to the collection where their write/query evidence was extracted; the relationship remains inferred from field naming, not a MongoDB-enforced foreign key.
- Route registrations generated dynamically are represented from the `add_api_route` source pattern; inspect JSON `dynamic` flags if a template expands into multiple concrete routes.
- Frontend boundaries include pages and `*Panel` components whose static import closure reaches a service module. API function/path lists are based on imported symbols; dynamically assembled requests may be missing. BCE links are emitted only when literal paths match extracted backend route paths.
- `overrides.json` is not yet applied by the extractor; dynamic route/collection corrections require code changes to the extractor or a later override implementation.
- The scanner does not modify source application code.

## Extraction coverage
- Routes extracted: 35; dynamic route entries: 0.
- Collections extracted: 12; collections with no detected fields: 5.
- Frontend boundaries extracted: 0 (route pages plus statically linked pages/panels).
- Separate vector stores extracted: 1.
- Check `spec.json` for file and line evidence; add service-specific cases to `overrides.json` if static extraction missed dynamic code.

## Verified repository activity checked during review

- `long_term_memory` remains in the extraction. It is indexed in `backend/ai/src/core/infrastructure/database.py`, read and updated by `backend/ai/src/repositories/memory.py`, exposed through `backend/ai/src/memory/long_term.py`, consumed by `backend/ai/src/knowledge/hybrid.py`, and written for completed runs by `backend/ai/src/runtime/ai_run_worker.py`.
- Qdrant collection `veriq` is represented as a separate vector store, not as a MongoDB collection; its payload extraction is under `stores` in `spec.json`.
