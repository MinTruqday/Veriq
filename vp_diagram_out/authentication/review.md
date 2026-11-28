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
- Route registrations generated dynamically are represented from the `add_api_route` source pattern; inspect JSON `dynamic` flags if a template expands into multiple concrete routes.
- The scanner does not modify source application code.

## Extraction coverage
- Routes extracted: 107; dynamic route entries: 2.
- Collections extracted: 12; collections with no detected fields: 0.
- Separate vector stores extracted: 0.
- Check `spec.json` for file and line evidence; add service-specific cases to `overrides.json` if static extraction missed dynamic code.

## Verified schema/write-path ambiguity checked during review

- `AccountService.preferences()` reads the `preferences` key, and `update_preferences()` writes nested `preferences.*`; `update_notification_settings()` separately writes `notification_settings.*` (`backend/authentication/src/services/account.py`). This means both shapes are retained as distinct code-backed keys where extracted; the scanner does not reconcile them into one field.
- User-facing name `user` is represented by the extracted `auth_credentials` collection for local `user_id` references. This is a naming map inferred from service code, not a MongoDB-enforced foreign key.
