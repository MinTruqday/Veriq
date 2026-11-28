# Review — ai

## [SUY RA]
- Field-only references and multiplicities are inferred from identifier naming and static query/write evidence; MongoDB does not enforce these relationships.
- Missing type hints on extracted document keys default to `varchar(255)` as required by V6.
- Optionality defaults to nullable when a write path or annotation does not guarantee presence.

## Excluded from Domain Model
| Collection | Reason |
|---|---|
| `ai_run_source_facts` | Technical/infrastructure collection excluded by V6 rule |
| `document_ingestion_page_checkpoints` | Technical/infrastructure collection excluded by V6 rule |
| `ai_run_derivation_receipts` | Technical/infrastructure collection excluded by V6 rule |
| `ai_run_checkpoints` | Technical/infrastructure collection excluded by V6 rule |
| `agent_traces` | Technical/infrastructure collection excluded by V6 rule |
| `retrieval_audit` | Technical/infrastructure collection excluded by V6 rule |
| `dead_letter_recovery_audit` | Technical/infrastructure collection excluded by V6 rule |

## Code ambiguities / possible issues
- Dict-shaped and update-only fields are merged from static key evidence. The scanner cannot prove every runtime payload shape.
- Route registrations generated dynamically are represented from the `add_api_route` source pattern; inspect JSON `dynamic` flags if a template expands into multiple concrete routes.
- The scanner does not modify source application code.

## Extraction coverage
- Routes extracted: 35; dynamic route entries: 0.
- Collections extracted: 12; collections with no detected fields: 5.
- Separate vector stores extracted: 1.
- Check `spec.json` for file and line evidence; add service-specific cases to `overrides.json` if static extraction missed dynamic code.

## Verified repository activity checked during review

- `long_term_memory` remains in the extraction. It is actively indexed in `backend/ai/src/core/infrastructure/database.py`, read and updated by `backend/ai/src/repositories/memory.py`, exposed through `backend/ai/src/memory/long_term.py`, consumed by `backend/ai/src/knowledge/hybrid.py`, and written for completed runs by `backend/ai/src/runtime/ai_run_worker.py`. The current code therefore supports keeping this collection in the inventory and domain candidates.
- Qdrant collection `veriq` is represented as a separate vector store, not as a MongoDB collection; its payload extraction is under `stores` in `spec.json`.
