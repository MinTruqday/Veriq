# Customer Data Retention and Deletion Standard

Document owner: Security Operations
Version: 1.8
Status: Approved
Effective date: 2026-05-01

## 1. Customer account deletion

When an account owner confirms deletion, interactive access is revoked immediately. Customer profile data and user-uploaded attachments enter a thirty-day recovery period before permanent deletion. Legal holds suspend permanent deletion only for the records covered by the hold; they do not restore interactive access.

## 2. Audit event retention

Security audit events are retained for four hundred days from event creation. At the end of that period, the event is removed from the active search index and scheduled for deletion from the archive. Audit events are not subject to the thirty-day customer profile recovery period because they serve a separate security and compliance purpose.

## 3. Payment record retention

Settlement and refund ledger entries are retained for seven years after the relevant financial year closes. Deleting a customer account does not remove a legally required ledger entry. Where possible, the account reference is replaced with a non-reversible pseudonymous identifier after account deletion.

## 4. Backup lifecycle

Encrypted backups are rotated every thirty-five days. A deletion request may remain in an immutable backup until that backup expires, but the deleted record must not be restored into active service during routine recovery. If a backup is restored for disaster recovery, deletion markers are reapplied before customer access is enabled.

## 5. Search index behavior

Search indexes are derived copies, not authoritative records. A deletion or access revocation must be enforced by the serving API immediately; asynchronous index cleanup is not an authorization mechanism. Index cleanup jobs record the source identifier, generation, completion time, and retry status.

| Record class | Retention period | Deletion behavior |
|---|---|---|
| Customer profile and uploaded attachments | Thirty-day recovery period | Then permanently delete unless covered by a legal hold |
| Security audit event | Four hundred days | Remove from active search, then delete from archive |
| Settlement and refund ledger | Seven years after financial year close | Retain with pseudonymous account reference where possible |
| Encrypted backup | Thirty-five-day rotation | Reapply deletion markers before restored service opens |
