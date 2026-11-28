# Rename map — ai

Tên code | Tên sơ đồ | Loại | Căn cứ
---|---|---|---
`ai_run_source_facts` | `AiRunSourceFact` | collection/table | `backend/ai/src/core/infrastructure/database.py:?, backend/ai/src/repositories/ai_runs.py:455, backend/ai/src/repositories/ai_runs.py:466`
`_id` | `AiRunSourceFactId` | field | `backend/ai/src/repositories/ai_runs.py:467`
`ai_run_id` | `AiRunId` | field | `backend/ai/src/repositories/ai_runs.py:467, backend/ai/src/repositories/ai_runs.py:494`
`document_ingestion_page_checkpoints` | `DocumentIngestionPageCheckpoint` | collection/table | `backend/ai/src/core/infrastructure/database.py:175, backend/ai/src/core/infrastructure/database.py:?, backend/ai/src/repositories/document_ingestion_checkpoint.py:113`
`_id` | `DocumentIngestionPageCheckpointId` | field | `backend/ai/src/repositories/document_ingestion_checkpoint.py:89`
`created_at` | `CreatedAt` | field | `backend/ai/src/schemas/document_ingestion_checkpoint.py:24`
`document_id` | `DocumentId` | field | `backend/ai/src/schemas/document_ingestion_checkpoint.py:9`
`expires_at` | `ExpiresAt` | field | `backend/ai/src/schemas/document_ingestion_checkpoint.py:25`
`extraction_warnings` | `ExtractionWarnings` | field | `backend/ai/src/schemas/document_ingestion_checkpoint.py:22`
`markdown` | `Markdown` | field | `backend/ai/src/schemas/document_ingestion_checkpoint.py:19`
`ocr_enabled` | `OcrEnabled` | field | `backend/ai/src/schemas/document_ingestion_checkpoint.py:23`
`ocr_language` | `OcrLanguage` | field | `backend/ai/src/schemas/document_ingestion_checkpoint.py:16`
`owner_id` | `OwnerId` | field | `backend/ai/src/schemas/document_ingestion_checkpoint.py:11`
`page_count` | `PageCount` | field | `backend/ai/src/schemas/document_ingestion_checkpoint.py:18`
`page_no` | `PageNo` | field | `backend/ai/src/schemas/document_ingestion_checkpoint.py:17`
`parser_contract_version` | `ParserContractVersion` | field | `backend/ai/src/schemas/document_ingestion_checkpoint.py:15`
`parser_name` | `ParserName` | field | `backend/ai/src/schemas/document_ingestion_checkpoint.py:13`
`parser_version` | `ParserVersion` | field | `backend/ai/src/schemas/document_ingestion_checkpoint.py:14`
`project_id` | `ProjectId` | field | `backend/ai/src/schemas/document_ingestion_checkpoint.py:10`
`source_hash` | `SourceHash` | field | `backend/ai/src/schemas/document_ingestion_checkpoint.py:12`
`structure` | `Structure` | field | `backend/ai/src/schemas/document_ingestion_checkpoint.py:20`
`unprocessed_blocks` | `UnprocessedBlocks` | field | `backend/ai/src/schemas/document_ingestion_checkpoint.py:21`
`long_term_memory` | `LongTermMemory` | collection/table | `backend/ai/src/core/infrastructure/database.py:?, backend/ai/src/memory/long_term.py:10, backend/ai/src/memory/long_term.py:35`
`_id` | `LongTermMemoryId` | field | `backend/ai/src/memory/long_term.py:23`
`created_at` | `CreatedAt` | field | `backend/ai/src/memory/long_term.py:23`
`evidence_refs` | `EvidenceRefs` | field | `backend/ai/src/memory/long_term.py:23`
`intent` | `Intent` | field | `backend/ai/src/memory/long_term.py:23`
`objective` | `Objective` | field | `backend/ai/src/memory/long_term.py:23`
`owner_id` | `OwnerId` | field | `backend/ai/src/memory/long_term.py:23, backend/ai/src/repositories/memory.py:12`
`project_id` | `ProjectId` | field | `backend/ai/src/memory/long_term.py:23, backend/ai/src/repositories/memory.py:12`
`proposal` | `Proposal` | field | `backend/ai/src/memory/long_term.py:23`
`run_id` | `RunId` | field | `backend/ai/src/memory/long_term.py:23, backend/ai/src/repositories/memory.py:21`
`trusted` | `Trusted` | field | `backend/ai/src/memory/long_term.py:23, backend/ai/src/repositories/memory.py:12`
`ai_run_derivation_receipts` | `AiRunDerivationReceipt` | collection/table | `backend/ai/src/core/infrastructure/database.py:?, backend/ai/src/repositories/ai_runs.py:477, backend/ai/src/repositories/ai_runs.py:484`
`_id` | `AiRunDerivationReceiptId` | field | `backend/ai/src/repositories/ai_runs.py:479`
`ai_run_id` | `AiRunId` | field | `backend/ai/src/repositories/ai_runs.py:478, backend/ai/src/repositories/ai_runs.py:485`
`ai_run_checkpoints` | `AiRunCheckpoint` | collection/table | `backend/ai/src/core/infrastructure/database.py:?, backend/ai/src/repositories/ai_runs.py:156, backend/ai/src/repositories/ai_runs.py:324`
`ai_run_id` | `AiRunId` | field | `backend/ai/src/schemas/ai_runs.py:189`
`checkpoint_id` | `CheckpointId` | field | `backend/ai/src/schemas/ai_runs.py:188`
`checkpoint_sequence` | `CheckpointSequence` | field | `backend/ai/src/schemas/ai_runs.py:190`
`created_at` | `CreatedAt` | field | `backend/ai/src/schemas/ai_runs.py:195`
`detail` | `Detail` | field | `backend/ai/src/schemas/ai_runs.py:193`
`phase` | `Phase` | field | `backend/ai/src/schemas/ai_runs.py:191`
`state_snapshot` | `StateSnapshot` | field | `backend/ai/src/schemas/ai_runs.py:194`
`status` | `Status` | field | `backend/ai/src/schemas/ai_runs.py:192`
`agent_traces` | `AgentTrace` | collection/table | `backend/ai/src/core/infrastructure/database.py:?, backend/ai/src/services/agent_metrics.py:153`
`ai_sessions` | `AiSession` | collection/table | `backend/ai/src/core/infrastructure/database.py:?`
`retrieval_audit` | `RetrievalAudit` | collection/table | `backend/ai/src/core/infrastructure/database.py:?, backend/ai/src/repositories/retrieval_audit.py:6, backend/ai/src/repositories/retrieval_audit.py:9`
`ai_messages` | `AiMessage` | collection/table | `backend/ai/src/core/infrastructure/database.py:?`
`dead_letter_recovery_audit` | `DeadLetterRecoveryAudit` | collection/table | `backend/ai/src/core/infrastructure/database.py:?`
`acknowledged_at` | `AcknowledgedAt` | field | `backend/ai/src/schemas/queue_recovery.py:36`
`action_id` | `ActionId` | field | `backend/ai/src/schemas/queue_recovery.py:16`
`created_at` | `CreatedAt` | field | `backend/ai/src/schemas/queue_recovery.py:34`
`delivery_attempt_reset` | `DeliveryAttemptReset` | field | `backend/ai/src/schemas/queue_recovery.py:24`
`identity_sha256` | `IdentitySha256` | field | `backend/ai/src/schemas/queue_recovery.py:21`
`identity_type` | `IdentityType` | field | `backend/ai/src/schemas/queue_recovery.py:20`
`origin_queue` | `OriginQueue` | field | `backend/ai/src/schemas/queue_recovery.py:19`
`payload_sha256` | `PayloadSha256` | field | `backend/ai/src/schemas/queue_recovery.py:18`
`published_at` | `PublishedAt` | field | `backend/ai/src/schemas/queue_recovery.py:35`
`reason` | `Reason` | field | `backend/ai/src/schemas/queue_recovery.py:33`
`redrive_count` | `RedriveCount` | field | `backend/ai/src/schemas/queue_recovery.py:22`
`requested_by` | `RequestedBy` | field | `backend/ai/src/schemas/queue_recovery.py:17`
`source_delivery_attempt` | `SourceDeliveryAttempt` | field | `backend/ai/src/schemas/queue_recovery.py:23`
`status` | `Status` | field | `backend/ai/src/schemas/queue_recovery.py:25`
`updated_at` | `UpdatedAt` | field | `backend/ai/src/schemas/queue_recovery.py:37`
`ai_workspaces` | `AiWorkspace` | collection/table | `backend/ai/src/core/infrastructure/database.py:?`
`ai_runs` | `AiRun` | collection/table | `backend/ai/src/core/infrastructure/database.py:?, backend/ai/src/repositories/ai_runs.py:134, backend/ai/src/repositories/ai_runs.py:194`
`_id` | `AiRunId` | field | `backend/ai/src/repositories/ai_runs.py:368, backend/ai/src/repositories/ai_runs.py:387`
`ai_run_id` | `AiRunId` | field | `backend/ai/src/schemas/ai_runs.py:261`
`automatic_retry_count` | `AutomaticRetryCount` | field | `backend/ai/src/schemas/ai_runs.py:285`
`change_simulation` | `ChangeSimulation` | field | `backend/ai/src/schemas/ai_runs.py:280`
`checkpoint_sequence` | `CheckpointSequence` | field | `backend/ai/src/schemas/ai_runs.py:287`
`constraints` | `Constraints` | field | `backend/ai/src/schemas/ai_runs.py:279`
`created_at` | `CreatedAt` | field | `backend/ai/src/schemas/ai_runs.py:290`
`definition_id` | `DefinitionId` | field | `backend/ai/src/schemas/ai_runs.py:271`
`error_code` | `ErrorCode` | field | `backend/ai/src/schemas/ai_runs.py:284`
`evidence` | `Evidence` | field | `backend/ai/src/schemas/ai_runs.py:278`
`execution_permissions` | `ExecutionPermissions` | field | `backend/ai/src/schemas/ai_runs.py:268`
`execution_role` | `ExecutionRole` | field | `backend/ai/src/schemas/ai_runs.py:267`
`execution_user_id` | `ExecutionUserId` | field | `backend/ai/src/schemas/ai_runs.py:266`
`intent` | `Intent` | field | `backend/ai/src/schemas/ai_runs.py:275`
`intent_arguments` | `IntentArguments` | field | `backend/ai/src/schemas/ai_runs.py:276`
`kind` | `Kind` | field | `backend/ai/src/schemas/ai_runs.py:269`
`objective` | `Objective` | field | `backend/ai/src/schemas/ai_runs.py:274`
`project_id` | `ProjectId` | field | `backend/ai/src/schemas/ai_runs.py:262`
`queue_dispatch_lease_expires_at` | `QueueDispatchLeaseExpiresAt` | field | `backend/ai/src/schemas/ai_runs.py:289`
`requester_permissions` | `RequesterPermissions` | field | `backend/ai/src/schemas/ai_runs.py:265`
`requester_role` | `RequesterRole` | field | `backend/ai/src/schemas/ai_runs.py:264`
`requester_user_id` | `RequesterUserId` | field | `backend/ai/src/schemas/ai_runs.py:263`
`result` | `Result` | field | `backend/ai/src/schemas/ai_runs.py:283`
`revision` | `Revision` | field | `backend/ai/src/schemas/ai_runs.py:286`
`source_event_id` | `SourceEventId` | field | `backend/ai/src/schemas/ai_runs.py:272`
`source_event_verified` | `SourceEventVerified` | field | `backend/ai/src/schemas/ai_runs.py:273`
`status` | `Status` | field | `backend/ai/src/schemas/ai_runs.py:281`
`target_artifact_ids` | `TargetArtifactIds` | field | `backend/ai/src/schemas/ai_runs.py:277`
`trace_id` | `TraceId` | field | `backend/ai/src/schemas/ai_runs.py:282`
`trigger` | `Trigger` | field | `backend/ai/src/schemas/ai_runs.py:270`
`updated_at` | `UpdatedAt` | field | `backend/ai/src/schemas/ai_runs.py:291`
`worker_lease_expires_at` | `WorkerLeaseExpiresAt` | field | `backend/ai/src/schemas/ai_runs.py:288`
`verified_tool_evidence_records` | `VerifiedToolEvidenceRecords` | method | `backend/ai/src/services/agent_evidence.py:1`
`verified_tool_evidence` | `VerifiedToolEvidence` | method | `backend/ai/src/services/agent_evidence.py:34`
`record_session_start` | `RecordSessionStart` | method | `backend/ai/src/services/agent_metrics.py:52`
`record_session_end` | `RecordSessionEnd` | method | `backend/ai/src/services/agent_metrics.py:60`
`current_session_id` | `CurrentSessionId` | method | `backend/ai/src/services/agent_metrics.py:78`
`record_tool_call` | `RecordToolCall` | method | `backend/ai/src/services/agent_metrics.py:81`
`record_llm_call` | `RecordLlmCall` | method | `backend/ai/src/services/agent_metrics.py:97`
`record_security_event` | `RecordSecurityEvent` | method | `backend/ai/src/services/agent_metrics.py:113`
`evidence_text` | `EvidenceText` | method | `backend/ai/src/services/ai_capabilities.py:67`
`evidence_payload` | `EvidencePayload` | method | `backend/ai/src/services/ai_capabilities.py:94`
`evidence_reference_ids` | `EvidenceReferenceIds` | method | `backend/ai/src/services/ai_capabilities.py:112`
`suppress_execution_assistance_credential_requests` | `SuppressExecutionAssistanceCredentialRequests` | method | `backend/ai/src/services/ai_capabilities.py:120`
`nested_values` | `NestedValues` | method | `backend/ai/src/services/ai_capabilities.py:151`
`generated_cases_have_grounded_citations` | `GeneratedCasesHaveGroundedCitations` | method | `backend/ai/src/services/ai_capabilities.py:165`
`grounded_requirement_recommendations` | `GroundedRequirementRecommendations` | method | `backend/ai/src/services/ai_capabilities.py:191`
`generate_ai_capability` | `GenerateAiCapability` | method | `backend/ai/src/services/ai_capabilities.py:224`
`observe_prompt_attempt` | `ObservePromptAttempt` | method | `backend/ai/src/services/ai_capabilities.py:260`
`record` | `Record` | method | `backend/ai/src/services/ai_capabilities.py:261`
`publish_ai_run` | `PublishAiRun` | method | `backend/ai/src/services/ai_runs.py:30`
`create_user_run` | `CreateUserRun` | method | `backend/ai/src/services/ai_runs.py:43`
`create_requirement_document_run` | `CreateRequirementDocumentRun` | method | `backend/ai/src/services/ai_runs.py:164`
`authorize_retry` | `AuthorizeRetry` | method | `backend/ai/src/services/ai_runs.py:228`
`cancel` | `Cancel` | method | `backend/ai/src/services/ai_runs.py:322`
`cancel_document_ingestion_runs` | `CancelDocumentIngestionRuns` | method | `backend/ai/src/services/ai_runs.py:361`
`token_for` | `TokenFor` | method | `backend/ai/src/services/ai_runs.py:412`
`change_simulation_batches` | `ChangeSimulationBatches` | method | `backend/ai/src/services/change_simulation.py:5`
`simulation_trace_scope_is_current` | `SimulationTraceScopeIsCurrent` | method | `backend/ai/src/services/change_simulation.py:51`
`validate_change_simulation_report` | `ValidateChangeSimulationReport` | method | `backend/ai/src/services/change_simulation.py:64`
`simulation_source_payload` | `SimulationSourcePayload` | method | `backend/ai/src/services/change_simulation.py:137`
`iter_chunk_document` | `IterChunkDocument` | method | `backend/ai/src/services/chunking.py:43`
`pages_for` | `PagesFor` | method | `backend/ai/src/services/chunking.py:183`
`storage_ready` | `StorageReady` | method | `backend/ai/src/services/conversion.py:118`
`delete_picture_assets` | `DeletePictureAssets` | method | `backend/ai/src/services/conversion.py:167`
`read_picture_asset` | `ReadPictureAsset` | method | `backend/ai/src/services/conversion.py:214`
`parse_document` | `ParseDocument` | method | `backend/ai/src/services/conversion.py:1083`
`parse_document_checkpointed` | `ParseDocumentCheckpointed` | method | `backend/ai/src/services/conversion.py:1092`
`parse_bytes_checkpointed` | `ParseBytesCheckpointed` | method | `backend/ai/src/services/conversion.py:1213`
`clear_document_checkpoints` | `ClearDocumentCheckpoints` | method | `backend/ai/src/services/conversion.py:1486`
`parse_bytes` | `ParseBytes` | method | `backend/ai/src/services/conversion.py:1497`
`delete_batch` | `DeleteBatch` | method | `backend/ai/src/services/conversion.py:140`
`belongs_to_page` | `BelongsToPage` | method | `backend/ai/src/services/conversion.py:957`
`depth` | `Depth` | method | `backend/ai/src/services/dead_letter_recovery.py:52`
`list_audit` | `ListAudit` | method | `backend/ai/src/services/dead_letter_recovery.py:64`
`redrive` | `Redrive` | method | `backend/ai/src/services/dead_letter_recovery.py:77`
`initialize` | `Initialize` | method | `backend/ai/src/services/embedding.py:24`
`embed_query` | `EmbedQuery` | method | `backend/ai/src/services/embedding.py:43`
`embed_batch` | `EmbedBatch` | method | `backend/ai/src/services/embedding.py:78`
`model_metadata` | `ModelMetadata` | method | `backend/ai/src/services/inference.py:19`
`chat` | `Chat` | method | `backend/ai/src/services/inference.py:23`
`structured` | `Structured` | method | `backend/ai/src/services/inference.py:62`
`prompt_messages` | `PromptMessages` | method | `backend/ai/src/services/inference.py:104`
`decompose_retrieval` | `DecomposeRetrieval` | method | `backend/ai/src/services/inference.py:111`
`summarize_document` | `SummarizeDocument` | method | `backend/ai/src/services/inference.py:124`
`source_timestamp` | `SourceTimestamp` | method | `backend/ai/src/services/ingestion.py:61`
`parsed_utc_datetime` | `ParsedUtcDatetime` | method | `backend/ai/src/services/ingestion.py:76`
`source_snapshot_values` | `SourceSnapshotValues` | method | `backend/ai/src/services/ingestion.py:147`
`source_snapshot_fingerprint` | `SourceSnapshotFingerprint` | method | `backend/ai/src/services/ingestion.py:151`
`embed_and_index_chunks` | `EmbedAndIndexChunks` | method | `backend/ai/src/services/ingestion.py:166`
`validated_indexing_status` | `ValidatedIndexingStatus` | method | `backend/ai/src/services/ingestion.py:273`
`publish_index_generation` | `PublishIndexGeneration` | method | `backend/ai/src/services/ingestion.py:282`
`select_summary_chunks` | `SelectSummaryChunks` | method | `backend/ai/src/services/ingestion.py:351`
`index_document` | `IndexDocument` | method | `backend/ai/src/services/ingestion.py:931`
`convert_attachment` | `ConvertAttachment` | method | `backend/ai/src/services/ingestion.py:1040`
`remove_document` | `RemoveDocument` | method | `backend/ai/src/services/ingestion.py:1088`
`append` | `Append` | method | `backend/ai/src/services/ingestion.py:39`
`clear` | `Clear` | method | `backend/ai/src/services/ingestion.py:44`
`add` | `Add` | method | `backend/ai/src/services/ingestion.py:434`
`select` | `Select` | method | `backend/ai/src/services/ingestion.py:451`
`ingest_document` | `IngestDocument` | method | `backend/ai/src/services/ingestion.py:464`
`artifact_value` | `ArtifactValue` | method | `backend/ai/src/services/ingestion.py:490`
`verify_source_snapshot` | `VerifySourceSnapshot` | method | `backend/ai/src/services/ingestion.py:539`
`report_page_progress` | `ReportPageProgress` | method | `backend/ai/src/services/ingestion.py:574`
`indexed_chunks` | `IndexedChunks` | method | `backend/ai/src/services/ingestion.py:681`
`renew_lease_until_cancelled` | `RenewLeaseUntilCancelled` | method | `backend/ai/src/services/ingestion.py:976`
`project_access` | `ProjectAccess` | method | `backend/ai/src/services/project_access.py:9`
`project_artifact_metadata` | `ProjectArtifactMetadata` | method | `backend/ai/src/services/project_knowledge.py:94`
`project_artifact_point_payload` | `ProjectArtifactPointPayload` | method | `backend/ai/src/services/project_knowledge.py:179`
`project_artifact_chunk_read_metadata` | `ProjectArtifactChunkReadMetadata` | method | `backend/ai/src/services/project_knowledge.py:194`
`index_project_artifact` | `IndexProjectArtifact` | method | `backend/ai/src/services/project_knowledge.py:216`
`remove_project_artifact` | `RemoveProjectArtifact` | method | `backend/ai/src/services/project_knowledge.py:433`
`list_project_artifact_chunks` | `ListProjectArtifactChunks` | method | `backend/ai/src/services/project_knowledge.py:469`
`search_project_knowledge` | `SearchProjectKnowledge` | method | `backend/ai/src/services/project_knowledge.py:566`
`write_batch` | `WriteBatch` | method | `backend/ai/src/services/project_knowledge.py:263`
`initialize_retrieval` | `InitializeRetrieval` | method | `backend/ai/src/services/retrieval.py:35`
`migrate_current_vectors` | `MigrateCurrentVectors` | method | `backend/ai/src/services/retrieval.py:41`
`initialize` | `Initialize` | method | `backend/ai/src/services/retrieval.py:363`
`get_citations` | `GetCitations` | method | `backend/ai/src/services/retrieval.py:373`
`detect_source_conflicts` | `DetectSourceConflicts` | method | `backend/ai/src/services/retrieval.py:416`
`retrieve` | `Retrieve` | method | `backend/ai/src/services/retrieval.py:456`
`cross_document_retrieve` | `CrossDocumentRetrieve` | method | `backend/ai/src/services/retrieval.py:564`
`hybrid_search` | `HybridSearch` | method | `backend/ai/src/services/retrieval.py:479`
`record` | `Record` | method | `backend/ai/src/services/retrieval_audit.py:12`
`list` | `List` | method | `backend/ai/src/services/retrieval_audit.py:35`
`is_source_fact_evidence` | `IsSourceFactEvidence` | method | `backend/ai/src/services/source_provenance.py:8`
`source_fact_identity` | `SourceFactIdentity` | method | `backend/ai/src/services/source_provenance.py:21`
`source_location_metadata` | `SourceLocationMetadata` | method | `backend/ai/src/services/source_provenance.py:38`
`verified_source_offset_basis` | `VerifiedSourceOffsetBasis` | method | `backend/ai/src/services/source_provenance.py:72`
`canonicalize_source_facts` | `CanonicalizeSourceFacts` | method | `backend/ai/src/services/source_provenance.py:90`
`verified_source_span` | `VerifiedSourceSpan` | method | `backend/ai/src/services/source_provenance.py:122`
`carry_source_fact_lineage` | `CarrySourceFactLineage` | method | `backend/ai/src/services/source_provenance.py:226`
`has_provenance_gap` | `HasProvenanceGap` | method | `backend/ai/src/services/source_provenance.py:242`
`markdown_table_cell_spans` | `MarkdownTableCellSpans` | method | `backend/ai/src/services/table_spans.py:17`
`markdown_table_metadata` | `MarkdownTableMetadata` | method | `backend/ai/src/services/table_spans.py:49`
`usage_values` | `UsageValues` | method | `backend/ai/src/services/token_accounting.py:4`
`record_usage` | `RecordUsage` | method | `backend/ai/src/services/token_accounting.py:21`
`get_value` | `GetValue` | method | `backend/ai/src/services/token_accounting.py:9`
`create_run_with_checkpoint` | `CreateRunWithCheckpoint` | method | `backend/ai/src/repositories/ai_runs.py:27`
`get_run` | `GetRun` | method | `backend/ai/src/repositories/ai_runs.py:56`
`find_event_run` | `FindEventRun` | method | `backend/ai/src/repositories/ai_runs.py:63`
`list_incomplete_document_ingestion_runs` | `ListIncompleteDocumentIngestionRuns` | method | `backend/ai/src/repositories/ai_runs.py:72`
`list_runs` | `ListRuns` | method | `backend/ai/src/repositories/ai_runs.py:90`
`transition_with_checkpoint` | `TransitionWithCheckpoint` | method | `backend/ai/src/repositories/ai_runs.py:106`
`recover_interrupted_runs` | `RecoverInterruptedRuns` | method | `backend/ai/src/repositories/ai_runs.py:164`
`list_retryable_queue_runs` | `ListRetryableQueueRuns` | method | `backend/ai/src/repositories/ai_runs.py:272`
`claim_stale_queued_runs` | `ClaimStaleQueuedRuns` | method | `backend/ai/src/repositories/ai_runs.py:293`
`latest_checkpoint` | `LatestCheckpoint` | method | `backend/ai/src/repositories/ai_runs.py:323`
`latest_checkpoint_with_evidence` | `LatestCheckpointWithEvidence` | method | `backend/ai/src/repositories/ai_runs.py:337`
`save_checkpoint` | `SaveCheckpoint` | method | `backend/ai/src/repositories/ai_runs.py:356`
`list_checkpoints` | `ListCheckpoints` | method | `backend/ai/src/repositories/ai_runs.py:414`
`count_retry_checkpoints` | `CountRetryCheckpoints` | method | `backend/ai/src/repositories/ai_runs.py:428`
`save_source_facts` | `SaveSourceFacts` | method | `backend/ai/src/repositories/ai_runs.py:441`
`replace_provenance` | `ReplaceProvenance` | method | `backend/ai/src/repositories/ai_runs.py:457`
`save_receipt` | `SaveReceipt` | method | `backend/ai/src/repositories/ai_runs.py:473`
`get_receipt` | `GetReceipt` | method | `backend/ai/src/repositories/ai_runs.py:483`
`list_source_facts` | `ListSourceFacts` | method | `backend/ai/src/repositories/ai_runs.py:492`
`collection` | `Collection` | method | `backend/ai/src/repositories/document_ingestion_checkpoint.py:12`
`iter_pages` | `IterPages` | method | `backend/ai/src/repositories/document_ingestion_checkpoint.py:42`
`save_page` | `SavePage` | method | `backend/ai/src/repositories/document_ingestion_checkpoint.py:68`
`delete_source_version` | `DeleteSourceVersion` | method | `backend/ai/src/repositories/document_ingestion_checkpoint.py:92`
`delete_document_versions` | `DeleteDocumentVersions` | method | `backend/ai/src/repositories/document_ingestion_checkpoint.py:108`
`list_long_term` | `ListLongTerm` | method | `backend/ai/src/repositories/memory.py:10`
`record_long_term` | `RecordLongTerm` | method | `backend/ai/src/repositories/memory.py:19`
`get_or_migrate` | `GetOrMigrate` | method | `backend/ai/src/repositories/project_artifact_generation.py:73`
`publish` | `Publish` | method | `backend/ai/src/repositories/project_artifact_generation.py:90`
`begin_removal` | `BeginRemoval` | method | `backend/ai/src/repositories/project_artifact_generation.py:117`
`finish_removal` | `FinishRemoval` | method | `backend/ai/src/repositories/project_artifact_generation.py:143`
`removal_is_current` | `RemovalIsCurrent` | method | `backend/ai/src/repositories/project_artifact_generation.py:164`
`active_generations` | `ActiveGenerations` | method | `backend/ai/src/repositories/project_artifact_generation.py:170`
`filter_active` | `FilterActive` | method | `backend/ai/src/repositories/project_artifact_generation.py:217`
`insert` | `Insert` | method | `backend/ai/src/repositories/retrieval_audit.py:5`
`list` | `List` | method | `backend/ai/src/repositories/retrieval_audit.py:8`
`list_ai_run_capabilities` | `Ctrl_AiRuns` | route method in grouped control | `backend/ai/src/api/ai_runs.py:22`
`create_user_ai_run` | `Ctrl_AiRuns` | route method in grouped control | `backend/ai/src/api/ai_runs.py:43`
`create_requirement_document_run` | `Ctrl_AiRuns` | route method in grouped control | `backend/ai/src/api/ai_runs.py:60`
`cancel_requirement_document_runs` | `Ctrl_AiRuns` | route method in grouped control | `backend/ai/src/api/ai_runs.py:92`
`get_internal_run_execution_status` | `Ctrl_AiRuns` | route method in grouped control | `backend/ai/src/api/ai_runs.py:102`
`get_ai_run` | `Ctrl_AiRuns` | route method in grouped control | `backend/ai/src/api/ai_runs.py:120`
`get_ai_run_evidence` | `Ctrl_AiRuns` | route method in grouped control | `backend/ai/src/api/ai_runs.py:134`
`list_ai_runs` | `Ctrl_AiRuns` | route method in grouped control | `backend/ai/src/api/ai_runs.py:151`
`retry_ai_run` | `Ctrl_AiRuns` | route method in grouped control | `backend/ai/src/api/ai_runs.py:176`
`cancel_ai_run` | `Ctrl_AiRuns` | route method in grouped control | `backend/ai/src/api/ai_runs.py:187`
`embed_single_query` | `Ctrl_Embedding` | route method in grouped control | `backend/ai/src/api/embedding.py:21`
`embed_batch_texts` | `Ctrl_Embedding` | route method in grouped control | `backend/ai/src/api/embedding.py:33`
`queue_uploaded_document` | `Ctrl_Indexing` | route method in grouped control | `backend/ai/src/api/indexing.py:31`
`ingest_endpoint` | `Ctrl_Indexing` | route method in grouped control | `backend/ai/src/api/indexing.py:60`
`delete_document_endpoint` | `Ctrl_Indexing` | route method in grouped control | `backend/ai/src/api/indexing.py:81`
`convert_attachment` | `Ctrl_Indexing` | route method in grouped control | `backend/ai/src/api/indexing.py:116`
`clear_conversion_checkpoints` | `Ctrl_Indexing` | route method in grouped control | `backend/ai/src/api/indexing.py:137`
`read_document_picture_asset` | `Ctrl_Indexing` | route method in grouped control | `backend/ai/src/api/indexing.py:152`
`delete_document` | `Ctrl_Indexing` | route method in grouped control | `backend/ai/src/api/indexing.py:183`
`decompose_cross_document_query` | `Ctrl_Inference` | route method in grouped control | `backend/ai/src/api/inference.py:30`
`summarize_knowledge_document` | `Ctrl_Inference` | route method in grouped control | `backend/ai/src/api/inference.py:45`
`ai_capability` | `Ctrl_Inference` | route method in grouped control | `backend/ai/src/api/inference.py:59`
`stream_ai_capability` | `Ctrl_Inference` | route method in grouped control | `backend/ai/src/api/inference.py:64`
`index_artifact` | `Ctrl_Projects` | route method in grouped control | `backend/ai/src/api/projects.py:19`
`remove_artifact` | `Ctrl_Projects` | route method in grouped control | `backend/ai/src/api/projects.py:24`
`list_artifact_chunks` | `Ctrl_Projects` | route method in grouped control | `backend/ai/src/api/projects.py:29`
`search_knowledge` | `Ctrl_Projects` | route method in grouped control | `backend/ai/src/api/projects.py:44`
`dead_letter_status` | `Ctrl_QueueRecovery` | route method in grouped control | `backend/ai/src/api/queue_recovery.py:14`
`dead_letter_audit` | `Ctrl_QueueRecovery` | route method in grouped control | `backend/ai/src/api/queue_recovery.py:22`
`redrive_dead_letters` | `Ctrl_QueueRecovery` | route method in grouped control | `backend/ai/src/api/queue_recovery.py:27`
`list_retrieval_access_audit` | `Ctrl_Retrieval` | route method in grouped control | `backend/ai/src/api/retrieval.py:60`
`retrieve_documents` | `Ctrl_Retrieval` | route method in grouped control | `backend/ai/src/api/retrieval.py:76`
`cross_document_retrieve` | `Ctrl_Retrieval` | route method in grouped control | `backend/ai/src/api/retrieval.py:103`
`health_check` | `Ctrl_Main` | route method in grouped control | `backend/ai/src/main.py:85`
`readiness_check` | `Ctrl_Main` | route method in grouped control | `backend/ai/src/main.py:90`
