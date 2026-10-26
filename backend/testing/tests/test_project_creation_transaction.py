import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from src.repositories.project import ProjectRepository


class TransactionContext:
    def __init__(self):
        self.error = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, error_type, error, traceback):
        self.error = error
        return False


class SessionContext:
    def __init__(self):
        self.transaction = TransactionContext()

    async def __aenter__(self):
        return self

    async def __aexit__(self, error_type, error, traceback):
        return False

    def start_transaction(self):
        return self.transaction


class ProjectCreationTransactionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.session = SessionContext()
        self.project_collection = SimpleNamespace(insert_one=AsyncMock())
        self.membership_collection = SimpleNamespace(insert_many=AsyncMock())
        self.value = SimpleNamespace(
            projects=self.project_collection,
            project_members=self.membership_collection,
        )
        self.database = SimpleNamespace(
            value=self.value,
            client=SimpleNamespace(start_session=AsyncMock(return_value=self.session)),
        )

    async def test_project_memberships_and_audit_share_one_transaction(self):
        audit_event = {"_id": "AUD-1", "action": "project_created"}
        insert_audit = AsyncMock(return_value=audit_event)

        with (
            patch("src.repositories.project.database", self.database),
            patch("src.repositories.project.common_repository.insert_audit_event", insert_audit),
        ):
            await ProjectRepository().create_with_memberships(
                {"_id": "PRJ-1"}, [{"_id": "PM-1"}], audit_event
            )

        self.project_collection.insert_one.assert_awaited_once_with(
            {"_id": "PRJ-1"}, session=self.session
        )
        self.membership_collection.insert_many.assert_awaited_once_with(
            [{"_id": "PM-1"}], session=self.session
        )
        insert_audit.assert_awaited_once_with(audit_event, session=self.session)
        self.assertIsNone(self.session.transaction.error)

    async def test_audit_failure_aborts_project_creation_transaction(self):
        audit_event = {"_id": "AUD-1", "action": "project_created"}
        insert_audit = AsyncMock(side_effect=RuntimeError("audit storage unavailable"))

        with (
            patch("src.repositories.project.database", self.database),
            patch("src.repositories.project.common_repository.insert_audit_event", insert_audit),
        ):
            with self.assertRaisesRegex(RuntimeError, "audit storage unavailable"):
                await ProjectRepository().create_with_memberships(
                    {"_id": "PRJ-1"}, [{"_id": "PM-1"}], audit_event
                )

        self.assertIsInstance(self.session.transaction.error, RuntimeError)
        self.assertEqual(str(self.session.transaction.error), "audit storage unavailable")


if __name__ == "__main__":
    unittest.main()
