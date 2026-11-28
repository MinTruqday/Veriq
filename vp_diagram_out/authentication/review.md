# Review — authentication

## [SUY RA]
- Field-only references and multiplicities are inferred from identifier naming and static query/write evidence; MongoDB does not enforce these relationships.
- Missing type hints on extracted document keys default to `varchar(255)` as required by V6.
- Optionality defaults to nullable when a write path or annotation does not guarantee presence.

## Excluded from Domain Model
| Collection | Reason |
|---|---|
| `platform_state` | Technical/infrastructure collection excluded by V6 rule |
| `sessions` | Technical/infrastructure collection excluded by V6 rule |
| `password_reset_tokens` | Technical/infrastructure collection excluded by V6 rule |
| `email_verification_tokens` | Technical/infrastructure collection excluded by V6 rule |
| `audit_logs` | Technical/infrastructure collection excluded by V6 rule |
| `system_configs` | Technical/infrastructure collection excluded by V6 rule |
| `ai_providers` | Technical/infrastructure collection excluded by V6 rule |
| `ai_models` | Technical/infrastructure collection excluded by V6 rule |
| `admin_operations` | Technical/infrastructure collection excluded by V6 rule |
| `service_identities` | Technical/infrastructure collection excluded by V6 rule |
| `secret_references` | Technical/infrastructure collection excluded by V6 rule |

## Code ambiguities / possible issues
- Dict-shaped and update-only fields are merged from static key evidence. The scanner cannot prove every runtime payload shape.
- Identifier fields are attached to the collection where their write/query evidence was extracted; the relationship remains inferred from field naming, not a MongoDB-enforced foreign key.
- Route registrations generated dynamically are represented from the `add_api_route` source pattern; inspect JSON `dynamic` flags if a template expands into multiple concrete routes.
- Frontend boundaries include pages and `*Panel` components whose static import closure reaches a service module. API function/path lists are based on imported symbols; dynamically assembled requests may be missing. BCE links are emitted only when literal paths match extracted backend route paths.
- `overrides.json` is not yet applied by the extractor; dynamic route/collection corrections require code changes to the extractor or a later override implementation.
- The scanner does not modify source application code.

## Extraction coverage
- Routes extracted: 107; dynamic route entries: 2.
- Collections extracted: 12; collections with no detected fields: 0.
- Frontend boundaries extracted: 9 (route pages plus statically linked pages/panels).
- Separate vector stores extracted: 0.
- Check `spec.json` for file and line evidence; add service-specific cases to `overrides.json` if static extraction missed dynamic code.

## Verified schema/write-path ambiguity checked during review

- `AccountService.preferences()` reads `preferences`, and `update_preferences()` writes nested `preferences.*`; `update_notification_settings()` separately writes `notification_settings.*` (`backend/authentication/src/services/account.py`). These remain separate code-backed keys in the extraction.
- `user` references are mapped to the `auth_credentials` collection for the local ERD. This naming map is inferred from code and is not a MongoDB-enforced foreign key.
