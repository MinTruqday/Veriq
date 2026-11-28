# Rename map — content

Tên code | Tên sơ đồ | Loại | Căn cứ
---|---|---|---
`documents` | `Document` | collection/table | `backend/content/src/core/infrastructure/database.py:55, backend/content/src/core/infrastructure/database.py:58, backend/content/src/core/infrastructure/database.py:59`
`artifact_metadata` | `ArtifactMetadata` | field | `backend/content/src/schemas/document.py:76`
`category` | `Category` | field | `backend/content/src/schemas/document.py:66`
`content` | `Content` | field | `backend/content/src/schemas/document.py:63`
`content_format` | `ContentFormat` | field | `backend/content/src/schemas/document.py:64`
`content_hash` | `ContentHash` | field | `backend/content/src/core/infrastructure/database.py:75`
`cover_url` | `CoverUrl` | field | `backend/content/src/schemas/document.py:60`
`created_at` | `CreatedAt` | field | `backend/content/src/schemas/document.py:151`
`creator_id` | `CreatorId` | field | `backend/content/src/schemas/document.py:149`
`deleted_at` | `DeletedAt` | field | `backend/content/src/schemas/document.py:70`
`description` | `Description` | field | `backend/content/src/schemas/document.py:59`
`draft_content` | `DraftContent` | field | `backend/content/src/schemas/document.py:73`
`file_url` | `FileUrl` | field | `backend/content/src/schemas/document.py:61`
`folder_id` | `FolderId` | field | `backend/content/src/schemas/document.py:72`
`indexing_attempt_id` | `IndexingAttemptId` | field | `backend/content/src/schemas/document.py:154`
`indexing_lease_token` | `IndexingLeaseToken` | field | `backend/content/src/schemas/document.py:155`
`indexing_lease_until` | `IndexingLeaseUntil` | field | `backend/content/src/schemas/document.py:156`
`is_deleted` | `IsDeleted` | field | `backend/content/src/schemas/document.py:69`
`pages_count` | `PagesCount` | field | `backend/content/src/schemas/document.py:67`
`preview_pages` | `PreviewPages` | field | `backend/content/src/schemas/document.py:68`
`publisher_name` | `PublisherName` | field | `backend/content/src/schemas/document.py:71`
`reading_time_minutes` | `ReadingTimeMinutes` | field | `backend/content/src/schemas/document.py:75`
`slug` | `Slug` | field | `backend/content/src/schemas/document.py:56`
`source_url` | `SourceUrl` | field | `backend/content/src/core/infrastructure/database.py:75`
`status` | `Status` | field | `backend/content/src/schemas/document.py:150`
`tags` | `Tags` | field | `backend/content/src/schemas/document.py:62`
`title` | `Title` | field | `backend/content/src/schemas/document.py:55`
`toc` | `Toc` | field | `backend/content/src/schemas/document.py:74`
`updated_at` | `UpdatedAt` | field | `backend/content/src/schemas/document.py:152`
`views` | `Views` | field | `backend/content/src/schemas/document.py:153`
`visibility` | `Visibility` | field | `backend/content/src/schemas/document.py:65`
`comments` | `Comment` | collection/table | `backend/content/src/core/infrastructure/database.py:97, backend/content/src/core/infrastructure/database.py:98`
`editor_comments` | `EditorComment` | collection/table | `backend/content/src/core/infrastructure/database.py:100`
`document_versions` | `DocumentVersion` | collection/table | `backend/content/src/core/infrastructure/database.py:104, backend/content/src/repositories/document.py:43, backend/content/src/repositories/document.py:47`
`document_ingestion_outbox` | `DocumentIngestionOutbox` | collection/table | `backend/content/src/core/infrastructure/database.py:107, backend/content/src/core/infrastructure/database.py:111`
`workspace_folders` | `WorkspaceFolder` | collection/table | `backend/content/src/core/infrastructure/database.py:115, backend/content/src/repositories/folder.py:11, backend/content/src/repositories/folder.py:15`
`document_revisions` | `DocumentRevision` | collection/table | `backend/content/src/repositories/document.py:39`
`serialize_document` | `SerializeDocument` | method | `backend/content/src/services/document/base.py:10`
`is_admin` | `IsAdmin` | method | `backend/content/src/services/document/base.py:28`
`can_read_full` | `CanReadFull` | method | `backend/content/src/services/document/base.py:34`
`bulk_delete_documents` | `BulkDeleteDocuments` | method | `backend/content/src/services/document/bulk.py:18`
`bulk_restore_documents` | `BulkRestoreDocuments` | method | `backend/content/src/services/document/bulk.py:41`
`bulk_move_documents` | `BulkMoveDocuments` | method | `backend/content/src/services/document/bulk.py:71`
`bulk_export_documents` | `BulkExportDocuments` | method | `backend/content/src/services/document/bulk.py:92`
`create_document` | `CreateDocument` | method | `backend/content/src/services/document/crud.py:24`
`get_my_documents` | `GetMyDocuments` | method | `backend/content/src/services/document/crud.py:70`
`update_document_content` | `UpdateDocumentContent` | method | `backend/content/src/services/document/crud.py:125`
`update_document` | `UpdateDocument` | method | `backend/content/src/services/document/crud.py:200`
`retry_document_indexing` | `RetryDocumentIndexing` | method | `backend/content/src/services/document/crud.py:281`
`list_documents` | `ListDocuments` | method | `backend/content/src/services/document/crud.py:323`
`get_document_by_id` | `GetDocumentById` | method | `backend/content/src/services/document/crud.py:353`
`get_document_by_slug` | `GetDocumentBySlug` | method | `backend/content/src/services/document/crud.py:413`
`soft_delete_document` | `SoftDeleteDocument` | method | `backend/content/src/services/document/crud.py:429`
`restore_document` | `RestoreDocument` | method | `backend/content/src/services/document/crud.py:452`
`get_trash` | `GetTrash` | method | `backend/content/src/services/document/crud.py:470`
`toggle_star_document` | `ToggleStarDocument` | method | `backend/content/src/services/document/crud.py:490`
`set_document_password` | `SetDocumentPassword` | method | `backend/content/src/services/document/crud.py:506`
`get_document_preview` | `GetDocumentPreview` | method | `backend/content/src/services/document/crud.py:529`
`get_folders` | `GetFolders` | method | `backend/content/src/services/document/hierarchy.py:14`
`create_folder` | `CreateFolder` | method | `backend/content/src/services/document/hierarchy.py:25`
`delete_folder` | `DeleteFolder` | method | `backend/content/src/services/document/hierarchy.py:38`
`move_document_to_folder` | `MoveDocumentToFolder` | method | `backend/content/src/services/document/hierarchy.py:51`
`transfer_document` | `TransferDocument` | method | `backend/content/src/services/document/hierarchy.py:78`
`serialize_internal` | `SerializeInternal` | method | `backend/content/src/services/document/internal.py:63`
`indexing_status_from_report` | `IndexingStatusFromReport` | method | `backend/content/src/services/document/internal.py:75`
`internal_document_data` | `InternalDocumentData` | method | `backend/content/src/services/document/internal.py:88`
`get_internal_document` | `GetInternalDocument` | method | `backend/content/src/services/document/internal.py:154`
`get_internal_document_stats` | `GetInternalDocumentStats` | method | `backend/content/src/services/document/internal.py:182`
`exchange_internal_document` | `ExchangeInternalDocument` | method | `backend/content/src/services/document/internal.py:208`
`get_document_analytics` | `GetDocumentAnalytics` | method | `backend/content/src/services/document/metadata.py:14`
`get_document_academic` | `GetDocumentAcademic` | method | `backend/content/src/services/document/metadata.py:37`
`get_approval_queue` | `GetApprovalQueue` | method | `backend/content/src/services/document/metadata.py:66`
`get_trending_documents` | `GetTrendingDocuments` | method | `backend/content/src/services/document/metadata.py:99`
`get_suggested_documents` | `GetSuggestedDocuments` | method | `backend/content/src/services/document/metadata.py:112`
`format_date` | `FormatDate` | method | `backend/content/src/services/document/metadata.py:77`
`get_tags_categories` | `GetTagsCategories` | method | `backend/content/src/services/document/tag.py:10`
`get_trending_tags` | `GetTrendingTags` | method | `backend/content/src/services/document/tag.py:43`
`start` | `Start` | method | `backend/content/src/services/document_ingestion_dispatcher.py:21`
`stop` | `Stop` | method | `backend/content/src/services/document_ingestion_dispatcher.py:27`
`save_version` | `SaveVersion` | method | `backend/content/src/services/version.py:11`
`get_versions` | `GetVersions` | method | `backend/content/src/services/version.py:37`
`restore_version` | `RestoreVersion` | method | `backend/content/src/services/version.py:48`
`invalidate_document` | `InvalidateDocument` | method | `backend/content/src/repositories/cache.py:6`
`password_attempts` | `PasswordAttempts` | method | `backend/content/src/repositories/cache.py:16`
`record_password_failure` | `RecordPasswordFailure` | method | `backend/content/src/repositories/cache.py:21`
`clear_password_failures` | `ClearPasswordFailures` | method | `backend/content/src/repositories/cache.py:27`
`normalize_query` | `NormalizeQuery` | method | `backend/content/src/repositories/document.py:12`
`identifiers` | `Identifiers` | method | `backend/content/src/repositories/document.py:26`
`update_one` | `UpdateOne` | method | `backend/content/src/repositories/document.py:30`
`find_one` | `FindOne` | method | `backend/content/src/repositories/document.py:34`
`insert_revision` | `InsertRevision` | method | `backend/content/src/repositories/document.py:38`
`insert_version` | `InsertVersion` | method | `backend/content/src/repositories/document.py:42`
`find_version` | `FindVersion` | method | `backend/content/src/repositories/document.py:46`
`find_versions` | `FindVersions` | method | `backend/content/src/repositories/document.py:50`
`insert_one` | `InsertOne` | method | `backend/content/src/repositories/document.py:54`
`insert_one_if_unique` | `InsertOneIfUnique` | method | `backend/content/src/repositories/document.py:58`
`find_one_and_update` | `FindOneAndUpdate` | method | `backend/content/src/repositories/document.py:66`
`insert_many` | `InsertMany` | method | `backend/content/src/repositories/document.py:75`
`update_many` | `UpdateMany` | method | `backend/content/src/repositories/document.py:79`
`delete_one` | `DeleteOne` | method | `backend/content/src/repositories/document.py:83`
`delete_many` | `DeleteMany` | method | `backend/content/src/repositories/document.py:87`
`count_documents` | `CountDocuments` | method | `backend/content/src/repositories/document.py:91`
`find` | `Find` | method | `backend/content/src/repositories/document.py:95`
`aggregate` | `Aggregate` | method | `backend/content/src/repositories/document.py:99`
`query` | `Query` | method | `backend/content/src/repositories/document.py:103`
`source_snapshot_from_document` | `SourceSnapshotFromDocument` | method | `backend/content/src/repositories/document_ingestion_outbox.py:73`
`enqueue` | `Enqueue` | method | `backend/content/src/repositories/document_ingestion_outbox.py:77`
`claim` | `Claim` | method | `backend/content/src/repositories/document_ingestion_outbox.py:158`
`complete` | `Complete` | method | `backend/content/src/repositories/document_ingestion_outbox.py:191`
`retry` | `Retry` | method | `backend/content/src/repositories/document_ingestion_outbox.py:212`
`list_documents_requiring_dispatch` | `ListDocumentsRequiringDispatch` | method | `backend/content/src/repositories/document_ingestion_outbox.py:248`
`recover_expired_indexing_claims` | `RecoverExpiredIndexingClaims` | method | `backend/content/src/repositories/document_ingestion_outbox.py:281`
`find_one` | `FindOne` | method | `backend/content/src/repositories/folder.py:6`
`insert_one` | `InsertOne` | method | `backend/content/src/repositories/folder.py:10`
`delete_one` | `DeleteOne` | method | `backend/content/src/repositories/folder.py:14`
`query` | `Query` | method | `backend/content/src/repositories/folder.py:18`
`bulk_delete_documents` | `Ctrl_Bulk` | route method in grouped control | `backend/content/src/api/document/bulk.py:13`
`bulk_restore_documents` | `Ctrl_Bulk` | route method in grouped control | `backend/content/src/api/document/bulk.py:22`
`bulk_move_documents` | `Ctrl_Bulk` | route method in grouped control | `backend/content/src/api/document/bulk.py:31`
`bulk_export_documents` | `Ctrl_Bulk` | route method in grouped control | `backend/content/src/api/document/bulk.py:41`
`create_document` | `Ctrl_Crud` | route method in grouped control | `backend/content/src/api/document/crud.py:20`
`get_my_documents` | `Ctrl_Crud` | route method in grouped control | `backend/content/src/api/document/crud.py:32`
`get_trash` | `Ctrl_Crud` | route method in grouped control | `backend/content/src/api/document/crud.py:46`
`list_documents` | `Ctrl_Crud` | route method in grouped control | `backend/content/src/api/document/crud.py:52`
`restore_document` | `Ctrl_Crud` | route method in grouped control | `backend/content/src/api/document/crud.py:70`
`get_document_by_slug` | `Ctrl_Crud` | route method in grouped control | `backend/content/src/api/document/crud.py:78`
`get_document_preview` | `Ctrl_Crud` | route method in grouped control | `backend/content/src/api/document/crud.py:86`
`get_document` | `Ctrl_Crud` | route method in grouped control | `backend/content/src/api/document/crud.py:94`
`update_document_content` | `Ctrl_Crud` | route method in grouped control | `backend/content/src/api/document/crud.py:106`
`update_document` | `Ctrl_Crud` | route method in grouped control | `backend/content/src/api/document/crud.py:116`
`retry_document_indexing` | `Ctrl_Crud` | route method in grouped control | `backend/content/src/api/document/crud.py:126`
`delete_document` | `Ctrl_Crud` | route method in grouped control | `backend/content/src/api/document/crud.py:139`
`set_document_password` | `Ctrl_Crud` | route method in grouped control | `backend/content/src/api/document/crud.py:150`
`unlock_document` | `Ctrl_Crud` | route method in grouped control | `backend/content/src/api/document/crud.py:160`
`get_folders` | `Ctrl_Hierarchy` | route method in grouped control | `backend/content/src/api/document/hierarchy.py:14`
`create_folder` | `Ctrl_Hierarchy` | route method in grouped control | `backend/content/src/api/document/hierarchy.py:22`
`delete_folder` | `Ctrl_Hierarchy` | route method in grouped control | `backend/content/src/api/document/hierarchy.py:31`
`move_document_to_folder` | `Ctrl_Hierarchy` | route method in grouped control | `backend/content/src/api/document/hierarchy.py:39`
`transfer_document` | `Ctrl_Hierarchy` | route method in grouped control | `backend/content/src/api/document/hierarchy.py:50`
`internal_document_data` | `Ctrl_Internal` | route method in grouped control | `backend/content/src/api/document/internal.py:14`
`get_internal_document` | `Ctrl_Internal` | route method in grouped control | `backend/content/src/api/document/internal.py:20`
`get_internal_document_stats` | `Ctrl_Internal` | route method in grouped control | `backend/content/src/api/document/internal.py:26`
`exchange_internal_document` | `Ctrl_Internal` | route method in grouped control | `backend/content/src/api/document/internal.py:32`
`get_document_analytics` | `Ctrl_Metadata` | route method in grouped control | `backend/content/src/api/document/metadata.py:13`
`get_document_academic` | `Ctrl_Metadata` | route method in grouped control | `backend/content/src/api/document/metadata.py:21`
`get_approval_queue` | `Ctrl_Metadata` | route method in grouped control | `backend/content/src/api/document/metadata.py:33`
`get_trending_documents` | `Ctrl_Metadata` | route method in grouped control | `backend/content/src/api/document/metadata.py:41`
`get_suggested_documents` | `Ctrl_Metadata` | route method in grouped control | `backend/content/src/api/document/metadata.py:49`
`get_tags_categories` | `Ctrl_Tag` | route method in grouped control | `backend/content/src/api/document/tag.py:14`
`get_trending_tags` | `Ctrl_Tag` | route method in grouped control | `backend/content/src/api/document/tag.py:22`
`toggle_star_document` | `Ctrl_Tag` | route method in grouped control | `backend/content/src/api/document/tag.py:30`
`update_tags` | `Ctrl_Tag` | route method in grouped control | `backend/content/src/api/document/tag.py:38`
`save_version` | `Ctrl_Version` | route method in grouped control | `backend/content/src/api/version.py:13`
`get_document_versions` | `Ctrl_Version` | route method in grouped control | `backend/content/src/api/version.py:27`
`restore_version` | `Ctrl_Version` | route method in grouped control | `backend/content/src/api/version.py:37`
`health_check` | `Ctrl_Main` | route method in grouped control | `backend/content/src/main.py:47`
`readiness_check` | `Ctrl_Main` | route method in grouped control | `backend/content/src/main.py:52`
