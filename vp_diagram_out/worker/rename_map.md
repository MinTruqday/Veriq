# Rename map — worker

Tên code | Tên sơ đồ | Loại | Căn cứ
---|---|---|---
`worker_jobs` | `WorkerJob` | collection/table | `backend/worker/src/core/infrastructure/database.py:19, backend/worker/src/repositories/jobs.py:112, backend/worker/src/repositories/jobs.py:13`
`_id` | `WorkerJobId` | field | `backend/worker/src/repositories/jobs.py:157, backend/worker/src/repositories/jobs.py:173`
`attempt_started_at` | `AttemptStartedAt` | field | `backend/worker/src/repositories/jobs.py:159`
`canceled_at` | `CanceledAt` | field | `backend/worker/src/repositories/jobs.py:228`
`delivery_count` | `DeliveryCount` | field | `backend/worker/src/repositories/jobs.py:166`
`dispatch_generation` | `DispatchGeneration` | field | `backend/worker/src/repositories/jobs.py:128`
`error` | `Error` | field | `backend/worker/src/repositories/jobs.py:122, backend/worker/src/repositories/jobs.py:208`
`error_code` | `ErrorCode` | field | `backend/worker/src/repositories/jobs.py:122, backend/worker/src/repositories/jobs.py:208`
`execution_lease_token` | `ExecutionLeaseToken` | field | `backend/worker/src/repositories/jobs.py:159, backend/worker/src/repositories/jobs.py:173`
`execution_lease_until` | `ExecutionLeaseUntil` | field | `backend/worker/src/repositories/jobs.py:159, backend/worker/src/repositories/jobs.py:179`
`manual_retry_count` | `ManualRetryCount` | field | `backend/worker/src/repositories/jobs.py:128`
`reconciliation_required_at` | `ReconciliationRequiredAt` | field | `backend/worker/src/repositories/jobs.py:208`
`request` | `Request` | field | `backend/worker/src/repositories/jobs.py:270`
`status` | `Status` | field | `backend/worker/src/repositories/jobs.py:122, backend/worker/src/repositories/jobs.py:157`
`updated_at` | `UpdatedAt` | field | `backend/worker/src/repositories/jobs.py:122, backend/worker/src/repositories/jobs.py:159`
`worker_job_outbox` | `WorkerJobOutbox` | collection/table | `backend/worker/src/core/infrastructure/database.py:23, backend/worker/src/repositories/jobs.py:139, backend/worker/src/repositories/jobs.py:17`
`_id` | `WorkerJobOutboxId` | field | `backend/worker/src/repositories/jobs.py:140, backend/worker/src/repositories/jobs.py:41`
`attempt_count` | `AttemptCount` | field | `backend/worker/src/repositories/jobs.py:140, backend/worker/src/repositories/jobs.py:43`
`created_at` | `CreatedAt` | field | `backend/worker/src/repositories/jobs.py:140, backend/worker/src/repositories/jobs.py:43`
`dispatch_generation` | `DispatchGeneration` | field | `backend/worker/src/repositories/jobs.py:140, backend/worker/src/repositories/jobs.py:240`
`expire_at` | `ExpireAt` | field | `backend/worker/src/repositories/jobs.py:246, backend/worker/src/repositories/jobs.py:84`
`job_id` | `JobId` | field | `backend/worker/src/repositories/jobs.py:140, backend/worker/src/repositories/jobs.py:240`
`last_error` | `LastError` | field | `backend/worker/src/repositories/jobs.py:90, backend/worker/src/repositories/jobs.py:98`
`lease_token` | `LeaseToken` | field | `backend/worker/src/repositories/jobs.py:104, backend/worker/src/repositories/jobs.py:68`
`lease_until` | `LeaseUntil` | field | `backend/worker/src/repositories/jobs.py:104, backend/worker/src/repositories/jobs.py:68`
`next_attempt_at` | `NextAttemptAt` | field | `backend/worker/src/repositories/jobs.py:140, backend/worker/src/repositories/jobs.py:43`
`payload` | `Payload` | field | `backend/worker/src/repositories/jobs.py:140, backend/worker/src/repositories/jobs.py:43`
`published_at` | `PublishedAt` | field | `backend/worker/src/repositories/jobs.py:84`
`status` | `Status` | field | `backend/worker/src/repositories/jobs.py:140, backend/worker/src/repositories/jobs.py:240`
`updated_at` | `UpdatedAt` | field | `backend/worker/src/repositories/jobs.py:140, backend/worker/src/repositories/jobs.py:246`
`collection` | `Collection` | method | `backend/worker/src/repositories/jobs.py:12`
`outbox` | `Outbox` | method | `backend/worker/src/repositories/jobs.py:16`
`create_job_with_outbox` | `CreateJobWithOutbox` | method | `backend/worker/src/repositories/jobs.py:19`
`ensure_queued_job_outbox` | `EnsureQueuedJobOutbox` | method | `backend/worker/src/repositories/jobs.py:33`
`claim_next_outbox` | `ClaimNextOutbox` | method | `backend/worker/src/repositories/jobs.py:59`
`mark_outbox_published` | `MarkOutboxPublished` | method | `backend/worker/src/repositories/jobs.py:80`
`reschedule_outbox` | `RescheduleOutbox` | method | `backend/worker/src/repositories/jobs.py:94`
`claim_retry_with_outbox` | `ClaimRetryWithOutbox` | method | `backend/worker/src/repositories/jobs.py:108`
`claim_execution` | `ClaimExecution` | method | `backend/worker/src/repositories/jobs.py:155`
`renew_execution_lease` | `RenewExecutionLease` | method | `backend/worker/src/repositories/jobs.py:171`
`finalize_execution` | `FinalizeExecution` | method | `backend/worker/src/repositories/jobs.py:186`
`mark_expired_executions_for_reconciliation` | `MarkExpiredExecutionsForReconciliation` | method | `backend/worker/src/repositories/jobs.py:200`
`fail_execution` | `FailExecution` | method | `backend/worker/src/repositories/jobs.py:219`
`cancel_queued` | `CancelQueued` | method | `backend/worker/src/repositories/jobs.py:222`
`record` | `Record` | method | `backend/worker/src/repositories/jobs.py:257`
`find_one` | `FindOne` | method | `backend/worker/src/repositories/jobs.py:264`
`list` | `List` | method | `backend/worker/src/repositories/jobs.py:267`
`count` | `Count` | method | `backend/worker/src/repositories/jobs.py:275`
`overview` | `Overview` | method | `backend/worker/src/repositories/jobs.py:278`
`discard` | `Discard` | method | `backend/worker/src/repositories/jobs.py:283`
`health` | `Ctrl_Main` | route method in grouped control | `backend/worker/src/main.py:40`
`ready` | `Ctrl_Main` | route method in grouped control | `backend/worker/src/main.py:45`
`enqueue_testing_job` | `Ctrl_Main` | route method in grouped control | `backend/worker/src/main.py:74`
`retry_job` | `Ctrl_Main` | route method in grouped control | `backend/worker/src/main.py:83`
`cancel_job` | `Ctrl_Main` | route method in grouped control | `backend/worker/src/main.py:88`
`get_job` | `Ctrl_Main` | route method in grouped control | `backend/worker/src/main.py:93`
`list_jobs` | `Ctrl_Main` | route method in grouped control | `backend/worker/src/main.py:98`
`job_overview` | `Ctrl_Main` | route method in grouped control | `backend/worker/src/main.py:108`
`discard_job` | `Ctrl_Main` | route method in grouped control | `backend/worker/src/main.py:116`
