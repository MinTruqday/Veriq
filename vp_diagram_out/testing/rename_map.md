# Rename map — testing

Tên code | Tên sơ đồ | Loại | Căn cứ
---|---|---|---
`ai_run_outbox` | `AiRunOutbox` | collection/table | `backend/testing/src/clients/ai_capabilities.py:140, backend/testing/src/clients/ai_capabilities.py:226, backend/testing/src/clients/ai_capabilities.py:243`
`_id` | `AiRunOutboxId` | field | `backend/testing/src/clients/ai_capabilities.py:227, backend/testing/src/clients/ai_capabilities.py:244`
`attempts` | `Attempts` | field | `backend/testing/src/clients/ai_capabilities.py:229, backend/testing/src/clients/ai_capabilities.py:378`
`cancel_reason` | `CancelReason` | field | `backend/testing/src/clients/ai_capabilities.py:149`
`created_at` | `CreatedAt` | field | `backend/testing/src/clients/ai_capabilities.py:229`
`dispatch_token` | `DispatchToken` | field | `backend/testing/src/clients/ai_capabilities.py:154, backend/testing/src/clients/ai_capabilities.py:274`
`event_fingerprint` | `EventFingerprint` | field | `backend/testing/src/clients/ai_capabilities.py:229, backend/testing/src/clients/ai_capabilities.py:245`
`last_error` | `LastError` | field | `backend/testing/src/clients/ai_capabilities.py:348, backend/testing/src/clients/ai_capabilities.py:378`
`next_attempt_at` | `NextAttemptAt` | field | `backend/testing/src/clients/ai_capabilities.py:229, backend/testing/src/clients/ai_capabilities.py:378`
`payload` | `Payload` | field | `backend/testing/src/clients/ai_capabilities.py:141, backend/testing/src/clients/ai_capabilities.py:154`
`status` | `Status` | field | `backend/testing/src/clients/ai_capabilities.py:141, backend/testing/src/clients/ai_capabilities.py:149`
`suppressed_at` | `SuppressedAt` | field | `backend/testing/src/clients/ai_capabilities.py:348`
`suppression_reason` | `SuppressionReason` | field | `backend/testing/src/clients/ai_capabilities.py:348`
`trigger` | `Trigger` | field | `backend/testing/src/clients/ai_capabilities.py:141`
`updated_at` | `UpdatedAt` | field | `backend/testing/src/clients/ai_capabilities.py:149, backend/testing/src/clients/ai_capabilities.py:229`
`requirement_versions` | `RequirementVersion` | collection/table | `backend/testing/src/clients/notification.py:48, backend/testing/src/core/database.py:182, backend/testing/src/modules/design/services/test_case_review.py:185`
`_id` | `RequirementVersionId` | field | `backend/testing/src/clients/notification.py:49, backend/testing/src/modules/design/services/test_case_review.py:186`
`acceptance_criterion_ids` | `AcceptanceCriterionIds` | field | `backend/testing/src/repositories/requirement.py:212`
`dependencies` | `Dependencies` | field | `backend/testing/src/repositories/requirement_analysis.py:47`
`index_error_code` | `IndexErrorCode` | field | `backend/testing/src/repositories/requirement_document.py:523`
`index_status` | `IndexStatus` | field | `backend/testing/src/repositories/requirement_document.py:523`
`obsolete_at` | `ObsoleteAt` | field | `backend/testing/src/repositories/requirement.py:544, backend/testing/src/repositories/requirement.py:589`
`obsolete_by` | `ObsoleteBy` | field | `backend/testing/src/repositories/requirement.py:544, backend/testing/src/repositories/requirement.py:589`
`obsolete_reason` | `ObsoleteReason` | field | `backend/testing/src/repositories/requirement.py:544, backend/testing/src/repositories/requirement.py:589`
`project_id` | `ProjectId` | field | `backend/testing/src/modules/design/services/test_case_review.py:186, backend/testing/src/modules/execution/api/simple_reports.py:82`
`requirement_id` | `RequirementId` | field | `backend/testing/src/clients/notification.py:49, backend/testing/src/modules/requirements/services/requirement_import_workflow.py:771`
`restore_reason` | `RestoreReason` | field | `backend/testing/src/repositories/requirement.py:582`
`restored_at` | `RestoredAt` | field | `backend/testing/src/repositories/requirement.py:582`
`restored_by` | `RestoredBy` | field | `backend/testing/src/repositories/requirement.py:582`
`revision` | `Revision` | field | `backend/testing/src/repositories/requirement.py:174, backend/testing/src/repositories/requirement.py:279`
`source_refs` | `SourceRefs` | field | `backend/testing/src/repositories/requirement.py:42, backend/testing/src/repositories/requirement.py:46`
`status` | `Status` | field | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:61, backend/testing/src/modules/quality/services/requirement_impact_worker.py:62`
`status_before_obsolete` | `StatusBeforeObsolete` | field | `backend/testing/src/repositories/requirement.py:544, backend/testing/src/repositories/requirement.py:589`
`superseded_at` | `SupersededAt` | field | `backend/testing/src/repositories/requirement.py:74`
`superseded_by` | `SupersededBy` | field | `backend/testing/src/repositories/requirement.py:74`
`superseded_by_requirement_ids` | `SupersededByRequirementIds` | field | `backend/testing/src/repositories/requirement.py:74`
`superseded_by_transformation_id` | `SupersededByTransformationId` | field | `backend/testing/src/repositories/requirement.py:166, backend/testing/src/repositories/requirement.py:67`
`updated_at` | `UpdatedAt` | field | `backend/testing/src/repositories/requirement.py:172, backend/testing/src/repositories/requirement.py:544`
`version` | `Version` | field | `backend/testing/src/repositories/analysis.py:22, backend/testing/src/repositories/requirement.py:363`
`test_case_versions` | `TestCaseVersion` | collection/table | `backend/testing/src/clients/notification.py:53, backend/testing/src/core/database.py:204, backend/testing/src/core/database.py:205`
`_id` | `TestCaseVersionId` | field | `backend/testing/src/clients/notification.py:54, backend/testing/src/core/database.py:586`
`approval_audit_error_code` | `ApprovalAuditErrorCode` | field | `backend/testing/src/repositories/test_design.py:231`
`approval_audit_status` | `ApprovalAuditStatus` | field | `backend/testing/src/modules/design/services/test_case_batch_review.py:336, backend/testing/src/repositories/test_design.py:231`
`created_at` | `CreatedAt` | field | `backend/testing/src/repositories/test_design.py:54`
`index_error_code` | `IndexErrorCode` | field | `backend/testing/src/repositories/test_design.py:231`
`index_status` | `IndexStatus` | field | `backend/testing/src/modules/design/services/test_case_batch_review.py:336, backend/testing/src/repositories/test_design.py:231`
`indexed_at` | `IndexedAt` | field | `backend/testing/src/repositories/test_design.py:231`
`project_id` | `ProjectId` | field | `backend/testing/src/modules/design/services/test_case_batch_review.py:146, backend/testing/src/modules/design/services/test_case_batch_review.py:255`
`requirement_version_ids` | `RequirementVersionIds` | field | `backend/testing/src/repositories/requirement_import.py:44, backend/testing/src/repositories/requirement_import.py:45`
`status` | `Status` | field | `backend/testing/src/modules/integrations/services/junit_import.py:155, backend/testing/src/repositories/test_design.py:54`
`test_case_id` | `TestCaseId` | field | `backend/testing/src/clients/notification.py:54, backend/testing/src/modules/design/services/test_case_batch_review.py:289`
`test_case_key` | `TestCaseKey` | field | `backend/testing/src/modules/execution/api/simple_reports.py:150`
`title` | `Title` | field | `backend/testing/src/modules/execution/api/simple_reports.py:150, backend/testing/src/modules/execution/services/test_period.py:187`
`trace_error_code` | `TraceErrorCode` | field | `backend/testing/src/repositories/test_design.py:231`
`trace_status` | `TraceStatus` | field | `backend/testing/src/modules/design/services/test_case_batch_review.py:336, backend/testing/src/repositories/test_design.py:231`
`version` | `Version` | field | `backend/testing/src/modules/execution/api/simple_reports.py:150, backend/testing/src/modules/execution/services/test_period.py:187`
`notification_subscriptions` | `NotificationSubscription` | collection/table | `backend/testing/src/clients/notification.py:65, backend/testing/src/core/database.py:302, backend/testing/src/core/database.py:305`
`artifact_id` | `ArtifactId` | field | `backend/testing/src/clients/notification.py:66`
`artifact_type` | `ArtifactType` | field | `backend/testing/src/clients/notification.py:66`
`project_id` | `ProjectId` | field | `backend/testing/src/clients/notification.py:66`
`user_id` | `UserId` | field | `backend/testing/src/clients/notification.py:71`
`project_notification_preferences` | `ProjectNotificationPreference` | collection/table | `backend/testing/src/clients/notification.py:82, backend/testing/src/core/database.py:309, backend/testing/src/repositories/project_notification.py:17`
`channels` | `Channels` | field | `backend/testing/src/clients/notification.py:84`
`digest_frequency` | `DigestFrequency` | field | `backend/testing/src/clients/notification.py:84`
`muted_events` | `MutedEvents` | field | `backend/testing/src/clients/notification.py:84`
`project_id` | `ProjectId` | field | `backend/testing/src/clients/notification.py:83`
`user_id` | `UserId` | field | `backend/testing/src/clients/notification.py:83, backend/testing/src/clients/notification.py:84`
`test_results` | `TestResult` | collection/table | `backend/testing/src/clients/notification.py:58, backend/testing/src/core/database.py:361, backend/testing/src/modules/execution/api/simple_reports.py:125`
`_id` | `TestResultId` | field | `backend/testing/src/clients/notification.py:59, backend/testing/src/modules/execution/services/test_period.py:95`
`completed_at` | `CompletedAt` | field | `backend/testing/src/modules/integrations/services/junit_import.py:191, backend/testing/src/modules/integrations/services/junit_import.py:92`
`executor_id` | `ExecutorId` | field | `backend/testing/src/modules/integrations/services/junit_import.py:191, backend/testing/src/modules/integrations/services/junit_import.py:92`
`linked_defect_ids` | `LinkedDefectIds` | field | `backend/testing/src/repositories/defect.py:90`
`note` | `Note` | field | `backend/testing/src/modules/integrations/services/junit_import.py:191, backend/testing/src/modules/integrations/services/junit_import.py:92`
`project_id` | `ProjectId` | field | `backend/testing/src/modules/execution/api/simple_reports.py:125, backend/testing/src/modules/execution/services/test_period.py:172`
`retested_defect_ids` | `RetestedDefectIds` | field | `backend/testing/src/repositories/defect.py:246, backend/testing/src/repositories/defect.py:257`
`revision` | `Revision` | field | `backend/testing/src/modules/integrations/services/junit_import.py:189, backend/testing/src/modules/integrations/services/junit_import.py:198`
`status` | `Status` | field | `backend/testing/src/modules/integrations/services/junit_import.py:191, backend/testing/src/modules/integrations/services/junit_import.py:92`
`test_case_version_id` | `TestCaseVersionId` | field | `backend/testing/src/modules/integrations/services/junit_import.py:164, backend/testing/src/modules/integrations/services/junit_import.py:83`
`test_run_id` | `TestRunId` | field | `backend/testing/src/clients/notification.py:59, backend/testing/src/modules/execution/api/simple_reports.py:125`
`updated_at` | `UpdatedAt` | field | `backend/testing/src/modules/integrations/services/junit_import.py:191, backend/testing/src/modules/integrations/services/junit_import.py:92`
`requirements` | `Requirement` | collection/table | `backend/testing/src/core/ai_capabilities.py:102, backend/testing/src/core/database.py:139, backend/testing/src/modules/design/services/test_case_review.py:191`
`_id` | `RequirementId` | field | `backend/testing/src/core/ai_capabilities.py:103, backend/testing/src/core/ai_capabilities.py:109`
`current_version_id` | `CurrentVersionId` | field | `backend/testing/src/core/ai_capabilities.py:103, backend/testing/src/modules/design/services/test_case_review.py:193`
`obsolete_at` | `ObsoleteAt` | field | `backend/testing/src/repositories/requirement.py:506, backend/testing/src/repositories/requirement.py:628`
`obsolete_by` | `ObsoleteBy` | field | `backend/testing/src/repositories/requirement.py:506, backend/testing/src/repositories/requirement.py:628`
`obsolete_reason` | `ObsoleteReason` | field | `backend/testing/src/repositories/requirement.py:506, backend/testing/src/repositories/requirement.py:628`
`owner_id` | `OwnerId` | field | `backend/testing/src/repositories/requirement.py:336`
`project_id` | `ProjectId` | field | `backend/testing/src/core/ai_capabilities.py:103, backend/testing/src/modules/design/services/test_case_review.py:192`
`requirement_key` | `RequirementKey` | field | `backend/testing/src/repositories/analysis.py:16, backend/testing/src/repositories/requirement.py:268`
`restore_reason` | `RestoreReason` | field | `backend/testing/src/repositories/requirement.py:621`
`restored_at` | `RestoredAt` | field | `backend/testing/src/repositories/requirement.py:621`
`restored_by` | `RestoredBy` | field | `backend/testing/src/repositories/requirement.py:621`
`status` | `Status` | field | `backend/testing/src/core/ai_capabilities.py:103, backend/testing/src/repositories/analysis.py:148`
`status_before_obsolete` | `StatusBeforeObsolete` | field | `backend/testing/src/repositories/requirement.py:506, backend/testing/src/repositories/requirement.py:628`
`superseded_at` | `SupersededAt` | field | `backend/testing/src/repositories/requirement.py:108`
`superseded_by` | `SupersededBy` | field | `backend/testing/src/repositories/requirement.py:108`
`superseded_by_requirement_ids` | `SupersededByRequirementIds` | field | `backend/testing/src/repositories/requirement.py:108`
`superseded_by_transformation_id` | `SupersededByTransformationId` | field | `backend/testing/src/repositories/requirement.py:100, backend/testing/src/repositories/requirement.py:108`
`tags` | `Tags` | field | `backend/testing/src/repositories/requirement.py:336`
`title` | `Title` | field | `backend/testing/src/repositories/analysis.py:16`
`updated_at` | `UpdatedAt` | field | `backend/testing/src/repositories/requirement.py:108, backend/testing/src/repositories/requirement.py:163`
`ai_request_audit` | `AiRequestAudit` | collection/table | `backend/testing/src/core/ai_capabilities.py:48, backend/testing/src/core/database.py:223, backend/testing/src/core/database.py:224`
`projects` | `Project` | collection/table | `backend/testing/src/core/ai_capabilities.py:152, backend/testing/src/core/database.py:122, backend/testing/src/core/database.py:128`
`_id` | `ProjectId` | field | `backend/testing/src/core/ai_capabilities.py:152, backend/testing/src/core/database.py:96`
`locale` | `Locale` | field | `backend/testing/src/core/ai_capabilities.py:152, backend/testing/src/modules/quality/services/requirement_impact_worker.py:59`
`project_lead_user_id` | `ProjectLeadUserId` | field | `backend/testing/src/core/human_decisions.py:11`
`project_owner_user_id` | `ProjectOwnerUserId` | field | `backend/testing/src/core/database.py:91`
`revision` | `Revision` | field | `backend/testing/src/modules/projects/services/project_progress.py:16`
`settings` | `Settings` | field | `backend/testing/src/modules/design/services/test_case_review.py:251, backend/testing/src/repositories/execution_context.py:35`
`test_case_publication_revision` | `TestCasePublicationRevision` | field | `backend/testing/src/modules/design/services/test_case_review.py:244`
`test_analysis_findings` | `TestAnalysisFinding` | collection/table | `backend/testing/src/core/database.py:288, backend/testing/src/core/database.py:289, backend/testing/src/core/database.py:292`
`_id` | `TestAnalysisFindingId` | field | `backend/testing/src/repositories/test_analysis.py:27`
`revision` | `Revision` | field | `backend/testing/src/repositories/test_analysis.py:37`
`test_conditions` | `TestCondition` | collection/table | `backend/testing/src/core/database.py:285, backend/testing/src/core/database.py:286, backend/testing/src/core/database.py:287`
`_id` | `TestConditionId` | field | `backend/testing/src/repositories/test_design.py:280`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/test_analysis.py:9`
`status` | `Status` | field | `backend/testing/src/repositories/test_analysis.py:9, backend/testing/src/repositories/test_design.py:280`
`test_plans` | `TestPlan` | collection/table | `backend/testing/src/core/database.py:125, backend/testing/src/core/database.py:284, backend/testing/src/core/database.py:430`
`_id` | `TestPlanId` | field | `backend/testing/src/core/database.py:496, backend/testing/src/modules/execution/api/simple_reports.py:233`
`approved_at` | `ApprovedAt` | field | `backend/testing/src/modules/execution/api/simple_reports.py:234`
`created_at` | `CreatedAt` | field | `backend/testing/src/modules/execution/api/simple_reports.py:234`
`name` | `Name` | field | `backend/testing/src/modules/execution/api/simple_reports.py:234, backend/testing/src/modules/quality/services/requirement_impact_worker.py:81`
`project_id` | `ProjectId` | field | `backend/testing/src/modules/execution/api/simple_reports.py:233, backend/testing/src/modules/execution/api/simple_reports.py:66`
`requirement_version_ids` | `RequirementVersionIds` | field | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:80, backend/testing/src/modules/quality/services/requirement_impact_worker.py:81`
`revision` | `Revision` | field | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:225, backend/testing/src/modules/requirements/api/requirement_records.py:140`
`status` | `Status` | field | `backend/testing/src/modules/execution/api/simple_reports.py:234, backend/testing/src/modules/execution/services/test_period.py:161`
`test_case_version_ids` | `TestCaseVersionIds` | field | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:81`
`test_period_id` | `TestPeriodId` | field | `backend/testing/src/modules/execution/api/simple_reports.py:234, backend/testing/src/modules/execution/services/test_period.py:161`
`test_suite_snapshots` | `TestSuiteSnapshots` | field | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:81`
`test_case_drafts` | `TestCaseDraft` | collection/table | `backend/testing/src/core/database.py:198, backend/testing/src/core/database.py:199, backend/testing/src/core/database.py:200`
`_id` | `TestCaseDraftId` | field | `backend/testing/src/core/database.py:533, backend/testing/src/modules/design/services/generation.py:232`
`approval_batch_id` | `ApprovalBatchId` | field | `backend/testing/src/modules/design/services/test_case_batch_review.py:162`
`approved_at` | `ApprovedAt` | field | `backend/testing/src/modules/design/services/test_case_batch_review.py:162, backend/testing/src/modules/design/services/test_case_lifecycle.py:333`
`approved_by` | `ApprovedBy` | field | `backend/testing/src/modules/design/services/test_case_batch_review.py:162, backend/testing/src/modules/design/services/test_case_lifecycle.py:333`
`expected_result_doc` | `ExpectedResultDoc` | field | `backend/testing/src/modules/design/services/generation.py:232`
`frozen_version_id` | `FrozenVersionId` | field | `backend/testing/src/modules/design/services/test_case_batch_review.py:162, backend/testing/src/modules/design/services/test_case_batch_review.py:252`
`merge_decision_ids` | `MergeDecisionIds` | field | `backend/testing/src/repositories/test_case_review.py:42`
`objective_doc` | `ObjectiveDoc` | field | `backend/testing/src/modules/design/services/generation.py:232`
`preconditions_doc` | `PreconditionsDoc` | field | `backend/testing/src/modules/design/services/generation.py:232`
`project_id` | `ProjectId` | field | `backend/testing/src/modules/design/services/test_case_batch_review.py:137, backend/testing/src/modules/design/services/test_case_batch_review.py:162`
`revision` | `Revision` | field | `backend/testing/src/modules/design/services/generation.py:232, backend/testing/src/modules/design/services/test_case_batch_review.py:137`
`status` | `Status` | field | `backend/testing/src/modules/design/services/generation.py:228, backend/testing/src/modules/design/services/generation.py:232`
`steps` | `Steps` | field | `backend/testing/src/modules/design/services/generation.py:232`
`test_case_key` | `TestCaseKey` | field | `backend/testing/src/modules/design/services/test_case_batch_review.py:284`
`title` | `Title` | field | `backend/testing/src/modules/design/services/generation.py:232`
`updated_at` | `UpdatedAt` | field | `backend/testing/src/modules/design/services/test_case_lifecycle.py:333`
`test_case_custom_fields` | `TestCaseCustomField` | collection/table | `backend/testing/src/core/database.py:536, backend/testing/src/core/database.py:551`
`_id` | `TestCaseCustomFieldId` | field | `backend/testing/src/core/database.py:551`
`test_runs` | `TestRun` | collection/table | `backend/testing/src/core/database.py:126, backend/testing/src/core/database.py:127, backend/testing/src/core/database.py:296`
`_id` | `TestRunId` | field | `backend/testing/src/core/database.py:616, backend/testing/src/modules/execution/services/test_period.py:102`
`assignee_id` | `AssigneeId` | field | `backend/testing/src/repositories/test_run.py:261`
`idempotency_key` | `IdempotencyKey` | field | `backend/testing/src/repositories/test_run.py:24, backend/testing/src/repositories/test_run.py:29`
`name` | `Name` | field | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:103`
`project_id` | `ProjectId` | field | `backend/testing/src/modules/execution/api/simple_reports.py:102, backend/testing/src/modules/execution/services/test_period.py:102`
`rerun_of_run_id` | `RerunOfRunId` | field | `backend/testing/src/repositories/test_run.py:29`
`revision` | `Revision` | field | `backend/testing/src/repositories/test_run.py:102, backend/testing/src/repositories/test_run.py:158`
`status` | `Status` | field | `backend/testing/src/modules/execution/services/test_period.py:272, backend/testing/src/modules/quality/services/requirement_impact_worker.py:103`
`test_case_assignments` | `TestCaseAssignments` | field | `backend/testing/src/repositories/test_run.py:261`
`test_case_version_ids` | `TestCaseVersionIds` | field | `backend/testing/src/repositories/bulk_operation.py:98`
`test_period_id` | `TestPeriodId` | field | `backend/testing/src/modules/execution/services/test_period.py:103, backend/testing/src/modules/execution/services/test_period.py:153`
`test_plan_id` | `TestPlanId` | field | `backend/testing/src/modules/execution/api/simple_reports.py:102, backend/testing/src/repositories/test_plan_progress.py:12`
`test_plan_schedule_snapshot` | `TestPlanScheduleSnapshot` | field | `backend/testing/src/repositories/test_run.py:261`
`updated_at` | `UpdatedAt` | field | `backend/testing/src/repositories/test_run.py:158`
`document_summary_jobs` | `DocumentSummaryJob` | collection/table | `backend/testing/src/core/database.py:102, backend/testing/src/modules/requirements/services/document_reader.py:1065, backend/testing/src/modules/requirements/services/document_reader.py:1071`
`_id` | `DocumentSummaryJobId` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1066, backend/testing/src/modules/requirements/services/document_reader.py:1072`
`cancel_requested` | `CancelRequested` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1079, backend/testing/src/modules/requirements/services/document_reader.py:691`
`dispatch_generation` | `DispatchGeneration` | field | `backend/testing/src/modules/requirements/services/document_reader.py:691`
`locked_sources` | `LockedSources` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1175`
`project_id` | `ProjectId` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1066, backend/testing/src/modules/requirements/services/document_reader.py:1072`
`requester_id` | `RequesterId` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1066, backend/testing/src/modules/requirements/services/document_reader.py:1072`
`started_at` | `StartedAt` | field | `backend/testing/src/modules/requirements/services/document_reader.py:742`
`status` | `Status` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1067, backend/testing/src/modules/requirements/services/document_reader.py:1072`
`updated_at` | `UpdatedAt` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1079, backend/testing/src/modules/requirements/services/document_reader.py:598`
`worker_job_id` | `WorkerJobId` | field | `backend/testing/src/modules/requirements/services/document_reader.py:678, backend/testing/src/modules/requirements/services/document_reader.py:742`
`worker_status` | `WorkerStatus` | field | `backend/testing/src/modules/requirements/services/document_reader.py:678`
`requirement_documents` | `RequirementDocument` | collection/table | `backend/testing/src/core/database.py:106, backend/testing/src/core/database.py:141, backend/testing/src/core/database.py:151`
`_id` | `RequirementDocumentId` | field | `backend/testing/src/repositories/requirement_import.py:256, backend/testing/src/repositories/requirement_import.py:73`
`content_hash` | `ContentHash` | field | `backend/testing/src/repositories/requirement_import.py:73`
`last_import_job_id` | `LastImportJobId` | field | `backend/testing/src/repositories/requirement_import.py:80`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/requirement_import.py:256, backend/testing/src/repositories/requirement_import.py:73`
`requirement_import_status` | `RequirementImportStatus` | field | `backend/testing/src/repositories/requirement_import.py:262, backend/testing/src/repositories/requirement_import.py:80`
`revision` | `Revision` | field | `backend/testing/src/repositories/requirement_import.py:267, backend/testing/src/repositories/requirement_import.py:86`
`source_series_id` | `SourceSeriesId` | field | `backend/testing/src/core/database.py:109`
`status` | `Status` | field | `backend/testing/src/repositories/requirement_import.py:256, backend/testing/src/repositories/requirement_import.py:262`
`updated_at` | `UpdatedAt` | field | `backend/testing/src/repositories/requirement_import.py:262, backend/testing/src/repositories/requirement_import.py:80`
`requirement_impact_jobs` | `RequirementImpactJob` | collection/table | `backend/testing/src/core/database.py:111, backend/testing/src/core/database.py:112, backend/testing/src/modules/quality/services/requirement_impact_worker.py:234`
`_id` | `RequirementImpactJobId` | field | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:244, backend/testing/src/modules/requirements/api/requirement_records.py:107`
`cases` | `Cases` | field | `backend/testing/src/modules/requirements/api/requirement_records.py:163`
`comparison` | `Comparison` | field | `backend/testing/src/modules/requirements/api/requirement_records.py:163`
`created_at` | `CreatedAt` | field | `backend/testing/src/modules/requirements/services/requirement_lifecycle.py:498`
`error_code` | `ErrorCode` | field | `backend/testing/src/modules/requirements/api/requirement_records.py:163`
`from_version_id` | `FromVersionId` | field | `backend/testing/src/modules/requirements/services/requirement_lifecycle.py:498`
`lease_token` | `LeaseToken` | field | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:234, backend/testing/src/modules/quality/services/requirement_impact_worker.py:244`
`lease_until` | `LeaseUntil` | field | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:234, backend/testing/src/modules/quality/services/requirement_impact_worker.py:244`
`limitations` | `Limitations` | field | `backend/testing/src/modules/requirements/api/requirement_records.py:163`
`new_candidates` | `NewCandidates` | field | `backend/testing/src/modules/requirements/api/requirement_records.py:163`
`plans` | `Plans` | field | `backend/testing/src/modules/requirements/api/requirement_records.py:163`
`project_id` | `ProjectId` | field | `backend/testing/src/modules/requirements/api/requirement_records.py:107, backend/testing/src/modules/requirements/api/requirement_records.py:161`
`requested_by` | `RequestedBy` | field | `backend/testing/src/modules/requirements/api/requirement_records.py:162, backend/testing/src/modules/requirements/services/requirement_lifecycle.py:498`
`requirement_id` | `RequirementId` | field | `backend/testing/src/modules/requirements/services/requirement_lifecycle.py:498`
`runs` | `Runs` | field | `backend/testing/src/modules/requirements/api/requirement_records.py:163`
`status` | `Status` | field | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:234, backend/testing/src/modules/quality/services/requirement_impact_worker.py:244`
`to_version_id` | `ToVersionId` | field | `backend/testing/src/modules/requirements/services/requirement_lifecycle.py:498`
`updated_at` | `UpdatedAt` | field | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:234, backend/testing/src/modules/quality/services/requirement_impact_worker.py:244`
`requirement_change_sets` | `RequirementChangeSet` | collection/table | `backend/testing/src/core/database.py:117, backend/testing/src/core/database.py:252, backend/testing/src/repositories/analysis.py:31`
`_id` | `RequirementChangeSetId` | field | `backend/testing/src/repositories/analysis.py:43, backend/testing/src/repositories/analysis.py:74`
`changes` | `Changes` | field | `backend/testing/src/repositories/analysis.py:43, backend/testing/src/repositories/analysis.py:51`
`model_version` | `ModelVersion` | field | `backend/testing/src/repositories/analysis.py:51`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/analysis.py:43, backend/testing/src/repositories/analysis.py:74`
`requirement_id` | `RequirementId` | field | `backend/testing/src/repositories/analysis.py:32`
`revision` | `Revision` | field | `backend/testing/src/core/database.py:118, backend/testing/src/repositories/analysis.py:43`
`status` | `Status` | field | `backend/testing/src/repositories/analysis.py:43, backend/testing/src/repositories/analysis.py:74`
`to_version_id` | `ToVersionId` | field | `backend/testing/src/repositories/analysis.py:32`
`updated_at` | `UpdatedAt` | field | `backend/testing/src/repositories/impact_analysis.py:110, backend/testing/src/repositories/impact_analysis.py:124`
`import_jobs` | `ImportJob` | collection/table | `backend/testing/src/core/database.py:120, backend/testing/src/core/database.py:169, backend/testing/src/core/database.py:388`
`_id` | `ImportJobId` | field | `backend/testing/src/repositories/requirement_import.py:118, backend/testing/src/repositories/requirement_import.py:171`
`confirmed_at` | `ConfirmedAt` | field | `backend/testing/src/repositories/requirement_import.py:236`
`confirmed_by` | `ConfirmedBy` | field | `backend/testing/src/repositories/requirement_import.py:236`
`confirming_by` | `ConfirmingBy` | field | `backend/testing/src/repositories/requirement_import.py:198`
`created_requirement_ids` | `CreatedRequirementIds` | field | `backend/testing/src/repositories/requirement_import.py:244`
`created_requirement_version_ids` | `CreatedRequirementVersionIds` | field | `backend/testing/src/repositories/requirement_import.py:244`
`preview` | `Preview` | field | `backend/testing/src/repositories/requirement_import.py:144`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/requirement_import.py:118, backend/testing/src/repositories/requirement_import.py:13`
`rejected_indexes` | `RejectedIndexes` | field | `backend/testing/src/repositories/requirement_import.py:236`
`revision` | `Revision` | field | `backend/testing/src/core/database.py:120, backend/testing/src/repositories/requirement_import.py:118`
`selected_indexes` | `SelectedIndexes` | field | `backend/testing/src/repositories/requirement_import.py:236`
`source_content_hash` | `SourceContentHash` | field | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:1253`
`source_document_id` | `SourceDocumentId` | field | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:1253, backend/testing/src/repositories/requirement_import.py:17`
`status` | `Status` | field | `backend/testing/src/repositories/requirement_import.py:118, backend/testing/src/repositories/requirement_import.py:171`
`template_id` | `TemplateId` | field | `backend/testing/src/core/database.py:170, backend/testing/src/repositories/requirement_import.py:13`
`template_public_view` | `TemplatePublicView` | field | `backend/testing/src/core/database.py:170, backend/testing/src/core/database.py:171`
`template_version` | `TemplateVersion` | field | `backend/testing/src/repositories/requirement_import.py:13`
`updated_at` | `UpdatedAt` | field | `backend/testing/src/repositories/requirement_import.py:198, backend/testing/src/repositories/requirement_import.py:214`
`trace_links` | `TraceLink` | collection/table | `backend/testing/src/core/database.py:121, backend/testing/src/core/database.py:206, backend/testing/src/core/database.py:207`
`_id` | `TraceLinkId` | field | `backend/testing/src/repositories/proposal_application.py:190, backend/testing/src/repositories/traceability.py:22`
`created_at` | `CreatedAt` | field | `backend/testing/src/repositories/proposal_application.py:190`
`created_by` | `CreatedBy` | field | `backend/testing/src/repositories/proposal_application.py:190`
`project_id` | `ProjectId` | field | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:72, backend/testing/src/repositories/analysis.py:59`
`revision` | `Revision` | field | `backend/testing/src/core/database.py:121, backend/testing/src/repositories/traceability.py:23`
`source_id` | `SourceId` | field | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:72, backend/testing/src/repositories/analysis.py:59`
`source_type` | `SourceType` | field | `backend/testing/src/repositories/requirement.py:247`
`status` | `Status` | field | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:72, backend/testing/src/repositories/analysis.py:59`
`target_id` | `TargetId` | field | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:72, backend/testing/src/repositories/proposal_application.py:128`
`target_type` | `TargetType` | field | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:72`
`updated_at` | `UpdatedAt` | field | `backend/testing/src/repositories/analysis.py:64, backend/testing/src/repositories/proposal_application.py:133`
`test_periods` | `TestPeriod` | collection/table | `backend/testing/src/core/database.py:123, backend/testing/src/core/database.py:124, backend/testing/src/modules/execution/api/simple_reports.py:75`
`_id` | `TestPeriodId` | field | `backend/testing/src/modules/execution/api/simple_reports.py:76, backend/testing/src/modules/execution/services/test_period.py:23`
`carry_over_items` | `CarryOverItems` | field | `backend/testing/src/modules/execution/services/test_period.py:292`
`close_note` | `CloseNote` | field | `backend/testing/src/modules/execution/services/test_period.py:292`
`close_summary` | `CloseSummary` | field | `backend/testing/src/modules/execution/services/test_period.py:292`
`closed_at` | `ClosedAt` | field | `backend/testing/src/modules/execution/services/test_period.py:292`
`closed_by` | `ClosedBy` | field | `backend/testing/src/modules/execution/services/test_period.py:292`
`name` | `Name` | field | `backend/testing/src/modules/execution/api/simple_reports.py:76`
`project_id` | `ProjectId` | field | `backend/testing/src/modules/execution/api/simple_reports.py:76, backend/testing/src/modules/execution/services/test_period.py:14`
`revision` | `Revision` | field | `backend/testing/src/modules/execution/services/test_period.py:285, backend/testing/src/modules/execution/services/test_period.py:308`
`sequence` | `Sequence` | field | `backend/testing/src/modules/execution/api/simple_reports.py:76`
`status` | `Status` | field | `backend/testing/src/modules/execution/services/test_period.py:285, backend/testing/src/modules/execution/services/test_period.py:292`
`updated_at` | `UpdatedAt` | field | `backend/testing/src/modules/execution/services/test_period.py:292`
`project_members` | `ProjectMember` | collection/table | `backend/testing/src/core/database.py:129, backend/testing/src/core/database.py:130, backend/testing/src/repositories/common.py:51`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/review.py:55, backend/testing/src/repositories/test_analysis.py:31`
`status` | `Status` | field | `backend/testing/src/repositories/review.py:55, backend/testing/src/repositories/test_analysis.py:31`
`user_id` | `UserId` | field | `backend/testing/src/repositories/review.py:55, backend/testing/src/repositories/test_analysis.py:31`
`defect_search_index_outbox` | `DefectSearchIndexOutbox` | collection/table | `backend/testing/src/core/database.py:133, backend/testing/src/core/database.py:136, backend/testing/src/repositories/defect_search_index.py:13`
`requirement_source_blocks` | `RequirementSourceBlock` | collection/table | `backend/testing/src/core/database.py:158, backend/testing/src/core/database.py:162, backend/testing/src/repositories/requirement_source_block.py:9`
`requirement_templates` | `RequirementTemplate` | collection/table | `backend/testing/src/core/database.py:165, backend/testing/src/core/database.py:166, backend/testing/src/repositories/requirement_template.py:13`
`_id` | `RequirementTemplateId` | field | `backend/testing/src/repositories/requirement_template.py:13, backend/testing/src/repositories/requirement_template.py:46`
`revision` | `Revision` | field | `backend/testing/src/repositories/requirement_template.py:47, backend/testing/src/repositories/requirement_template.py:56`
`version` | `Version` | field | `backend/testing/src/repositories/requirement_template.py:46, backend/testing/src/repositories/requirement_template.py:47`
`requirement_template_versions` | `RequirementTemplateVersion` | collection/table | `backend/testing/src/core/database.py:167, backend/testing/src/repositories/requirement_template.py:29, backend/testing/src/repositories/requirement_template.py:34`
`_id` | `RequirementTemplateVersionId` | field | `backend/testing/src/repositories/requirement_template.py:30`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/requirement_template.py:35, backend/testing/src/repositories/requirement_template.py:41`
`snapshot` | `Snapshot` | field | `backend/testing/src/repositories/requirement_template.py:36`
`template_id` | `TemplateId` | field | `backend/testing/src/repositories/requirement_template.py:35, backend/testing/src/repositories/requirement_template.py:41`
`version` | `Version` | field | `backend/testing/src/repositories/requirement_template.py:41`
`requirement_custom_fields` | `RequirementCustomField` | collection/table | `backend/testing/src/core/database.py:168, backend/testing/src/repositories/requirement_template.py:62, backend/testing/src/repositories/requirement_template.py:67`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/requirement_template.py:63`
`acceptance_criteria` | `AcceptanceCriteria` | collection/table | `backend/testing/src/core/database.py:183, backend/testing/src/modules/quality/services/requirement_impact_worker.py:65, backend/testing/src/repositories/analysis.py:87`
`_id` | `AcceptanceCriteriaId` | field | `backend/testing/src/repositories/proposal_application.py:153, backend/testing/src/repositories/requirement_document.py:514`
`approved_at` | `ApprovedAt` | field | `backend/testing/src/repositories/requirement.py:477`
`approved_by` | `ApprovedBy` | field | `backend/testing/src/repositories/requirement.py:477`
`project_id` | `ProjectId` | field | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:65, backend/testing/src/repositories/proposal_application.py:146`
`requirement_version_id` | `RequirementVersionId` | field | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:65, backend/testing/src/repositories/impact_analysis.py:14`
`status` | `Status` | field | `backend/testing/src/repositories/requirement.py:475, backend/testing/src/repositories/requirement.py:477`
`requirement_transformations` | `RequirementTransformation` | collection/table | `backend/testing/src/core/database.py:186, backend/testing/src/core/database.py:189, backend/testing/src/repositories/requirement.py:130`
`_id` | `RequirementTransformationId` | field | `backend/testing/src/repositories/requirement.py:131, backend/testing/src/repositories/requirement.py:17`
`attempt` | `Attempt` | field | `backend/testing/src/repositories/requirement.py:25`
`confirmed_at` | `ConfirmedAt` | field | `backend/testing/src/repositories/requirement.py:137`
`error_code` | `ErrorCode` | field | `backend/testing/src/repositories/requirement.py:195, backend/testing/src/repositories/requirement.py:24`
`idempotency_key` | `IdempotencyKey` | field | `backend/testing/src/repositories/requirement.py:10`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/requirement.py:10, backend/testing/src/repositories/requirement.py:131`
`result_requirement_ids` | `ResultRequirementIds` | field | `backend/testing/src/repositories/requirement.py:137`
`result_version_ids` | `ResultVersionIds` | field | `backend/testing/src/repositories/requirement.py:137`
`status` | `Status` | field | `backend/testing/src/repositories/requirement.py:131, backend/testing/src/repositories/requirement.py:137`
`updated_at` | `UpdatedAt` | field | `backend/testing/src/repositories/requirement.py:137, backend/testing/src/repositories/requirement.py:195`
`requirement_duplicate_scans` | `RequirementDuplicateScan` | collection/table | `backend/testing/src/core/database.py:192, backend/testing/src/repositories/requirement_analysis.py:17`
`test_scenarios` | `TestScenario` | collection/table | `backend/testing/src/core/database.py:193, backend/testing/src/repositories/impact_analysis.py:34`
`test_case_templates` | `TestCaseTemplate` | collection/table | `backend/testing/src/core/database.py:194, backend/testing/src/core/database.py:195, backend/testing/src/repositories/test_design.py:407`
`_id` | `TestCaseTemplateId` | field | `backend/testing/src/repositories/test_design.py:419`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/test_design.py:419`
`revision` | `Revision` | field | `backend/testing/src/repositories/test_design.py:419, backend/testing/src/repositories/test_design.py:425`
`status` | `Status` | field | `backend/testing/src/repositories/test_design.py:419`
`test_cases` | `TestCase` | collection/table | `backend/testing/src/core/database.py:203, backend/testing/src/modules/design/services/generation.py:243, backend/testing/src/modules/design/services/test_case_batch_review.py:144`
`_id` | `TestCaseId` | field | `backend/testing/src/modules/design/services/test_case_batch_review.py:159, backend/testing/src/modules/design/services/test_case_batch_review.py:309`
`current_version_id` | `CurrentVersionId` | field | `backend/testing/src/modules/design/services/test_case_batch_review.py:159, backend/testing/src/modules/design/services/test_case_lifecycle.py:315`
`project_id` | `ProjectId` | field | `backend/testing/src/modules/design/services/test_case_batch_review.py:144, backend/testing/src/modules/design/services/test_case_batch_review.py:159`
`review_required_by` | `ReviewRequiredBy` | field | `backend/testing/src/repositories/bulk_operation.py:86`
`review_required_reason` | `ReviewRequiredReason` | field | `backend/testing/src/repositories/bulk_operation.py:86`
`status` | `Status` | field | `backend/testing/src/modules/design/services/test_case_batch_review.py:159, backend/testing/src/modules/design/services/test_case_lifecycle.py:320`
`test_case_key` | `TestCaseKey` | field | `backend/testing/src/modules/design/services/test_case_batch_review.py:144, backend/testing/src/modules/design/services/test_case_batch_review.py:310`
`updated_at` | `UpdatedAt` | field | `backend/testing/src/modules/design/services/test_case_batch_review.py:159, backend/testing/src/modules/design/services/test_case_lifecycle.py:320`
`ai_results` | `AiResult` | collection/table | `backend/testing/src/core/database.py:219, backend/testing/src/core/database.py:220, backend/testing/src/modules/execution/services/execution_assistance.py:174`
`_id` | `AiResultId` | field | `backend/testing/src/modules/execution/services/execution_assistance.py:358, backend/testing/src/modules/execution/services/execution_assistance.py:368`
`claim_token` | `ClaimToken` | field | `backend/testing/src/modules/execution/services/execution_assistance.py:358, backend/testing/src/modules/execution/services/execution_assistance.py:368`
`idempotency_key` | `IdempotencyKey` | field | `backend/testing/src/repositories/defect.py:307`
`project_id` | `ProjectId` | field | `backend/testing/src/modules/execution/services/execution_assistance.py:337, backend/testing/src/modules/execution/services/execution_assistance.py:385`
`result_type` | `ResultType` | field | `backend/testing/src/modules/execution/services/execution_assistance.py:337, backend/testing/src/modules/execution/services/execution_assistance.py:385`
`revision` | `Revision` | field | `backend/testing/src/repositories/defect.py:345`
`source_fingerprint` | `SourceFingerprint` | field | `backend/testing/src/modules/execution/services/execution_assistance.py:337`
`subject_id` | `SubjectId` | field | `backend/testing/src/modules/execution/services/execution_assistance.py:337, backend/testing/src/modules/execution/services/execution_assistance.py:385`
`ai_findings` | `AiFinding` | collection/table | `backend/testing/src/core/database.py:237, backend/testing/src/repositories/requirement_ai.py:13, backend/testing/src/repositories/requirement_ai.py:16`
`_id` | `AiFindingId` | field | `backend/testing/src/repositories/requirement_ai.py:21, backend/testing/src/repositories/requirement_ai.py:40`
`artifact_id` | `ArtifactId` | field | `backend/testing/src/repositories/requirement_ai.py:62, backend/testing/src/repositories/test_design.py:169`
`artifact_type` | `ArtifactType` | field | `backend/testing/src/repositories/requirement_ai.py:62, backend/testing/src/repositories/test_design.py:169`
`attempt` | `Attempt` | field | `backend/testing/src/repositories/requirement_ai.py:33`
`claim_token` | `ClaimToken` | field | `backend/testing/src/repositories/requirement_ai.py:28, backend/testing/src/repositories/requirement_ai.py:40`
`claimed_at` | `ClaimedAt` | field | `backend/testing/src/repositories/requirement_ai.py:28`
`lease_expires_at` | `LeaseExpiresAt` | field | `backend/testing/src/repositories/requirement_ai.py:21, backend/testing/src/repositories/requirement_ai.py:28`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/requirement_ai.py:62, backend/testing/src/repositories/test_design.py:169`
`request_fingerprint` | `RequestFingerprint` | field | `backend/testing/src/repositories/requirement_ai.py:21`
`result_type` | `ResultType` | field | `backend/testing/src/repositories/requirement_ai.py:21, backend/testing/src/repositories/requirement_ai.py:40`
`coverage_snapshots` | `CoverageSnapshot` | collection/table | `backend/testing/src/core/database.py:246, backend/testing/src/repositories/traceability.py:40, backend/testing/src/repositories/traceability.py:45`
`idempotency_key` | `IdempotencyKey` | field | `backend/testing/src/repositories/traceability.py:41`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/traceability.py:41`
`impact_analyses` | `ImpactAnalyse` | collection/table | `backend/testing/src/core/database.py:255, backend/testing/src/core/database.py:263, backend/testing/src/repositories/api_artifact.py:51`
`_id` | `ImpactAnalyseId` | field | `backend/testing/src/repositories/impact_analysis.py:146, backend/testing/src/repositories/impact_analysis.py:158`
`change_set_id` | `ChangeSetId` | field | `backend/testing/src/repositories/impact_analysis.py:129, backend/testing/src/repositories/impact_analysis.py:9`
`from_artifact_id` | `FromArtifactId` | field | `backend/testing/src/repositories/api_artifact.py:52`
`model_version` | `ModelVersion` | field | `backend/testing/src/repositories/impact_analysis.py:9`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/api_artifact.py:52, backend/testing/src/repositories/impact_analysis.py:129`
`rerun_requested_at` | `RerunRequestedAt` | field | `backend/testing/src/repositories/impact_analysis.py:168`
`rerun_requested_by` | `RerunRequestedBy` | field | `backend/testing/src/repositories/impact_analysis.py:168`
`revision` | `Revision` | field | `backend/testing/src/repositories/impact_analysis.py:146, backend/testing/src/repositories/impact_analysis.py:169`
`snapshot_number` | `SnapshotNumber` | field | `backend/testing/src/repositories/maintenance_proposal.py:59`
`source_type` | `SourceType` | field | `backend/testing/src/core/database.py:266, backend/testing/src/repositories/api_artifact.py:52`
`status` | `Status` | field | `backend/testing/src/repositories/impact_analysis.py:146, backend/testing/src/repositories/impact_analysis.py:165`
`to_artifact_id` | `ToArtifactId` | field | `backend/testing/src/repositories/api_artifact.py:52`
`updated_at` | `UpdatedAt` | field | `backend/testing/src/repositories/impact_analysis.py:167`
`maintenance_proposals` | `MaintenanceProposal` | collection/table | `backend/testing/src/core/database.py:268, backend/testing/src/repositories/maintenance_proposal.py:19, backend/testing/src/repositories/maintenance_proposal.py:25`
`_id` | `MaintenanceProposalId` | field | `backend/testing/src/repositories/maintenance_proposal.py:78, backend/testing/src/repositories/proposal_application.py:25`
`impact_analysis_id` | `ImpactAnalysisId` | field | `backend/testing/src/repositories/maintenance_proposal.py:9`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/maintenance_proposal.py:71, backend/testing/src/repositories/maintenance_proposal.py:78`
`revision` | `Revision` | field | `backend/testing/src/repositories/maintenance_proposal.py:65, backend/testing/src/repositories/maintenance_proposal.py:86`
`status` | `Status` | field | `backend/testing/src/repositories/maintenance_proposal.py:71, backend/testing/src/repositories/maintenance_proposal.py:84`
`superseded_by` | `SupersededBy` | field | `backend/testing/src/repositories/maintenance_proposal.py:78, backend/testing/src/repositories/maintenance_proposal.py:85`
`updated_at` | `UpdatedAt` | field | `backend/testing/src/repositories/maintenance_proposal.py:84`
`regression_recommendations` | `RegressionRecommendation` | collection/table | `backend/testing/src/core/database.py:273, backend/testing/src/repositories/regression_recommendation.py:21, backend/testing/src/repositories/regression_recommendation.py:26`
`change_set_id` | `ChangeSetId` | field | `backend/testing/src/repositories/regression_recommendation.py:27`
`impact_analysis_id` | `ImpactAnalysisId` | field | `backend/testing/src/repositories/regression_recommendation.py:27`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/regression_recommendation.py:27`
`revision` | `Revision` | field | `backend/testing/src/repositories/regression_recommendation.py:51`
`test_suites` | `TestSuite` | collection/table | `backend/testing/src/core/database.py:295, backend/testing/src/repositories/bulk_operation.py:35, backend/testing/src/repositories/bulk_operation.py:51`
`_id` | `TestSuiteId` | field | `backend/testing/src/repositories/bulk_operation.py:36, backend/testing/src/repositories/bulk_operation.py:52`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/bulk_operation.py:36, backend/testing/src/repositories/bulk_operation.py:52`
`revision` | `Revision` | field | `backend/testing/src/repositories/bulk_operation.py:52, backend/testing/src/repositories/bulk_operation.py:62`
`status` | `Status` | field | `backend/testing/src/repositories/test_plan.py:12`
`test_case_version_ids` | `TestCaseVersionIds` | field | `backend/testing/src/repositories/bulk_operation.py:58`
`updated_at` | `UpdatedAt` | field | `backend/testing/src/repositories/bulk_operation.py:58`
`project_notification_rules` | `ProjectNotificationRule` | collection/table | `backend/testing/src/core/database.py:308, backend/testing/src/repositories/project_notification.py:13`
`security_test_suggestions` | `SecurityTestSuggestion` | collection/table | `backend/testing/src/core/database.py:312, backend/testing/src/core/database.py:315, backend/testing/src/repositories/test_design.py:362`
`idempotency_key` | `IdempotencyKey` | field | `backend/testing/src/repositories/test_design.py:368`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/test_design.py:363, backend/testing/src/repositories/test_design.py:368`
`performance_plan_drafts` | `PerformancePlanDraft` | collection/table | `backend/testing/src/core/database.py:316, backend/testing/src/core/database.py:319, backend/testing/src/repositories/test_design.py:376`
`idempotency_key` | `IdempotencyKey` | field | `backend/testing/src/repositories/test_design.py:382`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/test_design.py:377, backend/testing/src/repositories/test_design.py:382`
`automation_executions` | `AutomationExecution` | collection/table | `backend/testing/src/core/database.py:320, backend/testing/src/core/database.py:323, backend/testing/src/repositories/execution_asset.py:110`
`_id` | `AutomationExecutionId` | field | `backend/testing/src/repositories/execution_asset.py:100, backend/testing/src/repositories/execution_asset.py:111`
`idempotency_key` | `IdempotencyKey` | field | `backend/testing/src/repositories/execution_asset.py:33`
`operation_id` | `OperationId` | field | `backend/testing/src/repositories/execution_asset.py:100, backend/testing/src/repositories/execution_asset.py:111`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/execution_asset.py:28, backend/testing/src/repositories/execution_asset.py:33`
`queued_at` | `QueuedAt` | field | `backend/testing/src/repositories/execution_asset.py:94`
`revision` | `Revision` | field | `backend/testing/src/repositories/execution_asset.py:116, backend/testing/src/repositories/execution_asset.py:71`
`start_idempotency_key` | `StartIdempotencyKey` | field | `backend/testing/src/repositories/execution_asset.py:94`
`status` | `Status` | field | `backend/testing/src/repositories/execution_asset.py:111, backend/testing/src/repositories/execution_asset.py:71`
`updated_at` | `UpdatedAt` | field | `backend/testing/src/repositories/execution_asset.py:93`
`junit_result_imports` | `JunitResultImport` | collection/table | `backend/testing/src/core/database.py:326, backend/testing/src/modules/integrations/services/junit_import.py:112, backend/testing/src/modules/integrations/services/junit_import.py:123`
`_id` | `JunitResultImportId` | field | `backend/testing/src/modules/integrations/services/junit_import.py:138, backend/testing/src/modules/integrations/services/junit_import.py:175`
`mapped_test_case_version_ids` | `MappedTestCaseVersionIds` | field | `backend/testing/src/modules/integrations/services/junit_import.py:219`
`project_id` | `ProjectId` | field | `backend/testing/src/modules/integrations/services/junit_import.py:124, backend/testing/src/modules/integrations/services/junit_import.py:134`
`revision` | `Revision` | field | `backend/testing/src/modules/integrations/services/junit_import.py:175, backend/testing/src/modules/integrations/services/junit_import.py:182`
`source_hash` | `SourceHash` | field | `backend/testing/src/modules/integrations/services/junit_import.py:124, backend/testing/src/modules/integrations/services/junit_import.py:44`
`status` | `Status` | field | `backend/testing/src/modules/integrations/services/junit_import.py:175, backend/testing/src/modules/integrations/services/junit_import.py:181`
`test_run_id` | `TestRunId` | field | `backend/testing/src/modules/integrations/services/junit_import.py:124, backend/testing/src/modules/integrations/services/junit_import.py:44`
`unresolved` | `Unresolved` | field | `backend/testing/src/modules/integrations/services/junit_import.py:214`
`updated_at` | `UpdatedAt` | field | `backend/testing/src/modules/integrations/services/junit_import.py:181, backend/testing/src/modules/integrations/services/junit_import.py:205`
`collaboration_sessions` | `CollaborationSession` | collection/table | `backend/testing/src/core/database.py:332, backend/testing/src/core/database.py:342, backend/testing/src/repositories/collaboration.py:13`
`collaboration_operations` | `CollaborationOperation` | collection/table | `backend/testing/src/core/database.py:343, backend/testing/src/repositories/collaboration.py:26, backend/testing/src/repositories/collaboration.py:33`
`artifact_id` | `ArtifactId` | field | `backend/testing/src/repositories/collaboration.py:34`
`artifact_type` | `ArtifactType` | field | `backend/testing/src/repositories/collaboration.py:34`
`operation_id` | `OperationId` | field | `backend/testing/src/repositories/collaboration.py:27`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/collaboration.py:27, backend/testing/src/repositories/collaboration.py:34`
`result_revision` | `ResultRevision` | field | `backend/testing/src/repositories/collaboration.py:34`
`draft_conflicts` | `DraftConflict` | collection/table | `backend/testing/src/core/database.py:346, backend/testing/src/repositories/collaboration.py:43, backend/testing/src/repositories/collaboration.py:51`
`_id` | `DraftConflictId` | field | `backend/testing/src/repositories/collaboration.py:57`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/collaboration.py:52, backend/testing/src/repositories/collaboration.py:57`
`revision` | `Revision` | field | `backend/testing/src/repositories/collaboration.py:57, backend/testing/src/repositories/collaboration.py:63`
`status` | `Status` | field | `backend/testing/src/repositories/collaboration.py:57`
`test_run_resume_events` | `TestRunResumeEvent` | collection/table | `backend/testing/src/core/database.py:352, backend/testing/src/repositories/test_run.py:108, backend/testing/src/repositories/test_run.py:114`
`idempotency_key` | `IdempotencyKey` | field | `backend/testing/src/repositories/test_run.py:109`
`test_run_id` | `TestRunId` | field | `backend/testing/src/repositories/test_run.py:109`
`releases` | `Release` | collection/table | `backend/testing/src/core/database.py:355, backend/testing/src/core/database.py:356, backend/testing/src/modules/execution/services/execution_context.py:165`
`_id` | `ReleaseId` | field | `backend/testing/src/modules/execution/services/execution_context.py:166, backend/testing/src/repositories/execution_context.py:129`
`gate_revision` | `GateRevision` | field | `backend/testing/src/repositories/execution_context.py:29`
`is_current` | `IsCurrent` | field | `backend/testing/src/repositories/execution_context.py:145, backend/testing/src/repositories/execution_context.py:150`
`project_id` | `ProjectId` | field | `backend/testing/src/modules/execution/services/execution_context.py:166, backend/testing/src/repositories/execution_context.py:129`
`status` | `Status` | field | `backend/testing/src/repositories/execution_context.py:140`
`builds` | `Build` | collection/table | `backend/testing/src/core/database.py:357, backend/testing/src/core/database.py:358, backend/testing/src/repositories/execution_context.py:155`
`_id` | `BuildId` | field | `backend/testing/src/repositories/execution_context.py:165, backend/testing/src/repositories/execution_context.py:170`
`is_current` | `IsCurrent` | field | `backend/testing/src/repositories/execution_context.py:166, backend/testing/src/repositories/execution_context.py:171`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/execution_context.py:165, backend/testing/src/repositories/execution_context.py:170`
`status` | `Status` | field | `backend/testing/src/repositories/execution_context.py:170`
`test_environments` | `TestEnvironment` | collection/table | `backend/testing/src/core/database.py:359, backend/testing/src/core/database.py:360, backend/testing/src/repositories/execution_asset.py:57`
`_id` | `TestEnvironmentId` | field | `backend/testing/src/repositories/execution_asset.py:58, backend/testing/src/repositories/test_run.py:96`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/execution_asset.py:58, backend/testing/src/repositories/execution_context.py:178`
`status` | `Status` | field | `backend/testing/src/repositories/execution_asset.py:58, backend/testing/src/repositories/execution_context.py:178`
`test_result_corrections` | `TestResultCorrection` | collection/table | `backend/testing/src/core/database.py:364, backend/testing/src/repositories/test_run.py:187, backend/testing/src/repositories/test_run.py:193`
`idempotency_key` | `IdempotencyKey` | field | `backend/testing/src/repositories/test_run.py:188`
`test_result_id` | `TestResultId` | field | `backend/testing/src/repositories/test_run.py:188`
`defects` | `Defect` | collection/table | `backend/testing/src/core/database.py:367, backend/testing/src/modules/execution/api/simple_reports.py:178, backend/testing/src/modules/execution/services/test_period.py:219`
`_id` | `DefectId` | field | `backend/testing/src/modules/execution/services/test_run_execution.py:111, backend/testing/src/repositories/defect.py:102`
`created_by` | `CreatedBy` | field | `backend/testing/src/repositories/defect.py:125`
`defect_key` | `DefectKey` | field | `backend/testing/src/modules/execution/api/simple_reports.py:180`
`idempotency_key` | `IdempotencyKey` | field | `backend/testing/src/repositories/defect.py:125`
`last_retest_id` | `LastRetestId` | field | `backend/testing/src/repositories/defect.py:285`
`last_retest_result_id` | `LastRetestResultId` | field | `backend/testing/src/repositories/defect.py:285`
`linked_test_result_id` | `LinkedTestResultId` | field | `backend/testing/src/modules/execution/api/simple_reports.py:180`
`priority` | `Priority` | field | `backend/testing/src/modules/quality/services/defect_records.py:64`
`project_id` | `ProjectId` | field | `backend/testing/src/modules/execution/services/test_run_execution.py:111, backend/testing/src/modules/quality/services/defect_records.py:64`
`retest_event_ids` | `RetestEventIds` | field | `backend/testing/src/repositories/defect.py:292`
`revision` | `Revision` | field | `backend/testing/src/repositories/defect.py:102, backend/testing/src/repositories/defect.py:109`
`severity` | `Severity` | field | `backend/testing/src/modules/execution/api/simple_reports.py:180, backend/testing/src/modules/execution/services/test_period.py:227`
`status` | `Status` | field | `backend/testing/src/modules/execution/api/simple_reports.py:180, backend/testing/src/modules/execution/services/test_period.py:227`
`title` | `Title` | field | `backend/testing/src/modules/execution/api/simple_reports.py:180`
`updated_at` | `UpdatedAt` | field | `backend/testing/src/repositories/defect.py:108, backend/testing/src/repositories/defect.py:285`
`defect_retests` | `DefectRetest` | collection/table | `backend/testing/src/core/database.py:373, backend/testing/src/repositories/defect.py:216, backend/testing/src/repositories/defect.py:227`
`_id` | `DefectRetestId` | field | `backend/testing/src/repositories/defect.py:300`
`application_status` | `ApplicationStatus` | field | `backend/testing/src/repositories/defect.py:301`
`defect_id` | `DefectId` | field | `backend/testing/src/repositories/defect.py:217`
`idempotency_key` | `IdempotencyKey` | field | `backend/testing/src/repositories/defect.py:217`
`test_execution_updates` | `TestExecutionUpdate` | collection/table | `backend/testing/src/core/database.py:374, backend/testing/src/repositories/test_run.py:164, backend/testing/src/repositories/test_run.py:170`
`idempotency_key` | `IdempotencyKey` | field | `backend/testing/src/repositories/test_run.py:165`
`test_result_id` | `TestResultId` | field | `backend/testing/src/repositories/test_run.py:165`
`audit_events` | `AuditEvent` | collection/table | `backend/testing/src/core/database.py:377, backend/testing/src/core/database.py:481, backend/testing/src/core/database.py:518`
`_id` | `AuditEventId` | field | `backend/testing/src/core/database.py:482, backend/testing/src/core/database.py:483`
`action` | `Action` | field | `backend/testing/src/core/database.py:483, backend/testing/src/core/database.py:520`
`actor_id` | `ActorId` | field | `backend/testing/src/core/database.py:483, backend/testing/src/core/database.py:520`
`created_at` | `CreatedAt` | field | `backend/testing/src/core/database.py:483, backend/testing/src/core/database.py:520`
`details` | `Details` | field | `backend/testing/src/core/database.py:483, backend/testing/src/core/database.py:520`
`entity_id` | `EntityId` | field | `backend/testing/src/core/database.py:483, backend/testing/src/core/database.py:520`
`entity_type` | `EntityType` | field | `backend/testing/src/core/database.py:483, backend/testing/src/core/database.py:520`
`project_deleted` | `ProjectDeleted` | field | `backend/testing/src/repositories/internal_admin.py:56`
`project_id` | `ProjectId` | field | `backend/testing/src/core/database.py:483, backend/testing/src/core/database.py:520`
`review_comments` | `ReviewComment` | collection/table | `backend/testing/src/core/database.py:378, backend/testing/src/repositories/defect.py:168, backend/testing/src/repositories/review.py:9`
`artifact_id` | `ArtifactId` | field | `backend/testing/src/repositories/defect.py:169`
`artifact_type` | `ArtifactType` | field | `backend/testing/src/repositories/defect.py:169`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/defect.py:169`
`attachments` | `Attachment` | collection/table | `backend/testing/src/core/database.py:381, backend/testing/src/core/database.py:382, backend/testing/src/repositories/defect.py:179`
`_id` | `AttachmentId` | field | `backend/testing/src/repositories/test_design.py:470`
`artifact_id` | `ArtifactId` | field | `backend/testing/src/repositories/defect.py:180`
`artifact_type` | `ArtifactType` | field | `backend/testing/src/repositories/defect.py:180`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/defect.py:180, backend/testing/src/repositories/test_design.py:470`
`revision` | `Revision` | field | `backend/testing/src/repositories/test_design.py:470, backend/testing/src/repositories/test_design.py:476`
`status` | `Status` | field | `backend/testing/src/repositories/defect.py:180, backend/testing/src/repositories/test_design.py:470`
`break_glass_grants` | `BreakGlassGrant` | collection/table | `backend/testing/src/core/database.py:385, backend/testing/src/repositories/common.py:54, backend/testing/src/repositories/internal_admin.py:64`
`_id` | `BreakGlassGrantId` | field | `backend/testing/src/repositories/internal_admin.py:76`
`actor_id` | `ActorId` | field | `backend/testing/src/schemas/internal_admin.py:24`
`expires_at` | `ExpiresAt` | field | `backend/testing/src/repositories/common.py:55`
`permissions` | `Permissions` | field | `backend/testing/src/schemas/internal_admin.py:22`
`project_id` | `ProjectId` | field | `backend/testing/src/schemas/internal_admin.py:20`
`reason` | `Reason` | field | `backend/testing/src/schemas/internal_admin.py:23`
`status` | `Status` | field | `backend/testing/src/repositories/common.py:55, backend/testing/src/repositories/internal_admin.py:76`
`ttl_minutes` | `TtlMinutes` | field | `backend/testing/src/schemas/internal_admin.py:25`
`user_id` | `UserId` | field | `backend/testing/src/schemas/internal_admin.py:21`
`api_imports` | `ApiImport` | collection/table | `backend/testing/src/core/database.py:395, backend/testing/src/repositories/api_artifact.py:14, backend/testing/src/repositories/api_artifact.py:20`
`_id` | `ApiImportId` | field | `backend/testing/src/repositories/api_artifact.py:15, backend/testing/src/repositories/execution_asset.py:38`
`format` | `Format` | field | `backend/testing/src/repositories/execution_asset.py:38`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/api_artifact.py:15, backend/testing/src/repositories/execution_asset.py:38`
`status` | `Status` | field | `backend/testing/src/repositories/execution_asset.py:38`
`api_operations` | `ApiOperation` | collection/table | `backend/testing/src/core/database.py:401, backend/testing/src/core/database.py:402, backend/testing/src/repositories/api_artifact.py:32`
`_id` | `ApiOperationId` | field | `backend/testing/src/repositories/api_artifact.py:41, backend/testing/src/repositories/api_artifact.py:46`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/api_artifact.py:41`
`test_imports` | `TestImport` | collection/table | `backend/testing/src/core/database.py:405, backend/testing/src/repositories/test_design.py:313, backend/testing/src/repositories/test_design.py:320`
`_id` | `TestImportId` | field | `backend/testing/src/repositories/test_design.py:321, backend/testing/src/repositories/test_design.py:325`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/test_design.py:329, backend/testing/src/repositories/test_design.py:333`
`status` | `Status` | field | `backend/testing/src/repositories/test_design.py:338, backend/testing/src/repositories/test_design.py:339`
`worker_events` | `WorkerEvent` | collection/table | `backend/testing/src/core/database.py:406, backend/testing/src/repositories/analysis.py:179`
`_id` | `WorkerEventId` | field | `backend/testing/src/repositories/analysis.py:180`
`bulk_operations` | `BulkOperation` | collection/table | `backend/testing/src/core/database.py:407, backend/testing/src/modules/design/services/test_case_records.py:728, backend/testing/src/modules/design/services/test_case_records.py:776`
`_id` | `BulkOperationId` | field | `backend/testing/src/modules/design/services/test_case_records.py:777`
`created_at` | `CreatedAt` | field | `backend/testing/src/modules/design/services/test_case_records.py:777`
`created_by` | `CreatedBy` | field | `backend/testing/src/modules/design/services/test_case_records.py:777`
`draft_ids` | `DraftIds` | field | `backend/testing/src/modules/design/services/test_case_records.py:777`
`idempotency_key` | `IdempotencyKey` | field | `backend/testing/src/modules/design/services/test_case_records.py:729, backend/testing/src/modules/design/services/test_case_records.py:777`
`operation_id` | `OperationId` | field | `backend/testing/src/modules/design/services/test_case_records.py:777`
`operation_type` | `OperationType` | field | `backend/testing/src/modules/design/services/test_case_records.py:777`
`project_id` | `ProjectId` | field | `backend/testing/src/modules/design/services/test_case_records.py:729, backend/testing/src/modules/design/services/test_case_records.py:777`
`request_hash` | `RequestHash` | field | `backend/testing/src/modules/design/services/test_case_records.py:777`
`project_access_control` | `ProjectAccessControl` | collection/table | `backend/testing/src/main.py:47, backend/testing/src/modules/projects/api/access.py:44, backend/testing/src/modules/projects/api/access.py:68`
`_id` | `ProjectAccessControlId` | field | `backend/testing/src/main.py:47, backend/testing/src/modules/projects/api/access.py:44`
`capabilities` | `Capabilities` | field | `backend/testing/src/schemas/project_access.py:58`
`migrated_at` | `MigratedAt` | field | `backend/testing/src/repositories/project_access.py:310`
`migration_source` | `MigrationSource` | field | `backend/testing/src/repositories/project_access.py:310`
`revision` | `Revision` | field | `backend/testing/src/schemas/project_access.py:57`
`role_grants` | `RoleGrants` | field | `backend/testing/src/schemas/project_access.py:59`
`role_grants_managed_by_admin` | `RoleGrantsManagedByAdmin` | field | `backend/testing/src/modules/projects/api/access.py:68`
`schema_version` | `SchemaVersion` | field | `backend/testing/src/schemas/project_access.py:56`
`setting_grants` | `SettingGrants` | field | `backend/testing/src/schemas/project_access.py:60`
`updated_at` | `UpdatedAt` | field | `backend/testing/src/repositories/project_access.py:119, backend/testing/src/repositories/project_access.py:196`
`simple_test_reports` | `SimpleTestReport` | collection/table | `backend/testing/src/modules/execution/api/simple_reports.py:322, backend/testing/src/modules/execution/api/simple_reports.py:333, backend/testing/src/modules/execution/api/simple_reports.py:337`
`_id` | `SimpleTestReportId` | field | `backend/testing/src/modules/execution/api/simple_reports.py:322, backend/testing/src/modules/execution/api/simple_reports.py:337`
`case_results` | `CaseResults` | field | `backend/testing/src/modules/execution/api/simple_reports.py:352`
`defects` | `Defects` | field | `backend/testing/src/modules/execution/api/simple_reports.py:352`
`project_id` | `ProjectId` | field | `backend/testing/src/modules/execution/api/simple_reports.py:322, backend/testing/src/modules/execution/api/simple_reports.py:337`
`type` | `Type` | field | `backend/testing/src/modules/execution/api/simple_reports.py:351`
`test_period_counters` | `TestPeriodCounter` | collection/table | `backend/testing/src/modules/execution/services/test_period.py:28, backend/testing/src/modules/execution/services/test_plan.py:437`
`_id` | `TestPeriodCounterId` | field | `backend/testing/src/modules/execution/services/test_period.py:29, backend/testing/src/modules/execution/services/test_plan.py:438`
`sequence` | `Sequence` | field | `backend/testing/src/modules/execution/services/test_period.py:30, backend/testing/src/modules/execution/services/test_plan.py:439`
`document_summary_cache` | `DocumentSummaryCache` | collection/table | `backend/testing/src/modules/requirements/services/document_reader.py:1266, backend/testing/src/modules/requirements/services/document_reader.py:1357`
`_id` | `DocumentSummaryCacheId` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1266, backend/testing/src/modules/requirements/services/document_reader.py:1358`
`document_id` | `DocumentId` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1359`
`output_language` | `OutputLanguage` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1359`
`project_id` | `ProjectId` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1359`
`prompt_version` | `PromptVersion` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1359`
`source_hash` | `SourceHash` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1359`
`summary` | `Summary` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1359`
`document_summary_chunk_cache` | `DocumentSummaryChunkCache` | collection/table | `backend/testing/src/modules/requirements/services/document_reader.py:1283, backend/testing/src/modules/requirements/services/document_reader.py:1305`
`_id` | `DocumentSummaryChunkCacheId` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1284, backend/testing/src/modules/requirements/services/document_reader.py:1306`
`chunk_hash` | `ChunkHash` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1307`
`chunk_index` | `ChunkIndex` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1307`
`document_id` | `DocumentId` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1307`
`output_language` | `OutputLanguage` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1307`
`project_id` | `ProjectId` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1307`
`prompt_version` | `PromptVersion` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1307`
`source_hash` | `SourceHash` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1307`
`summary` | `Summary` | field | `backend/testing/src/modules/requirements/services/document_reader.py:1307`
`ai_run_access_leases` | `AiRunAccessLease` | collection/table | `backend/testing/src/repositories/ai_run_access.py:14`
`counters` | `Counter` | collection/table | `backend/testing/src/repositories/common.py:95, backend/testing/src/repositories/internal_admin.py:58, backend/testing/src/repositories/review.py:64`
`_id` | `CounterId` | field | `backend/testing/src/repositories/common.py:96, backend/testing/src/repositories/review.py:65`
`value` | `Value` | field | `backend/testing/src/repositories/common.py:97, backend/testing/src/repositories/review.py:66`
`automation_script_drafts` | `AutomationScriptDraft` | collection/table | `backend/testing/src/repositories/execution_asset.py:13, backend/testing/src/repositories/execution_asset.py:23, backend/testing/src/repositories/execution_asset.py:47`
`_id` | `AutomationScriptDraftId` | field | `backend/testing/src/repositories/execution_asset.py:48`
`framework` | `Framework` | field | `backend/testing/src/repositories/execution_asset.py:48`
`idempotency_key` | `IdempotencyKey` | field | `backend/testing/src/repositories/execution_asset.py:14`
`project_id` | `ProjectId` | field | `backend/testing/src/repositories/execution_asset.py:14, backend/testing/src/repositories/execution_asset.py:48`
`status` | `Status` | field | `backend/testing/src/repositories/execution_asset.py:48`
`impact_review_perspectives` | `ImpactReviewPerspective` | collection/table | `backend/testing/src/repositories/impact_analysis.py:193`
`runtime_policies` | `RuntimePolicy` | collection/table | `backend/testing/src/repositories/project_access.py:300`
`_id` | `RuntimePolicyId` | field | `backend/testing/src/repositories/project_access.py:300`
`require_assigned_design_draft` | `RequireAssignedDesignDraft` | method | `backend/testing/src/modules/design/services/design_authorization.py:5`
`select_generation_criteria` | `SelectGenerationCriteria` | method | `backend/testing/src/modules/design/services/generation.py:21`
`validated_suggestions` | `ValidatedSuggestions` | method | `backend/testing/src/modules/design/services/generation.py:32`
`grounded_retry_instruction` | `GroundedRetryInstruction` | method | `backend/testing/src/modules/design/services/generation.py:55`
`request_grounded_test_generation` | `RequestGroundedTestGeneration` | method | `backend/testing/src/modules/design/services/generation.py:76`
`merge_duplicate_generated_cases` | `MergeDuplicateGeneratedCases` | method | `backend/testing/src/modules/design/services/generation.py:90`
`generated_cases_have_equivalent_actions` | `GeneratedCasesHaveEquivalentActions` | method | `backend/testing/src/modules/design/services/generation.py:163`
`generate_requirement_drafts` | `GenerateRequirementDrafts` | method | `backend/testing/src/modules/design/services/generation.py:180`
`evaluate_rules` | `EvaluateRules` | method | `backend/testing/src/modules/design/services/linters.py:7`
`requirement_findings` | `RequirementFindings` | method | `backend/testing/src/modules/design/services/linters.py:71`
`requirement_duplicate_score` | `RequirementDuplicateScore` | method | `backend/testing/src/modules/design/services/linters.py:106`
`lint_test_case` | `LintTestCase` | method | `backend/testing/src/modules/design/services/linters.py:179`
`has_verifiable_steps` | `HasVerifiableSteps` | method | `backend/testing/src/modules/design/services/linters.py:219`
`duplicate_score` | `DuplicateScore` | method | `backend/testing/src/modules/design/services/linters.py:232`
`conflicting_data_values` | `ConflictingDataValues` | method | `backend/testing/src/modules/design/services/linters.py:242`
`get_condition_for_user` | `GetConditionForUser` | method | `backend/testing/src/modules/design/services/test_analysis.py:35`
`list_conditions` | `ListConditions` | method | `backend/testing/src/modules/design/services/test_analysis.py:51`
`create_condition` | `CreateCondition` | method | `backend/testing/src/modules/design/services/test_analysis.py:73`
`clone_approved_condition` | `CloneApprovedCondition` | method | `backend/testing/src/modules/design/services/test_analysis.py:114`
`update_condition` | `UpdateCondition` | method | `backend/testing/src/modules/design/services/test_analysis.py:162`
`transition_condition` | `TransitionCondition` | method | `backend/testing/src/modules/design/services/test_analysis.py:202`
`resolve_finding` | `ResolveFinding` | method | `backend/testing/src/modules/design/services/test_analysis.py:286`
`run_deterministic_analysis` | `RunDeterministicAnalysis` | method | `backend/testing/src/modules/design/services/test_analysis.py:356`
`list_analysis_findings` | `ListAnalysisFindings` | method | `backend/testing/src/modules/design/services/test_analysis.py:381`
`create_analysis_finding` | `CreateAnalysisFinding` | method | `backend/testing/src/modules/design/services/test_analysis.py:392`
`assign_analysis_finding` | `AssignAnalysisFinding` | method | `backend/testing/src/modules/design/services/test_analysis.py:436`
`transition_analysis_finding` | `TransitionAnalysisFinding` | method | `backend/testing/src/modules/design/services/test_analysis.py:480`
`review_condition` | `ReviewCondition` | method | `backend/testing/src/modules/design/services/test_analysis.py:540`
`bulk_prioritize_conditions` | `BulkPrioritizeConditions` | method | `backend/testing/src/modules/design/services/test_analysis.py:571`
`basis_text` | `BasisText` | method | `backend/testing/src/modules/design/services/test_analysis_basis.py:9`
`resolve_basis` | `ResolveBasis` | method | `backend/testing/src/modules/design/services/test_analysis_basis.py:16`
`list_test_basis` | `ListTestBasis` | method | `backend/testing/src/modules/design/services/test_analysis_basis.py:88`
`deterministic_testability_findings` | `DeterministicTestabilityFindings` | method | `backend/testing/src/modules/design/services/test_analysis_basis.py:135`
`accept_test_case_group` | `AcceptTestCaseGroup` | method | `backend/testing/src/modules/design/services/test_case_batch_review.py:21`
`commit` | `Commit` | method | `backend/testing/src/modules/design/services/test_case_batch_review.py:99`
`valid_ids` | `ValidIds` | method | `backend/testing/src/modules/design/services/test_case_batch_review.py:219`
`generate_test_case_draft_records` | `GenerateTestCaseDraftRecords` | method | `backend/testing/src/modules/design/services/test_case_generation.py:21`
`recommend_test_design_techniques` | `RecommendTestDesignTechniques` | method | `backend/testing/src/modules/design/services/test_case_generation.py:131`
`find_duplicate_test_case_records` | `FindDuplicateTestCaseRecords` | method | `backend/testing/src/modules/design/services/test_case_generation.py:241`
`compare_test_case_draft_batch` | `CompareTestCaseDraftBatch` | method | `backend/testing/src/modules/design/services/test_case_generation.py:312`
`lint_test_case_draft_record` | `LintTestCaseDraftRecord` | method | `backend/testing/src/modules/design/services/test_case_lifecycle.py:25`
`get_latest_test_case_draft_lint` | `GetLatestTestCaseDraftLint` | method | `backend/testing/src/modules/design/services/test_case_lifecycle.py:60`
`submit_test_case_review_record` | `SubmitTestCaseReviewRecord` | method | `backend/testing/src/modules/design/services/test_case_lifecycle.py:74`
`request_test_case_changes_record` | `RequestTestCaseChangesRecord` | method | `backend/testing/src/modules/design/services/test_case_lifecycle.py:143`
`approve_test_case_draft_record` | `ApproveTestCaseDraftRecord` | method | `backend/testing/src/modules/design/services/test_case_lifecycle.py:189`
`approved_test_case_result` | `ApprovedTestCaseResult` | method | `backend/testing/src/modules/design/services/test_case_lifecycle.py:375`
`finalize_test_case_derivatives` | `FinalizeTestCaseDerivatives` | method | `backend/testing/src/modules/design/services/test_case_lifecycle.py:404`
`build_test_case_version` | `BuildTestCaseVersion` | method | `backend/testing/src/modules/design/services/test_case_lifecycle.py:501`
`create_suggested_trace_records` | `CreateSuggestedTraceRecords` | method | `backend/testing/src/modules/design/services/test_case_lifecycle.py:576`
`publish` | `Publish` | method | `backend/testing/src/modules/design/services/test_case_lifecycle.py:244`
`list_test_case_records` | `ListTestCaseRecords` | method | `backend/testing/src/modules/design/services/test_case_query.py:28`
`matches_test_case` | `MatchesTestCase` | method | `backend/testing/src/modules/design/services/test_case_query.py:195`
`list_test_case_drafts` | `ListTestCaseDrafts` | method | `backend/testing/src/modules/design/services/test_case_query.py:201`
`get_test_case_record` | `GetTestCaseRecord` | method | `backend/testing/src/modules/design/services/test_case_query.py:215`
`clone_test_case_record` | `CloneTestCaseRecord` | method | `backend/testing/src/modules/design/services/test_case_query.py:223`
`list_test_case_versions` | `ListTestCaseVersions` | method | `backend/testing/src/modules/design/services/test_case_query.py:285`
`create_test_case_version_draft_record` | `CreateTestCaseVersionDraftRecord` | method | `backend/testing/src/modules/design/services/test_case_query.py:292`
`diff_test_case_version_records` | `DiffTestCaseVersionRecords` | method | `backend/testing/src/modules/design/services/test_case_query.py:352`
`set_test_case_obsolete` | `SetTestCaseObsolete` | method | `backend/testing/src/modules/design/services/test_case_query.py:406`
`restore_test_case_record` | `RestoreTestCaseRecord` | method | `backend/testing/src/modules/design/services/test_case_query.py:434`
`coverage_source_items` | `CoverageSourceItems` | method | `backend/testing/src/modules/design/services/test_case_records.py:38`
`list_coverage_source_items` | `ListCoverageSourceItems` | method | `backend/testing/src/modules/design/services/test_case_records.py:89`
`project_test_text` | `ProjectTestText` | method | `backend/testing/src/modules/design/services/test_case_records.py:95`
`canonical_case_steps` | `CanonicalCaseSteps` | method | `backend/testing/src/modules/design/services/test_case_records.py:142`
`project_test_index_metadata` | `ProjectTestIndexMetadata` | method | `backend/testing/src/modules/design/services/test_case_records.py:166`
`active_suite_signature` | `ActiveSuiteSignature` | method | `backend/testing/src/modules/design/services/test_case_records.py:181`
`acceptance_criteria_snapshot_matches` | `AcceptanceCriteriaSnapshotMatches` | method | `backend/testing/src/modules/design/services/test_case_records.py:203`
`require_current_baselined_version` | `RequireCurrentBaselinedVersion` | method | `backend/testing/src/modules/design/services/test_case_records.py:212`
`require_current_design_source` | `RequireCurrentDesignSource` | method | `backend/testing/src/modules/design/services/test_case_records.py:228`
`comparison_cases` | `ComparisonCases` | method | `backend/testing/src/modules/design/services/test_case_records.py:237`
`validate_design_sources` | `ValidateDesignSources` | method | `backend/testing/src/modules/design/services/test_case_records.py:257`
`validate_test_case_owner` | `ValidateTestCaseOwner` | method | `backend/testing/src/modules/design/services/test_case_records.py:319`
`validate_coverage_items` | `ValidateCoverageItems` | method | `backend/testing/src/modules/design/services/test_case_records.py:343`
`attach_manual_criterion_evidence` | `AttachManualCriterionEvidence` | method | `backend/testing/src/modules/design/services/test_case_records.py:358`
`create_test_case_draft_record` | `CreateTestCaseDraftRecord` | method | `backend/testing/src/modules/design/services/test_case_records.py:458`
`create_generated_test_case_draft_batch` | `CreateGeneratedTestCaseDraftBatch` | method | `backend/testing/src/modules/design/services/test_case_records.py:674`
`update_test_case_draft_record` | `UpdateTestCaseDraftRecord` | method | `backend/testing/src/modules/design/services/test_case_records.py:829`
`delete_test_case_draft_record` | `DeleteTestCaseDraftRecord` | method | `backend/testing/src/modules/design/services/test_case_records.py:964`
`persist` | `Persist` | method | `backend/testing/src/modules/design/services/test_case_records.py:640`
`persist_batch` | `PersistBatch` | method | `backend/testing/src/modules/design/services/test_case_records.py:758`
`persist` | `Persist` | method | `backend/testing/src/modules/design/services/test_case_records.py:925`
`list_acceptance_criteria_in_session` | `ListAcceptanceCriteriaInSession` | method | `backend/testing/src/modules/design/services/test_case_review.py:22`
`fingerprint` | `Fingerprint` | method | `backend/testing/src/modules/design/services/test_case_review.py:27`
`validate_merge_replay` | `ValidateMergeReplay` | method | `backend/testing/src/modules/design/services/test_case_review.py:31`
`proposal_snapshot` | `ProposalSnapshot` | method | `backend/testing/src/modules/design/services/test_case_review.py:76`
`validate_merge_choices` | `ValidateMergeChoices` | method | `backend/testing/src/modules/design/services/test_case_review.py:84`
`ensure_unique_step_ids` | `EnsureUniqueStepIds` | method | `backend/testing/src/modules/design/services/test_case_review.py:158`
`assert_sources_current_in_session` | `AssertSourcesCurrentInSession` | method | `backend/testing/src/modules/design/services/test_case_review.py:177`
`validate_test_case_publication_uniqueness` | `ValidateTestCasePublicationUniqueness` | method | `backend/testing/src/modules/design/services/test_case_review.py:234`
`comparison_sources` | `ComparisonSources` | method | `backend/testing/src/modules/design/services/test_case_review.py:333`
`review_context` | `ReviewContext` | method | `backend/testing/src/modules/design/services/test_case_review.py:372`
`save_merged_test_case` | `SaveMergedTestCase` | method | `backend/testing/src/modules/design/services/test_case_review.py:416`
`validate_review_sources_before_approval` | `ValidateReviewSourcesBeforeApproval` | method | `backend/testing/src/modules/design/services/test_case_review.py:523`
`list` | `List` | method | `backend/testing/src/modules/design/services/test_case_template.py:29`
`get` | `Get` | method | `backend/testing/src/modules/design/services/test_case_template.py:39`
`create` | `Create` | method | `backend/testing/src/modules/design/services/test_case_template.py:50`
`update` | `Update` | method | `backend/testing/src/modules/design/services/test_case_template.py:83`
`archive` | `Archive` | method | `backend/testing/src/modules/design/services/test_case_template.py:120`
`compare_test_import_candidates` | `CompareTestImportCandidates` | method | `backend/testing/src/modules/design/services/test_case_transfer.py:26`
`store_test_import_preview` | `StoreTestImportPreview` | method | `backend/testing/src/modules/design/services/test_case_transfer.py:65`
`recover_trace_links` | `RecoverTraceLinks` | method | `backend/testing/src/modules/design/services/test_case_transfer.py:98`
`preview_test_import` | `PreviewTestImport` | method | `backend/testing/src/modules/design/services/test_case_transfer.py:172`
`upload_test_import` | `UploadTestImport` | method | `backend/testing/src/modules/design/services/test_case_transfer.py:298`
`confirm_test_import` | `ConfirmTestImport` | method | `backend/testing/src/modules/design/services/test_case_transfer.py:328`
`export_test_cases` | `ExportTestCases` | method | `backend/testing/src/modules/design/services/test_case_transfer.py:562`
`persist_import` | `PersistImport` | method | `backend/testing/src/modules/design/services/test_case_transfer.py:481`
`requirement_test_evidence_text` | `RequirementTestEvidenceText` | method | `backend/testing/src/modules/design/services/test_evidence.py:4`
`requirement_test_evidence_matches` | `RequirementTestEvidenceMatches` | method | `backend/testing/src/modules/design/services/test_evidence.py:30`
`generate_execution_assistance` | `GenerateExecutionAssistance` | method | `backend/testing/src/modules/execution/services/execution_assistance.py:332`
`latest_execution_assistance` | `LatestExecutionAssistance` | method | `backend/testing/src/modules/execution/services/execution_assistance.py:382`
`matches_source` | `MatchesSource` | method | `backend/testing/src/modules/execution/services/execution_assistance.py:116`
`serialize_release_gate` | `SerializeReleaseGate` | method | `backend/testing/src/modules/execution/services/execution_context.py:11`
`raise_release_gate_conflict` | `RaiseReleaseGateConflict` | method | `backend/testing/src/modules/execution/services/execution_context.py:42`
`defect_blocks_release` | `DefectBlocksRelease` | method | `backend/testing/src/modules/execution/services/execution_context.py:49`
`resolve_execution_context` | `ResolveExecutionContext` | method | `backend/testing/src/modules/execution/services/execution_context.py:60`
`clean_secret_fields` | `CleanSecretFields` | method | `backend/testing/src/modules/execution/services/execution_context.py:124`
`list_releases` | `ListReleases` | method | `backend/testing/src/modules/execution/services/execution_context.py:133`
`get_release` | `GetRelease` | method | `backend/testing/src/modules/execution/services/execution_context.py:143`
`release_close_readiness` | `ReleaseCloseReadiness` | method | `backend/testing/src/modules/execution/services/execution_context.py:153`
`create_release` | `CreateRelease` | method | `backend/testing/src/modules/execution/services/execution_context.py:223`
`update_release` | `UpdateRelease` | method | `backend/testing/src/modules/execution/services/execution_context.py:259`
`transition_release` | `TransitionRelease` | method | `backend/testing/src/modules/execution/services/execution_context.py:304`
`list_builds` | `ListBuilds` | method | `backend/testing/src/modules/execution/services/execution_context.py:420`
`get_build` | `GetBuild` | method | `backend/testing/src/modules/execution/services/execution_context.py:428`
`create_build` | `CreateBuild` | method | `backend/testing/src/modules/execution/services/execution_context.py:438`
`update_build` | `UpdateBuild` | method | `backend/testing/src/modules/execution/services/execution_context.py:483`
`set_current_build` | `SetCurrentBuild` | method | `backend/testing/src/modules/execution/services/execution_context.py:508`
`list_environments` | `ListEnvironments` | method | `backend/testing/src/modules/execution/services/execution_context.py:540`
`get_environment` | `GetEnvironment` | method | `backend/testing/src/modules/execution/services/execution_context.py:549`
`create_environment` | `CreateEnvironment` | method | `backend/testing/src/modules/execution/services/execution_context.py:560`
`update_environment` | `UpdateEnvironment` | method | `backend/testing/src/modules/execution/services/execution_context.py:591`
`archive_environment` | `ArchiveEnvironment` | method | `backend/testing/src/modules/execution/services/execution_context.py:618`
`defect_transitions` | `DefectTransitions` | method | `backend/testing/src/modules/execution/services/execution_state.py:7`
`execution_transitions` | `ExecutionTransitions` | method | `backend/testing/src/modules/execution/services/execution_state.py:11`
`frozen_run_scope` | `FrozenRunScope` | method | `backend/testing/src/modules/execution/services/execution_state.py:15`
`frozen_run_scope_hash` | `FrozenRunScopeHash` | method | `backend/testing/src/modules/execution/services/execution_state.py:36`
`enforce_not_applicable_policy` | `EnforceNotApplicablePolicy` | method | `backend/testing/src/modules/execution/services/execution_state.py:41`
`assigned_execution_versions` | `AssignedExecutionVersions` | method | `backend/testing/src/modules/execution/services/execution_state.py:58`
`require_case_execution_assignment` | `RequireCaseExecutionAssignment` | method | `backend/testing/src/modules/execution/services/execution_state.py:79`
`select_resume_execution` | `SelectResumeExecution` | method | `backend/testing/src/modules/execution/services/execution_state.py:88`
`replay_resume_event` | `ReplayResumeEvent` | method | `backend/testing/src/modules/execution/services/execution_state.py:134`
`validate_test_versions` | `ValidateTestVersions` | method | `backend/testing/src/modules/execution/services/execution_state.py:162`
`validate_report_document` | `ValidateReportDocument` | method | `backend/testing/src/modules/execution/services/report_document.py:24`
`document_text` | `DocumentText` | method | `backend/testing/src/modules/execution/services/report_document.py:107`
`paragraph` | `Paragraph` | method | `backend/testing/src/modules/execution/services/report_document.py:117`
`format_report_datetime` | `FormatReportDatetime` | method | `backend/testing/src/modules/execution/services/report_document.py:124`
`resolve_report_fields` | `ResolveReportFields` | method | `backend/testing/src/modules/execution/services/report_document.py:137`
`export_report_docx` | `ExportReportDocx` | method | `backend/testing/src/modules/execution/services/report_document.py:323`
`convert_report_pdf` | `ConvertReportPdf` | method | `backend/testing/src/modules/execution/services/report_document.py:666`
`legacy_report_document` | `LegacyReportDocument` | method | `backend/testing/src/modules/execution/services/report_document.py:693`
`visit` | `Visit` | method | `backend/testing/src/modules/execution/services/report_document.py:31`
`replace` | `Replace` | method | `backend/testing/src/modules/execution/services/report_document.py:157`
`marked` | `Marked` | method | `backend/testing/src/modules/execution/services/report_document.py:252`
`signature_cell` | `SignatureCell` | method | `backend/testing/src/modules/execution/services/report_document.py:254`
`inline` | `Inline` | method | `backend/testing/src/modules/execution/services/report_document.py:479`
`list_numbering` | `ListNumbering` | method | `backend/testing/src/modules/execution/services/report_document.py:505`
`render` | `Render` | method | `backend/testing/src/modules/execution/services/report_document.py:533`
`field` | `Field` | method | `backend/testing/src/modules/execution/services/report_document.py:159`
`result_timestamp` | `ResultTimestamp` | method | `backend/testing/src/modules/execution/services/result_metrics.py:4`
`pass_rate_metrics` | `PassRateMetrics` | method | `backend/testing/src/modules/execution/services/result_metrics.py:18`
`list_test_period_records` | `ListTestPeriodRecords` | method | `backend/testing/src/modules/execution/services/test_period.py:11`
`create_test_period_record` | `CreateTestPeriodRecord` | method | `backend/testing/src/modules/execution/services/test_period.py:18`
`get_test_period_record` | `GetTestPeriodRecord` | method | `backend/testing/src/modules/execution/services/test_period.py:52`
`touch_open_test_period` | `TouchOpenTestPeriod` | method | `backend/testing/src/modules/execution/services/test_period.py:56`
`register_period_activity` | `RegisterPeriodActivity` | method | `backend/testing/src/modules/execution/services/test_period.py:78`
`register_test_result_period_activity` | `RegisterTestResultPeriodActivity` | method | `backend/testing/src/modules/execution/services/test_period.py:91`
`update_test_period_record` | `UpdateTestPeriodRecord` | method | `backend/testing/src/modules/execution/services/test_period.py:111`
`get_test_period_summary` | `GetTestPeriodSummary` | method | `backend/testing/src/modules/execution/services/test_period.py:128`
`close_test_period_record` | `CloseTestPeriodRecord` | method | `backend/testing/src/modules/execution/services/test_period.py:240`
`plan_snapshot` | `PlanSnapshot` | method | `backend/testing/src/modules/execution/services/test_plan.py:68`
`validate_carry_over_items` | `ValidateCarryOverItems` | method | `backend/testing/src/modules/execution/services/test_plan.py:90`
`plan_snapshot_hash` | `PlanSnapshotHash` | method | `backend/testing/src/modules/execution/services/test_plan.py:145`
`verified_approved_plan_snapshot` | `VerifiedApprovedPlanSnapshot` | method | `backend/testing/src/modules/execution/services/test_plan.py:212`
`plan_completeness` | `PlanCompleteness` | method | `backend/testing/src/modules/execution/services/test_plan.py:259`
`plan_definition_completeness` | `PlanDefinitionCompleteness` | method | `backend/testing/src/modules/execution/services/test_plan.py:273`
`plan_incomplete_message` | `PlanIncompleteMessage` | method | `backend/testing/src/modules/execution/services/test_plan.py:286`
`validate_plan_owner` | `ValidatePlanOwner` | method | `backend/testing/src/modules/execution/services/test_plan.py:296`
`validate_plan_scope` | `ValidatePlanScope` | method | `backend/testing/src/modules/execution/services/test_plan.py:306`
`create_test_plan_record` | `CreateTestPlanRecord` | method | `backend/testing/src/modules/execution/services/test_plan.py:353`
`list_test_plan_records` | `ListTestPlanRecords` | method | `backend/testing/src/modules/execution/services/test_plan.py:499`
`get_test_plan_record` | `GetTestPlanRecord` | method | `backend/testing/src/modules/execution/services/test_plan.py:531`
`validate_test_plan_record` | `ValidateTestPlanRecord` | method | `backend/testing/src/modules/execution/services/test_plan.py:534`
`update_test_plan_record` | `UpdateTestPlanRecord` | method | `backend/testing/src/modules/execution/services/test_plan.py:538`
`submit_test_plan_record` | `SubmitTestPlanRecord` | method | `backend/testing/src/modules/execution/services/test_plan.py:672`
`approve_test_plan_record` | `ApproveTestPlanRecord` | method | `backend/testing/src/modules/execution/services/test_plan.py:720`
`request_test_plan_revision` | `RequestTestPlanRevision` | method | `backend/testing/src/modules/execution/services/test_plan.py:791`
`archive_test_plan_record` | `ArchiveTestPlanRecord` | method | `backend/testing/src/modules/execution/services/test_plan.py:814`
`clone_test_plan_record` | `CloneTestPlanRecord` | method | `backend/testing/src/modules/execution/services/test_plan.py:847`
`generate_test_plan_suggestion` | `GenerateTestPlanSuggestion` | method | `backend/testing/src/modules/execution/services/test_plan_generation.py:45`
`get_live_plan_progress` | `GetLivePlanProgress` | method | `backend/testing/src/modules/execution/services/test_plan_progress.py:55`
`create_test_run_record` | `CreateTestRunRecord` | method | `backend/testing/src/modules/execution/services/test_run.py:177`
`rerun_test_run_record` | `RerunTestRunRecord` | method | `backend/testing/src/modules/execution/services/test_run.py:395`
`update_test_run_record` | `UpdateTestRunRecord` | method | `backend/testing/src/modules/execution/services/test_run.py:843`
`assign_test_run_record` | `AssignTestRunRecord` | method | `backend/testing/src/modules/execution/services/test_run.py:863`
`result_has_execution_history` | `ResultHasExecutionHistory` | method | `backend/testing/src/modules/execution/services/test_run.py:726`
`link_existing_defect_to_result` | `LinkExistingDefectToResult` | method | `backend/testing/src/modules/execution/services/test_run_execution.py:96`
`start_test_run_record` | `StartTestRunRecord` | method | `backend/testing/src/modules/execution/services/test_run_execution.py:191`
`resume_test_run_record` | `ResumeTestRunRecord` | method | `backend/testing/src/modules/execution/services/test_run_execution.py:310`
`record_test_result_entry` | `RecordTestResultEntry` | method | `backend/testing/src/modules/execution/services/test_run_execution.py:417`
`update_test_execution_record` | `UpdateTestExecutionRecord` | method | `backend/testing/src/modules/execution/services/test_run_execution.py:588`
`correct_test_result_record` | `CorrectTestResultRecord` | method | `backend/testing/src/modules/execution/services/test_run_execution.py:758`
`complete_test_run_record` | `CompleteTestRunRecord` | method | `backend/testing/src/modules/execution/services/test_run_execution.py:857`
`abort_test_run_record` | `AbortTestRunRecord` | method | `backend/testing/src/modules/execution/services/test_run_execution.py:913`
`persist_start` | `PersistStart` | method | `backend/testing/src/modules/execution/services/test_run_execution.py:281`
`persist_resume` | `PersistResume` | method | `backend/testing/src/modules/execution/services/test_run_execution.py:363`
`persist_result` | `PersistResult` | method | `backend/testing/src/modules/execution/services/test_run_execution.py:470`
`list_test_run_records` | `ListTestRunRecords` | method | `backend/testing/src/modules/execution/services/test_run_query.py:19`
`list_test_result_records` | `ListTestResultRecords` | method | `backend/testing/src/modules/execution/services/test_run_query.py:71`
`get_test_run_record` | `GetTestRunRecord` | method | `backend/testing/src/modules/execution/services/test_run_query.py:88`
`get_test_result_record` | `GetTestResultRecord` | method | `backend/testing/src/modules/execution/services/test_run_query.py:127`
`build_test_run_report` | `BuildTestRunReport` | method | `backend/testing/src/modules/execution/services/test_run_query.py:153`
`create_test_suite_record` | `CreateTestSuiteRecord` | method | `backend/testing/src/modules/execution/services/test_suite.py:21`
`list_test_suite_records` | `ListTestSuiteRecords` | method | `backend/testing/src/modules/execution/services/test_suite.py:43`
`get_test_suite_record` | `GetTestSuiteRecord` | method | `backend/testing/src/modules/execution/services/test_suite.py:65`
`update_test_suite_record` | `UpdateTestSuiteRecord` | method | `backend/testing/src/modules/execution/services/test_suite.py:69`
`clone_test_suite_record` | `CloneTestSuiteRecord` | method | `backend/testing/src/modules/execution/services/test_suite.py:91`
`archive_test_suite_record` | `ArchiveTestSuiteRecord` | method | `backend/testing/src/modules/execution/services/test_suite.py:124`
`api_operation_source_text` | `ApiOperationSourceText` | method | `backend/testing/src/modules/integrations/services/api_artifact.py:48`
`list_api_artifacts` | `ListApiArtifacts` | method | `backend/testing/src/modules/integrations/services/api_artifact.py:83`
`get_api_artifact` | `GetApiArtifact` | method | `backend/testing/src/modules/integrations/services/api_artifact.py:97`
`import_api_artifact` | `ImportApiArtifact` | method | `backend/testing/src/modules/integrations/services/api_artifact.py:124`
`review_api_artifact` | `ReviewApiArtifact` | method | `backend/testing/src/modules/integrations/services/api_artifact.py:176`
`confirm_api_artifact` | `ConfirmApiArtifact` | method | `backend/testing/src/modules/integrations/services/api_artifact.py:220`
`list_api_operations` | `ListApiOperations` | method | `backend/testing/src/modules/integrations/services/api_artifact.py:336`
`get_api_operation` | `GetApiOperation` | method | `backend/testing/src/modules/integrations/services/api_artifact.py:368`
`generate_api_tests` | `GenerateApiTests` | method | `backend/testing/src/modules/integrations/services/api_artifact.py:384`
`get_test_import_preview` | `GetTestImportPreview` | method | `backend/testing/src/modules/integrations/services/api_artifact.py:566`
`build_api_artifact_diff` | `BuildApiArtifactDiff` | method | `backend/testing/src/modules/integrations/services/api_artifact.py:570`
`diff_api_artifacts` | `DiffApiArtifacts` | method | `backend/testing/src/modules/integrations/services/api_artifact.py:604`
`analyze_api_artifact_impact` | `AnalyzeApiArtifactImpact` | method | `backend/testing/src/modules/integrations/services/api_artifact.py:613`
`archive_api_artifact` | `ArchiveApiArtifact` | method | `backend/testing/src/modules/integrations/services/api_artifact.py:693`
`collect_references` | `CollectReferences` | method | `backend/testing/src/modules/integrations/services/api_artifact.py:57`
`persist_confirmation` | `PersistConfirmation` | method | `backend/testing/src/modules/integrations/services/api_artifact.py:277`
`secret_pattern` | `SecretPattern` | method | `backend/testing/src/modules/integrations/services/api_artifact_formats.py:10`
`public_api_import` | `PublicApiImport` | method | `backend/testing/src/modules/integrations/services/api_artifact_formats.py:14`
`operation_identity` | `OperationIdentity` | method | `backend/testing/src/modules/integrations/services/api_artifact_formats.py:22`
`operation_fingerprint` | `OperationFingerprint` | method | `backend/testing/src/modules/integrations/services/api_artifact_formats.py:26`
`json_bytes` | `JsonBytes` | method | `backend/testing/src/modules/integrations/services/api_artifact_formats.py:37`
`create_xlsx` | `CreateXlsx` | method | `backend/testing/src/modules/integrations/services/api_artifact_formats.py:48`
`xlsx_column` | `XlsxColumn` | method | `backend/testing/src/modules/integrations/services/api_artifact_formats.py:76`
`parse_openapi` | `ParseOpenapi` | method | `backend/testing/src/modules/integrations/services/api_artifact_formats.py:84`
`parse_postman` | `ParsePostman` | method | `backend/testing/src/modules/integrations/services/api_artifact_formats.py:113`
`sanitize` | `Sanitize` | method | `backend/testing/src/modules/integrations/services/api_artifact_formats.py:165`
`sanitize_postman` | `SanitizePostman` | method | `backend/testing/src/modules/integrations/services/api_artifact_formats.py:185`
`terms` | `Terms` | method | `backend/testing/src/modules/integrations/services/api_artifact_formats.py:220`
`lexical_similarity` | `LexicalSimilarity` | method | `backend/testing/src/modules/integrations/services/api_artifact_formats.py:229`
`model_metadata` | `ModelMetadata` | method | `backend/testing/src/modules/integrations/services/api_artifact_formats.py:236`
`walk` | `Walk` | method | `backend/testing/src/modules/integrations/services/api_artifact_formats.py:122`
`validate_source` | `ValidateSource` | method | `backend/testing/src/modules/integrations/services/automation_script.py:37`
`generated_script` | `GeneratedScript` | method | `backend/testing/src/modules/integrations/services/automation_script.py:46`
`default_filename` | `DefaultFilename` | method | `backend/testing/src/modules/integrations/services/automation_script.py:91`
`list` | `List` | method | `backend/testing/src/modules/integrations/services/automation_script.py:103`
`get` | `Get` | method | `backend/testing/src/modules/integrations/services/automation_script.py:108`
`generate` | `Generate` | method | `backend/testing/src/modules/integrations/services/automation_script.py:117`
`update` | `Update` | method | `backend/testing/src/modules/integrations/services/automation_script.py:271`
`approve` | `Approve` | method | `backend/testing/src/modules/integrations/services/automation_script.py:303`
`export` | `Export` | method | `backend/testing/src/modules/integrations/services/automation_script.py:340`
`junit_cases` | `JunitCases` | method | `backend/testing/src/modules/integrations/services/junit_import.py:12`
`import_junit_result` | `ImportJunitResult` | method | `backend/testing/src/modules/integrations/services/junit_import.py:37`
`list_junit_imports` | `ListJunitImports` | method | `backend/testing/src/modules/integrations/services/junit_import.py:132`
`resolve_junit_unresolved_mapping` | `ResolveJunitUnresolvedMapping` | method | `backend/testing/src/modules/integrations/services/junit_import.py:137`
`junit_import_source_hash` | `JunitImportSourceHash` | method | `backend/testing/src/modules/integrations/services/junit_import_identity.py:4`
`operation_key` | `OperationKey` | method | `backend/testing/src/modules/operations/services/bulk_operation.py:32`
`item_result` | `ItemResult` | method | `backend/testing/src/modules/operations/services/bulk_operation.py:36`
`decorate` | `Decorate` | method | `backend/testing/src/modules/operations/services/bulk_operation.py:45`
`finish` | `Finish` | method | `backend/testing/src/modules/operations/services/bulk_operation.py:75`
`replay` | `Replay` | method | `backend/testing/src/modules/operations/services/bulk_operation.py:167`
`tags` | `Tags` | method | `backend/testing/src/modules/operations/services/bulk_operation.py:177`
`add_to_suite` | `AddToSuite` | method | `backend/testing/src/modules/operations/services/bulk_operation.py:236`
`mark_review_required` | `MarkReviewRequired` | method | `backend/testing/src/modules/operations/services/bulk_operation.py:295`
`archive` | `Archive` | method | `backend/testing/src/modules/operations/services/bulk_operation.py:344`
`run` | `Run` | method | `backend/testing/src/modules/operations/services/bulk_operation.py:47`
`persist` | `Persist` | method | `backend/testing/src/modules/operations/services/bulk_operation.py:126`
`enqueue` | `Enqueue` | method | `backend/testing/src/modules/operations/services/delegated_jobs.py:11`
`get` | `Get` | method | `backend/testing/src/modules/operations/services/delegated_jobs.py:40`
`attachment_size` | `AttachmentSize` | method | `backend/testing/src/modules/operations/services/internal_admin.py:12`
`user_memberships` | `UserMemberships` | method | `backend/testing/src/modules/operations/services/internal_admin.py:28`
`projects` | `Projects` | method | `backend/testing/src/modules/operations/services/internal_admin.py:36`
`project` | `Project` | method | `backend/testing/src/modules/operations/services/internal_admin.py:68`
`change_status` | `ChangeStatus` | method | `backend/testing/src/modules/operations/services/internal_admin.py:92`
`change_quota` | `ChangeQuota` | method | `backend/testing/src/modules/operations/services/internal_admin.py:109`
`project_memberships` | `ProjectMemberships` | method | `backend/testing/src/modules/operations/services/internal_admin.py:123`
`delete_project` | `DeleteProject` | method | `backend/testing/src/modules/operations/services/internal_admin.py:142`
`break_glass_grants` | `BreakGlassGrants` | method | `backend/testing/src/modules/operations/services/internal_admin.py:159`
`create_break_glass_grant` | `CreateBreakGlassGrant` | method | `backend/testing/src/modules/operations/services/internal_admin.py:173`
`revoke_break_glass_grant` | `RevokeBreakGlassGrant` | method | `backend/testing/src/modules/operations/services/internal_admin.py:192`
`operations_metrics` | `OperationsMetrics` | method | `backend/testing/src/modules/operations/services/internal_admin.py:210`
`rag_status` | `RagStatus` | method | `backend/testing/src/modules/operations/services/internal_admin.py:224`
`reindex_candidates` | `ReindexCandidates` | method | `backend/testing/src/modules/operations/services/internal_admin.py:235`
`storage_usage` | `StorageUsage` | method | `backend/testing/src/modules/operations/services/internal_admin.py:254`
`process_delegated_job` | `ProcessDelegatedJob` | method | `backend/testing/src/modules/operations/services/job_execution.py:14`
`execute_job` | `ExecuteJob` | method | `backend/testing/src/modules/operations/services/job_execution.py:65`
`reindex_artifact` | `ReindexArtifact` | method | `backend/testing/src/modules/operations/services/job_execution.py:97`
`overview` | `Overview` | method | `backend/testing/src/modules/operations/services/operations.py:13`
`retry_failed_job` | `RetryFailedJob` | method | `backend/testing/src/modules/operations/services/operations.py:70`
`register` | `Register` | method | `backend/testing/src/modules/projects/services/attachment.py:19`
`list` | `List` | method | `backend/testing/src/modules/projects/services/attachment.py:133`
`delete` | `Delete` | method | `backend/testing/src/modules/projects/services/attachment.py:182`
`moderate` | `Moderate` | method | `backend/testing/src/modules/projects/services/attachment.py:204`
`artifact_context` | `ArtifactContext` | method | `backend/testing/src/modules/projects/services/collaboration.py:39`
`update_presence` | `UpdatePresence` | method | `backend/testing/src/modules/projects/services/collaboration.py:71`
`list_presence` | `ListPresence` | method | `backend/testing/src/modules/projects/services/collaboration.py:93`
`apply_operation` | `ApplyOperation` | method | `backend/testing/src/modules/projects/services/collaboration.py:108`
`list_conflicts` | `ListConflicts` | method | `backend/testing/src/modules/projects/services/collaboration.py:240`
`resolve_conflict` | `ResolveConflict` | method | `backend/testing/src/modules/projects/services/collaboration.py:248`
`explain_project_access` | `ExplainProjectAccess` | method | `backend/testing/src/modules/projects/services/effective_access.py:14`
`get_effective_project_access` | `GetEffectiveProjectAccess` | method | `backend/testing/src/modules/projects/services/effective_access.py:75`
`project_access` | `ProjectAccess` | method | `backend/testing/src/modules/projects/services/project.py:46`
`project_settings` | `ProjectSettings` | method | `backend/testing/src/modules/projects/services/project.py:130`
`can_create_project` | `CanCreateProject` | method | `backend/testing/src/modules/projects/services/project.py:144`
`validate_project_roles` | `ValidateProjectRoles` | method | `backend/testing/src/modules/projects/services/project.py:148`
`create` | `Create` | method | `backend/testing/src/modules/projects/services/project.py:160`
`list` | `List` | method | `backend/testing/src/modules/projects/services/project.py:232`
`list_invitations` | `ListInvitations` | method | `backend/testing/src/modules/projects/services/project.py:278`
`get` | `Get` | method | `backend/testing/src/modules/projects/services/project.py:292`
`update` | `Update` | method | `backend/testing/src/modules/projects/services/project.py:313`
`get_settings` | `GetSettings` | method | `backend/testing/src/modules/projects/services/project.py:342`
`update_settings` | `UpdateSettings` | method | `backend/testing/src/modules/projects/services/project.py:350`
`archive` | `Archive` | method | `backend/testing/src/modules/projects/services/project.py:392`
`restore` | `Restore` | method | `backend/testing/src/modules/projects/services/project.py:418`
`list_members` | `ListMembers` | method | `backend/testing/src/modules/projects/services/project.py:446`
`add_member` | `AddMember` | method | `backend/testing/src/modules/projects/services/project.py:478`
`accept_invitation` | `AcceptInvitation` | method | `backend/testing/src/modules/projects/services/project.py:519`
`accept_project_invitation` | `AcceptProjectInvitation` | method | `backend/testing/src/modules/projects/services/project.py:544`
`decline_invitation` | `DeclineInvitation` | method | `backend/testing/src/modules/projects/services/project.py:565`
`leave` | `Leave` | method | `backend/testing/src/modules/projects/services/project.py:590`
`resend_invitation` | `ResendInvitation` | method | `backend/testing/src/modules/projects/services/project.py:615`
`cancel_invitation` | `CancelInvitation` | method | `backend/testing/src/modules/projects/services/project.py:641`
`update_member` | `UpdateMember` | method | `backend/testing/src/modules/projects/services/project.py:671`
`remove_member` | `RemoveMember` | method | `backend/testing/src/modules/projects/services/project.py:729`
`artifact_label` | `ArtifactLabel` | method | `backend/testing/src/modules/projects/services/project_notification.py:9`
`default_rules` | `DefaultRules` | method | `backend/testing/src/modules/projects/services/project_notification.py:19`
`default_preferences` | `DefaultPreferences` | method | `backend/testing/src/modules/projects/services/project_notification.py:31`
`require_artifact` | `RequireArtifact` | method | `backend/testing/src/modules/projects/services/project_notification.py:48`
`list_watches` | `ListWatches` | method | `backend/testing/src/modules/projects/services/project_notification.py:64`
`set_watch` | `SetWatch` | method | `backend/testing/src/modules/projects/services/project_notification.py:93`
`get_rules` | `GetRules` | method | `backend/testing/src/modules/projects/services/project_notification.py:116`
`update_rules` | `UpdateRules` | method | `backend/testing/src/modules/projects/services/project_notification.py:122`
`get_preferences` | `GetPreferences` | method | `backend/testing/src/modules/projects/services/project_notification.py:172`
`update_preferences` | `UpdatePreferences` | method | `backend/testing/src/modules/projects/services/project_notification.py:178`
`update_project_progress` | `UpdateProjectProgress` | method | `backend/testing/src/modules/projects/services/project_progress.py:11`
`operation` | `Operation` | method | `backend/testing/src/modules/projects/services/project_progress.py:14`
`assignable_responsibilities` | `AssignableResponsibilities` | method | `backend/testing/src/modules/projects/services/project_responsibilities.py:23`
`validate_project_responsibilities` | `ValidateProjectResponsibilities` | method | `backend/testing/src/modules/projects/services/project_responsibilities.py:43`
`validate_entries` | `ValidateEntries` | method | `backend/testing/src/modules/projects/services/project_responsibilities.py:13`
`percentage` | `Percentage` | method | `backend/testing/src/modules/quality/services/analytics.py:12`
`lexical_score` | `LexicalScore` | method | `backend/testing/src/modules/quality/services/analytics.py:16`
`search` | `Search` | method | `backend/testing/src/modules/quality/services/analytics.py:24`
`dashboard` | `Dashboard` | method | `backend/testing/src/modules/quality/services/analytics.py:73`
`search_knowledge` | `SearchKnowledge` | method | `backend/testing/src/modules/quality/services/analytics.py:180`
`ask_project` | `AskProject` | method | `backend/testing/src/modules/quality/services/analytics.py:443`
`project_audit` | `ProjectAudit` | method | `backend/testing/src/modules/quality/services/analytics.py:503`
`maintenance` | `Maintenance` | method | `backend/testing/src/modules/quality/services/analytics.py:525`
`ai` | `Ai` | method | `backend/testing/src/modules/quality/services/analytics.py:537`
`execution_report` | `ExecutionReport` | method | `backend/testing/src/modules/quality/services/analytics.py:852`
`defect_report` | `DefectReport` | method | `backend/testing/src/modules/quality/services/analytics.py:911`
`activity` | `Activity` | method | `backend/testing/src/modules/quality/services/analytics.py:967`
`coverage_snapshot` | `CoverageSnapshot` | method | `backend/testing/src/modules/quality/services/analytics.py:988`
`passage_rank` | `PassageRank` | method | `backend/testing/src/modules/quality/services/analytics.py:336`
`semantic_candidate_score` | `SemanticCandidateScore` | method | `backend/testing/src/modules/quality/services/change_analysis.py:6`
`semantic_changes` | `SemanticChanges` | method | `backend/testing/src/modules/quality/services/change_analysis.py:14`
`classify_test_impact` | `ClassifyTestImpact` | method | `backend/testing/src/modules/quality/services/change_analysis.py:33`
`enrich_change_set_records` | `EnrichChangeSetRecords` | method | `backend/testing/src/modules/quality/services/change_set.py:9`
`mark_previous_traces_stale` | `MarkPreviousTracesStale` | method | `backend/testing/src/modules/quality/services/change_set.py:56`
`create_change_set_record` | `CreateChangeSetRecord` | method | `backend/testing/src/modules/quality/services/change_set.py:88`
`list_change_set_records` | `ListChangeSetRecords` | method | `backend/testing/src/modules/quality/services/change_set.py:177`
`get_change_set_record` | `GetChangeSetRecord` | method | `backend/testing/src/modules/quality/services/change_set.py:200`
`review_change_set_record` | `ReviewChangeSetRecord` | method | `backend/testing/src/modules/quality/services/change_set.py:207`
`confidence_band` | `ConfidenceBand` | method | `backend/testing/src/modules/quality/services/defect_analysis.py:7`
`find_duplicate_defect_pairs` | `FindDuplicateDefectPairs` | method | `backend/testing/src/modules/quality/services/defect_analysis.py:15`
`build_defect_trace_candidates` | `BuildDefectTraceCandidates` | method | `backend/testing/src/modules/quality/services/defect_analysis.py:45`
`require_defect_editor_assignment` | `RequireDefectEditorAssignment` | method | `backend/testing/src/modules/quality/services/defect_authorization.py:7`
`resolve_defect_classification` | `ResolveDefectClassification` | method | `backend/testing/src/modules/quality/services/defect_classification.py:11`
`resolve_severity_classification` | `ResolveSeverityClassification` | method | `backend/testing/src/modules/quality/services/defect_classification.py:15`
`resolve_priority_classification` | `ResolvePriorityClassification` | method | `backend/testing/src/modules/quality/services/defect_classification.py:19`
`defect_is_blocking` | `DefectIsBlocking` | method | `backend/testing/src/modules/quality/services/defect_classification.py:23`
`defect_is_critical` | `DefectIsCritical` | method | `backend/testing/src/modules/quality/services/defect_classification.py:27`
`update_defect_record` | `UpdateDefectRecord` | method | `backend/testing/src/modules/quality/services/defect_lifecycle.py:81`
`transition_defect_record` | `TransitionDefectRecord` | method | `backend/testing/src/modules/quality/services/defect_lifecycle.py:280`
`retest_defect_record` | `RetestDefectRecord` | method | `backend/testing/src/modules/quality/services/defect_lifecycle.py:356`
`defect_classification_options` | `DefectClassificationOptions` | method | `backend/testing/src/modules/quality/services/defect_records.py:55`
`create_defect_record` | `CreateDefectRecord` | method | `backend/testing/src/modules/quality/services/defect_records.py:71`
`list_defect_records` | `ListDefectRecords` | method | `backend/testing/src/modules/quality/services/defect_records.py:321`
`build_defect_export` | `BuildDefectExport` | method | `backend/testing/src/modules/quality/services/defect_records.py:406`
`get_defect_record` | `GetDefectRecord` | method | `backend/testing/src/modules/quality/services/defect_records.py:418`
`defect_search_text` | `DefectSearchText` | method | `backend/testing/src/modules/quality/services/defect_search.py:8`
`index_defect_for_search` | `IndexDefectForSearch` | method | `backend/testing/src/modules/quality/services/defect_search.py:50`
`process_next_defect_search_index` | `ProcessNextDefectSearchIndex` | method | `backend/testing/src/modules/quality/services/defect_search_index_worker.py:14`
`start_defect_search_index_worker` | `StartDefectSearchIndexWorker` | method | `backend/testing/src/modules/quality/services/defect_search_index_worker.py:78`
`stop_defect_search_index_worker` | `StopDefectSearchIndexWorker` | method | `backend/testing/src/modules/quality/services/defect_search_index_worker.py:84`
`suggest_defect_trace_record` | `SuggestDefectTraceRecord` | method | `backend/testing/src/modules/quality/services/defect_trace.py:32`
`list_defect_trace_suggestions` | `ListDefectTraceSuggestions` | method | `backend/testing/src/modules/quality/services/defect_trace.py:154`
`list_defect_trace_candidates` | `ListDefectTraceCandidates` | method | `backend/testing/src/modules/quality/services/defect_trace.py:168`
`update_defect_trace_record` | `UpdateDefectTraceRecord` | method | `backend/testing/src/modules/quality/services/defect_trace.py:174`
`document` | `Document` | method | `backend/testing/src/modules/quality/services/impact_ai.py:7`
`normalize_maintenance_patch` | `NormalizeMaintenancePatch` | method | `backend/testing/src/modules/quality/services/impact_ai.py:14`
`request_impact_classification` | `RequestImpactClassification` | method | `backend/testing/src/modules/quality/services/impact_ai.py:55`
`apply_ai_impact_suggestions` | `ApplyAiImpactSuggestions` | method | `backend/testing/src/modules/quality/services/impact_ai.py:83`
`ai_new_test_requirements` | `AiNewTestRequirements` | method | `backend/testing/src/modules/quality/services/impact_ai.py:125`
`impact_test_version_ids` | `ImpactTestVersionIds` | method | `backend/testing/src/modules/quality/services/impact_analysis.py:70`
`trace_target_sets` | `TraceTargetSets` | method | `backend/testing/src/modules/quality/services/impact_analysis.py:79`
`require_current_impact_source` | `RequireCurrentImpactSource` | method | `backend/testing/src/modules/quality/services/impact_analysis.py:204`
`create_impact_analysis_record` | `CreateImpactAnalysisRecord` | method | `backend/testing/src/modules/quality/services/impact_analysis.py:222`
`get_change_set_impact_record` | `GetChangeSetImpactRecord` | method | `backend/testing/src/modules/quality/services/impact_analysis.py:567`
`get_impact_analysis_record` | `GetImpactAnalysisRecord` | method | `backend/testing/src/modules/quality/services/impact_analysis.py:582`
`rerun_impact_analysis_record` | `RerunImpactAnalysisRecord` | method | `backend/testing/src/modules/quality/services/impact_analysis.py:591`
`review_impact_analysis_record` | `ReviewImpactAnalysisRecord` | method | `backend/testing/src/modules/quality/services/impact_analysis.py:686`
`add_impact_review_perspective_record` | `AddImpactReviewPerspectiveRecord` | method | `backend/testing/src/modules/quality/services/impact_analysis.py:811`
`document` | `Document` | method | `backend/testing/src/modules/quality/services/impact_automation.py:7`
`normalize_maintenance_patch` | `NormalizeMaintenancePatch` | method | `backend/testing/src/modules/quality/services/impact_automation.py:14`
`request_impact_classification` | `RequestImpactClassification` | method | `backend/testing/src/modules/quality/services/impact_automation.py:55`
`apply_ai_impact_suggestions` | `ApplyAiImpactSuggestions` | method | `backend/testing/src/modules/quality/services/impact_automation.py:83`
`ai_new_test_requirements` | `AiNewTestRequirements` | method | `backend/testing/src/modules/quality/services/impact_automation.py:126`
`create_maintenance_proposal_records` | `CreateMaintenanceProposalRecords` | method | `backend/testing/src/modules/quality/services/maintenance_proposal.py:13`
`list_maintenance_proposal_records` | `ListMaintenanceProposalRecords` | method | `backend/testing/src/modules/quality/services/maintenance_proposal.py:93`
`get_maintenance_proposal_record` | `GetMaintenanceProposalRecord` | method | `backend/testing/src/modules/quality/services/maintenance_proposal.py:188`
`review_maintenance_proposal_record` | `ReviewMaintenanceProposalRecord` | method | `backend/testing/src/modules/quality/services/maintenance_proposal.py:192`
`require_pending_revision` | `RequirePendingRevision` | method | `backend/testing/src/modules/quality/services/maintenance_proposal.py:229`
`update_proposal_acceptance_rate` | `UpdateProposalAcceptanceRate` | method | `backend/testing/src/modules/quality/services/maintenance_proposal.py:245`
`reject_maintenance_proposal_record` | `RejectMaintenanceProposalRecord` | method | `backend/testing/src/modules/quality/services/maintenance_proposal.py:256`
`regenerate_maintenance_proposal_record` | `RegenerateMaintenanceProposalRecord` | method | `backend/testing/src/modules/quality/services/maintenance_proposal.py:293`
`approve_maintenance_proposal` | `ApproveMaintenanceProposal` | method | `backend/testing/src/modules/quality/services/proposal_application.py:22`
`apply_maintenance_proposal` | `ApplyMaintenanceProposal` | method | `backend/testing/src/modules/quality/services/proposal_application.py:46`
`create_test_version_from_proposal` | `CreateTestVersionFromProposal` | method | `backend/testing/src/modules/quality/services/proposal_application.py:326`
`recover_partial_proposal` | `RecoverPartialProposal` | method | `backend/testing/src/modules/quality/services/proposal_application.py:552`
`create_test_draft_from_proposal` | `CreateTestDraftFromProposal` | method | `backend/testing/src/modules/quality/services/proposal_application.py:666`
`mark_test_obsolete` | `MarkTestObsolete` | method | `backend/testing/src/modules/quality/services/proposal_application.py:710`
`recent_failure_versions` | `RecentFailureVersions` | method | `backend/testing/src/modules/quality/services/regression_recommendation.py:12`
`create_regression_recommendation_record` | `CreateRegressionRecommendationRecord` | method | `backend/testing/src/modules/quality/services/regression_recommendation.py:25`
`get_change_set_regression_record` | `GetChangeSetRegressionRecord` | method | `backend/testing/src/modules/quality/services/regression_recommendation.py:131`
`get_regression_recommendation_record` | `GetRegressionRecommendationRecord` | method | `backend/testing/src/modules/quality/services/regression_recommendation.py:146`
`edit_regression_recommendation_record` | `EditRegressionRecommendationRecord` | method | `backend/testing/src/modules/quality/services/regression_recommendation.py:157`
`approve_regression_recommendation_record` | `ApproveRegressionRecommendationRecord` | method | `backend/testing/src/modules/quality/services/regression_recommendation.py:216`
`validated_suggestion` | `ValidatedSuggestion` | method | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:22`
`process_next_requirement_impact` | `ProcessNextRequirementImpact` | method | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:231`
`start_requirement_impact_worker` | `StartRequirementImpactWorker` | method | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:260`
`stop_requirement_impact_worker` | `StopRequirementImpactWorker` | method | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:266`
`valid_quote` | `ValidQuote` | method | `backend/testing/src/modules/quality/services/requirement_impact_worker.py:135`
`compare_requirement_versions` | `CompareRequirementVersions` | method | `backend/testing/src/modules/quality/services/requirement_version_diff.py:42`
`create` | `Create` | method | `backend/testing/src/modules/quality/services/review_comment.py:30`
`list` | `List` | method | `backend/testing/src/modules/quality/services/review_comment.py:65`
`update` | `Update` | method | `backend/testing/src/modules/quality/services/review_comment.py:90`
`delete` | `Delete` | method | `backend/testing/src/modules/quality/services/review_comment.py:112`
`resolve` | `Resolve` | method | `backend/testing/src/modules/quality/services/review_comment.py:147`
`reopen` | `Reopen` | method | `backend/testing/src/modules/quality/services/review_comment.py:159`
`percent` | `Percent` | method | `backend/testing/src/modules/quality/services/traceability.py:23`
`scope_traceability_matrix` | `ScopeTraceabilityMatrix` | method | `backend/testing/src/modules/quality/services/traceability.py:27`
`validate_artifact` | `ValidateArtifact` | method | `backend/testing/src/modules/quality/services/traceability.py:85`
`create_link` | `CreateLink` | method | `backend/testing/src/modules/quality/services/traceability.py:96`
`get_link` | `GetLink` | method | `backend/testing/src/modules/quality/services/traceability.py:132`
`confirm_link` | `ConfirmLink` | method | `backend/testing/src/modules/quality/services/traceability.py:136`
`reject_link` | `RejectLink` | method | `backend/testing/src/modules/quality/services/traceability.py:142`
`review_link` | `ReviewLink` | method | `backend/testing/src/modules/quality/services/traceability.py:148`
`revoke_link` | `RevokeLink` | method | `backend/testing/src/modules/quality/services/traceability.py:189`
`matrix` | `Matrix` | method | `backend/testing/src/modules/quality/services/traceability.py:215`
`coverage` | `Coverage` | method | `backend/testing/src/modules/quality/services/traceability.py:400`
`requirement_coverage` | `RequirementCoverage` | method | `backend/testing/src/modules/quality/services/traceability.py:529`
`list_snapshots` | `ListSnapshots` | method | `backend/testing/src/modules/quality/services/traceability.py:556`
`create_snapshot` | `CreateSnapshot` | method | `backend/testing/src/modules/quality/services/traceability.py:563`
`test_case_trace` | `TestCaseTrace` | method | `backend/testing/src/modules/quality/services/traceability.py:615`
`export` | `Export` | method | `backend/testing/src/modules/quality/services/traceability.py:629`
`split_source_text` | `SplitSourceText` | method | `backend/testing/src/modules/requirements/services/document_reader.py:163`
`read_document_page` | `ReadDocumentPage` | method | `backend/testing/src/modules/requirements/services/document_reader.py:185`
`read_document_source_page` | `ReadDocumentSourcePage` | method | `backend/testing/src/modules/requirements/services/document_reader.py:307`
`read_document_source_image` | `ReadDocumentSourceImage` | method | `backend/testing/src/modules/requirements/services/document_reader.py:360`
`search_document` | `SearchDocument` | method | `backend/testing/src/modules/requirements/services/document_reader.py:388`
`process_document_summary_job` | `ProcessDocumentSummaryJob` | method | `backend/testing/src/modules/requirements/services/document_reader.py:699`
`start_document_summary_job` | `StartDocumentSummaryJob` | method | `backend/testing/src/modules/requirements/services/document_reader.py:835`
`get_document_summary_job` | `GetDocumentSummaryJob` | method | `backend/testing/src/modules/requirements/services/document_reader.py:931`
`cancel_document_summary_job` | `CancelDocumentSummaryJob` | method | `backend/testing/src/modules/requirements/services/document_reader.py:1063`
`retry_document_summary_job` | `RetryDocumentSummaryJob` | method | `backend/testing/src/modules/requirements/services/document_reader.py:1098`
`summarize_project_documents` | `SummarizeProjectDocuments` | method | `backend/testing/src/modules/requirements/services/document_reader.py:1170`
`maintain_leases` | `MaintainLeases` | method | `backend/testing/src/modules/requirements/services/document_reader.py:501`
`get_latest_requirement_quality_analysis` | `GetLatestRequirementQualityAnalysis` | method | `backend/testing/src/modules/requirements/services/requirement_ai.py:19`
`analyze_requirement_quality` | `AnalyzeRequirementQuality` | method | `backend/testing/src/modules/requirements/services/requirement_ai.py:35`
`compare_requirement_versions` | `CompareRequirementVersions` | method | `backend/testing/src/modules/requirements/services/requirement_analysis.py:13`
`find_requirement_duplicates` | `FindRequirementDuplicates` | method | `backend/testing/src/modules/requirements/services/requirement_analysis.py:41`
`dependency_reaches` | `DependencyReaches` | method | `backend/testing/src/modules/requirements/services/requirement_dependencies.py:10`
`add_dependency` | `AddDependency` | method | `backend/testing/src/modules/requirements/services/requirement_dependencies.py:34`
`remove_dependency` | `RemoveDependency` | method | `backend/testing/src/modules/requirements/services/requirement_dependencies.py:97`
`process_next_requirement_document_parse` | `ProcessNextRequirementDocumentParse` | method | `backend/testing/src/modules/requirements/services/requirement_document_worker.py:21`
`start_requirement_document_parse_worker` | `StartRequirementDocumentParseWorker` | method | `backend/testing/src/modules/requirements/services/requirement_document_worker.py:99`
`stop_requirement_document_parse_worker` | `StopRequirementDocumentParseWorker` | method | `backend/testing/src/modules/requirements/services/requirement_document_worker.py:105`
`queue_document_ingestion` | `QueueDocumentIngestion` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:80`
`open_requirement_document_source_if_current` | `OpenRequirementDocumentSourceIfCurrent` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:109`
`open_requirement_document_indexing_source_if_current` | `OpenRequirementDocumentIndexingSourceIfCurrent` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:133`
`finish_requirement_document_ai_revocation` | `FinishRequirementDocumentAiRevocation` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:159`
`begin_requirement_document_archive_cleanup` | `BeginRequirementDocumentArchiveCleanup` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:218`
`finish_requirement_document_archive_cleanup` | `FinishRequirementDocumentArchiveCleanup` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:289`
`recover_document_ingestion` | `RecoverDocumentIngestion` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:396`
`validate_document_recipients` | `ValidateDocumentRecipients` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:424`
`require_document_access` | `RequireDocumentAccess` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:435`
`can_read_requirement_document` | `CanReadRequirementDocument` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:442`
`normalized_document_duplicate_text` | `NormalizedDocumentDuplicateText` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:461`
`accessible_requirement_document_project_ids` | `AccessibleRequirementDocumentProjectIds` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:470`
`find_requirement_document_duplicates` | `FindRequirementDocumentDuplicates` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:489`
`find_matching_requirement_document_projects` | `FindMatchingRequirementDocumentProjects` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:600`
`require_duplicate_import_decision` | `RequireDuplicateImportDecision` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:660`
`requirement_document_read_query` | `RequirementDocumentReadQuery` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:706`
`require_document_owner` | `RequireDocumentOwner` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:729`
`find_reusable_document_duplicate` | `FindReusableDocumentDuplicate` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:736`
`reuse_ready_requirement_document` | `ReuseReadyRequirementDocument` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:763`
`reuse_uploaded_requirement_document` | `ReuseUploadedRequirementDocument` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:791`
`ensure_duplicate_settings_match` | `EnsureDuplicateSettingsMatch` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:817`
`resolve_source_successor` | `ResolveSourceSuccessor` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:836`
`raise_source_version_insert_conflict` | `RaiseSourceVersionInsertConflict` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:886`
`normalize_ocr_language` | `NormalizeOcrLanguage` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:908`
`requirement_document_deduplication_key` | `RequirementDocumentDeduplicationKey` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:920`
`create_requirement_document_record` | `CreateRequirementDocumentRecord` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:950`
`store_raw_requirement_source` | `StoreRawRequirementSource` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:1135`
`remove_unclaimed_raw_requirement_source` | `RemoveUnclaimedRawRequirementSource` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:1141`
`read_raw_requirement_source` | `ReadRawRequirementSource` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:1162`
`parse_requirement_source` | `ParseRequirementSource` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:1178`
`read_and_parse_requirement_source` | `ReadAndParseRequirementSource` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:1208`
`index_requirement_document` | `IndexRequirementDocument` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:1286`
`requirement_document_index_status` | `RequirementDocumentIndexStatus` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:1439`
`ai_safe_parse_report` | `AiSafeParseReport` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:1450`
`can_retry_requirement_document_parse` | `CanRetryRequirementDocumentParse` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:1509`
`maintain_requirement_parse_lease` | `MaintainRequirementParseLease` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:1523`
`upload_requirement_document_record` | `UploadRequirementDocumentRecord` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:1540`
`list_requirement_document_records` | `ListRequirementDocumentRecords` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:1754`
`encode_ai_document_cursor` | `EncodeAiDocumentCursor` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:1789`
`decode_ai_document_cursor` | `DecodeAiDocumentCursor` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:1798`
`list_ai_requirement_document_page` | `ListAiRequirementDocumentPage` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:1823`
`list_requirement_source_structure_page` | `ListRequirementSourceStructurePage` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:1859`
`get_requirement_document_record` | `GetRequirementDocumentRecord` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:1929`
`get_requirement_source_impact` | `GetRequirementSourceImpact` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:1945`
`update_requirement_document_record` | `UpdateRequirementDocumentRecord` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:2084`
`update_requirement_document_access` | `UpdateRequirementDocumentAccess` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:2154`
`update_requirement_document_ai_read` | `UpdateRequirementDocumentAiRead` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:2353`
`start_requirement_document_ai_processing` | `StartRequirementDocumentAiProcessing` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:2589`
`reindex_requirement_document_record` | `ReindexRequirementDocumentRecord` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:2699`
`archive_requirement_document_record` | `ArchiveRequirementDocumentRecord` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:2788`
`restore_requirement_document_record` | `RestoreRequirementDocumentRecord` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:2816`
`retry_requirement_document_parse_record` | `RetryRequirementDocumentParseRecord` | method | `backend/testing/src/modules/requirements/services/requirement_documents.py:2892`
`is_labeled_acceptance_criterion_line` | `IsLabeledAcceptanceCriterionLine` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:88`
`is_acceptance_criteria_table_header` | `IsAcceptanceCriteriaTableHeader` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:95`
`extract_labeled_acceptance_criteria` | `ExtractLabeledAcceptanceCriteria` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:107`
`normalized_acceptance_criterion` | `NormalizedAcceptanceCriterion` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:137`
`normalized_acceptance_criterion_key` | `NormalizedAcceptanceCriterionKey` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:148`
`explicit_acceptance_criteria` | `ExplicitAcceptanceCriteria` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:153`
`attach_labeled_acceptance_criteria` | `AttachLabeledAcceptanceCriteria` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:208`
`supported_requirement_formats` | `SupportedRequirementFormats` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:271`
`safe_requirement_filename` | `SafeRequirementFilename` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:275`
`source_document_text` | `SourceDocumentText` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:282`
`parse_requirement_import` | `ParseRequirementImport` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:317`
`atomic_requirement_candidates` | `AtomicRequirementCandidates` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:503`
`extract_file_content` | `ExtractFileContent` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:632`
`parse_api_content` | `ParseApiContent` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:646`
`extract_docx` | `ExtractDocx` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:664`
`extract_xlsx_csv` | `ExtractXlsxCsv` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:717`
`api_operation_identifiers` | `ApiOperationIdentifiers` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:767`
`parse_api_artifact` | `ParseApiArtifact` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:800`
`retain_pending` | `RetainPending` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:159`
`render` | `Render` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:288`
`add_paragraph` | `AddParagraph` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:530`
`paragraph_text` | `ParagraphText` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:669`
`walk` | `Walk` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:830`
`walk` | `Walk` | method | `backend/testing/src/modules/requirements/services/requirement_import.py:781`
`requirement_import_needs_refresh` | `RequirementImportNeedsRefresh` | method | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:61`
`extract_document_candidates` | `ExtractDocumentCandidates` | method | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:70`
`grounded_requirement_candidates` | `GroundedRequirementCandidates` | method | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:97`
`extract_grounded_requirement_candidates` | `ExtractGroundedRequirementCandidates` | method | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:300`
`requirement_import_match_score` | `RequirementImportMatchScore` | method | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:335`
`authorize_requirement_import_job` | `AuthorizeRequirementImportJob` | method | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:346`
`compare_requirement_import_job` | `CompareRequirementImportJob` | method | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:372`
`resolve_requirement_import_candidate` | `ResolveRequirementImportCandidate` | method | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:594`
`extract_requirement_candidates` | `ExtractRequirementCandidates` | method | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:952`
`create_requirement_import_job` | `CreateRequirementImportJob` | method | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:1108`
`create_requirement_preview_from_candidates` | `CreateRequirementPreviewFromCandidates` | method | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:1132`
`link_template_import_to_source` | `LinkTemplateImportToSource` | method | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:1230`
`review_requirement_import_job` | `ReviewRequirementImportJob` | method | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:1287`
`merge_requirement_import_candidates` | `MergeRequirementImportCandidates` | method | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:1351`
`split_requirement_import_candidate` | `SplitRequirementImportCandidate` | method | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:1438`
`reject_requirement_import_candidate` | `RejectRequirementImportCandidate` | method | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:1524`
`apply_requirement_import_job` | `ApplyRequirementImportJob` | method | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:1585`
`confirm_requirement_import_job` | `ConfirmRequirementImportJob` | method | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:1750`
`recover_confirmed_import_index` | `RecoverConfirmedImportIndex` | method | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:1754`
`source_reference_for` | `SourceReferenceFor` | method | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:127`
`contains` | `Contains` | method | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:201`
`grounded_values` | `GroundedValues` | method | `backend/testing/src/modules/requirements/services/requirement_import_workflow.py:204`
`validate_requirement_sources` | `ValidateRequirementSources` | method | `backend/testing/src/modules/requirements/services/requirement_indexing.py:15`
`validate_requirement_api_operations` | `ValidateRequirementApiOperations` | method | `backend/testing/src/modules/requirements/services/requirement_indexing.py:70`
`index_requirement_version` | `IndexRequirementVersion` | method | `backend/testing/src/modules/requirements/services/requirement_indexing.py:100`
`save_requirement_ready` | `SaveRequirementReady` | method | `backend/testing/src/modules/requirements/services/requirement_lifecycle.py:31`
`submit_requirement_for_review` | `SubmitRequirementForReview` | method | `backend/testing/src/modules/requirements/services/requirement_lifecycle.py:70`
`return_requirement_for_changes` | `ReturnRequirementForChanges` | method | `backend/testing/src/modules/requirements/services/requirement_lifecycle.py:185`
`reopen_requirement_for_editing` | `ReopenRequirementForEditing` | method | `backend/testing/src/modules/requirements/services/requirement_lifecycle.py:275`
`technical_review_requirement` | `TechnicalReviewRequirement` | method | `backend/testing/src/modules/requirements/services/requirement_lifecycle.py:350`
`baseline_requirement` | `BaselineRequirement` | method | `backend/testing/src/modules/requirements/services/requirement_lifecycle.py:398`
`make_requirement_obsolete` | `MakeRequirementObsolete` | method | `backend/testing/src/modules/requirements/services/requirement_lifecycle.py:528`
`restore_obsolete_requirement` | `RestoreObsoleteRequirement` | method | `backend/testing/src/modules/requirements/services/requirement_lifecycle.py:610`
`status` | `Status` | method | `backend/testing/src/modules/requirements/services/requirement_lifecycle.py:20`
`degraded_mode` | `DegradedMode` | method | `backend/testing/src/modules/requirements/services/requirement_lifecycle.py:28`
`persist_acceptance_criteria` | `PersistAcceptanceCriteria` | method | `backend/testing/src/modules/requirements/services/requirement_records.py:29`
`validate_requirement_custom_values` | `ValidateRequirementCustomValues` | method | `backend/testing/src/modules/requirements/services/requirement_records.py:57`
`create_requirement_record` | `CreateRequirementRecord` | method | `backend/testing/src/modules/requirements/services/requirement_records.py:95`
`list_requirement_records` | `ListRequirementRecords` | method | `backend/testing/src/modules/requirements/services/requirement_records.py:200`
`get_requirement_record` | `GetRequirementRecord` | method | `backend/testing/src/modules/requirements/services/requirement_records.py:302`
`update_requirement_draft_record` | `UpdateRequirementDraftRecord` | method | `backend/testing/src/modules/requirements/services/requirement_records.py:308`
`create_requirement_version_record` | `CreateRequirementVersionRecord` | method | `backend/testing/src/modules/requirements/services/requirement_records.py:458`
`list_requirement_version_records` | `ListRequirementVersionRecords` | method | `backend/testing/src/modules/requirements/services/requirement_records.py:549`
`get_requirement_version_record` | `GetRequirementVersionRecord` | method | `backend/testing/src/modules/requirements/services/requirement_records.py:553`
`persist` | `Persist` | method | `backend/testing/src/modules/requirements/services/requirement_records.py:158`
`persist` | `Persist` | method | `backend/testing/src/modules/requirements/services/requirement_records.py:402`
`persist` | `Persist` | method | `backend/testing/src/modules/requirements/services/requirement_records.py:515`
`create_requirement_source` | `CreateRequirementSource` | method | `backend/testing/src/modules/requirements/services/requirement_sources.py:49`
`list_requirement_sources` | `ListRequirementSources` | method | `backend/testing/src/modules/requirements/services/requirement_sources.py:174`
`reindex_requirement_source` | `ReindexRequirementSource` | method | `backend/testing/src/modules/requirements/services/requirement_sources.py:193`
`archive_requirement_source` | `ArchiveRequirementSource` | method | `backend/testing/src/modules/requirements/services/requirement_sources.py:251`
`status` | `Status` | method | `backend/testing/src/modules/requirements/services/requirement_sources.py:17`
`degraded_mode` | `DegradedMode` | method | `backend/testing/src/modules/requirements/services/requirement_sources.py:28`
`starter_templates` | `StarterTemplates` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:36`
`requirement_source_refs_from_suggestion` | `RequirementSourceRefsFromSuggestion` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:64`
`public_view` | `PublicView` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:112`
`pending_publication_view` | `PendingPublicationView` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:129`
`visible_template` | `VisibleTemplate` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:140`
`list_templates` | `ListTemplates` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:164`
`list_template_versions` | `ListTemplateVersions` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:204`
`get_template_version` | `GetTemplateVersion` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:222`
`list_custom_fields` | `ListCustomFields` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:244`
`create_custom_field` | `CreateCustomField` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:249`
`validate_template_documents` | `ValidateTemplateDocuments` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:259`
`template_lineage_documents` | `TemplateLineageDocuments` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:271`
`validate_template_ai_sources` | `ValidateTemplateAiSources` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:308`
`synthesis_source_fingerprint` | `SynthesisSourceFingerprint` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:312`
`requirement_document_synthesis_snapshot` | `RequirementDocumentSynthesisSnapshot` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:356`
`template_synthesis_source_snapshot` | `TemplateSynthesisSourceSnapshot` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:386`
`revalidate_template_synthesis_sources` | `RevalidateTemplateSynthesisSources` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:406`
`create_template` | `CreateTemplate` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:452`
`update_template` | `UpdateTemplate` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:511`
`preview_template` | `PreviewTemplate` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:589`
`review_template` | `ReviewTemplate` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:665`
`synthesize_template` | `SynthesizeTemplate` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:766`
`request_publication` | `RequestPublication` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:989`
`consent_publication` | `ConsentPublication` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:1014`
`approve_publication` | `ApprovePublication` | method | `backend/testing/src/modules/requirements/services/requirement_templates.py:1033`
`unique_source_refs` | `UniqueSourceRefs` | method | `backend/testing/src/modules/requirements/services/requirement_transformations.py:24`
`find_requirement_transformation` | `FindRequirementTransformation` | method | `backend/testing/src/modules/requirements/services/requirement_transformations.py:36`
`load_requirement_baselines` | `LoadRequirementBaselines` | method | `backend/testing/src/modules/requirements/services/requirement_transformations.py:40`
`claim_requirement_transformation` | `ClaimRequirementTransformation` | method | `backend/testing/src/modules/requirements/services/requirement_transformations.py:93`
`prepare_requirement_output` | `PrepareRequirementOutput` | method | `backend/testing/src/modules/requirements/services/requirement_transformations.py:160`
`hydrate_requirement_transformation` | `HydrateRequirementTransformation` | method | `backend/testing/src/modules/requirements/services/requirement_transformations.py:250`
`execute_requirement_transformation` | `ExecuteRequirementTransformation` | method | `backend/testing/src/modules/requirements/services/requirement_transformations.py:271`
`text_doc` | `TextDoc` | method | `backend/testing/src/modules/requirements/services/requirement_workflow.py:7`
`serialized_content` | `SerializedContent` | method | `backend/testing/src/modules/requirements/services/requirement_workflow.py:14`
`acceptance_criterion_text` | `AcceptanceCriterionText` | method | `backend/testing/src/modules/requirements/services/requirement_workflow.py:20`
`normalized_business_rule_lines` | `NormalizedBusinessRuleLines` | method | `backend/testing/src/modules/requirements/services/requirement_workflow.py:24`
`prepare_requirement_ai_suggestion` | `PrepareRequirementAiSuggestion` | method | `backend/testing/src/modules/requirements/services/requirement_workflow.py:44`
`requirement_suggestion_changes` | `RequirementSuggestionChanges` | method | `backend/testing/src/modules/requirements/services/requirement_workflow.py:75`
`prepare_requirement_candidates` | `PrepareRequirementCandidates` | method | `backend/testing/src/modules/requirements/services/requirement_workflow.py:101`
`candidate_quality_issues` | `CandidateQualityIssues` | method | `backend/testing/src/modules/requirements/services/requirement_workflow.py:120`
`candidate_fingerprint` | `CandidateFingerprint` | method | `backend/testing/src/modules/requirements/services/requirement_workflow.py:137`
`leases` | `Leases` | method | `backend/testing/src/repositories/ai_run_access.py:13`
`acquire` | `Acquire` | method | `backend/testing/src/repositories/ai_run_access.py:16`
`release` | `Release` | method | `backend/testing/src/repositories/ai_run_access.py:52`
`heartbeat` | `Heartbeat` | method | `backend/testing/src/repositories/ai_run_access.py:62`
`revoke_and_wait` | `RevokeAndWait` | method | `backend/testing/src/repositories/ai_run_access.py:103`
`allow_source` | `AllowSource` | method | `backend/testing/src/repositories/ai_run_access.py:133`
`list_requirements_by_ids` | `ListRequirementsByIds` | method | `backend/testing/src/repositories/analysis.py:13`
`list_requirement_version_labels` | `ListRequirementVersionLabels` | method | `backend/testing/src/repositories/analysis.py:19`
`list_change_pair_versions` | `ListChangePairVersions` | method | `backend/testing/src/repositories/analysis.py:25`
`find_change_set_for_target` | `FindChangeSetForTarget` | method | `backend/testing/src/repositories/analysis.py:30`
`insert_change_set` | `InsertChangeSet` | method | `backend/testing/src/repositories/analysis.py:35`
`refresh_empty_change_set` | `RefreshEmptyChangeSet` | method | `backend/testing/src/repositories/analysis.py:39`
`mark_traces_stale` | `MarkTracesStale` | method | `backend/testing/src/repositories/analysis.py:57`
`list_change_sets` | `ListChangeSets` | method | `backend/testing/src/repositories/analysis.py:67`
`review_change_set` | `ReviewChangeSet` | method | `backend/testing/src/repositories/analysis.py:72`
`list_acceptance_criteria` | `ListAcceptanceCriteria` | method | `backend/testing/src/repositories/analysis.py:84`
`list_active_test_case_versions` | `ListActiveTestCaseVersions` | method | `backend/testing/src/repositories/analysis.py:90`
`iter_active_test_case_version_pages` | `IterActiveTestCaseVersionPages` | method | `backend/testing/src/repositories/analysis.py:99`
`list_related_active_test_case_versions` | `ListRelatedActiveTestCaseVersions` | method | `backend/testing/src/repositories/analysis.py:131`
`list_active_defects` | `ListActiveDefects` | method | `backend/testing/src/repositories/analysis.py:141`
`list_current_requirements` | `ListCurrentRequirements` | method | `backend/testing/src/repositories/analysis.py:146`
`list_requirement_versions` | `ListRequirementVersions` | method | `backend/testing/src/repositories/analysis.py:151`
`list_current_test_cases` | `ListCurrentTestCases` | method | `backend/testing/src/repositories/analysis.py:156`
`list_test_case_versions` | `ListTestCaseVersions` | method | `backend/testing/src/repositories/analysis.py:164`
`failure_counts` | `FailureCounts` | method | `backend/testing/src/repositories/analysis.py:170`
`upsert_worker_event` | `UpsertWorkerEvent` | method | `backend/testing/src/repositories/analysis.py:178`
`find_requirement_version` | `FindRequirementVersion` | method | `backend/testing/src/repositories/analysis.py:183`
`find_test_case_version` | `FindTestCaseVersion` | method | `backend/testing/src/repositories/analysis.py:188`
`set_artifact_index_result` | `SetArtifactIndexResult` | method | `backend/testing/src/repositories/analysis.py:193`
`list_records` | `ListRecords` | method | `backend/testing/src/repositories/analytics.py:5`
`count_records` | `CountRecords` | method | `backend/testing/src/repositories/analytics.py:11`
`group_counts` | `GroupCounts` | method | `backend/testing/src/repositories/analytics.py:14`
`find_latest` | `FindLatest` | method | `backend/testing/src/repositories/analytics.py:22`
`insert_ai_audit` | `InsertAiAudit` | method | `backend/testing/src/repositories/analytics.py:27`
`list_imports` | `ListImports` | method | `backend/testing/src/repositories/api_artifact.py:7`
`find_import` | `FindImport` | method | `backend/testing/src/repositories/api_artifact.py:13`
`insert_import` | `InsertImport` | method | `backend/testing/src/repositories/api_artifact.py:19`
`transition_import` | `TransitionImport` | method | `backend/testing/src/repositories/api_artifact.py:22`
`list_operations` | `ListOperations` | method | `backend/testing/src/repositories/api_artifact.py:31`
`find_operation` | `FindOperation` | method | `backend/testing/src/repositories/api_artifact.py:39`
`upsert_operation` | `UpsertOperation` | method | `backend/testing/src/repositories/api_artifact.py:44`
`find_impact` | `FindImpact` | method | `backend/testing/src/repositories/api_artifact.py:50`
`list_test_cases` | `ListTestCases` | method | `backend/testing/src/repositories/api_artifact.py:60`
`list_test_case_versions` | `ListTestCaseVersions` | method | `backend/testing/src/repositories/api_artifact.py:65`
`insert_impact` | `InsertImpact` | method | `backend/testing/src/repositories/api_artifact.py:70`
`find_operation` | `FindOperation` | method | `backend/testing/src/repositories/bulk_operation.py:12`
`insert_operation` | `InsertOperation` | method | `backend/testing/src/repositories/bulk_operation.py:17`
`find_artifact` | `FindArtifact` | method | `backend/testing/src/repositories/bulk_operation.py:20`
`update_artifact_tags` | `UpdateArtifactTags` | method | `backend/testing/src/repositories/bulk_operation.py:25`
`find_suite` | `FindSuite` | method | `backend/testing/src/repositories/bulk_operation.py:34`
`find_current_case` | `FindCurrentCase` | method | `backend/testing/src/repositories/bulk_operation.py:39`
`update_suite_versions` | `UpdateSuiteVersions` | method | `backend/testing/src/repositories/bulk_operation.py:48`
`mark_case_review_required` | `MarkCaseReviewRequired` | method | `backend/testing/src/repositories/bulk_operation.py:68`
`find_active_run` | `FindActiveRun` | method | `backend/testing/src/repositories/bulk_operation.py:96`
`archive_artifact` | `ArchiveArtifact` | method | `backend/testing/src/repositories/bulk_operation.py:106`
`find_requirement_version` | `FindRequirementVersion` | method | `backend/testing/src/repositories/collaboration.py:7`
`upsert_presence` | `UpsertPresence` | method | `backend/testing/src/repositories/collaboration.py:12`
`list_presence` | `ListPresence` | method | `backend/testing/src/repositories/collaboration.py:20`
`find_operation` | `FindOperation` | method | `backend/testing/src/repositories/collaboration.py:25`
`list_operations_since` | `ListOperationsSince` | method | `backend/testing/src/repositories/collaboration.py:30`
`insert_conflict` | `InsertConflict` | method | `backend/testing/src/repositories/collaboration.py:42`
`insert_operation` | `InsertOperation` | method | `backend/testing/src/repositories/collaboration.py:46`
`list_conflicts` | `ListConflicts` | method | `backend/testing/src/repositories/collaboration.py:50`
`resolve_conflict` | `ResolveConflict` | method | `backend/testing/src/repositories/collaboration.py:55`
`list_all_by_id` | `ListAllById` | method | `backend/testing/src/repositories/common.py:7`
`list_all_acceptance_criteria` | `ListAllAcceptanceCriteria` | method | `backend/testing/src/repositories/common.py:30`
`insert_audit_event` | `InsertAuditEvent` | method | `backend/testing/src/repositories/common.py:38`
`find_project` | `FindProject` | method | `backend/testing/src/repositories/common.py:44`
`find_membership` | `FindMembership` | method | `backend/testing/src/repositories/common.py:47`
`find_active_grant` | `FindActiveGrant` | method | `backend/testing/src/repositories/common.py:53`
`find_entity_identity` | `FindEntityIdentity` | method | `backend/testing/src/repositories/common.py:63`
`find_project_entity` | `FindProjectEntity` | method | `backend/testing/src/repositories/common.py:66`
`optimistic_patch` | `OptimisticPatch` | method | `backend/testing/src/repositories/common.py:71`
`find_entity` | `FindEntity` | method | `backend/testing/src/repositories/common.py:91`
`next_counter` | `NextCounter` | method | `backend/testing/src/repositories/common.py:94`
`migrate_legacy_severity_flags` | `MigrateLegacySeverityFlags` | method | `backend/testing/src/repositories/defect.py:7`
`find_test_result` | `FindTestResult` | method | `backend/testing/src/repositories/defect.py:61`
`find_test_run` | `FindTestRun` | method | `backend/testing/src/repositories/defect.py:69`
`link_failed_result_to_defect` | `LinkFailedResultToDefect` | method | `backend/testing/src/repositories/defect.py:75`
`set_retest_source` | `SetRetestSource` | method | `backend/testing/src/repositories/defect.py:98`
`insert_defect` | `InsertDefect` | method | `backend/testing/src/repositories/defect.py:115`
`find_defect_by_idempotency` | `FindDefectByIdempotency` | method | `backend/testing/src/repositories/defect.py:121`
`list_requirement_version_ids` | `ListRequirementVersionIds` | method | `backend/testing/src/repositories/defect.py:133`
`list_test_case_version_ids` | `ListTestCaseVersionIds` | method | `backend/testing/src/repositories/defect.py:139`
`count_defects` | `CountDefects` | method | `backend/testing/src/repositories/defect.py:145`
`list_defects` | `ListDefects` | method | `backend/testing/src/repositories/defect.py:148`
`list_project_defects` | `ListProjectDefects` | method | `backend/testing/src/repositories/defect.py:153`
`list_trace_links` | `ListTraceLinks` | method | `backend/testing/src/repositories/defect.py:156`
`list_comments` | `ListComments` | method | `backend/testing/src/repositories/defect.py:167`
`list_attachments` | `ListAttachments` | method | `backend/testing/src/repositories/defect.py:176`
`find_test_case_version` | `FindTestCaseVersion` | method | `backend/testing/src/repositories/defect.py:188`
`count_requirement_versions` | `CountRequirementVersions` | method | `backend/testing/src/repositories/defect.py:194`
`transition_defect` | `TransitionDefect` | method | `backend/testing/src/repositories/defect.py:200`
`find_retest` | `FindRetest` | method | `backend/testing/src/repositories/defect.py:215`
`find_defect` | `FindDefect` | method | `backend/testing/src/repositories/defect.py:220`
`insert_retest` | `InsertRetest` | method | `backend/testing/src/repositories/defect.py:226`
`claim_retest_result` | `ClaimRetestResult` | method | `backend/testing/src/repositories/defect.py:232`
`apply_retest` | `ApplyRetest` | method | `backend/testing/src/repositories/defect.py:265`
`mark_retest_applied` | `MarkRetestApplied` | method | `backend/testing/src/repositories/defect.py:298`
`find_ai_result_by_idempotency` | `FindAiResultByIdempotency` | method | `backend/testing/src/repositories/defect.py:305`
`insert_ai_result` | `InsertAiResult` | method | `backend/testing/src/repositories/defect.py:310`
`find_ai_result` | `FindAiResult` | method | `backend/testing/src/repositories/defect.py:316`
`list_ai_results_for_defects` | `ListAiResultsForDefects` | method | `backend/testing/src/repositories/defect.py:326`
`review_ai_result` | `ReviewAiResult` | method | `backend/testing/src/repositories/defect.py:342`
`entries` | `Entries` | method | `backend/testing/src/repositories/defect_search_index.py:12`
`entry_id` | `EntryId` | method | `backend/testing/src/repositories/defect_search_index.py:15`
`enqueue` | `Enqueue` | method | `backend/testing/src/repositories/defect_search_index.py:18`
`claim_next` | `ClaimNext` | method | `backend/testing/src/repositories/defect_search_index.py:41`
`complete` | `Complete` | method | `backend/testing/src/repositories/defect_search_index.py:70`
`defer` | `Defer` | method | `backend/testing/src/repositories/defect_search_index.py:89`
`list_script_drafts` | `ListScriptDrafts` | method | `backend/testing/src/repositories/execution_asset.py:7`
`find_script_by_idempotency_key` | `FindScriptByIdempotencyKey` | method | `backend/testing/src/repositories/execution_asset.py:12`
`find_test_case_version` | `FindTestCaseVersion` | method | `backend/testing/src/repositories/execution_asset.py:17`
`insert_script_draft` | `InsertScriptDraft` | method | `backend/testing/src/repositories/execution_asset.py:22`
`list_executions` | `ListExecutions` | method | `backend/testing/src/repositories/execution_asset.py:26`
`find_execution_by_idempotency_key` | `FindExecutionByIdempotencyKey` | method | `backend/testing/src/repositories/execution_asset.py:31`
`find_confirmed_postman_import` | `FindConfirmedPostmanImport` | method | `backend/testing/src/repositories/execution_asset.py:36`
`find_approved_playwright_script` | `FindApprovedPlaywrightScript` | method | `backend/testing/src/repositories/execution_asset.py:46`
`find_active_environment` | `FindActiveEnvironment` | method | `backend/testing/src/repositories/execution_asset.py:56`
`insert_execution` | `InsertExecution` | method | `backend/testing/src/repositories/execution_asset.py:65`
`transition_execution` | `TransitionExecution` | method | `backend/testing/src/repositories/execution_asset.py:69`
`rollback_queued_execution` | `RollbackQueuedExecution` | method | `backend/testing/src/repositories/execution_asset.py:76`
`find_execution_operation` | `FindExecutionOperation` | method | `backend/testing/src/repositories/execution_asset.py:98`
`ingest_execution_result` | `IngestExecutionResult` | method | `backend/testing/src/repositories/execution_asset.py:103`
`advance_release_gate_revision` | `AdvanceReleaseGateRevision` | method | `backend/testing/src/repositories/execution_context.py:5`
`project_settings` | `ProjectSettings` | method | `backend/testing/src/repositories/execution_context.py:34`
`list_open_blocking_defects` | `ListOpenBlockingDefects` | method | `backend/testing/src/repositories/execution_context.py:37`
`list_releases` | `ListReleases` | method | `backend/testing/src/repositories/execution_context.py:122`
`find_release` | `FindRelease` | method | `backend/testing/src/repositories/execution_context.py:127`
`insert_release` | `InsertRelease` | method | `backend/testing/src/repositories/execution_context.py:132`
`set_current_release` | `SetCurrentRelease` | method | `backend/testing/src/repositories/execution_context.py:138`
`list_builds` | `ListBuilds` | method | `backend/testing/src/repositories/execution_context.py:154`
`insert_build` | `InsertBuild` | method | `backend/testing/src/repositories/execution_context.py:159`
`set_current_build` | `SetCurrentBuild` | method | `backend/testing/src/repositories/execution_context.py:163`
`list_active_environments` | `ListActiveEnvironments` | method | `backend/testing/src/repositories/execution_context.py:176`
`insert_environment` | `InsertEnvironment` | method | `backend/testing/src/repositories/execution_context.py:181`
`project_settings` | `ProjectSettings` | method | `backend/testing/src/repositories/execution_state.py:5`
`list_results` | `ListResults` | method | `backend/testing/src/repositories/execution_state.py:8`
`find_result` | `FindResult` | method | `backend/testing/src/repositories/execution_state.py:13`
`find_test_case_version` | `FindTestCaseVersion` | method | `backend/testing/src/repositories/execution_state.py:16`
`count_test_case_versions` | `CountTestCaseVersions` | method | `backend/testing/src/repositories/execution_state.py:21`
`find_by_change_and_model` | `FindByChangeAndModel` | method | `backend/testing/src/repositories/impact_analysis.py:7`
`list_acceptance_criteria` | `ListAcceptanceCriteria` | method | `backend/testing/src/repositories/impact_analysis.py:12`
`list_trace_links` | `ListTraceLinks` | method | `backend/testing/src/repositories/impact_analysis.py:17`
`list_current_tests` | `ListCurrentTests` | method | `backend/testing/src/repositories/impact_analysis.py:26`
`list_scenarios_for_sources` | `ListScenariosForSources` | method | `backend/testing/src/repositories/impact_analysis.py:31`
`list_plans_for_impact` | `ListPlansForImpact` | method | `backend/testing/src/repositories/impact_analysis.py:44`
`list_runs_for_impact` | `ListRunsForImpact` | method | `backend/testing/src/repositories/impact_analysis.py:63`
`list_test_versions` | `ListTestVersions` | method | `backend/testing/src/repositories/impact_analysis.py:79`
`find_requirement_version` | `FindRequirementVersion` | method | `backend/testing/src/repositories/impact_analysis.py:84`
`insert_analysis` | `InsertAnalysis` | method | `backend/testing/src/repositories/impact_analysis.py:89`
`commit_analysis_for_change_set` | `CommitAnalysisForChangeSet` | method | `backend/testing/src/repositories/impact_analysis.py:92`
`set_change_status` | `SetChangeStatus` | method | `backend/testing/src/repositories/impact_analysis.py:121`
`find_latest_for_change` | `FindLatestForChange` | method | `backend/testing/src/repositories/impact_analysis.py:127`
`transition_analysis` | `TransitionAnalysis` | method | `backend/testing/src/repositories/impact_analysis.py:133`
`delete_analysis` | `DeleteAnalysis` | method | `backend/testing/src/repositories/impact_analysis.py:156`
`restore_analysis_status` | `RestoreAnalysisStatus` | method | `backend/testing/src/repositories/impact_analysis.py:161`
`review_analysis` | `ReviewAnalysis` | method | `backend/testing/src/repositories/impact_analysis.py:173`
`find_analysis` | `FindAnalysis` | method | `backend/testing/src/repositories/impact_analysis.py:187`
`insert_perspective` | `InsertPerspective` | method | `backend/testing/src/repositories/impact_analysis.py:192`
`list_memberships` | `ListMemberships` | method | `backend/testing/src/repositories/internal_admin.py:7`
`list_projects` | `ListProjects` | method | `backend/testing/src/repositories/internal_admin.py:13`
`member_counts` | `MemberCounts` | method | `backend/testing/src/repositories/internal_admin.py:19`
`find_project` | `FindProject` | method | `backend/testing/src/repositories/internal_admin.py:27`
`count_members` | `CountMembers` | method | `backend/testing/src/repositories/internal_admin.py:30`
`update_project` | `UpdateProject` | method | `backend/testing/src/repositories/internal_admin.py:36`
`purge_project` | `PurgeProject` | method | `backend/testing/src/repositories/internal_admin.py:44`
`list_break_glass_grants` | `ListBreakGlassGrants` | method | `backend/testing/src/repositories/internal_admin.py:62`
`insert_break_glass_grant` | `InsertBreakGlassGrant` | method | `backend/testing/src/repositories/internal_admin.py:69`
`revoke_break_glass_grant` | `RevokeBreakGlassGrant` | method | `backend/testing/src/repositories/internal_admin.py:72`
`count_records` | `CountRecords` | method | `backend/testing/src/repositories/internal_admin.py:81`
`index_status_counts` | `IndexStatusCounts` | method | `backend/testing/src/repositories/internal_admin.py:84`
`distinct_ids` | `DistinctIds` | method | `backend/testing/src/repositories/internal_admin.py:90`
`list_project_documents` | `ListProjectDocuments` | method | `backend/testing/src/repositories/internal_admin.py:95`
`list_by_impact` | `ListByImpact` | method | `backend/testing/src/repositories/maintenance_proposal.py:7`
`find_change_set` | `FindChangeSet` | method | `backend/testing/src/repositories/maintenance_proposal.py:12`
`insert_many` | `InsertMany` | method | `backend/testing/src/repositories/maintenance_proposal.py:17`
`insert` | `Insert` | method | `backend/testing/src/repositories/maintenance_proposal.py:24`
`list_proposals` | `ListProposals` | method | `backend/testing/src/repositories/maintenance_proposal.py:28`
`proposal_scope_snapshot` | `ProposalScopeSnapshot` | method | `backend/testing/src/repositories/maintenance_proposal.py:36`
`list_test_case_versions` | `ListTestCaseVersions` | method | `backend/testing/src/repositories/maintenance_proposal.py:51`
`list_impact_analyses` | `ListImpactAnalyses` | method | `backend/testing/src/repositories/maintenance_proposal.py:56`
`update` | `Update` | method | `backend/testing/src/repositories/maintenance_proposal.py:62`
`count_by_statuses` | `CountByStatuses` | method | `backend/testing/src/repositories/maintenance_proposal.py:69`
`rollback_supersede` | `RollbackSupersede` | method | `backend/testing/src/repositories/maintenance_proposal.py:74`
`list_records` | `ListRecords` | method | `backend/testing/src/repositories/operations.py:5`
`count_records` | `CountRecords` | method | `backend/testing/src/repositories/operations.py:10`
`list_project_storage_values` | `ListProjectStorageValues` | method | `backend/testing/src/repositories/operations.py:13`
`average_impact_latency` | `AverageImpactLatency` | method | `backend/testing/src/repositories/operations.py:20`
`projects` | `Projects` | method | `backend/testing/src/repositories/project.py:10`
`members` | `Members` | method | `backend/testing/src/repositories/project.py:14`
`grants` | `Grants` | method | `backend/testing/src/repositories/project.py:18`
`create_with_memberships` | `CreateWithMemberships` | method | `backend/testing/src/repositories/project.py:21`
`list_active_memberships` | `ListActiveMemberships` | method | `backend/testing/src/repositories/project.py:29`
`list_active_grants` | `ListActiveGrants` | method | `backend/testing/src/repositories/project.py:34`
`list_projects` | `ListProjects` | method | `backend/testing/src/repositories/project.py:43`
`list_invitations` | `ListInvitations` | method | `backend/testing/src/repositories/project.py:46`
`list_project_summaries` | `ListProjectSummaries` | method | `backend/testing/src/repositories/project.py:51`
`find_member` | `FindMember` | method | `backend/testing/src/repositories/project.py:59`
`find_active_grant` | `FindActiveGrant` | method | `backend/testing/src/repositories/project.py:65`
`list_members` | `ListMembers` | method | `backend/testing/src/repositories/project.py:75`
`list_active_members_with_permission` | `ListActiveMembersWithPermission` | method | `backend/testing/src/repositories/project.py:80`
`add_member` | `AddMember` | method | `backend/testing/src/repositories/project.py:118`
`transition_invitation` | `TransitionInvitation` | method | `backend/testing/src/repositories/project.py:122`
`transition_membership` | `TransitionMembership` | method | `backend/testing/src/repositories/project.py:129`
`update_invitation` | `UpdateInvitation` | method | `backend/testing/src/repositories/project.py:136`
`fence_active_members_with_permission` | `FenceActiveMembersWithPermission` | method | `backend/testing/src/repositories/project.py:148`
`update_member` | `UpdateMember` | method | `backend/testing/src/repositories/project.py:196`
`remove_member` | `RemoveMember` | method | `backend/testing/src/repositories/project.py:207`
`ensure_test_case_approval_admin_only` | `EnsureTestCaseApprovalAdminOnly` | method | `backend/testing/src/repositories/project_access.py:11`
`ensure_workflow_role_capabilities` | `EnsureWorkflowRoleCapabilities` | method | `backend/testing/src/repositories/project_access.py:69`
`ensure_private_defect_capability` | `EnsurePrivateDefectCapability` | method | `backend/testing/src/repositories/project_access.py:147`
`ensure_read_only_comment_capabilities` | `EnsureReadOnlyCommentCapabilities` | method | `backend/testing/src/repositories/project_access.py:221`
`migrate_legacy` | `MigrateLegacy` | method | `backend/testing/src/repositories/project_access.py:297`
`subscriptions` | `Subscriptions` | method | `backend/testing/src/repositories/project_notification.py:8`
`rules` | `Rules` | method | `backend/testing/src/repositories/project_notification.py:12`
`preferences` | `Preferences` | method | `backend/testing/src/repositories/project_notification.py:16`
`artifact_exists` | `ArtifactExists` | method | `backend/testing/src/repositories/project_notification.py:19`
`list_subscriptions` | `ListSubscriptions` | method | `backend/testing/src/repositories/project_notification.py:27`
`list_artifact_labels` | `ListArtifactLabels` | method | `backend/testing/src/repositories/project_notification.py:30`
`remove_subscription` | `RemoveSubscription` | method | `backend/testing/src/repositories/project_notification.py:43`
`set_subscription` | `SetSubscription` | method | `backend/testing/src/repositories/project_notification.py:46`
`find_rules` | `FindRules` | method | `backend/testing/src/repositories/project_notification.py:61`
`insert_rules` | `InsertRules` | method | `backend/testing/src/repositories/project_notification.py:64`
`find_preferences` | `FindPreferences` | method | `backend/testing/src/repositories/project_notification.py:68`
`insert_preferences` | `InsertPreferences` | method | `backend/testing/src/repositories/project_notification.py:73`
`find_applied_artifact` | `FindAppliedArtifact` | method | `backend/testing/src/repositories/proposal_application.py:8`
`find_proposal` | `FindProposal` | method | `backend/testing/src/repositories/proposal_application.py:23`
`transition_proposal` | `TransitionProposal` | method | `backend/testing/src/repositories/proposal_application.py:28`
`take_over_expired_proposal_application` | `TakeOverExpiredProposalApplication` | method | `backend/testing/src/repositories/proposal_application.py:42`
`update_proposal` | `UpdateProposal` | method | `backend/testing/src/repositories/proposal_application.py:70`
`find_test_case` | `FindTestCase` | method | `backend/testing/src/repositories/proposal_application.py:75`
`find_test_version` | `FindTestVersion` | method | `backend/testing/src/repositories/proposal_application.py:80`
`find_test_draft` | `FindTestDraft` | method | `backend/testing/src/repositories/proposal_application.py:86`
`insert_test_version` | `InsertTestVersion` | method | `backend/testing/src/repositories/proposal_application.py:91`
`activate_test_version` | `ActivateTestVersion` | method | `backend/testing/src/repositories/proposal_application.py:94`
`set_test_case_status` | `SetTestCaseStatus` | method | `backend/testing/src/repositories/proposal_application.py:119`
`mark_previous_traces` | `MarkPreviousTraces` | method | `backend/testing/src/repositories/proposal_application.py:126`
`find_impact_analysis` | `FindImpactAnalysis` | method | `backend/testing/src/repositories/proposal_application.py:136`
`find_change_set` | `FindChangeSet` | method | `backend/testing/src/repositories/proposal_application.py:139`
`list_acceptance_criteria_for_version` | `ListAcceptanceCriteriaForVersion` | method | `backend/testing/src/repositories/proposal_application.py:144`
`list_acceptance_criteria_by_ids` | `ListAcceptanceCriteriaByIds` | method | `backend/testing/src/repositories/proposal_application.py:149`
`find_requirement_version` | `FindRequirementVersion` | method | `backend/testing/src/repositories/proposal_application.py:156`
`find_trace` | `FindTrace` | method | `backend/testing/src/repositories/proposal_application.py:161`
`insert_trace` | `InsertTrace` | method | `backend/testing/src/repositories/proposal_application.py:164`
`ensure_confirmed_requirement_trace` | `EnsureConfirmedRequirementTrace` | method | `backend/testing/src/repositories/proposal_application.py:167`
`mark_test_obsolete` | `MarkTestObsolete` | method | `backend/testing/src/repositories/proposal_application.py:206`
`list_recent_runs` | `ListRecentRuns` | method | `backend/testing/src/repositories/regression_recommendation.py:7`
`list_results_by_status` | `ListResultsByStatus` | method | `backend/testing/src/repositories/regression_recommendation.py:12`
`find_by_change_set` | `FindByChangeSet` | method | `backend/testing/src/repositories/regression_recommendation.py:17`
`find_by_impact_analysis` | `FindByImpactAnalysis` | method | `backend/testing/src/repositories/regression_recommendation.py:25`
`find_latest_impact_analysis` | `FindLatestImpactAnalysis` | method | `backend/testing/src/repositories/regression_recommendation.py:34`
`find_test_case` | `FindTestCase` | method | `backend/testing/src/repositories/regression_recommendation.py:39`
`insert_recommendation` | `InsertRecommendation` | method | `backend/testing/src/repositories/regression_recommendation.py:44`
`update_recommendation` | `UpdateRecommendation` | method | `backend/testing/src/repositories/regression_recommendation.py:48`
`supersede_pending_recommendation` | `SupersedePendingRecommendation` | method | `backend/testing/src/repositories/regression_recommendation.py:55`
`find_suite` | `FindSuite` | method | `backend/testing/src/repositories/regression_recommendation.py:73`
`list_active_test_cases` | `ListActiveTestCases` | method | `backend/testing/src/repositories/regression_recommendation.py:78`
`insert_suite` | `InsertSuite` | method | `backend/testing/src/repositories/regression_recommendation.py:87`
`delete_suite` | `DeleteSuite` | method | `backend/testing/src/repositories/regression_recommendation.py:91`
`find_transformation` | `FindTransformation` | method | `backend/testing/src/repositories/requirement.py:8`
`claim_failed_transformation` | `ClaimFailedTransformation` | method | `backend/testing/src/repositories/requirement.py:13`
`insert_transformation` | `InsertTransformation` | method | `backend/testing/src/repositories/requirement.py:30`
`list_requirements_by_ids` | `ListRequirementsByIds` | method | `backend/testing/src/repositories/requirement.py:33`
`list_versions_by_source_documents` | `ListVersionsBySourceDocuments` | method | `backend/testing/src/repositories/requirement.py:38`
`insert_outputs` | `InsertOutputs` | method | `backend/testing/src/repositories/requirement.py:49`
`supersede_version` | `SupersedeVersion` | method | `backend/testing/src/repositories/requirement.py:55`
`supersede_requirement` | `SupersedeRequirement` | method | `backend/testing/src/repositories/requirement.py:87`
`confirm_transformation` | `ConfirmTransformation` | method | `backend/testing/src/repositories/requirement.py:120`
`rollback_superseded_source` | `RollbackSupersededSource` | method | `backend/testing/src/repositories/requirement.py:148`
`discard_transformation_outputs` | `DiscardTransformationOutputs` | method | `backend/testing/src/repositories/requirement.py:178`
`fail_transformation` | `FailTransformation` | method | `backend/testing/src/repositories/requirement.py:189`
`insert_acceptance_criteria` | `InsertAcceptanceCriteria` | method | `backend/testing/src/repositories/requirement.py:203`
`set_acceptance_criterion_ids` | `SetAcceptanceCriterionIds` | method | `backend/testing/src/repositories/requirement.py:209`
`insert_requirement` | `InsertRequirement` | method | `backend/testing/src/repositories/requirement.py:216`
`insert_version` | `InsertVersion` | method | `backend/testing/src/repositories/requirement.py:221`
`delete_version` | `DeleteVersion` | method | `backend/testing/src/repositories/requirement.py:226`
`list_requirements` | `ListRequirements` | method | `backend/testing/src/repositories/requirement.py:232`
`list_versions_by_ids` | `ListVersionsByIds` | method | `backend/testing/src/repositories/requirement.py:238`
`list_confirmed_trace_sources` | `ListConfirmedTraceSources` | method | `backend/testing/src/repositories/requirement.py:243`
`list_pending_impact_targets` | `ListPendingImpactTargets` | method | `backend/testing/src/repositories/requirement.py:256`
`find_duplicate_key` | `FindDuplicateKey` | method | `backend/testing/src/repositories/requirement.py:266`
`update_draft` | `UpdateDraft` | method | `backend/testing/src/repositories/requirement.py:275`
`update_requirement_identity` | `UpdateRequirementIdentity` | method | `backend/testing/src/repositories/requirement.py:290`
`replace_acceptance_criteria` | `ReplaceAcceptanceCriteria` | method | `backend/testing/src/repositories/requirement.py:303`
`find_latest_version` | `FindLatestVersion` | method | `backend/testing/src/repositories/requirement.py:311`
`find_requirement` | `FindRequirement` | method | `backend/testing/src/repositories/requirement.py:316`
`activate_version` | `ActivateVersion` | method | `backend/testing/src/repositories/requirement.py:322`
`list_versions` | `ListVersions` | method | `backend/testing/src/repositories/requirement.py:348`
`find_prior_baseline_candidates` | `FindPriorBaselineCandidates` | method | `backend/testing/src/repositories/requirement.py:357`
`find_version` | `FindVersion` | method | `backend/testing/src/repositories/requirement.py:373`
`list_acceptance_criteria` | `ListAcceptanceCriteria` | method | `backend/testing/src/repositories/requirement.py:383`
`list_acceptance_criteria_for_versions` | `ListAcceptanceCriteriaForVersions` | method | `backend/testing/src/repositories/requirement.py:389`
`find_project_settings` | `FindProjectSettings` | method | `backend/testing/src/repositories/requirement.py:399`
`transition_version` | `TransitionVersion` | method | `backend/testing/src/repositories/requirement.py:402`
`set_requirement_status` | `SetRequirementStatus` | method | `backend/testing/src/repositories/requirement.py:418`
`baseline_version` | `BaselineVersion` | method | `backend/testing/src/repositories/requirement.py:438`
`set_current_baseline` | `SetCurrentBaseline` | method | `backend/testing/src/repositories/requirement.py:451`
`approve_acceptance_criteria` | `ApproveAcceptanceCriteria` | method | `backend/testing/src/repositories/requirement.py:471`
`mark_requirement_obsolete` | `MarkRequirementObsolete` | method | `backend/testing/src/repositories/requirement.py:486`
`mark_version_obsolete` | `MarkVersionObsolete` | method | `backend/testing/src/repositories/requirement.py:519`
`restore_version` | `RestoreVersion` | method | `backend/testing/src/repositories/requirement.py:558`
`restore_requirement` | `RestoreRequirement` | method | `backend/testing/src/repositories/requirement.py:601`
`find_finding` | `FindFinding` | method | `backend/testing/src/repositories/requirement_ai.py:7`
`find_quality_analysis_request` | `FindQualityAnalysisRequest` | method | `backend/testing/src/repositories/requirement_ai.py:12`
`insert_quality_analysis_claim` | `InsertQualityAnalysisClaim` | method | `backend/testing/src/repositories/requirement_ai.py:15`
`reclaim_quality_analysis_claim` | `ReclaimQualityAnalysisClaim` | method | `backend/testing/src/repositories/requirement_ai.py:19`
`replace_quality_analysis_claim` | `ReplaceQualityAnalysisClaim` | method | `backend/testing/src/repositories/requirement_ai.py:38`
`release_quality_analysis_claim` | `ReleaseQualityAnalysisClaim` | method | `backend/testing/src/repositories/requirement_ai.py:50`
`find_latest_quality_analysis` | `FindLatestQualityAnalysis` | method | `backend/testing/src/repositories/requirement_ai.py:59`
`list_acceptance_criteria` | `ListAcceptanceCriteria` | method | `backend/testing/src/repositories/requirement_ai.py:75`
`insert_finding` | `InsertFinding` | method | `backend/testing/src/repositories/requirement_ai.py:81`
`find_requirement_version` | `FindRequirementVersion` | method | `backend/testing/src/repositories/requirement_ai.py:87`
`list_versions` | `ListVersions` | method | `backend/testing/src/repositories/requirement_analysis.py:7`
`list_requirements` | `ListRequirements` | method | `backend/testing/src/repositories/requirement_analysis.py:10`
`list_acceptance_criteria` | `ListAcceptanceCriteria` | method | `backend/testing/src/repositories/requirement_analysis.py:13`
`insert_duplicate_scan` | `InsertDuplicateScan` | method | `backend/testing/src/repositories/requirement_analysis.py:16`
`find_requirement` | `FindRequirement` | method | `backend/testing/src/repositories/requirement_analysis.py:20`
`find_version` | `FindVersion` | method | `backend/testing/src/repositories/requirement_analysis.py:25`
`update_draft_dependencies` | `UpdateDraftDependencies` | method | `backend/testing/src/repositories/requirement_analysis.py:30`
`find_basis` | `FindBasis` | method | `backend/testing/src/repositories/requirement_analysis.py:53`
`list_basis` | `ListBasis` | method | `backend/testing/src/repositories/requirement_analysis.py:56`
`documents` | `Documents` | method | `backend/testing/src/repositories/requirement_document.py:8`
`find_ai_search_sources` | `FindAiSearchSources` | method | `backend/testing/src/repositories/requirement_document.py:11`
`find_by_hash` | `FindByHash` | method | `backend/testing/src/repositories/requirement_document.py:30`
`find_embedded_knowledge_source_by_hash` | `FindEmbeddedKnowledgeSourceByHash` | method | `backend/testing/src/repositories/requirement_document.py:35`
`find_by_deduplication_key` | `FindByDeduplicationKey` | method | `backend/testing/src/repositories/requirement_document.py:55`
`find_reusable_duplicate` | `FindReusableDuplicate` | method | `backend/testing/src/repositories/requirement_document.py:63`
`latest_in_source_series` | `LatestInSourceSeries` | method | `backend/testing/src/repositories/requirement_document.py:93`
`list_source_series` | `ListSourceSeries` | method | `backend/testing/src/repositories/requirement_document.py:99`
`find` | `Find` | method | `backend/testing/src/repositories/requirement_document.py:104`
`normalize_requirement_import_status` | `NormalizeRequirementImportStatus` | method | `backend/testing/src/repositories/requirement_document.py:109`
`list_by_ids` | `ListByIds` | method | `backend/testing/src/repositories/requirement_document.py:132`
`insert` | `Insert` | method | `backend/testing/src/repositories/requirement_document.py:137`
`list` | `List` | method | `backend/testing/src/repositories/requirement_document.py:141`
`next_parse_candidate` | `NextParseCandidate` | method | `backend/testing/src/repositories/requirement_document.py:144`
`defer_parse_attempt` | `DeferParseAttempt` | method | `backend/testing/src/repositories/requirement_document.py:168`
`fail_unavailable_owner_parse` | `FailUnavailableOwnerParse` | method | `backend/testing/src/repositories/requirement_document.py:184`
`list_ai_scope_page` | `ListAiScopePage` | method | `backend/testing/src/repositories/requirement_document.py:216`
`set_index_result` | `SetIndexResult` | method | `backend/testing/src/repositories/requirement_document.py:226`
`update` | `Update` | method | `backend/testing/src/repositories/requirement_document.py:252`
`update_with_revision` | `UpdateWithRevision` | method | `backend/testing/src/repositories/requirement_document.py:260`
`acquire_archive_cleanup_lease` | `AcquireArchiveCleanupLease` | method | `backend/testing/src/repositories/requirement_document.py:285`
`complete_archive_cleanup` | `CompleteArchiveCleanup` | method | `backend/testing/src/repositories/requirement_document.py:308`
`release_archive_cleanup_lease` | `ReleaseArchiveCleanupLease` | method | `backend/testing/src/repositories/requirement_document.py:333`
`acquire_access_update_lease` | `AcquireAccessUpdateLease` | method | `backend/testing/src/repositories/requirement_document.py:353`
`complete_access_update` | `CompleteAccessUpdate` | method | `backend/testing/src/repositories/requirement_document.py:375`
`release_access_update_lease` | `ReleaseAccessUpdateLease` | method | `backend/testing/src/repositories/requirement_document.py:400`
`transition_status` | `TransitionStatus` | method | `backend/testing/src/repositories/requirement_document.py:419`
`claim_status` | `ClaimStatus` | method | `backend/testing/src/repositories/requirement_document.py:447`
`claim_stale_parse` | `ClaimStaleParse` | method | `backend/testing/src/repositories/requirement_document.py:475`
`heartbeat_parse_attempt` | `HeartbeatParseAttempt` | method | `backend/testing/src/repositories/requirement_document.py:497`
`list_acceptance_criterion_ids` | `ListAcceptanceCriterionIds` | method | `backend/testing/src/repositories/requirement_document.py:508`
`set_requirement_version_index_result` | `SetRequirementVersionIndexResult` | method | `backend/testing/src/repositories/requirement_document.py:517`
`project_authority_order` | `ProjectAuthorityOrder` | method | `backend/testing/src/repositories/requirement_document.py:531`
`release_exists` | `ReleaseExists` | method | `backend/testing/src/repositories/requirement_document.py:536`
`find_source_document` | `FindSourceDocument` | method | `backend/testing/src/repositories/requirement_import.py:7`
`find_by_template_version` | `FindByTemplateVersion` | method | `backend/testing/src/repositories/requirement_import.py:11`
`find_by_source_document` | `FindBySourceDocument` | method | `backend/testing/src/repositories/requirement_import.py:15`
`find` | `Find` | method | `backend/testing/src/repositories/requirement_import.py:20`
`list_current_requirements` | `ListCurrentRequirements` | method | `backend/testing/src/repositories/requirement_import.py:25`
`find_current_version` | `FindCurrentVersion` | method | `backend/testing/src/repositories/requirement_import.py:37`
`list_linked_test_cases` | `ListLinkedTestCases` | method | `backend/testing/src/repositories/requirement_import.py:42`
`insert` | `Insert` | method | `backend/testing/src/repositories/requirement_import.py:59`
`mark_document_extracted` | `MarkDocumentExtracted` | method | `backend/testing/src/repositories/requirement_import.py:62`
`update_preview` | `UpdatePreview` | method | `backend/testing/src/repositories/requirement_import.py:92`
`refresh_unreviewed_preview` | `RefreshUnreviewedPreview` | method | `backend/testing/src/repositories/requirement_import.py:128`
`finish_resolution` | `FinishResolution` | method | `backend/testing/src/repositories/requirement_import.py:150`
`claim_confirmation` | `ClaimConfirmation` | method | `backend/testing/src/repositories/requirement_import.py:182`
`reset_confirmation` | `ResetConfirmation` | method | `backend/testing/src/repositories/requirement_import.py:208`
`confirm` | `Confirm` | method | `backend/testing/src/repositories/requirement_import.py:219`
`confirm_document` | `ConfirmDocument` | method | `backend/testing/src/repositories/requirement_import.py:254`
`blocks` | `Blocks` | method | `backend/testing/src/repositories/requirement_source_block.py:8`
`block_id` | `BlockId` | method | `backend/testing/src/repositories/requirement_source_block.py:12`
`replace_version` | `ReplaceVersion` | method | `backend/testing/src/repositories/requirement_source_block.py:16`
`list_version` | `ListVersion` | method | `backend/testing/src/repositories/requirement_source_block.py:47`
`page_version` | `PageVersion` | method | `backend/testing/src/repositories/requirement_source_block.py:60`
`delete_version` | `DeleteVersion` | method | `backend/testing/src/repositories/requirement_source_block.py:79`
`delete_obsolete_versions` | `DeleteObsoleteVersions` | method | `backend/testing/src/repositories/requirement_source_block.py:90`
`list_visible` | `ListVisible` | method | `backend/testing/src/repositories/requirement_template.py:7`
`find` | `Find` | method | `backend/testing/src/repositories/requirement_template.py:12`
`insert` | `Insert` | method | `backend/testing/src/repositories/requirement_template.py:15`
`save_version` | `SaveVersion` | method | `backend/testing/src/repositories/requirement_template.py:20`
`list_versions` | `ListVersions` | method | `backend/testing/src/repositories/requirement_template.py:33`
`find_version` | `FindVersion` | method | `backend/testing/src/repositories/requirement_template.py:39`
`update` | `Update` | method | `backend/testing/src/repositories/requirement_template.py:44`
`update_state` | `UpdateState` | method | `backend/testing/src/repositories/requirement_template.py:54`
`list_fields` | `ListFields` | method | `backend/testing/src/repositories/requirement_template.py:61`
`insert_field` | `InsertField` | method | `backend/testing/src/repositories/requirement_template.py:66`
`comments` | `Comments` | method | `backend/testing/src/repositories/review.py:8`
`find_comment` | `FindComment` | method | `backend/testing/src/repositories/review.py:11`
`insert_comment` | `InsertComment` | method | `backend/testing/src/repositories/review.py:16`
`list_comments` | `ListComments` | method | `backend/testing/src/repositories/review.py:20`
`update_comment` | `UpdateComment` | method | `backend/testing/src/repositories/review.py:23`
`mark_comment_deleted` | `MarkCommentDeleted` | method | `backend/testing/src/repositories/review.py:30`
`transition_comment` | `TransitionComment` | method | `backend/testing/src/repositories/review.py:36`
`count_active_members` | `CountActiveMembers` | method | `backend/testing/src/repositories/review.py:53`
`find_artifact` | `FindArtifact` | method | `backend/testing/src/repositories/review.py:58`
`next_sequence` | `NextSequence` | method | `backend/testing/src/repositories/review.py:63`
`list_conditions` | `ListConditions` | method | `backend/testing/src/repositories/test_analysis.py:7`
`list_findings` | `ListFindings` | method | `backend/testing/src/repositories/test_analysis.py:12`
`find_basis` | `FindBasis` | method | `backend/testing/src/repositories/test_analysis.py:17`
`insert_finding` | `InsertFinding` | method | `backend/testing/src/repositories/test_analysis.py:22`
`find_finding` | `FindFinding` | method | `backend/testing/src/repositories/test_analysis.py:26`
`find_active_member` | `FindActiveMember` | method | `backend/testing/src/repositories/test_analysis.py:29`
`update_finding` | `UpdateFinding` | method | `backend/testing/src/repositories/test_analysis.py:34`
`merge` | `Merge` | method | `backend/testing/src/repositories/test_case_review.py:8`
`find_decision` | `FindDecision` | method | `backend/testing/src/repositories/test_case_review.py:53`
`commit` | `Commit` | method | `backend/testing/src/repositories/test_case_review.py:9`
`collection` | `Collection` | method | `backend/testing/src/repositories/test_condition.py:8`
`create` | `Create` | method | `backend/testing/src/repositories/test_condition.py:11`
`get` | `Get` | method | `backend/testing/src/repositories/test_condition.py:15`
`list` | `List` | method | `backend/testing/src/repositories/test_condition.py:21`
`update` | `Update` | method | `backend/testing/src/repositories/test_condition.py:32`
`list_cases` | `ListCases` | method | `backend/testing/src/repositories/test_design.py:7`
`list_cases_linked_to_requirement` | `ListCasesLinkedToRequirement` | method | `backend/testing/src/repositories/test_design.py:13`
`list_case_versions_linked_to_requirements` | `ListCaseVersionsLinkedToRequirements` | method | `backend/testing/src/repositories/test_design.py:44`
`list_cases_by_ids` | `ListCasesByIds` | method | `backend/testing/src/repositories/test_design.py:64`
`list_case_versions_by_ids` | `ListCaseVersionsByIds` | method | `backend/testing/src/repositories/test_design.py:72`
`list_confirmed_case_traces` | `ListConfirmedCaseTraces` | method | `backend/testing/src/repositories/test_design.py:77`
`list_case_results` | `ListCaseResults` | method | `backend/testing/src/repositories/test_design.py:83`
`find_defect` | `FindDefect` | method | `backend/testing/src/repositories/test_design.py:92`
`find_suite` | `FindSuite` | method | `backend/testing/src/repositories/test_design.py:95`
`list_requirement_version_ids` | `ListRequirementVersionIds` | method | `backend/testing/src/repositories/test_design.py:100`
`list_case_drafts` | `ListCaseDrafts` | method | `backend/testing/src/repositories/test_design.py:108`
`iter_case_draft_pages` | `IterCaseDraftPages` | method | `backend/testing/src/repositories/test_design.py:118`
`list_related_case_drafts` | `ListRelatedCaseDrafts` | method | `backend/testing/src/repositories/test_design.py:132`
`list_versions_for_case` | `ListVersionsForCase` | method | `backend/testing/src/repositories/test_design.py:138`
`list_selected_case_versions` | `ListSelectedCaseVersions` | method | `backend/testing/src/repositories/test_design.py:145`
`set_case_lifecycle_status` | `SetCaseLifecycleStatus` | method | `backend/testing/src/repositories/test_design.py:154`
`insert_ai_finding` | `InsertAiFinding` | method | `backend/testing/src/repositories/test_design.py:163`
`find_latest_test_draft_lint` | `FindLatestTestDraftLint` | method | `backend/testing/src/repositories/test_design.py:166`
`find_case_draft` | `FindCaseDraft` | method | `backend/testing/src/repositories/test_design.py:182`
`transition_case_draft` | `TransitionCaseDraft` | method | `backend/testing/src/repositories/test_design.py:187`
`find_case_version` | `FindCaseVersion` | method | `backend/testing/src/repositories/test_design.py:201`
`find_case` | `FindCase` | method | `backend/testing/src/repositories/test_design.py:206`
`find_case_by_key` | `FindCaseByKey` | method | `backend/testing/src/repositories/test_design.py:211`
`set_case_version_approval_result` | `SetCaseVersionApprovalResult` | method | `backend/testing/src/repositories/test_design.py:216`
`find_trace_link` | `FindTraceLink` | method | `backend/testing/src/repositories/test_design.py:243`
`insert_trace_link` | `InsertTraceLink` | method | `backend/testing/src/repositories/test_design.py:246`
`count_requirement_versions` | `CountRequirementVersions` | method | `backend/testing/src/repositories/test_design.py:249`
`count_acceptance_criteria` | `CountAcceptanceCriteria` | method | `backend/testing/src/repositories/test_design.py:254`
`list_acceptance_criteria_by_ids` | `ListAcceptanceCriteriaByIds` | method | `backend/testing/src/repositories/test_design.py:257`
`find_project_settings` | `FindProjectSettings` | method | `backend/testing/src/repositories/test_design.py:266`
`find_current_requirement` | `FindCurrentRequirement` | method | `backend/testing/src/repositories/test_design.py:272`
`list_conditions` | `ListConditions` | method | `backend/testing/src/repositories/test_design.py:278`
`insert_case_draft` | `InsertCaseDraft` | method | `backend/testing/src/repositories/test_design.py:283`
`list_requirement_versions` | `ListRequirementVersions` | method | `backend/testing/src/repositories/test_design.py:289`
`list_case_versions` | `ListCaseVersions` | method | `backend/testing/src/repositories/test_design.py:292`
`list_trace_links` | `ListTraceLinks` | method | `backend/testing/src/repositories/test_design.py:304`
`insert_trace_links` | `InsertTraceLinks` | method | `backend/testing/src/repositories/test_design.py:307`
`insert_import` | `InsertImport` | method | `backend/testing/src/repositories/test_design.py:312`
`upsert_import_once` | `UpsertImportOnce` | method | `backend/testing/src/repositories/test_design.py:316`
`find_import` | `FindImport` | method | `backend/testing/src/repositories/test_design.py:327`
`list_imports` | `ListImports` | method | `backend/testing/src/repositories/test_design.py:332`
`claim_import` | `ClaimImport` | method | `backend/testing/src/repositories/test_design.py:336`
`reset_import` | `ResetImport` | method | `backend/testing/src/repositories/test_design.py:343`
`confirm_import` | `ConfirmImport` | method | `backend/testing/src/repositories/test_design.py:349`
`list_requirement_evidence` | `ListRequirementEvidence` | method | `backend/testing/src/repositories/test_design.py:356`
`list_security_suggestions` | `ListSecuritySuggestions` | method | `backend/testing/src/repositories/test_design.py:361`
`find_security_suggestion` | `FindSecuritySuggestion` | method | `backend/testing/src/repositories/test_design.py:366`
`insert_security_suggestion` | `InsertSecuritySuggestion` | method | `backend/testing/src/repositories/test_design.py:371`
`list_performance_drafts` | `ListPerformanceDrafts` | method | `backend/testing/src/repositories/test_design.py:375`
`find_performance_draft` | `FindPerformanceDraft` | method | `backend/testing/src/repositories/test_design.py:380`
`insert_performance_draft` | `InsertPerformanceDraft` | method | `backend/testing/src/repositories/test_design.py:385`
`list_acceptance_criteria` | `ListAcceptanceCriteria` | method | `backend/testing/src/repositories/test_design.py:389`
`insert_suite` | `InsertSuite` | method | `backend/testing/src/repositories/test_design.py:397`
`list_suites` | `ListSuites` | method | `backend/testing/src/repositories/test_design.py:401`
`list_templates` | `ListTemplates` | method | `backend/testing/src/repositories/test_design.py:406`
`insert_template` | `InsertTemplate` | method | `backend/testing/src/repositories/test_design.py:411`
`update_template` | `UpdateTemplate` | method | `backend/testing/src/repositories/test_design.py:415`
`artifact_exists` | `ArtifactExists` | method | `backend/testing/src/repositories/test_design.py:429`
`find_active_attachment` | `FindActiveAttachment` | method | `backend/testing/src/repositories/test_design.py:437`
`insert_attachment` | `InsertAttachment` | method | `backend/testing/src/repositories/test_design.py:452`
`list_attachments` | `ListAttachments` | method | `backend/testing/src/repositories/test_design.py:456`
`mark_attachment_deleted` | `MarkAttachmentDeleted` | method | `backend/testing/src/repositories/test_design.py:461`
`count_requirement_versions` | `CountRequirementVersions` | method | `backend/testing/src/repositories/test_plan.py:5`
`list_suites` | `ListSuites` | method | `backend/testing/src/repositories/test_plan.py:10`
`count_test_case_versions` | `CountTestCaseVersions` | method | `backend/testing/src/repositories/test_plan.py:15`
`insert_plan` | `InsertPlan` | method | `backend/testing/src/repositories/test_plan.py:19`
`list_plans` | `ListPlans` | method | `backend/testing/src/repositories/test_plan.py:25`
`find_project_settings` | `FindProjectSettings` | method | `backend/testing/src/repositories/test_plan.py:30`
`find_plan` | `FindPlan` | method | `backend/testing/src/repositories/test_plan_progress.py:5`
`list_runs` | `ListRuns` | method | `backend/testing/src/repositories/test_plan_progress.py:10`
`list_results` | `ListResults` | method | `backend/testing/src/repositories/test_plan_progress.py:15`
`list_defects` | `ListDefects` | method | `backend/testing/src/repositories/test_plan_progress.py:22`
`find_plan` | `FindPlan` | method | `backend/testing/src/repositories/test_run.py:7`
`list_suites` | `ListSuites` | method | `backend/testing/src/repositories/test_run.py:13`
`insert_run` | `InsertRun` | method | `backend/testing/src/repositories/test_run.py:18`
`find_run_by_idempotency_key` | `FindRunByIdempotencyKey` | method | `backend/testing/src/repositories/test_run.py:22`
`find_rerun_by_key` | `FindRerunByKey` | method | `backend/testing/src/repositories/test_run.py:27`
`insert_results` | `InsertResults` | method | `backend/testing/src/repositories/test_run.py:37`
`count_runs` | `CountRuns` | method | `backend/testing/src/repositories/test_run.py:42`
`list_runs` | `ListRuns` | method | `backend/testing/src/repositories/test_run.py:45`
`count_recorded_results_by_run` | `CountRecordedResultsByRun` | method | `backend/testing/src/repositories/test_run.py:50`
`list_results` | `ListResults` | method | `backend/testing/src/repositories/test_run.py:60`
`delete_results_for_versions` | `DeleteResultsForVersions` | method | `backend/testing/src/repositories/test_run.py:68`
`list_versions` | `ListVersions` | method | `backend/testing/src/repositories/test_run.py:81`
`list_defects_for_results` | `ListDefectsForResults` | method | `backend/testing/src/repositories/test_run.py:86`
`find_environment` | `FindEnvironment` | method | `backend/testing/src/repositories/test_run.py:94`
`transition_run` | `TransitionRun` | method | `backend/testing/src/repositories/test_run.py:99`
`find_resume_event` | `FindResumeEvent` | method | `backend/testing/src/repositories/test_run.py:107`
`insert_resume_event` | `InsertResumeEvent` | method | `backend/testing/src/repositories/test_run.py:113`
`find_result_for_case` | `FindResultForCase` | method | `backend/testing/src/repositories/test_run.py:117`
`update_result` | `UpdateResult` | method | `backend/testing/src/repositories/test_run.py:122`
`insert_result` | `InsertResult` | method | `backend/testing/src/repositories/test_run.py:133`
`touch_run` | `TouchRun` | method | `backend/testing/src/repositories/test_run.py:139`
`find_execution_update` | `FindExecutionUpdate` | method | `backend/testing/src/repositories/test_run.py:163`
`insert_execution_update` | `InsertExecutionUpdate` | method | `backend/testing/src/repositories/test_run.py:169`
`find_result` | `FindResult` | method | `backend/testing/src/repositories/test_run.py:175`
`find_run` | `FindRun` | method | `backend/testing/src/repositories/test_run.py:178`
`find_correction` | `FindCorrection` | method | `backend/testing/src/repositories/test_run.py:186`
`insert_correction` | `InsertCorrection` | method | `backend/testing/src/repositories/test_run.py:192`
`count_results_by_status` | `CountResultsByStatus` | method | `backend/testing/src/repositories/test_run.py:198`
`project_settings` | `ProjectSettings` | method | `backend/testing/src/repositories/test_run.py:203`
`update_run` | `UpdateRun` | method | `backend/testing/src/repositories/test_run.py:208`
`iter_active_runs_for_members` | `IterActiveRunsForMembers` | method | `backend/testing/src/repositories/test_run.py:222`
`artifact_exists` | `ArtifactExists` | method | `backend/testing/src/repositories/traceability.py:7`
`find_link` | `FindLink` | method | `backend/testing/src/repositories/traceability.py:14`
`insert_link` | `InsertLink` | method | `backend/testing/src/repositories/traceability.py:17`
`transition_link` | `TransitionLink` | method | `backend/testing/src/repositories/traceability.py:20`
`count_links` | `CountLinks` | method | `backend/testing/src/repositories/traceability.py:27`
`list_records` | `ListRecords` | method | `backend/testing/src/repositories/traceability.py:30`
`count_records` | `CountRecords` | method | `backend/testing/src/repositories/traceability.py:36`
`find_snapshot` | `FindSnapshot` | method | `backend/testing/src/repositories/traceability.py:39`
`insert_snapshot` | `InsertSnapshot` | method | `backend/testing/src/repositories/traceability.py:44`
`ProjectWorkspacePage` | `GD_ProjectWorkspacePage` | page/boundary | `frontend/app/(main)/du-an/[projectId]/[[...section]]/page.jsx`
`ProjectsPage` | `GD_ProjectsPage` | page/boundary | `frontend/app/(main)/du-an/page.jsx`
`ProjectCreatePage` | `GD_ProjectCreatePage` | page/boundary | `frontend/app/(main)/du-an/tao-moi/page.jsx`
`OperationsPage` | `GD_OperationsPage` | page/boundary | `frontend/app/(main)/van-hanh/page.jsx`
`health` | `Ctrl_Main` | route method in grouped control | `backend/testing/src/main.py:258`
`ready` | `Ctrl_Main` | route method in grouped control | `backend/testing/src/main.py:263`
`list_templates` | `Ctrl_Templates` | route method in grouped control | `backend/testing/src/modules/design/api/templates.py:17`
`get_template` | `Ctrl_Templates` | route method in grouped control | `backend/testing/src/modules/design/api/templates.py:26`
`create_template` | `Ctrl_Templates` | route method in grouped control | `backend/testing/src/modules/design/api/templates.py:35`
`update_template` | `Ctrl_Templates` | route method in grouped control | `backend/testing/src/modules/design/api/templates.py:43`
`archive_template` | `Ctrl_Templates` | route method in grouped control | `backend/testing/src/modules/design/api/templates.py:53`
`list_test_conditions` | `Ctrl_TestAnalysis` | route method in grouped control | `backend/testing/src/modules/design/api/test_analysis.py:38`
`create_test_condition` | `Ctrl_TestAnalysis` | route method in grouped control | `backend/testing/src/modules/design/api/test_analysis.py:56`
`get_test_condition` | `Ctrl_TestAnalysis` | route method in grouped control | `backend/testing/src/modules/design/api/test_analysis.py:64`
`clone_test_condition` | `Ctrl_TestAnalysis` | route method in grouped control | `backend/testing/src/modules/design/api/test_analysis.py:70`
`patch_test_condition` | `Ctrl_TestAnalysis` | route method in grouped control | `backend/testing/src/modules/design/api/test_analysis.py:76`
`submit_test_condition_review` | `Ctrl_TestAnalysis` | route method in grouped control | `backend/testing/src/modules/design/api/test_analysis.py:84`
`approve_test_condition` | `Ctrl_TestAnalysis` | route method in grouped control | `backend/testing/src/modules/design/api/test_analysis.py:94`
`review_test_condition` | `Ctrl_TestAnalysis` | route method in grouped control | `backend/testing/src/modules/design/api/test_analysis.py:104`
`archive_test_condition` | `Ctrl_TestAnalysis` | route method in grouped control | `backend/testing/src/modules/design/api/test_analysis.py:114`
`resolve_test_analysis_finding` | `Ctrl_TestAnalysis` | route method in grouped control | `backend/testing/src/modules/design/api/test_analysis.py:124`
`list_test_analysis_basis` | `Ctrl_TestAnalysis` | route method in grouped control | `backend/testing/src/modules/design/api/test_analysis.py:135`
`run_deterministic_test_analysis` | `Ctrl_TestAnalysis` | route method in grouped control | `backend/testing/src/modules/design/api/test_analysis.py:146`
`list_test_analysis_findings` | `Ctrl_TestAnalysis` | route method in grouped control | `backend/testing/src/modules/design/api/test_analysis.py:153`
`create_test_analysis_finding` | `Ctrl_TestAnalysis` | route method in grouped control | `backend/testing/src/modules/design/api/test_analysis.py:165`
`assign_test_analysis_finding` | `Ctrl_TestAnalysis` | route method in grouped control | `backend/testing/src/modules/design/api/test_analysis.py:173`
`resolve_standalone_test_analysis_finding` | `Ctrl_TestAnalysis` | route method in grouped control | `backend/testing/src/modules/design/api/test_analysis.py:183`
`verify_test_analysis_finding` | `Ctrl_TestAnalysis` | route method in grouped control | `backend/testing/src/modules/design/api/test_analysis.py:193`
`bulk_prioritize_test_conditions` | `Ctrl_TestAnalysis` | route method in grouped control | `backend/testing/src/modules/design/api/test_analysis.py:203`
`get_coverage_source_items` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:62`
`compare_test_case_draft` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:69`
`save_test_case_merge` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:76`
`accept_test_case_draft_group` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:83`
`create_test_case_draft` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:92`
`create_test_case_draft` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:92`
`create_generated_test_case_batch` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:100`
`list_test_case_drafts` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:119`
`get_test_case_draft` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:138`
`delete_test_case_draft` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:143`
`get_test_case` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:148`
`get_test_case_version_by_id` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:153`
`update_test_case_draft` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:161`
`update_test_case_draft` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:161`
`update_test_case_draft` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:161`
`lint_test_case_draft` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:174`
`lint_test_case_draft` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:174`
`lint_test_case_draft` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:174`
`get_latest_test_case_draft_lint_result` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:184`
`submit_test_case_review` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:191`
`submit_test_case_review_alias` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:202`
`request_test_case_changes` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:210`
`freeze_test_case_draft` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:221`
`approve_test_case` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:233`
`approve_test_case_alias` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:246`
`list_test_cases` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:254`
`clone_test_case` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:299`
`list_test_case_versions` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:306`
`create_test_case_version_draft` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:311`
`diff_test_case_versions` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:321`
`mark_test_case_obsolete` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:335`
`restore_test_case` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:344`
`generate_test_cases` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:353`
`recommend_techniques` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:360`
`generate_project_test_cases` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:369`
`find_duplicates` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:392`
`compare_draft_batch` | `Ctrl_TestDesign` | route method in grouped control | `backend/testing/src/modules/design/api/test_design.py:409`
`create_test_plan` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:97`
`create_test_plan` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:97`
`suggest_test_plan` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:107`
`list_test_plans` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:116`
`get_test_plan` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:139`
`validate_test_plan` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:144`
`update_test_plan` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:149`
`submit_test_plan` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:157`
`approve_test_plan` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:165`
`archive_test_plan` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:173`
`revise_test_plan` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:181`
`clone_test_plan` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:187`
`create_test_suite` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:194`
`create_test_suite` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:194`
`list_test_suites` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:204`
`get_test_suite` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:225`
`update_test_suite` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:230`
`clone_test_suite` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:238`
`archive_test_suite` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:244`
`create_test_run` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:253`
`create_test_run` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:253`
`update_test_run` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:263`
`rerun_test_run` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:274`
`assign_test_run` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:285`
`list_test_runs` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:296`
`list_test_results` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:337`
`get_test_result` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:346`
`link_test_result_defect` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:351`
`get_execution_assistance` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:364`
`create_execution_assistance` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:376`
`get_test_run` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:386`
`export_test_run_report` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:391`
`start_test_run` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:401`
`resume_test_run` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:410`
`record_test_result` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:421`
`patch_test_execution` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:432`
`correct_test_result` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:443`
`complete_test_run` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:452`
`abort_test_run` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:457`
`create_defect` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:466`
`get_defect_classification_options` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:474`
`list_defects` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:481`
`find_duplicate_defects` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:530`
`export_defects` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:536`
`defect_detail` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:547`
`defect_detail` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:547`
`suggest_defect_trace` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:555`
`list_automated_defect_trace_suggestions` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:565`
`find_defect_trace_candidates` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:574`
`update_defect_trace` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:581`
`update_defect` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:593`
`update_defect` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:593`
`transition_defect` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:604`
`retest_defect` | `Ctrl_Execution` | route method in grouped control | `backend/testing/src/modules/execution/api/execution.py:612`
`list_releases` | `Ctrl_ExecutionContext` | route method in grouped control | `backend/testing/src/modules/execution/api/execution_context.py:20`
`get_release` | `Ctrl_ExecutionContext` | route method in grouped control | `backend/testing/src/modules/execution/api/execution_context.py:29`
`release_close_readiness` | `Ctrl_ExecutionContext` | route method in grouped control | `backend/testing/src/modules/execution/api/execution_context.py:35`
`create_release` | `Ctrl_ExecutionContext` | route method in grouped control | `backend/testing/src/modules/execution/api/execution_context.py:41`
`update_release` | `Ctrl_ExecutionContext` | route method in grouped control | `backend/testing/src/modules/execution/api/execution_context.py:47`
`activate_release` | `Ctrl_ExecutionContext` | route method in grouped control | `backend/testing/src/modules/execution/api/execution_context.py:53`
`close_release` | `Ctrl_ExecutionContext` | route method in grouped control | `backend/testing/src/modules/execution/api/execution_context.py:61`
`archive_release` | `Ctrl_ExecutionContext` | route method in grouped control | `backend/testing/src/modules/execution/api/execution_context.py:69`
`list_builds` | `Ctrl_ExecutionContext` | route method in grouped control | `backend/testing/src/modules/execution/api/execution_context.py:77`
`get_build` | `Ctrl_ExecutionContext` | route method in grouped control | `backend/testing/src/modules/execution/api/execution_context.py:86`
`create_build` | `Ctrl_ExecutionContext` | route method in grouped control | `backend/testing/src/modules/execution/api/execution_context.py:92`
`update_build` | `Ctrl_ExecutionContext` | route method in grouped control | `backend/testing/src/modules/execution/api/execution_context.py:98`
`set_current_build` | `Ctrl_ExecutionContext` | route method in grouped control | `backend/testing/src/modules/execution/api/execution_context.py:104`
`list_environments` | `Ctrl_ExecutionContext` | route method in grouped control | `backend/testing/src/modules/execution/api/execution_context.py:110`
`get_environment` | `Ctrl_ExecutionContext` | route method in grouped control | `backend/testing/src/modules/execution/api/execution_context.py:115`
`create_environment` | `Ctrl_ExecutionContext` | route method in grouped control | `backend/testing/src/modules/execution/api/execution_context.py:121`
`update_environment` | `Ctrl_ExecutionContext` | route method in grouped control | `backend/testing/src/modules/execution/api/execution_context.py:127`
`archive_environment` | `Ctrl_ExecutionContext` | route method in grouped control | `backend/testing/src/modules/execution/api/execution_context.py:133`
`get_plan_progress` | `Ctrl_PlanProgress` | route method in grouped control | `backend/testing/src/modules/execution/api/plan_progress.py:11`
`preview` | `Ctrl_SimpleReports` | route method in grouped control | `backend/testing/src/modules/execution/api/simple_reports.py:257`
`live_report` | `Ctrl_SimpleReports` | route method in grouped control | `backend/testing/src/modules/execution/api/simple_reports.py:264`
`export_live_report` | `Ctrl_SimpleReports` | route method in grouped control | `backend/testing/src/modules/execution/api/simple_reports.py:274`
`create` | `Ctrl_SimpleReports` | route method in grouped control | `backend/testing/src/modules/execution/api/simple_reports.py:318`
`list_reports` | `Ctrl_SimpleReports` | route method in grouped control | `backend/testing/src/modules/execution/api/simple_reports.py:343`
`get_report` | `Ctrl_SimpleReports` | route method in grouped control | `backend/testing/src/modules/execution/api/simple_reports.py:360`
`export` | `Ctrl_SimpleReports` | route method in grouped control | `backend/testing/src/modules/execution/api/simple_reports.py:373`
`list_test_periods` | `Ctrl_TestPeriods` | route method in grouped control | `backend/testing/src/modules/execution/api/test_periods.py:19`
`create_test_period` | `Ctrl_TestPeriods` | route method in grouped control | `backend/testing/src/modules/execution/api/test_periods.py:24`
`get_test_period` | `Ctrl_TestPeriods` | route method in grouped control | `backend/testing/src/modules/execution/api/test_periods.py:31`
`test_period_summary` | `Ctrl_TestPeriods` | route method in grouped control | `backend/testing/src/modules/execution/api/test_periods.py:36`
`close_test_period` | `Ctrl_TestPeriods` | route method in grouped control | `backend/testing/src/modules/execution/api/test_periods.py:41`
`update_test_period` | `Ctrl_TestPeriods` | route method in grouped control | `backend/testing/src/modules/execution/api/test_periods.py:51`
`list_api_artifacts` | `Ctrl_ApiArtifacts` | route method in grouped control | `backend/testing/src/modules/integrations/api/api_artifacts.py:19`
`get_api_artifact` | `Ctrl_ApiArtifacts` | route method in grouped control | `backend/testing/src/modules/integrations/api/api_artifacts.py:28`
`import_api_artifact` | `Ctrl_ApiArtifacts` | route method in grouped control | `backend/testing/src/modules/integrations/api/api_artifacts.py:40`
`review_api_artifact` | `Ctrl_ApiArtifacts` | route method in grouped control | `backend/testing/src/modules/integrations/api/api_artifacts.py:52`
`confirm_api_artifact` | `Ctrl_ApiArtifacts` | route method in grouped control | `backend/testing/src/modules/integrations/api/api_artifacts.py:64`
`list_api_operations` | `Ctrl_ApiArtifacts` | route method in grouped control | `backend/testing/src/modules/integrations/api/api_artifacts.py:76`
`get_api_operation` | `Ctrl_ApiArtifacts` | route method in grouped control | `backend/testing/src/modules/integrations/api/api_artifacts.py:84`
`generate_api_tests` | `Ctrl_ApiArtifacts` | route method in grouped control | `backend/testing/src/modules/integrations/api/api_artifacts.py:96`
`get_test_import_preview` | `Ctrl_ApiArtifacts` | route method in grouped control | `backend/testing/src/modules/integrations/api/api_artifacts.py:104`
`diff_api_artifacts` | `Ctrl_ApiArtifacts` | route method in grouped control | `backend/testing/src/modules/integrations/api/api_artifacts.py:115`
`analyze_api_artifact_impact` | `Ctrl_ApiArtifacts` | route method in grouped control | `backend/testing/src/modules/integrations/api/api_artifacts.py:134`
`archive_api_artifact` | `Ctrl_ApiArtifacts` | route method in grouped control | `backend/testing/src/modules/integrations/api/api_artifacts.py:146`
`recover_trace_links` | `Ctrl_ApiArtifacts` | route method in grouped control | `backend/testing/src/modules/integrations/api/api_artifacts.py:155`
`preview_test_import` | `Ctrl_ApiArtifacts` | route method in grouped control | `backend/testing/src/modules/integrations/api/api_artifacts.py:163`
`upload_test_import` | `Ctrl_ApiArtifacts` | route method in grouped control | `backend/testing/src/modules/integrations/api/api_artifacts.py:172`
`confirm_test_import` | `Ctrl_ApiArtifacts` | route method in grouped control | `backend/testing/src/modules/integrations/api/api_artifacts.py:182`
`export_test_cases` | `Ctrl_ApiArtifacts` | route method in grouped control | `backend/testing/src/modules/integrations/api/api_artifacts.py:191`
`list_automation_script_drafts` | `Ctrl_AutomationScripts` | route method in grouped control | `backend/testing/src/modules/integrations/api/automation_scripts.py:17`
`get_automation_script_draft` | `Ctrl_AutomationScripts` | route method in grouped control | `backend/testing/src/modules/integrations/api/automation_scripts.py:24`
`generate_automation_script_draft` | `Ctrl_AutomationScripts` | route method in grouped control | `backend/testing/src/modules/integrations/api/automation_scripts.py:32`
`update_automation_script_draft` | `Ctrl_AutomationScripts` | route method in grouped control | `backend/testing/src/modules/integrations/api/automation_scripts.py:42`
`approve_automation_script_draft` | `Ctrl_AutomationScripts` | route method in grouped control | `backend/testing/src/modules/integrations/api/automation_scripts.py:52`
`export_automation_script_draft` | `Ctrl_AutomationScripts` | route method in grouped control | `backend/testing/src/modules/integrations/api/automation_scripts.py:62`
`list_junit` | `Ctrl_JunitImport` | route method in grouped control | `backend/testing/src/modules/integrations/api/junit_import.py:16`
`import_junit` | `Ctrl_JunitImport` | route method in grouped control | `backend/testing/src/modules/integrations/api/junit_import.py:21`
`resolve_junit` | `Ctrl_JunitImport` | route method in grouped control | `backend/testing/src/modules/integrations/api/junit_import.py:27`
`bulk_tags` | `Ctrl_Bulk` | route method in grouped control | `backend/testing/src/modules/operations/api/bulk.py:17`
`bulk_add_to_suite` | `Ctrl_Bulk` | route method in grouped control | `backend/testing/src/modules/operations/api/bulk.py:24`
`bulk_mark_review_required` | `Ctrl_Bulk` | route method in grouped control | `backend/testing/src/modules/operations/api/bulk.py:31`
`bulk_archive` | `Ctrl_Bulk` | route method in grouped control | `backend/testing/src/modules/operations/api/bulk.py:40`
`user_memberships` | `Ctrl_InternalAdmin` | route method in grouped control | `backend/testing/src/modules/operations/api/internal_admin.py:22`
`projects` | `Ctrl_InternalAdmin` | route method in grouped control | `backend/testing/src/modules/operations/api/internal_admin.py:27`
`project` | `Ctrl_InternalAdmin` | route method in grouped control | `backend/testing/src/modules/operations/api/internal_admin.py:36`
`change_project_status` | `Ctrl_InternalAdmin` | route method in grouped control | `backend/testing/src/modules/operations/api/internal_admin.py:41`
`change_project_quota` | `Ctrl_InternalAdmin` | route method in grouped control | `backend/testing/src/modules/operations/api/internal_admin.py:46`
`project_memberships` | `Ctrl_InternalAdmin` | route method in grouped control | `backend/testing/src/modules/operations/api/internal_admin.py:51`
`delete_project` | `Ctrl_InternalAdmin` | route method in grouped control | `backend/testing/src/modules/operations/api/internal_admin.py:56`
`break_glass_grants` | `Ctrl_InternalAdmin` | route method in grouped control | `backend/testing/src/modules/operations/api/internal_admin.py:61`
`create_break_glass_grant` | `Ctrl_InternalAdmin` | route method in grouped control | `backend/testing/src/modules/operations/api/internal_admin.py:66`
`revoke_break_glass_grant` | `Ctrl_InternalAdmin` | route method in grouped control | `backend/testing/src/modules/operations/api/internal_admin.py:71`
`operations_metrics` | `Ctrl_InternalAdmin` | route method in grouped control | `backend/testing/src/modules/operations/api/internal_admin.py:76`
`rag_status` | `Ctrl_InternalAdmin` | route method in grouped control | `backend/testing/src/modules/operations/api/internal_admin.py:81`
`reindex_candidates` | `Ctrl_InternalAdmin` | route method in grouped control | `backend/testing/src/modules/operations/api/internal_admin.py:86`
`storage_usage` | `Ctrl_InternalAdmin` | route method in grouped control | `backend/testing/src/modules/operations/api/internal_admin.py:91`
`revoke_ai_run_access` | `Ctrl_InternalJobs` | route method in grouped control | `backend/testing/src/modules/operations/api/internal_jobs.py:12`
`process_job` | `Ctrl_InternalJobs` | route method in grouped control | `backend/testing/src/modules/operations/api/internal_jobs.py:26`
`enqueue_job` | `Ctrl_Jobs` | route method in grouped control | `backend/testing/src/modules/operations/api/jobs.py:12`
`get_job` | `Ctrl_Jobs` | route method in grouped control | `backend/testing/src/modules/operations/api/jobs.py:21`
`list_notification_watches` | `Ctrl_Notifications` | route method in grouped control | `backend/testing/src/modules/operations/api/notifications.py:16`
`set_notification_watch` | `Ctrl_Notifications` | route method in grouped control | `backend/testing/src/modules/operations/api/notifications.py:25`
`get_project_notification_rules` | `Ctrl_Notifications` | route method in grouped control | `backend/testing/src/modules/operations/api/notifications.py:40`
`update_project_notification_rules` | `Ctrl_Notifications` | route method in grouped control | `backend/testing/src/modules/operations/api/notifications.py:48`
`get_project_notification_preferences` | `Ctrl_Notifications` | route method in grouped control | `backend/testing/src/modules/operations/api/notifications.py:58`
`update_project_notification_preferences` | `Ctrl_Notifications` | route method in grouped control | `backend/testing/src/modules/operations/api/notifications.py:66`
`operations` | `Ctrl_Operations` | route method in grouped control | `backend/testing/src/modules/operations/api/operations.py:11`
`retry_failed_job` | `Ctrl_Operations` | route method in grouped control | `backend/testing/src/modules/operations/api/operations.py:26`
`project_role_permissions` | `Ctrl_Access` | route method in grouped control | `backend/testing/src/modules/projects/api/access.py:17`
`update_project_role_permissions` | `Ctrl_Access` | route method in grouped control | `backend/testing/src/modules/projects/api/access.py:41`
`effective_project_access` | `Ctrl_Access` | route method in grouped control | `backend/testing/src/modules/projects/api/access.py:77`
`register_attachment` | `Ctrl_Attachments` | route method in grouped control | `backend/testing/src/modules/projects/api/attachments.py:15`
`list_attachments` | `Ctrl_Attachments` | route method in grouped control | `backend/testing/src/modules/projects/api/attachments.py:23`
`delete_attachment` | `Ctrl_Attachments` | route method in grouped control | `backend/testing/src/modules/projects/api/attachments.py:33`
`moderate_attachment` | `Ctrl_Attachments` | route method in grouped control | `backend/testing/src/modules/projects/api/attachments.py:39`
`update_collaboration_presence` | `Ctrl_Collaboration` | route method in grouped control | `backend/testing/src/modules/projects/api/collaboration.py:16`
`list_collaboration_presence` | `Ctrl_Collaboration` | route method in grouped control | `backend/testing/src/modules/projects/api/collaboration.py:25`
`apply_requirement_collaboration_operation` | `Ctrl_Collaboration` | route method in grouped control | `backend/testing/src/modules/projects/api/collaboration.py:39`
`apply_test_case_collaboration_operation` | `Ctrl_Collaboration` | route method in grouped control | `backend/testing/src/modules/projects/api/collaboration.py:51`
`list_collaboration_conflicts` | `Ctrl_Collaboration` | route method in grouped control | `backend/testing/src/modules/projects/api/collaboration.py:63`
`resolve_collaboration_conflict` | `Ctrl_Collaboration` | route method in grouped control | `backend/testing/src/modules/projects/api/collaboration.py:70`
`project_capabilities` | `Ctrl_Projects` | route method in grouped control | `backend/testing/src/modules/projects/api/projects.py:31`
`create_project` | `Ctrl_Projects` | route method in grouped control | `backend/testing/src/modules/projects/api/projects.py:39`
`list_projects` | `Ctrl_Projects` | route method in grouped control | `backend/testing/src/modules/projects/api/projects.py:51`
`list_project_invitations` | `Ctrl_Projects` | route method in grouped control | `backend/testing/src/modules/projects/api/projects.py:61`
`project_detail` | `Ctrl_Projects` | route method in grouped control | `backend/testing/src/modules/projects/api/projects.py:66`
`update_project` | `Ctrl_Projects` | route method in grouped control | `backend/testing/src/modules/projects/api/projects.py:71`
`update_project_progress` | `Ctrl_Projects` | route method in grouped control | `backend/testing/src/modules/projects/api/projects.py:79`
`read_project_settings` | `Ctrl_Projects` | route method in grouped control | `backend/testing/src/modules/projects/api/projects.py:94`
`update_project_settings` | `Ctrl_Projects` | route method in grouped control | `backend/testing/src/modules/projects/api/projects.py:103`
`archive_project` | `Ctrl_Projects` | route method in grouped control | `backend/testing/src/modules/projects/api/projects.py:111`
`restore_project` | `Ctrl_Projects` | route method in grouped control | `backend/testing/src/modules/projects/api/projects.py:121`
`list_project_members` | `Ctrl_Projects` | route method in grouped control | `backend/testing/src/modules/projects/api/projects.py:131`
`add_project_member` | `Ctrl_Projects` | route method in grouped control | `backend/testing/src/modules/projects/api/projects.py:136`
`invite_project_member` | `Ctrl_Projects` | route method in grouped control | `backend/testing/src/modules/projects/api/projects.py:146`
`accept_project_invitation_by_id` | `Ctrl_Projects` | route method in grouped control | `backend/testing/src/modules/projects/api/projects.py:159`
`accept_project_invitation` | `Ctrl_Projects` | route method in grouped control | `backend/testing/src/modules/projects/api/projects.py:167`
`decline_project_invitation` | `Ctrl_Projects` | route method in grouped control | `backend/testing/src/modules/projects/api/projects.py:180`
`leave_project` | `Ctrl_Projects` | route method in grouped control | `backend/testing/src/modules/projects/api/projects.py:188`
`resend_project_invitation` | `Ctrl_Projects` | route method in grouped control | `backend/testing/src/modules/projects/api/projects.py:194`
`cancel_project_invitation` | `Ctrl_Projects` | route method in grouped control | `backend/testing/src/modules/projects/api/projects.py:204`
`update_project_member` | `Ctrl_Projects` | route method in grouped control | `backend/testing/src/modules/projects/api/projects.py:214`
`remove_project_member` | `Ctrl_Projects` | route method in grouped control | `backend/testing/src/modules/projects/api/projects.py:225`
`search_project` | `Ctrl_Analytics` | route method in grouped control | `backend/testing/src/modules/quality/api/analytics.py:12`
`dashboard` | `Ctrl_Analytics` | route method in grouped control | `backend/testing/src/modules/quality/api/analytics.py:25`
`search_knowledge` | `Ctrl_Analytics` | route method in grouped control | `backend/testing/src/modules/quality/api/analytics.py:30`
`ask_project` | `Ctrl_Analytics` | route method in grouped control | `backend/testing/src/modules/quality/api/analytics.py:38`
`project_audit` | `Ctrl_Analytics` | route method in grouped control | `backend/testing/src/modules/quality/api/analytics.py:47`
`maintenance_analytics` | `Ctrl_Analytics` | route method in grouped control | `backend/testing/src/modules/quality/api/analytics.py:62`
`ai_analytics` | `Ctrl_Analytics` | route method in grouped control | `backend/testing/src/modules/quality/api/analytics.py:67`
`execution_report` | `Ctrl_Analytics` | route method in grouped control | `backend/testing/src/modules/quality/api/analytics.py:72`
`defect_report` | `Ctrl_Analytics` | route method in grouped control | `backend/testing/src/modules/quality/api/analytics.py:90`
`project_activity` | `Ctrl_Analytics` | route method in grouped control | `backend/testing/src/modules/quality/api/analytics.py:108`
`list_proposals` | `Ctrl_Changes` | route method in grouped control | `backend/testing/src/modules/quality/api/changes.py:19`
`get_maintenance_proposal` | `Ctrl_Changes` | route method in grouped control | `backend/testing/src/modules/quality/api/changes.py:53`
`review_project_proposal` | `Ctrl_Changes` | route method in grouped control | `backend/testing/src/modules/quality/api/changes.py:58`
`accept_proposal` | `Ctrl_Changes` | route method in grouped control | `backend/testing/src/modules/quality/api/changes.py:69`
`approve_project_proposal` | `Ctrl_Changes` | route method in grouped control | `backend/testing/src/modules/quality/api/changes.py:76`
`accept_proposal_with_edit` | `Ctrl_Changes` | route method in grouped control | `backend/testing/src/modules/quality/api/changes.py:94`
`reject_proposal` | `Ctrl_Changes` | route method in grouped control | `backend/testing/src/modules/quality/api/changes.py:103`
`reject_project_proposal` | `Ctrl_Changes` | route method in grouped control | `backend/testing/src/modules/quality/api/changes.py:110`
`regenerate_proposal` | `Ctrl_Changes` | route method in grouped control | `backend/testing/src/modules/quality/api/changes.py:123`
`create_review_comment` | `Ctrl_Reviews` | route method in grouped control | `backend/testing/src/modules/quality/api/reviews.py:16`
`list_review_comments` | `Ctrl_Reviews` | route method in grouped control | `backend/testing/src/modules/quality/api/reviews.py:23`
`update_review_comment` | `Ctrl_Reviews` | route method in grouped control | `backend/testing/src/modules/quality/api/reviews.py:36`
`delete_review_comment` | `Ctrl_Reviews` | route method in grouped control | `backend/testing/src/modules/quality/api/reviews.py:43`
`resolve_review_comment` | `Ctrl_Reviews` | route method in grouped control | `backend/testing/src/modules/quality/api/reviews.py:48`
`reopen_review_comment` | `Ctrl_Reviews` | route method in grouped control | `backend/testing/src/modules/quality/api/reviews.py:55`
`create_trace_link` | `Ctrl_Traceability` | route method in grouped control | `backend/testing/src/modules/quality/api/traceability.py:14`
`create_trace_link` | `Ctrl_Traceability` | route method in grouped control | `backend/testing/src/modules/quality/api/traceability.py:14`
`confirm_trace_link` | `Ctrl_Traceability` | route method in grouped control | `backend/testing/src/modules/quality/api/traceability.py:24`
`confirm_trace_link` | `Ctrl_Traceability` | route method in grouped control | `backend/testing/src/modules/quality/api/traceability.py:24`
`get_trace_link` | `Ctrl_Traceability` | route method in grouped control | `backend/testing/src/modules/quality/api/traceability.py:33`
`reject_trace_link` | `Ctrl_Traceability` | route method in grouped control | `backend/testing/src/modules/quality/api/traceability.py:39`
`reject_trace_link` | `Ctrl_Traceability` | route method in grouped control | `backend/testing/src/modules/quality/api/traceability.py:39`
`revoke_trace_link` | `Ctrl_Traceability` | route method in grouped control | `backend/testing/src/modules/quality/api/traceability.py:49`
`revoke_trace_link` | `Ctrl_Traceability` | route method in grouped control | `backend/testing/src/modules/quality/api/traceability.py:49`
`traceability` | `Ctrl_Traceability` | route method in grouped control | `backend/testing/src/modules/quality/api/traceability.py:58`
`coverage` | `Ctrl_Traceability` | route method in grouped control | `backend/testing/src/modules/quality/api/traceability.py:72`
`requirement_coverage` | `Ctrl_Traceability` | route method in grouped control | `backend/testing/src/modules/quality/api/traceability.py:88`
`list_coverage_snapshots` | `Ctrl_Traceability` | route method in grouped control | `backend/testing/src/modules/quality/api/traceability.py:95`
`create_coverage_snapshot` | `Ctrl_Traceability` | route method in grouped control | `backend/testing/src/modules/quality/api/traceability.py:104`
`test_case_trace` | `Ctrl_Traceability` | route method in grouped control | `backend/testing/src/modules/quality/api/traceability.py:113`
`export_traceability` | `Ctrl_Traceability` | route method in grouped control | `backend/testing/src/modules/quality/api/traceability.py:118`
`check_requirement_source_ai_access` | `Ctrl_InternalDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/internal_documents.py:27`
`latest_requirement_quality_analysis` | `Ctrl_RequirementAnalysis` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_analysis.py:32`
`analyze_requirement_quality_for_event_run` | `Ctrl_RequirementAnalysis` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_analysis.py:40`
`analyze_requirement_quality_on_request` | `Ctrl_RequirementAnalysis` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_analysis.py:52`
`compare_requirement` | `Ctrl_RequirementAnalysis` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_analysis.py:61`
`diff_requirement` | `Ctrl_RequirementAnalysis` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_analysis.py:77`
`split_requirement` | `Ctrl_RequirementAnalysis` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_analysis.py:91`
`merge_requirements` | `Ctrl_RequirementAnalysis` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_analysis.py:120`
`find_duplicate_requirements` | `Ctrl_RequirementAnalysis` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_analysis.py:158`
`create_requirement_document` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:79`
`compare_requirement_document_content` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:89`
`compare_requirement_document_batch` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:113`
`upload_requirement_document` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:207`
`list_requirement_documents` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:273`
`summarize_project_requirement_documents` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:286`
`get_project_document_summary_job` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:296`
`retry_project_document_summary_job` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:305`
`cancel_project_document_summary_job` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:314`
`list_ai_readable_requirement_documents` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:323`
`create_knowledge_source` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:333`
`list_knowledge_sources` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:346`
`list_knowledge_source_chunks` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:357`
`list_knowledge_source_structure` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:377`
`read_knowledge_source_image` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:398`
`archive_knowledge_source` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:455`
`reindex_knowledge_source` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:463`
`get_requirement_document` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:476`
`read_requirement_document` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:482`
`read_requirement_document_image` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:497`
`search_requirement_document` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:509`
`get_requirement_document_impact` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:519`
`update_requirement_document_metadata` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:526`
`update_requirement_document_access_control` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:541`
`update_requirement_document_ai_read_access` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:551`
`start_requirement_document_ai` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:561`
`reindex_requirement_document` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:571`
`download_requirement_document` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:584`
`preview_requirement_document` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:601`
`archive_requirement_document` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:619`
`restore_requirement_document` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:627`
`retry_requirement_document_parse` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:635`
`extract_requirement_document` | `Ctrl_RequirementDocuments` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_documents.py:648`
`create_requirement_import` | `Ctrl_RequirementImports` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_imports.py:35`
`upload_requirement_import` | `Ctrl_RequirementImports` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_imports.py:43`
`get_requirement_import` | `Ctrl_RequirementImports` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_imports.py:67`
`compare_requirement_import` | `Ctrl_RequirementImports` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_imports.py:76`
`review_requirement_import` | `Ctrl_RequirementImports` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_imports.py:84`
`merge_requirement_candidates` | `Ctrl_RequirementImports` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_imports.py:92`
`split_requirement_candidate` | `Ctrl_RequirementImports` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_imports.py:102`
`reject_requirement_candidate` | `Ctrl_RequirementImports` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_imports.py:113`
`resolve_requirement_candidate` | `Ctrl_RequirementImports` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_imports.py:124`
`confirm_requirement_import` | `Ctrl_RequirementImports` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_imports.py:135`
`apply_requirement_import` | `Ctrl_RequirementImports` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_imports.py:145`
`accept_requirement_technical_review` | `Ctrl_RequirementRecords` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_records.py:41`
`create_requirement` | `Ctrl_RequirementRecords` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_records.py:53`
`list_requirements` | `Ctrl_RequirementRecords` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_records.py:60`
`requirement_detail` | `Ctrl_RequirementRecords` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_records.py:99`
`requirement_impact` | `Ctrl_RequirementRecords` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_records.py:104`
`retry_requirement_impact` | `Ctrl_RequirementRecords` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_records.py:150`
`update_requirement_draft` | `Ctrl_RequirementRecords` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_records.py:171`
`add_requirement_dependency` | `Ctrl_RequirementRecords` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_records.py:185`
`remove_requirement_dependency` | `Ctrl_RequirementRecords` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_records.py:200`
`create_requirement_version` | `Ctrl_RequirementRecords` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_records.py:213`
`list_requirement_versions` | `Ctrl_RequirementRecords` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_records.py:223`
`save_requirement` | `Ctrl_RequirementRecords` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_records.py:230`
`submit_requirement_review` | `Ctrl_RequirementRecords` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_records.py:235`
`submit_requirement_review_alias` | `Ctrl_RequirementRecords` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_records.py:252`
`request_requirement_changes` | `Ctrl_RequirementRecords` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_records.py:264`
`reopen_requirement_editing` | `Ctrl_RequirementRecords` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_records.py:281`
`baseline_requirement_version` | `Ctrl_RequirementRecords` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_records.py:298`
`get_requirement_version` | `Ctrl_RequirementRecords` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_records.py:318`
`approve_requirement` | `Ctrl_RequirementRecords` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_records.py:323`
`approve_requirement_alias` | `Ctrl_RequirementRecords` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_records.py:338`
`mark_requirement_obsolete` | `Ctrl_RequirementRecords` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_records.py:350`
`restore_requirement` | `Ctrl_RequirementRecords` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_records.py:366`
`list_requirement_templates` | `Ctrl_RequirementTemplates` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_templates.py:35`
`get_requirement_template` | `Ctrl_RequirementTemplates` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_templates.py:40`
`list_requirement_template_versions` | `Ctrl_RequirementTemplates` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_templates.py:46`
`get_requirement_template_version` | `Ctrl_RequirementTemplates` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_templates.py:51`
`create_requirement_template` | `Ctrl_RequirementTemplates` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_templates.py:56`
`update_requirement_template` | `Ctrl_RequirementTemplates` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_templates.py:61`
`synthesize_requirement_template` | `Ctrl_RequirementTemplates` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_templates.py:66`
`preview_requirement_template` | `Ctrl_RequirementTemplates` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_templates.py:71`
`review_requirement_template` | `Ctrl_RequirementTemplates` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_templates.py:76`
`list_requirement_fields` | `Ctrl_RequirementTemplates` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_templates.py:81`
`create_requirement_field` | `Ctrl_RequirementTemplates` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_templates.py:86`
`request_requirement_template_publication` | `Ctrl_RequirementTemplates` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_templates.py:91`
`consent_requirement_template_publication` | `Ctrl_RequirementTemplates` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_templates.py:96`
`approve_requirement_template_publication` | `Ctrl_RequirementTemplates` | route method in grouped control | `backend/testing/src/modules/requirements/api/requirement_templates.py:101`
