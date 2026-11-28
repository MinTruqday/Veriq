# Rename map — notification

Tên code | Tên sơ đồ | Loại | Căn cứ
---|---|---|---
`notifications` | `Notification` | collection/table | `backend/notification/src/core/infrastructure/database.py:24, backend/notification/src/core/infrastructure/database.py:25, backend/notification/src/core/infrastructure/database.py:26`
`idempotency_key` | `IdempotencyKey` | field | `backend/notification/src/core/infrastructure/database.py:29`
`notification_settings` | `NotificationSetting` | collection/table | `backend/notification/src/repositories/announcement.py:35, backend/notification/src/repositories/announcement.py:40`
`_id` | `NotificationSettingId` | field | `backend/notification/src/repositories/announcement.py:35, backend/notification/src/repositories/announcement.py:41`
`settings` | `Settings` | field | `backend/notification/src/repositories/announcement.py:41`
`get_announcements` | `GetAnnouncements` | method | `backend/notification/src/services/announcement.py:17`
`mark_as_read` | `MarkAsRead` | method | `backend/notification/src/services/announcement.py:34`
`mark_all_as_read` | `MarkAllAsRead` | method | `backend/notification/src/services/announcement.py:46`
`delete_announcement` | `DeleteAnnouncement` | method | `backend/notification/src/services/announcement.py:53`
`create_announcement` | `CreateAnnouncement` | method | `backend/notification/src/services/announcement.py:64`
`settings` | `Settings` | method | `backend/notification/src/services/announcement.py:107`
`update_settings` | `UpdateSettings` | method | `backend/notification/src/services/announcement.py:112`
`find` | `Find` | method | `backend/notification/src/repositories/announcement.py:6`
`find_one` | `FindOne` | method | `backend/notification/src/repositories/announcement.py:10`
`count_documents` | `CountDocuments` | method | `backend/notification/src/repositories/announcement.py:14`
`insert_one` | `InsertOne` | method | `backend/notification/src/repositories/announcement.py:18`
`update_one` | `UpdateOne` | method | `backend/notification/src/repositories/announcement.py:22`
`update_many` | `UpdateMany` | method | `backend/notification/src/repositories/announcement.py:26`
`delete_one` | `DeleteOne` | method | `backend/notification/src/repositories/announcement.py:30`
`get_settings` | `GetSettings` | method | `backend/notification/src/repositories/announcement.py:34`
`update_settings` | `UpdateSettings` | method | `backend/notification/src/repositories/announcement.py:39`
`NotificationPreferencesPanel` | `GD_NotificationPreferencesPanel` | page/boundary | ``
`AnnouncementsPage` | `GD_AnnouncementsPage` | page/boundary | `frontend/app/(main)/thong-bao/page.jsx`
`get_announcements` | `Ctrl_Announcement` | route method in grouped control | `backend/notification/src/api/announcement.py:14`
`mark_as_read` | `Ctrl_Announcement` | route method in grouped control | `backend/notification/src/api/announcement.py:26`
`mark_all_as_read` | `Ctrl_Announcement` | route method in grouped control | `backend/notification/src/api/announcement.py:36`
`delete_announcement` | `Ctrl_Announcement` | route method in grouped control | `backend/notification/src/api/announcement.py:44`
`create_announcement` | `Ctrl_Announcement` | route method in grouped control | `backend/notification/src/api/announcement.py:60`
`get_settings` | `Ctrl_Announcement` | route method in grouped control | `backend/notification/src/api/announcement.py:69`
`update_settings` | `Ctrl_Announcement` | route method in grouped control | `backend/notification/src/api/announcement.py:77`
`health_check` | `Ctrl_Main` | route method in grouped control | `backend/notification/src/main.py:50`
`readiness_check` | `Ctrl_Main` | route method in grouped control | `backend/notification/src/main.py:55`
