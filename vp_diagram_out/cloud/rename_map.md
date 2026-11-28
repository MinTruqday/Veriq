# Rename map — cloud

Tên code | Tên sơ đồ | Loại | Căn cứ
---|---|---|---
`storage_items` | `StorageItem` | collection/table | `backend/cloud/src/core/infrastructure/database.py:35, backend/cloud/src/core/infrastructure/database.py:38, backend/cloud/src/core/infrastructure/database.py:41`
`ai_processed` | `AiProcessed` | field | `backend/cloud/src/schemas/storage.py:32`
`broken_links` | `BrokenLinks` | field | `backend/cloud/src/schemas/storage.py:34`
`color` | `Color` | field | `backend/cloud/src/schemas/storage.py:24`
`created_at` | `CreatedAt` | field | `backend/cloud/src/schemas/storage.py:123`
`description` | `Description` | field | `backend/cloud/src/schemas/storage.py:23`
`duplicate_of` | `DuplicateOf` | field | `backend/cloud/src/schemas/storage.py:30`
`entities` | `Entities` | field | `backend/cloud/src/schemas/storage.py:33`
`environment_ready` | `EnvironmentReady` | field | `backend/cloud/src/schemas/storage.py:31`
`is_duplicate` | `IsDuplicate` | field | `backend/cloud/src/schemas/storage.py:29`
`is_folder` | `IsFolder` | field | `backend/cloud/src/schemas/storage.py:114`
`is_locked` | `IsLocked` | field | `backend/cloud/src/schemas/storage.py:35`
`is_public` | `IsPublic` | field | `backend/cloud/src/schemas/storage.py:120`
`is_shortcut` | `IsShortcut` | field | `backend/cloud/src/schemas/storage.py:27`
`is_starred` | `IsStarred` | field | `backend/cloud/src/schemas/storage.py:119`
`is_trashed` | `IsTrashed` | field | `backend/cloud/src/schemas/storage.py:118`
`locked_at` | `LockedAt` | field | `backend/cloud/src/schemas/storage.py:37`
`locked_by` | `LockedBy` | field | `backend/cloud/src/schemas/storage.py:36`
`mime_type` | `MimeType` | field | `backend/cloud/src/schemas/storage.py:116`
`name` | `Name` | field | `backend/cloud/src/schemas/storage.py:21`
`owner_id` | `OwnerId` | field | `backend/cloud/src/schemas/storage.py:113`
`parent_id` | `ParentId` | field | `backend/cloud/src/schemas/storage.py:22`
`share_token` | `ShareToken` | field | `backend/cloud/src/schemas/storage.py:121`
`shared_with` | `SharedWith` | field | `backend/cloud/src/schemas/storage.py:26`
`size` | `Size` | field | `backend/cloud/src/schemas/storage.py:115`
`tags` | `Tags` | field | `backend/cloud/src/schemas/storage.py:25`
`target_id` | `TargetId` | field | `backend/cloud/src/schemas/storage.py:28`
`updated_at` | `UpdatedAt` | field | `backend/cloud/src/schemas/storage.py:124`
`url` | `Url` | field | `backend/cloud/src/schemas/storage.py:117`
`versions` | `Versions` | field | `backend/cloud/src/schemas/storage.py:122`
`temp_chat_files` | `TempChatFile` | collection/table | `backend/cloud/src/core/infrastructure/database.py:52, backend/cloud/src/repositories/storage.py:102, backend/cloud/src/repositories/storage.py:105`
`_id` | `TempChatFileId` | field | `backend/cloud/src/repositories/storage.py:102, backend/cloud/src/repositories/storage.py:105`
`item_id` | `ItemId` | field | `backend/cloud/src/repositories/storage.py:89`
`owner_id` | `OwnerId` | field | `backend/cloud/src/repositories/storage.py:69, backend/cloud/src/repositories/storage.py:75`
`token` | `Token` | field | `backend/cloud/src/repositories/storage.py:117`
`storage_share_links` | `StorageShareLink` | collection/table | `backend/cloud/src/core/infrastructure/database.py:53, backend/cloud/src/repositories/storage.py:96`
`storage_activities` | `StorageActivity` | collection/table | `backend/cloud/src/repositories/storage.py:83`
`file_requests` | `FileRequest` | collection/table | `backend/cloud/src/repositories/storage.py:111`
`log_activity` | `LogActivity` | method | `backend/cloud/src/services/activity.py:13`
`get_item_activities` | `GetItemActivities` | method | `backend/cloud/src/services/activity.py:37`
`save_chunk` | `SaveChunk` | method | `backend/cloud/src/services/chunk.py:16`
`generate_download_url` | `GenerateDownloadUrl` | method | `backend/cloud/src/services/download.py:9`
`create_file_record` | `CreateFileRecord` | method | `backend/cloud/src/services/file.py:14`
`get_file_by_id` | `GetFileById` | method | `backend/cloud/src/services/file.py:43`
`update_file_metadata` | `UpdateFileMetadata` | method | `backend/cloud/src/services/file.py:52`
`rename_file` | `RenameFile` | method | `backend/cloud/src/services/file.py:65`
`move_file` | `MoveFile` | method | `backend/cloud/src/services/file.py:75`
`get_storage_quota` | `GetStorageQuota` | method | `backend/cloud/src/services/file.py:96`
`create_request` | `CreateRequest` | method | `backend/cloud/src/services/file_request.py:13`
`validate_request` | `ValidateRequest` | method | `backend/cloud/src/services/file_request.py:45`
`create_folder` | `CreateFolder` | method | `backend/cloud/src/services/folder.py:12`
`get_folder_contents` | `GetFolderContents` | method | `backend/cloud/src/services/folder.py:39`
`get_folder_tree` | `GetFolderTree` | method | `backend/cloud/src/services/folder.py:44`
`rename_folder` | `RenameFolder` | method | `backend/cloud/src/services/folder.py:49`
`move_folder` | `MoveFolder` | method | `backend/cloud/src/services/folder.py:59`
`serialize_internal` | `SerializeInternal` | method | `backend/cloud/src/services/internal_storage.py:10`
`execute` | `Execute` | method | `backend/cloud/src/services/internal_storage.py:24`
`duplicate_item` | `DuplicateItem` | method | `backend/cloud/src/services/search.py:13`
`set_folder_color` | `SetFolderColor` | method | `backend/cloud/src/services/search.py:33`
`update_item_tags` | `UpdateItemTags` | method | `backend/cloud/src/services/search.py:47`
`create_protected_share_link` | `CreateProtectedShareLink` | method | `backend/cloud/src/services/share.py:15`
`validate_protected_share_link` | `ValidateProtectedShareLink` | method | `backend/cloud/src/services/share.py:46`
`toggle_star_item` | `ToggleStarItem` | method | `backend/cloud/src/services/star.py:8`
`get_starred_items` | `GetStarredItems` | method | `backend/cloud/src/services/star.py:21`
`create_item` | `CreateItem` | method | `backend/cloud/src/services/storage.py:34`
`create_shortcut` | `CreateShortcut` | method | `backend/cloud/src/services/storage.py:69`
`get_items_by_parent` | `GetItemsByParent` | method | `backend/cloud/src/services/storage.py:93`
`search_items` | `SearchItems` | method | `backend/cloud/src/services/storage.py:118`
`get_item` | `GetItem` | method | `backend/cloud/src/services/storage.py:134`
`get_accessible_item` | `GetAccessibleItem` | method | `backend/cloud/src/services/storage.py:144`
`update_item` | `UpdateItem` | method | `backend/cloud/src/services/storage.py:155`
`copy_item` | `CopyItem` | method | `backend/cloud/src/services/storage.py:228`
`bulk_action` | `BulkAction` | method | `backend/cloud/src/services/storage.py:261`
`set_starred` | `SetStarred` | method | `backend/cloud/src/services/storage.py:298`
`set_tags_and_color` | `SetTagsAndColor` | method | `backend/cloud/src/services/storage.py:315`
`get_storage_quota` | `GetStorageQuota` | method | `backend/cloud/src/services/storage_analytics.py:4`
`get_quota_analytics` | `GetQuotaAnalytics` | method | `backend/cloud/src/services/storage_analytics.py:38`
`object_prefixes` | `ObjectPrefixes` | method | `backend/cloud/src/services/storage_paths.py:1`
`get_public_item` | `GetPublicItem` | method | `backend/cloud/src/services/storage_sharing.py:11`
`share_item` | `ShareItem` | method | `backend/cloud/src/services/storage_sharing.py:18`
`get_recent_items` | `GetRecentItems` | method | `backend/cloud/src/services/storage_sharing.py:46`
`share_internal` | `ShareInternal` | method | `backend/cloud/src/services/storage_sharing.py:59`
`revoke_internal_share` | `RevokeInternalShare` | method | `backend/cloud/src/services/storage_sharing.py:63`
`get_shared_with_me_items` | `GetSharedWithMeItems` | method | `backend/cloud/src/services/storage_sharing.py:75`
`delete_item` | `DeleteItem` | method | `backend/cloud/src/services/storage_trash.py:35`
`get_trashed_items` | `GetTrashedItems` | method | `backend/cloud/src/services/storage_trash.py:66`
`restore_from_trash` | `RestoreFromTrash` | method | `backend/cloud/src/services/storage_trash.py:74`
`empty_trash` | `EmptyTrash` | method | `backend/cloud/src/services/storage_trash.py:99`
`add_version` | `AddVersion` | method | `backend/cloud/src/services/storage_versions.py:32`
`lock_item` | `LockItem` | method | `backend/cloud/src/services/storage_versions.py:81`
`unlock_item` | `UnlockItem` | method | `backend/cloud/src/services/storage_versions.py:102`
`get_versions` | `GetVersions` | method | `backend/cloud/src/services/storage_versions.py:119`
`rollback_version` | `RollbackVersion` | method | `backend/cloud/src/services/storage_versions.py:148`
`move_to_trash` | `MoveToTrash` | method | `backend/cloud/src/services/trash.py:10`
`restore_from_trash` | `RestoreFromTrash` | method | `backend/cloud/src/services/trash.py:22`
`empty_trash` | `EmptyTrash` | method | `backend/cloud/src/services/trash.py:32`
`auto_purge_expired_trash` | `AutoPurgeExpiredTrash` | method | `backend/cloud/src/services/trash.py:43`
`validate_filename` | `ValidateFilename` | method | `backend/cloud/src/services/upload.py:59`
`read_limited` | `ReadLimited` | method | `backend/cloud/src/services/upload.py:77`
`object_path` | `ObjectPath` | method | `backend/cloud/src/services/upload.py:86`
`upload_image` | `UploadImage` | method | `backend/cloud/src/services/upload.py:113`
`upload_document` | `UploadDocument` | method | `backend/cloud/src/services/upload.py:133`
`get_presigned_url` | `GetPresignedUrl` | method | `backend/cloud/src/services/upload.py:162`
`get_presigned_upload_url` | `GetPresignedUploadUrl` | method | `backend/cloud/src/services/upload.py:172`
`validate_svg` | `ValidateSvg` | method | `backend/cloud/src/services/upload.py:194`
`file_size` | `FileSize` | method | `backend/cloud/src/services/upload.py:205`
`validate_size` | `ValidateSize` | method | `backend/cloud/src/services/upload.py:214`
`enforce_quota` | `EnforceQuota` | method | `backend/cloud/src/services/upload.py:221`
`register_item` | `RegisterItem` | method | `backend/cloud/src/services/upload.py:227`
`can_download` | `CanDownload` | method | `backend/cloud/src/services/upload.py:241`
`reserve` | `Reserve` | method | `backend/cloud/src/services/upload.py:261`
`confirm_reservation` | `ConfirmReservation` | method | `backend/cloud/src/services/upload.py:265`
`verify_stored_object` | `VerifyStoredObject` | method | `backend/cloud/src/services/upload.py:275`
`record_temporary_file` | `RecordTemporaryFile` | method | `backend/cloud/src/services/upload.py:287`
`create_file_version` | `CreateFileVersion` | method | `backend/cloud/src/services/version.py:8`
`get_file_versions` | `GetFileVersions` | method | `backend/cloud/src/services/version.py:13`
`restore_file_version` | `RestoreFileVersion` | method | `backend/cloud/src/services/version.py:20`
`collection` | `Collection` | method | `backend/cloud/src/repositories/storage.py:11`
`find_one` | `FindOne` | method | `backend/cloud/src/repositories/storage.py:14`
`find_many` | `FindMany` | method | `backend/cloud/src/repositories/storage.py:17`
`insert` | `Insert` | method | `backend/cloud/src/repositories/storage.py:31`
`update_one` | `UpdateOne` | method | `backend/cloud/src/repositories/storage.py:34`
`update_many` | `UpdateMany` | method | `backend/cloud/src/repositories/storage.py:37`
`find_one_and_update` | `FindOneAndUpdate` | method | `backend/cloud/src/repositories/storage.py:40`
`delete_one` | `DeleteOne` | method | `backend/cloud/src/repositories/storage.py:47`
`delete_many` | `DeleteMany` | method | `backend/cloud/src/repositories/storage.py:50`
`count` | `Count` | method | `backend/cloud/src/repositories/storage.py:53`
`aggregate` | `Aggregate` | method | `backend/cloud/src/repositories/storage.py:56`
`replace_version` | `ReplaceVersion` | method | `backend/cloud/src/repositories/storage.py:59`
`collection` | `Collection` | method | `backend/cloud/src/repositories/storage.py:82`
`insert` | `Insert` | method | `backend/cloud/src/repositories/storage.py:85`
`list_for_item` | `ListForItem` | method | `backend/cloud/src/repositories/storage.py:88`
`collection` | `Collection` | method | `backend/cloud/src/repositories/storage.py:95`
`insert` | `Insert` | method | `backend/cloud/src/repositories/storage.py:98`
`find` | `Find` | method | `backend/cloud/src/repositories/storage.py:101`
`delete` | `Delete` | method | `backend/cloud/src/repositories/storage.py:104`
`collection` | `Collection` | method | `backend/cloud/src/repositories/storage.py:110`
`insert` | `Insert` | method | `backend/cloud/src/repositories/storage.py:113`
`find` | `Find` | method | `backend/cloud/src/repositories/storage.py:116`
`collection` | `Collection` | method | `backend/cloud/src/repositories/storage.py:122`
`insert` | `Insert` | method | `backend/cloud/src/repositories/storage.py:125`
`key` | `Key` | method | `backend/cloud/src/repositories/storage.py:131`
`reserve` | `Reserve` | method | `backend/cloud/src/repositories/storage.py:134`
`consume` | `Consume` | method | `backend/cloud/src/repositories/storage.py:137`
`DefectsPage` | `GD_DefectsPage` | page/boundary | ``
`ExecutionPage` | `GD_ExecutionPage` | page/boundary | ``
`TestDesignPage` | `GD_TestDesignPage` | page/boundary | ``
`upload_chunk` | `Ctrl_Chunk` | route method in grouped control | `backend/cloud/src/api/chunk.py:16`
`get_download_url` | `Ctrl_Download` | route method in grouped control | `backend/cloud/src/api/download.py:13`
`create_file_record` | `Ctrl_File` | route method in grouped control | `backend/cloud/src/api/file.py:14`
`get_storage_quota` | `Ctrl_File` | route method in grouped control | `backend/cloud/src/api/file.py:26`
`get_file_metadata` | `Ctrl_File` | route method in grouped control | `backend/cloud/src/api/file.py:35`
`update_file_metadata` | `Ctrl_File` | route method in grouped control | `backend/cloud/src/api/file.py:47`
`rename_file` | `Ctrl_File` | route method in grouped control | `backend/cloud/src/api/file.py:58`
`move_file` | `Ctrl_File` | route method in grouped control | `backend/cloud/src/api/file.py:72`
`create_file_request` | `Ctrl_FileRequest` | route method in grouped control | `backend/cloud/src/api/file_request.py:14`
`validate_file_request` | `Ctrl_FileRequest` | route method in grouped control | `backend/cloud/src/api/file_request.py:33`
`create_folder` | `Ctrl_Folder` | route method in grouped control | `backend/cloud/src/api/folder.py:13`
`get_folder_contents` | `Ctrl_Folder` | route method in grouped control | `backend/cloud/src/api/folder.py:29`
`get_folder_tree` | `Ctrl_Folder` | route method in grouped control | `backend/cloud/src/api/folder.py:39`
`rename_folder` | `Ctrl_Folder` | route method in grouped control | `backend/cloud/src/api/folder.py:48`
`move_folder` | `Ctrl_Folder` | route method in grouped control | `backend/cloud/src/api/folder.py:62`
`store_qa_requirement_source` | `Ctrl_Internal` | route method in grouped control | `backend/cloud/src/api/internal.py:18`
`read_qa_requirement_source` | `Ctrl_Internal` | route method in grouped control | `backend/cloud/src/api/internal.py:47`
`delete_qa_requirement_source` | `Ctrl_Internal` | route method in grouped control | `backend/cloud/src/api/internal.py:63`
`internal_storage_data` | `Ctrl_Internal` | route method in grouped control | `backend/cloud/src/api/internal.py:72`
`store_report_asset` | `Ctrl_Internal` | route method in grouped control | `backend/cloud/src/api/internal.py:83`
`read_report_asset` | `Ctrl_Internal` | route method in grouped control | `backend/cloud/src/api/internal.py:96`
`duplicate_item` | `Ctrl_Search` | route method in grouped control | `backend/cloud/src/api/search.py:13`
`set_folder_color` | `Ctrl_Search` | route method in grouped control | `backend/cloud/src/api/search.py:22`
`update_item_tags` | `Ctrl_Search` | route method in grouped control | `backend/cloud/src/api/search.py:32`
`create_protected_share_link` | `Ctrl_Share` | route method in grouped control | `backend/cloud/src/api/share.py:14`
`validate_protected_share_link` | `Ctrl_Share` | route method in grouped control | `backend/cloud/src/api/share.py:25`
`toggle_star_item` | `Ctrl_Star` | route method in grouped control | `backend/cloud/src/api/star.py:13`
`get_starred_items` | `Ctrl_Star` | route method in grouped control | `backend/cloud/src/api/star.py:22`
`create_folder` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:28`
`create_file` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:43`
`list_items` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:63`
`search_items` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:81`
`get_recent_items` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:96`
`get_storage_quota` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:110`
`create_shortcut` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:123`
`download_zip` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:140`
`update_item` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:191`
`delete_item` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:221`
`copy_item` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:252`
`add_version` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:269`
`share_archive` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:287`
`get_public_item` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:299`
`bulk_action` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:314`
`lock_item` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:329`
`unlock_item` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:343`
`get_preview_url` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:357`
`get_item_activities` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:390`
`get_file_versions` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:408`
`rollback_file_version` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:425`
`toggle_starred` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:442`
`update_tags_and_color` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:459`
`get_trashed_items` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:476`
`restore_trash_item` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:489`
`empty_trash` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:505`
`get_quota_analytics` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:514`
`share_internal` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:527`
`revoke_internal_share` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:540`
`get_shared_with_me` | `Ctrl_Storage` | route method in grouped control | `backend/cloud/src/api/storage.py:553`
`move_to_trash` | `Ctrl_Trash` | route method in grouped control | `backend/cloud/src/api/trash.py:13`
`restore_from_trash` | `Ctrl_Trash` | route method in grouped control | `backend/cloud/src/api/trash.py:23`
`empty_trash` | `Ctrl_Trash` | route method in grouped control | `backend/cloud/src/api/trash.py:33`
`auto_purge_trash` | `Ctrl_Trash` | route method in grouped control | `backend/cloud/src/api/trash.py:42`
`upload_image` | `Ctrl_Upload` | route method in grouped control | `backend/cloud/src/api/upload.py:26`
`upload_document` | `Ctrl_Upload` | route method in grouped control | `backend/cloud/src/api/upload.py:37`
`upload_asset` | `Ctrl_Upload` | route method in grouped control | `backend/cloud/src/api/upload.py:47`
`get_presigned_url_for_upload` | `Ctrl_Upload` | route method in grouped control | `backend/cloud/src/api/upload.py:62`
`confirm_upload` | `Ctrl_Upload` | route method in grouped control | `backend/cloud/src/api/upload.py:95`
`get_presigned_preview_url` | `Ctrl_Upload` | route method in grouped control | `backend/cloud/src/api/upload.py:134`
`get_presigned_download_url` | `Ctrl_Upload` | route method in grouped control | `backend/cloud/src/api/upload.py:150`
`get_message_attachment_content` | `Ctrl_Upload` | route method in grouped control | `backend/cloud/src/api/upload.py:164`
`upload_chunk` | `Ctrl_Upload` | route method in grouped control | `backend/cloud/src/api/upload.py:177`
`upload_via_request` | `Ctrl_Upload` | route method in grouped control | `backend/cloud/src/api/upload.py:236`
`create_file_version` | `Ctrl_Version` | route method in grouped control | `backend/cloud/src/api/version.py:13`
`get_file_versions` | `Ctrl_Version` | route method in grouped control | `backend/cloud/src/api/version.py:24`
`restore_file_version` | `Ctrl_Version` | route method in grouped control | `backend/cloud/src/api/version.py:33`
`health_check` | `Ctrl_Main` | route method in grouped control | `backend/cloud/src/main.py:73`
`readiness_check` | `Ctrl_Main` | route method in grouped control | `backend/cloud/src/main.py:78`
