# Rename map — authentication

Tên code | Tên sơ đồ | Loại | Căn cứ
---|---|---|---
`platform_state` | `PlatformState` | collection/table | `backend/authentication/src/core/infrastructure/database.py:26, backend/authentication/src/repositories/identity.py:27`
`_id` | `PlatformStateId` | field | `backend/authentication/src/core/infrastructure/database.py:27, backend/authentication/src/repositories/identity.py:28`
`revision` | `Revision` | field | `backend/authentication/src/core/infrastructure/database.py:28, backend/authentication/src/repositories/identity.py:29`
`auth_credentials` | `AuthCredential` | collection/table | `backend/authentication/src/core/infrastructure/database.py:31, backend/authentication/src/core/infrastructure/database.py:32, backend/authentication/src/repositories/identity.py:107`
`_id` | `AuthCredentialId` | field | `backend/authentication/src/repositories/identity.py:107, backend/authentication/src/repositories/identity.py:202`
`avatar_url` | `AvatarUrl` | field | `backend/authentication/src/schemas/identity.py:37`
`bio` | `Bio` | field | `backend/authentication/src/schemas/identity.py:36`
`blocked_users` | `BlockedUsers` | field | `backend/authentication/src/schemas/identity.py:65`
`bookmarks` | `Bookmarks` | field | `backend/authentication/src/schemas/identity.py:44`
`cover_url` | `CoverUrl` | field | `backend/authentication/src/schemas/identity.py:38`
`created_at` | `CreatedAt` | field | `backend/authentication/src/schemas/identity.py:92`
`creator_status` | `CreatorStatus` | field | `backend/authentication/src/schemas/identity.py:49`
`donation_link` | `DonationLink` | field | `backend/authentication/src/schemas/identity.py:47`
`email` | `Email` | field | `backend/authentication/src/schemas/identity.py:31`
`email_verified` | `EmailVerified` | field | `backend/authentication/src/repositories/identity.py:455, backend/authentication/src/repositories/identity.py:475`
`email_verified_at` | `EmailVerifiedAt` | field | `backend/authentication/src/repositories/identity.py:455, backend/authentication/src/repositories/identity.py:475`
`full_name` | `FullName` | field | `backend/authentication/src/schemas/identity.py:32`
`is_active` | `IsActive` | field | `backend/authentication/src/schemas/identity.py:94`
`is_kyc_verified` | `IsKycVerified` | field | `backend/authentication/src/schemas/identity.py:95`
`is_shadowbanned` | `IsShadowbanned` | field | `backend/authentication/src/schemas/identity.py:45`
`is_verified` | `IsVerified` | field | `backend/authentication/src/schemas/identity.py:50`
`kyc_status` | `KycStatus` | field | `backend/authentication/src/schemas/identity.py:48`
`last_bank_update` | `LastBankUpdate` | field | `backend/authentication/src/schemas/identity.py:97`
`last_password_change` | `LastPasswordChange` | field | `backend/authentication/src/schemas/identity.py:96`
`last_read_date` | `LastReadDate` | field | `backend/authentication/src/schemas/identity.py:90`
`locale` | `Locale` | field | `backend/authentication/src/schemas/identity.py:34`
`location` | `Location` | field | `backend/authentication/src/schemas/identity.py:39`
`login_security` | `LoginSecurity` | field | `backend/authentication/src/repositories/identity.py:227, backend/authentication/src/repositories/identity.py:232`
`password_hash` | `PasswordHash` | field | `backend/authentication/src/schemas/identity.py:91`
`pending_email` | `PendingEmail` | field | `backend/authentication/src/repositories/identity.py:469, backend/authentication/src/repositories/identity.py:482`
`pending_email_requested_at` | `PendingEmailRequestedAt` | field | `backend/authentication/src/repositories/identity.py:482`
`permissions` | `Permissions` | field | `backend/authentication/src/schemas/identity.py:46`
`pinned_documents` | `PinnedDocuments` | field | `backend/authentication/src/schemas/identity.py:43`
`settings` | `Settings` | field | `backend/authentication/src/schemas/identity.py:66`
`slug` | `Slug` | field | `backend/authentication/src/schemas/identity.py:33`
`social_links` | `SocialLinks` | field | `backend/authentication/src/schemas/identity.py:42`
`storage_limit` | `StorageLimit` | field | `backend/authentication/src/schemas/identity.py:51`
`system_role` | `SystemRole` | field | `backend/authentication/src/schemas/identity.py:35`
`timezone` | `Timezone` | field | `backend/authentication/src/schemas/identity.py:41`
`tos_accepted_at` | `TosAcceptedAt` | field | `backend/authentication/src/schemas/identity.py:63`
`updated_at` | `UpdatedAt` | field | `backend/authentication/src/schemas/identity.py:93`
`website` | `Website` | field | `backend/authentication/src/schemas/identity.py:40`
`welcome_message` | `WelcomeMessage` | field | `backend/authentication/src/schemas/identity.py:64`
`sessions` | `Session` | collection/table | `backend/authentication/src/core/infrastructure/database.py:35, backend/authentication/src/core/infrastructure/database.py:36, backend/authentication/src/core/infrastructure/database.py:41`
`_id` | `SessionId` | field | `backend/authentication/src/repositories/identity.py:272, backend/authentication/src/repositories/identity.py:307`
`created_at` | `CreatedAt` | field | `backend/authentication/src/repositories/identity.py:272`
`expires_at` | `ExpiresAt` | field | `backend/authentication/src/repositories/identity.py:272, backend/authentication/src/repositories/identity.py:288`
`ip` | `Ip` | field | `backend/authentication/src/repositories/identity.py:272`
`last_ip` | `LastIp` | field | `backend/authentication/src/repositories/identity.py:294`
`last_refreshed_at` | `LastRefreshedAt` | field | `backend/authentication/src/repositories/identity.py:272, backend/authentication/src/repositories/identity.py:294`
`refresh_token_hash` | `RefreshTokenHash` | field | `backend/authentication/src/core/infrastructure/database.py:39, backend/authentication/src/repositories/identity.py:272`
`revoked_at` | `RevokedAt` | field | `backend/authentication/src/repositories/identity.py:272, backend/authentication/src/repositories/identity.py:288`
`user_id` | `UserId` | field | `backend/authentication/src/repositories/identity.py:272, backend/authentication/src/repositories/identity.py:307`
`password_reset_tokens` | `PasswordResetToken` | collection/table | `backend/authentication/src/core/infrastructure/database.py:42, backend/authentication/src/core/infrastructure/database.py:45, backend/authentication/src/repositories/identity.py:394`
`_id` | `PasswordResetTokenId` | field | `backend/authentication/src/services/session.py:315`
`created_at` | `CreatedAt` | field | `backend/authentication/src/services/session.py:315`
`email` | `Email` | field | `backend/authentication/src/repositories/identity.py:396, backend/authentication/src/services/session.py:315`
`expires_at` | `ExpiresAt` | field | `backend/authentication/src/services/session.py:315`
`token` | `Token` | field | `backend/authentication/src/services/session.py:315`
`token_hash` | `TokenHash` | field | `backend/authentication/src/core/infrastructure/database.py:43`
`used` | `Used` | field | `backend/authentication/src/repositories/identity.py:396, backend/authentication/src/repositories/identity.py:397`
`used_at` | `UsedAt` | field | `backend/authentication/src/repositories/identity.py:421`
`email_verification_tokens` | `EmailVerificationToken` | collection/table | `backend/authentication/src/core/infrastructure/database.py:46, backend/authentication/src/core/infrastructure/database.py:47, backend/authentication/src/core/infrastructure/database.py:48`
`_id` | `EmailVerificationTokenId` | field | `backend/authentication/src/services/session.py:94`
`created_at` | `CreatedAt` | field | `backend/authentication/src/services/session.py:94`
`email` | `Email` | field | `backend/authentication/src/services/session.py:94`
`expires_at` | `ExpiresAt` | field | `backend/authentication/src/repositories/identity.py:440, backend/authentication/src/services/session.py:94`
`invalidated_at` | `InvalidatedAt` | field | `backend/authentication/src/repositories/identity.py:433`
`purpose` | `Purpose` | field | `backend/authentication/src/services/session.py:94`
`requested_ip` | `RequestedIp` | field | `backend/authentication/src/services/session.py:94`
`token` | `Token` | field | `backend/authentication/src/services/session.py:94`
`token_hash` | `TokenHash` | field | `backend/authentication/src/repositories/identity.py:440`
`used` | `Used` | field | `backend/authentication/src/repositories/identity.py:432, backend/authentication/src/repositories/identity.py:433`
`used_at` | `UsedAt` | field | `backend/authentication/src/repositories/identity.py:445`
`user_id` | `UserId` | field | `backend/authentication/src/repositories/identity.py:432, backend/authentication/src/services/session.py:94`
`audit_logs` | `AuditLog` | collection/table | `backend/authentication/src/core/infrastructure/database.py:49, backend/authentication/src/repositories/identity.py:265, backend/authentication/src/repositories/platform.py:82`
`action` | `Action` | field | `backend/authentication/src/services/account.py:213, backend/authentication/src/services/platform.py:60`
`actor_email` | `ActorEmail` | field | `backend/authentication/src/services/account.py:213, backend/authentication/src/services/platform.py:60`
`actor_slug` | `ActorSlug` | field | `backend/authentication/src/services/session.py:190`
`changes` | `Changes` | field | `backend/authentication/src/services/platform_accounts.py:95`
`delivered` | `Delivered` | field | `backend/authentication/src/services/session.py:114`
`details` | `Details` | field | `backend/authentication/src/services/platform.py:60`
`ip` | `Ip` | field | `backend/authentication/src/services/session.py:114, backend/authentication/src/services/session.py:158`
`reason` | `Reason` | field | `backend/authentication/src/services/platform.py:60, backend/authentication/src/services/platform_accounts.py:95`
`target_user_id` | `TargetUserId` | field | `backend/authentication/src/services/account.py:213, backend/authentication/src/services/platform.py:60`
`timestamp` | `Timestamp` | field | `backend/authentication/src/services/account.py:213, backend/authentication/src/services/platform.py:60`
`system_configs` | `SystemConfig` | collection/table | `backend/authentication/src/repositories/identity.py:103, backend/authentication/src/repositories/identity.py:239, backend/authentication/src/services/platform.py:103`
`created_at` | `CreatedAt` | field | `backend/authentication/src/services/platform.py:107, backend/authentication/src/services/platform_projects.py:136`
`project_creation_policy` | `ProjectCreationPolicy` | field | `backend/authentication/src/services/platform_projects.py:131`
`type` | `Type` | field | `backend/authentication/src/repositories/identity.py:103, backend/authentication/src/repositories/identity.py:240`
`updated_at` | `UpdatedAt` | field | `backend/authentication/src/services/platform.py:106, backend/authentication/src/services/platform_projects.py:131`
`updated_by` | `UpdatedBy` | field | `backend/authentication/src/services/platform.py:106, backend/authentication/src/services/platform_projects.py:131`
`ai_providers` | `AiProvider` | collection/table | `backend/authentication/src/repositories/platform.py:17, backend/authentication/src/repositories/platform.py:21, backend/authentication/src/services/platform_ai.py:66`
`_id` | `AiProviderId` | field | `backend/authentication/src/repositories/platform.py:22`
`created_at` | `CreatedAt` | field | `backend/authentication/src/repositories/platform.py:23`
`enabled` | `Enabled` | field | `backend/authentication/src/schemas/platform.py:53`
`max_output_tokens` | `MaxOutputTokens` | field | `backend/authentication/src/schemas/platform.py:56`
`model` | `Model` | field | `backend/authentication/src/schemas/platform.py:54`
`secret_reference` | `SecretReference` | field | `backend/authentication/src/schemas/platform.py:57`
`timeout_seconds` | `TimeoutSeconds` | field | `backend/authentication/src/schemas/platform.py:55`
`ai_models` | `AiModel` | collection/table | `backend/authentication/src/repositories/platform.py:30, backend/authentication/src/repositories/platform.py:34, backend/authentication/src/repositories/platform.py:38`
`_id` | `AiModelId` | field | `backend/authentication/src/repositories/platform.py:39, backend/authentication/src/repositories/platform.py:48`
`capabilities` | `Capabilities` | field | `backend/authentication/src/schemas/platform.py:66`
`created_at` | `CreatedAt` | field | `backend/authentication/src/services/platform_ai.py:98`
`enabled` | `Enabled` | field | `backend/authentication/src/schemas/platform.py:65`
`model` | `Model` | field | `backend/authentication/src/schemas/platform.py:63`
`provider_id` | `ProviderId` | field | `backend/authentication/src/schemas/platform.py:62`
`updated_at` | `UpdatedAt` | field | `backend/authentication/src/services/platform_ai.py:98`
`updated_by` | `UpdatedBy` | field | `backend/authentication/src/services/platform_ai.py:98`
`version` | `Version` | field | `backend/authentication/src/schemas/platform.py:64`
`admin_operations` | `AdminOperation` | collection/table | `backend/authentication/src/repositories/platform.py:53, backend/authentication/src/repositories/platform.py:57, backend/authentication/src/repositories/platform.py:67`
`_id` | `AdminOperationId` | field | `backend/authentication/src/repositories/platform.py:69, backend/authentication/src/services/platform_account_controls.py:80`
`action` | `Action` | field | `backend/authentication/src/services/platform_account_controls.py:80`
`affected` | `Affected` | field | `backend/authentication/src/repositories/platform.py:71`
`completed_at` | `CompletedAt` | field | `backend/authentication/src/repositories/platform.py:71`
`confirmed_at` | `ConfirmedAt` | field | `backend/authentication/src/repositories/platform.py:59`
`created_at` | `CreatedAt` | field | `backend/authentication/src/services/platform_account_controls.py:80`
`created_by` | `CreatedBy` | field | `backend/authentication/src/services/platform_account_controls.py:80`
`expires_at` | `ExpiresAt` | field | `backend/authentication/src/services/platform_account_controls.py:80`
`kind` | `Kind` | field | `backend/authentication/src/services/platform_account_controls.py:80`
`missing_user_ids` | `MissingUserIds` | field | `backend/authentication/src/services/platform_account_controls.py:80`
`reason` | `Reason` | field | `backend/authentication/src/services/platform_account_controls.py:80`
`requested_user_ids` | `RequestedUserIds` | field | `backend/authentication/src/services/platform_account_controls.py:80`
`status` | `Status` | field | `backend/authentication/src/repositories/platform.py:59, backend/authentication/src/repositories/platform.py:71`
`user_ids` | `UserIds` | field | `backend/authentication/src/services/platform_account_controls.py:80`
`service_identities` | `ServiceIdentity` | collection/table | `backend/authentication/src/repositories/platform.py:100, backend/authentication/src/repositories/platform.py:113, backend/authentication/src/repositories/platform.py:92`
`_id` | `ServiceIdentityId` | field | `backend/authentication/src/repositories/platform.py:101, backend/authentication/src/services/platform_security.py:40`
`created_at` | `CreatedAt` | field | `backend/authentication/src/services/platform_security.py:40`
`created_by` | `CreatedBy` | field | `backend/authentication/src/services/platform_security.py:40`
`name` | `Name` | field | `backend/authentication/src/schemas/platform.py:111`
`revision` | `Revision` | field | `backend/authentication/src/repositories/platform.py:102, backend/authentication/src/services/platform_security.py:40`
`scopes` | `Scopes` | field | `backend/authentication/src/schemas/platform.py:113`
`secret_reference` | `SecretReference` | field | `backend/authentication/src/schemas/platform.py:112`
`status` | `Status` | field | `backend/authentication/src/repositories/platform.py:101, backend/authentication/src/services/platform_security.py:40`
`updated_at` | `UpdatedAt` | field | `backend/authentication/src/services/platform_security.py:40`
`secret_references` | `SecretReference` | collection/table | `backend/authentication/src/repositories/platform.py:117, backend/authentication/src/repositories/platform.py:121, backend/authentication/src/repositories/platform.py:125`
`_id` | `SecretReferenceId` | field | `backend/authentication/src/repositories/platform.py:126, backend/authentication/src/repositories/platform.py:133`
`created_at` | `CreatedAt` | field | `backend/authentication/src/services/platform_security.py:141`
`created_by` | `CreatedBy` | field | `backend/authentication/src/services/platform_security.py:141`
`name` | `Name` | field | `backend/authentication/src/schemas/platform.py:123`
`provider` | `Provider` | field | `backend/authentication/src/schemas/platform.py:124`
`reference` | `Reference` | field | `backend/authentication/src/schemas/platform.py:125`
`revision` | `Revision` | field | `backend/authentication/src/repositories/platform.py:127, backend/authentication/src/services/platform_security.py:141`
`updated_at` | `UpdatedAt` | field | `backend/authentication/src/services/platform_security.py:141`
`profile` | `Profile` | method | `backend/authentication/src/services/account.py:14`
`update_profile` | `UpdateProfile` | method | `backend/authentication/src/services/account.py:40`
`change_email` | `ChangeEmail` | method | `backend/authentication/src/services/account.py:58`
`resend_verification` | `ResendVerification` | method | `backend/authentication/src/services/account.py:92`
`preferences` | `Preferences` | method | `backend/authentication/src/services/account.py:110`
`update_preferences` | `UpdatePreferences` | method | `backend/authentication/src/services/account.py:115`
`update_notifications` | `UpdateNotifications` | method | `backend/authentication/src/services/account.py:129`
`deactivate` | `Deactivate` | method | `backend/authentication/src/services/account.py:143`
`change_password` | `ChangePassword` | method | `backend/authentication/src/services/account.py:157`
`sessions` | `Sessions` | method | `backend/authentication/src/services/account.py:184`
`revoke_session` | `RevokeSession` | method | `backend/authentication/src/services/account.py:191`
`set_refresh_cookie` | `SetRefreshCookie` | method | `backend/authentication/src/services/auth_cookie.py:4`
`smtp_configuration` | `SmtpConfiguration` | method | `backend/authentication/src/services/email.py:15`
`dispatch` | `Dispatch` | method | `backend/authentication/src/services/email.py:29`
`reset_password_body` | `ResetPasswordBody` | method | `backend/authentication/src/services/email.py:38`
`send_platform_test_email` | `SendPlatformTestEmail` | method | `backend/authentication/src/services/email.py:52`
`send_reset_password_email` | `SendResetPasswordEmail` | method | `backend/authentication/src/services/email.py:61`
`send_email_verification` | `SendEmailVerification` | method | `backend/authentication/src/services/email.py:78`
`lookup_accounts` | `LookupAccounts` | method | `backend/authentication/src/services/internal_identity.py:9`
`resolve_reference` | `ResolveReference` | method | `backend/authentication/src/services/internal_identity.py:33`
`validate_session` | `ValidateSession` | method | `backend/authentication/src/services/internal_identity.py:42`
`project_creation_policy` | `ProjectCreationPolicy` | method | `backend/authentication/src/services/internal_identity.py:59`
`account_by_id` | `AccountById` | method | `backend/authentication/src/services/internal_identity.py:70`
`account_by_email` | `AccountByEmail` | method | `backend/authentication/src/services/internal_identity.py:74`
`security_state` | `SecurityState` | method | `backend/authentication/src/services/internal_identity.py:78`
`account_view` | `AccountView` | method | `backend/authentication/src/services/platform.py:10`
`account_or_404` | `AccountOr404` | method | `backend/authentication/src/services/platform.py:39`
`protect_last_admin` | `ProtectLastAdmin` | method | `backend/authentication/src/services/platform.py:46`
`record_audit` | `RecordAudit` | method | `backend/authentication/src/services/platform.py:58`
`require_system_admin` | `RequireSystemAdmin` | method | `backend/authentication/src/services/platform.py:71`
`masked_config` | `MaskedConfig` | method | `backend/authentication/src/services/platform.py:77`
`get_platform_config` | `GetPlatformConfig` | method | `backend/authentication/src/services/platform.py:85`
`update_platform_config` | `UpdatePlatformConfig` | method | `backend/authentication/src/services/platform.py:94`
`resend_activation` | `ResendActivation` | method | `backend/authentication/src/services/platform_account_controls.py:20`
`anonymize` | `Anonymize` | method | `backend/authentication/src/services/platform_account_controls.py:31`
`preview_bulk` | `PreviewBulk` | method | `backend/authentication/src/services/platform_account_controls.py:72`
`confirm_bulk` | `ConfirmBulk` | method | `backend/authentication/src/services/platform_account_controls.py:97`
`create` | `Create` | method | `backend/authentication/src/services/platform_accounts.py:25`
`list` | `List` | method | `backend/authentication/src/services/platform_accounts.py:49`
`update` | `Update` | method | `backend/authentication/src/services/platform_accounts.py:73`
`detail` | `Detail` | method | `backend/authentication/src/services/platform_accounts.py:107`
`update_profile` | `UpdateProfile` | method | `backend/authentication/src/services/platform_accounts.py:122`
`change_status` | `ChangeStatus` | method | `backend/authentication/src/services/platform_accounts.py:143`
`activate` | `Activate` | method | `backend/authentication/src/services/platform_accounts.py:169`
`disable` | `Disable` | method | `backend/authentication/src/services/platform_accounts.py:175`
`lock` | `Lock` | method | `backend/authentication/src/services/platform_accounts.py:181`
`unlock` | `Unlock` | method | `backend/authentication/src/services/platform_accounts.py:187`
`force_password_reset` | `ForcePasswordReset` | method | `backend/authentication/src/services/platform_accounts.py:193`
`update_system_role` | `UpdateSystemRole` | method | `backend/authentication/src/services/platform_accounts.py:205`
`memberships` | `Memberships` | method | `backend/authentication/src/services/platform_accounts.py:229`
`provider_view` | `ProviderView` | method | `backend/authentication/src/services/platform_ai.py:20`
`providers` | `Providers` | method | `backend/authentication/src/services/platform_ai.py:35`
`update_provider` | `UpdateProvider` | method | `backend/authentication/src/services/platform_ai.py:52`
`test_provider` | `TestProvider` | method | `backend/authentication/src/services/platform_ai.py:75`
`models` | `Models` | method | `backend/authentication/src/services/platform_ai.py:91`
`register_model` | `RegisterModel` | method | `backend/authentication/src/services/platform_ai.py:96`
`update_model` | `UpdateModel` | method | `backend/authentication/src/services/platform_ai.py:116`
`defaults` | `Defaults` | method | `backend/authentication/src/services/platform_ai.py:139`
`update_defaults` | `UpdateDefaults` | method | `backend/authentication/src/services/platform_ai.py:143`
`versions` | `Versions` | method | `backend/authentication/src/services/platform_ai.py:166`
`request_rag_reindex` | `RequestRagReindex` | method | `backend/authentication/src/services/platform_control_operations.py:14`
`inspect_caches` | `InspectCaches` | method | `backend/authentication/src/services/platform_control_operations.py:62`
`clear_caches` | `ClearCaches` | method | `backend/authentication/src/services/platform_control_operations.py:69`
`runtime_versions` | `RuntimeVersions` | method | `backend/authentication/src/services/platform_control_operations.py:88`
`jobs` | `Jobs` | method | `backend/authentication/src/services/platform_operations.py:18`
`retry_job` | `RetryJob` | method | `backend/authentication/src/services/platform_operations.py:41`
`cancel_job` | `CancelJob` | method | `backend/authentication/src/services/platform_operations.py:53`
`dead_letter_jobs` | `DeadLetterJobs` | method | `backend/authentication/src/services/platform_operations.py:65`
`discard_job` | `DiscardJob` | method | `backend/authentication/src/services/platform_operations.py:84`
`test_smtp` | `TestSmtp` | method | `backend/authentication/src/services/platform_operations.py:114`
`queue_overview` | `QueueOverview` | method | `backend/authentication/src/services/platform_operations.py:134`
`requeue_dead_letter_job` | `RequeueDeadLetterJob` | method | `backend/authentication/src/services/platform_operations.py:156`
`rag_operations` | `RagOperations` | method | `backend/authentication/src/services/platform_operations.py:183`
`storage_usage` | `StorageUsage` | method | `backend/authentication/src/services/platform_operations.py:189`
`platform_health` | `PlatformHealth` | method | `backend/authentication/src/services/platform_operations.py:197`
`audit` | `Audit` | method | `backend/authentication/src/services/platform_operations.py:216`
`test_storage` | `TestStorage` | method | `backend/authentication/src/services/platform_operations.py:222`
`integration_health` | `IntegrationHealth` | method | `backend/authentication/src/services/platform_operations.py:236`
`metrics` | `Metrics` | method | `backend/authentication/src/services/platform_operations.py:248`
`export_audit` | `ExportAudit` | method | `backend/authentication/src/services/platform_operations.py:267`
`service_health` | `ServiceHealth` | method | `backend/authentication/src/services/platform_operations.py:286`
`list` | `List` | method | `backend/authentication/src/services/platform_projects.py:21`
`detail` | `Detail` | method | `backend/authentication/src/services/platform_projects.py:35`
`update_status` | `UpdateStatus` | method | `backend/authentication/src/services/platform_projects.py:63`
`update_quota` | `UpdateQuota` | method | `backend/authentication/src/services/platform_projects.py:89`
`policy` | `Policy` | method | `backend/authentication/src/services/platform_projects.py:114`
`update_policy` | `UpdatePolicy` | method | `backend/authentication/src/services/platform_projects.py:126`
`membership_diagnostics` | `MembershipDiagnostics` | method | `backend/authentication/src/services/platform_projects.py:153`
`hard_delete` | `HardDelete` | method | `backend/authentication/src/services/platform_projects.py:169`
`break_glass_grants` | `BreakGlassGrants` | method | `backend/authentication/src/services/platform_projects.py:195`
`create_break_glass` | `CreateBreakGlass` | method | `backend/authentication/src/services/platform_projects.py:206`
`revoke_break_glass` | `RevokeBreakGlass` | method | `backend/authentication/src/services/platform_projects.py:234`
`masked_reference` | `MaskedReference` | method | `backend/authentication/src/services/platform_security.py:21`
`service_identities` | `ServiceIdentities` | method | `backend/authentication/src/services/platform_security.py:33`
`create_service_identity` | `CreateServiceIdentity` | method | `backend/authentication/src/services/platform_security.py:38`
`rotate_service_identity` | `RotateServiceIdentity` | method | `backend/authentication/src/services/platform_security.py:62`
`emergency_revoke` | `EmergencyRevoke` | method | `backend/authentication/src/services/platform_security.py:82`
`audit` | `Audit` | method | `backend/authentication/src/services/platform_security.py:124`
`secret_references` | `SecretReferences` | method | `backend/authentication/src/services/platform_security.py:134`
`create_secret_reference` | `CreateSecretReference` | method | `backend/authentication/src/services/platform_security.py:139`
`rotate_secret_reference` | `RotateSecretReference` | method | `backend/authentication/src/services/platform_security.py:162`
`delete_secret_reference` | `DeleteSecretReference` | method | `backend/authentication/src/services/platform_security.py:181`
`refresh_cookie_seconds` | `RefreshCookieSeconds` | method | `backend/authentication/src/services/session.py:24`
`access_token_for_user` | `AccessTokenForUser` | method | `backend/authentication/src/services/session.py:28`
`create_platform_user` | `CreatePlatformUser` | method | `backend/authentication/src/services/session.py:42`
`issue_email_verification` | `IssueEmailVerification` | method | `backend/authentication/src/services/session.py:88`
`verify_email` | `VerifyEmail` | method | `backend/authentication/src/services/session.py:129`
`login_user` | `LoginUser` | method | `backend/authentication/src/services/session.py:173`
`revoke_all_sessions` | `RevokeAllSessions` | method | `backend/authentication/src/services/session.py:293`
`revoke_session` | `RevokeSession` | method | `backend/authentication/src/services/session.py:300`
`forgot_password` | `ForgotPassword` | method | `backend/authentication/src/services/session.py:305`
`reset_password` | `ResetPassword` | method | `backend/authentication/src/services/session.py:343`
`verify_reset_code` | `VerifyResetCode` | method | `backend/authentication/src/services/session.py:368`
`issue_token_for_user` | `IssueTokenForUser` | method | `backend/authentication/src/services/session.py:377`
`refresh_session` | `RefreshSession` | method | `backend/authentication/src/services/session.py:399`
`count_patterns` | `CountPatterns` | method | `backend/authentication/src/repositories/cache.py:6`
`delete_patterns` | `DeletePatterns` | method | `backend/authentication/src/repositories/cache.py:15`
`update_account_with_admin_guard` | `UpdateAccountWithAdminGuard` | method | `backend/authentication/src/repositories/identity.py:80`
`update_accounts_with_admin_guard` | `UpdateAccountsWithAdminGuard` | method | `backend/authentication/src/repositories/identity.py:88`
`get_system_config_by_type` | `GetSystemConfigByType` | method | `backend/authentication/src/repositories/identity.py:102`
`get_auth_credential_by_id` | `GetAuthCredentialById` | method | `backend/authentication/src/repositories/identity.py:106`
`get_auth_credential_by_email` | `GetAuthCredentialByEmail` | method | `backend/authentication/src/repositories/identity.py:110`
`get_user_by_email` | `GetUserByEmail` | method | `backend/authentication/src/repositories/identity.py:114`
`get_auth_credential_by_slug` | `GetAuthCredentialBySlug` | method | `backend/authentication/src/repositories/identity.py:118`
`find_auth_credential` | `FindAuthCredential` | method | `backend/authentication/src/repositories/identity.py:122`
`find_auth_credentials` | `FindAuthCredentials` | method | `backend/authentication/src/repositories/identity.py:126`
`list_auth_credentials` | `ListAuthCredentials` | method | `backend/authentication/src/repositories/identity.py:132`
`update_auth_credential` | `UpdateAuthCredential` | method | `backend/authentication/src/repositories/identity.py:144`
`update_auth_credentials` | `UpdateAuthCredentials` | method | `backend/authentication/src/repositories/identity.py:148`
`count_auth_credentials` | `CountAuthCredentials` | method | `backend/authentication/src/repositories/identity.py:152`
`find_and_update_auth_credential` | `FindAndUpdateAuthCredential` | method | `backend/authentication/src/repositories/identity.py:156`
`record_failed_login` | `RecordFailedLogin` | method | `backend/authentication/src/repositories/identity.py:162`
`complete_successful_login` | `CompleteSuccessfulLogin` | method | `backend/authentication/src/repositories/identity.py:216`
`update_system_config` | `UpdateSystemConfig` | method | `backend/authentication/src/repositories/identity.py:238`
`create_auth_credential` | `CreateAuthCredential` | method | `backend/authentication/src/repositories/identity.py:244`
`update_password_hash` | `UpdatePasswordHash` | method | `backend/authentication/src/repositories/identity.py:251`
`insert_audit_log` | `InsertAuditLog` | method | `backend/authentication/src/repositories/identity.py:264`
`register_session` | `RegisterSession` | method | `backend/authentication/src/repositories/identity.py:268`
`rotate_refresh_token` | `RotateRefreshToken` | method | `backend/authentication/src/repositories/identity.py:285`
`revoke_session` | `RevokeSession` | method | `backend/authentication/src/repositories/identity.py:304`
`revoke_all_sessions` | `RevokeAllSessions` | method | `backend/authentication/src/repositories/identity.py:314`
`revoke_every_session` | `RevokeEverySession` | method | `backend/authentication/src/repositories/identity.py:324`
`clear_every_session_cache` | `ClearEverySessionCache` | method | `backend/authentication/src/repositories/identity.py:330`
`revoke_other_sessions` | `RevokeOtherSessions` | method | `backend/authentication/src/repositories/identity.py:335`
`list_active_sessions` | `ListActiveSessions` | method | `backend/authentication/src/repositories/identity.py:351`
`get_session` | `GetSession` | method | `backend/authentication/src/repositories/identity.py:367`
`retain_session_cache` | `RetainSessionCache` | method | `backend/authentication/src/repositories/identity.py:373`
`cache_session` | `CacheSession` | method | `backend/authentication/src/repositories/identity.py:379`
`has_cached_session` | `HasCachedSession` | method | `backend/authentication/src/repositories/identity.py:387`
`create_password_reset_token` | `CreatePasswordResetToken` | method | `backend/authentication/src/repositories/identity.py:391`
`get_valid_password_reset_token` | `GetValidPasswordResetToken` | method | `backend/authentication/src/repositories/identity.py:403`
`consume_password_reset_token` | `ConsumePasswordResetToken` | method | `backend/authentication/src/repositories/identity.py:414`
`create_email_verification_token` | `CreateEmailVerificationToken` | method | `backend/authentication/src/repositories/identity.py:426`
`consume_email_verification_token` | `ConsumeEmailVerificationToken` | method | `backend/authentication/src/repositories/identity.py:438`
`mark_email_verified` | `MarkEmailVerified` | method | `backend/authentication/src/repositories/identity.py:450`
`confirm_pending_email` | `ConfirmPendingEmail` | method | `backend/authentication/src/repositories/identity.py:466`
`apply_changes` | `ApplyChanges` | method | `backend/authentication/src/repositories/identity.py:26`
`identifier` | `Identifier` | method | `backend/authentication/src/repositories/platform.py:9`
`list_ai_providers` | `ListAiProviders` | method | `backend/authentication/src/repositories/platform.py:16`
`upsert_ai_provider` | `UpsertAiProvider` | method | `backend/authentication/src/repositories/platform.py:20`
`list_ai_models` | `ListAiModels` | method | `backend/authentication/src/repositories/platform.py:29`
`insert_ai_model` | `InsertAiModel` | method | `backend/authentication/src/repositories/platform.py:33`
`update_ai_model` | `UpdateAiModel` | method | `backend/authentication/src/repositories/platform.py:37`
`count_ai_models` | `CountAiModels` | method | `backend/authentication/src/repositories/platform.py:45`
`insert_admin_operation` | `InsertAdminOperation` | method | `backend/authentication/src/repositories/platform.py:52`
`claim_admin_operation` | `ClaimAdminOperation` | method | `backend/authentication/src/repositories/platform.py:56`
`complete_admin_operation` | `CompleteAdminOperation` | method | `backend/authentication/src/repositories/platform.py:64`
`list_audit_logs` | `ListAuditLogs` | method | `backend/authentication/src/repositories/platform.py:80`
`database_ready` | `DatabaseReady` | method | `backend/authentication/src/repositories/platform.py:86`
`list_service_identities` | `ListServiceIdentities` | method | `backend/authentication/src/repositories/platform.py:91`
`insert_service_identity` | `InsertServiceIdentity` | method | `backend/authentication/src/repositories/platform.py:95`
`rotate_service_identity` | `RotateServiceIdentity` | method | `backend/authentication/src/repositories/platform.py:99`
`update_service_identities` | `UpdateServiceIdentities` | method | `backend/authentication/src/repositories/platform.py:107`
`count_service_identities` | `CountServiceIdentities` | method | `backend/authentication/src/repositories/platform.py:112`
`list_secret_references` | `ListSecretReferences` | method | `backend/authentication/src/repositories/platform.py:116`
`insert_secret_reference` | `InsertSecretReference` | method | `backend/authentication/src/repositories/platform.py:120`
`rotate_secret_reference` | `RotateSecretReference` | method | `backend/authentication/src/repositories/platform.py:124`
`delete_secret_reference` | `DeleteSecretReference` | method | `backend/authentication/src/repositories/platform.py:132`
`LoginPage` | `GD_LoginPage` | page/boundary | `frontend/app/(auth)/dang-nhap/page.jsx`
`ResetPasswordPage` | `GD_ResetPasswordPage` | page/boundary | `frontend/app/(auth)/dat-lai-mat-khau/page.jsx`
`ForgotPasswordPage` | `GD_ForgotPasswordPage` | page/boundary | `frontend/app/(auth)/quen-mat-khau/page.jsx`
`EmailVerificationPage` | `GD_EmailVerificationPage` | page/boundary | `frontend/app/(auth)/xac-minh-thu-dien-tu/page.jsx`
`VerificationPage` | `GD_VerificationPage` | page/boundary | `frontend/app/(auth)/xac-thuc/page.jsx`
`AccountPage` | `GD_AccountPage` | page/boundary | `frontend/app/(main)/cai-dat/page.jsx`
`lookup_accounts` | `Ctrl_Internal` | route method in grouped control | `backend/authentication/src/api/internal.py:15`
`resolve_account_reference` | `Ctrl_Internal` | route method in grouped control | `backend/authentication/src/api/internal.py:20`
`validate_session` | `Ctrl_Internal` | route method in grouped control | `backend/authentication/src/api/internal.py:25`
`project_creation_policy` | `Ctrl_Internal` | route method in grouped control | `backend/authentication/src/api/internal.py:30`
`get_account_by_id` | `Ctrl_Internal` | route method in grouped control | `backend/authentication/src/api/internal.py:35`
`get_account_by_email` | `Ctrl_Internal` | route method in grouped control | `backend/authentication/src/api/internal.py:40`
`get_security_state` | `Ctrl_Internal` | route method in grouped control | `backend/authentication/src/api/internal.py:45`
`create_account` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:36`
`list_accounts` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:50`
`update_account` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:64`
`account_detail` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:74`
`update_account_profile` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:82`
`enable_account` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:92`
`disable_account` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:102`
`lock_account` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:112`
`unlock_account` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:122`
`force_password_reset` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:132`
`update_system_role` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:150`
`list_user_memberships` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:160`
`list_project_metadata` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:170`
`project_metadata_detail` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:183`
`update_project_status` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:193`
`update_project_quota` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:205`
`get_project_policy` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:217`
`update_project_policy` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:225`
`list_ai_providers` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:235`
`update_ai_provider` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:243`
`test_ai_provider` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:253`
`list_operations_jobs` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:261`
`retry_operations_job` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:276`
`cancel_operations_job` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:284`
`list_dead_letter_jobs` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:292`
`discard_dead_letter_job` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:303`
`platform_health` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:313`
`list_auth_audit` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:321`
`get_auth_policy` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:333`
`update_auth_policy` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:338`
`get_integrations` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:345`
`update_integrations` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:350`
`get_storage_config` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:357`
`update_storage_config` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:362`
`get_system_config` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:369`
`update_system_config` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:374`
`list_ai_models` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:381`
`register_ai_model` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:389`
`update_ai_model` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:400`
`get_ai_defaults` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:410`
`update_ai_defaults` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:415`
`get_ai_versions` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:422`
`test_storage` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:430`
`integration_health` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:438`
`operations_metrics` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:446`
`export_global_audit` | `Ctrl_Platform` | route method in grouped control | `backend/authentication/src/api/platform.py:454`
`resend_account_activation` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:43`
`anonymize_user` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:61`
`preview_bulk_user_action` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:71`
`confirm_bulk_user_action` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:82`
`project_membership_diagnostics` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:94`
`hard_delete_project` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:104`
`list_break_glass_grants` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:116`
`create_break_glass_grant` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:126`
`revoke_break_glass_grant` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:137`
`get_rate_limits` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:147`
`update_rate_limits` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:152`
`list_service_identities` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:159`
`create_service_identity` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:167`
`rotate_service_identity` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:178`
`emergency_revoke` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:192`
`security_audit` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:202`
`list_secret_references` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:215`
`create_secret_reference` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:223`
`rotate_secret_reference` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:234`
`delete_secret_reference` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:248`
`test_smtp` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:260`
`queue_overview` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:270`
`requeue_dead_letter_job` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:280`
`rag_operations` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:293`
`request_rag_reindex` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:301`
`inspect_safe_caches` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:312`
`clear_safe_caches` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:320`
`storage_usage` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:330`
`runtime_versions` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:338`
`get_maintenance_mode` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:346`
`update_maintenance_mode` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:351`
`get_handler` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:386`
`update_handler` | `Ctrl_PlatformControls` | route method in grouped control | `backend/authentication/src/api/platform_controls.py:393`
`read_users_me` | `Ctrl_Session` | route method in grouped control | `backend/authentication/src/api/session.py:29`
`update_users_me` | `Ctrl_Session` | route method in grouped control | `backend/authentication/src/api/session.py:38`
`change_email` | `Ctrl_Session` | route method in grouped control | `backend/authentication/src/api/session.py:48`
`resend_email_verification` | `Ctrl_Session` | route method in grouped control | `backend/authentication/src/api/session.py:62`
`verify_email` | `Ctrl_Session` | route method in grouped control | `backend/authentication/src/api/session.py:77`
`read_settings` | `Ctrl_Session` | route method in grouped control | `backend/authentication/src/api/session.py:86`
`update_settings` | `Ctrl_Session` | route method in grouped control | `backend/authentication/src/api/session.py:94`
`update_notifications` | `Ctrl_Session` | route method in grouped control | `backend/authentication/src/api/session.py:104`
`deactivate_account` | `Ctrl_Session` | route method in grouped control | `backend/authentication/src/api/session.py:114`
`change_password` | `Ctrl_Session` | route method in grouped control | `backend/authentication/src/api/session.py:124`
`list_my_sessions` | `Ctrl_Session` | route method in grouped control | `backend/authentication/src/api/session.py:136`
`revoke_my_session` | `Ctrl_Session` | route method in grouped control | `backend/authentication/src/api/session.py:144`
`login` | `Ctrl_Session` | route method in grouped control | `backend/authentication/src/api/session.py:156`
`forgot_password` | `Ctrl_Session` | route method in grouped control | `backend/authentication/src/api/session.py:173`
`reset_password` | `Ctrl_Session` | route method in grouped control | `backend/authentication/src/api/session.py:187`
`verify_code` | `Ctrl_Session` | route method in grouped control | `backend/authentication/src/api/session.py:201`
`logout` | `Ctrl_Session` | route method in grouped control | `backend/authentication/src/api/session.py:211`
`logout_all` | `Ctrl_Session` | route method in grouped control | `backend/authentication/src/api/session.py:219`
`refresh_session` | `Ctrl_Session` | route method in grouped control | `backend/authentication/src/api/session.py:232`
`health_check` | `Ctrl_Main` | route method in grouped control | `backend/authentication/src/main.py:45`
`readiness_check` | `Ctrl_Main` | route method in grouped control | `backend/authentication/src/main.py:50`
