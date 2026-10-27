import hashlib
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from pydantic import ValidationError

from src.modules.requirements.services.requirement_templates import (
    requirement_document_synthesis_snapshot,
    revalidate_template_synthesis_sources,
    requirement_source_refs_from_suggestion,
    synthesize_template,
    template_synthesis_source_snapshot,
)
from src.modules.design.services.generation import requirement_test_evidence_text
from src.schemas.contracts.requirements import RequirementTemplateSynthesis


class RequirementTemplateSourceRefTests(unittest.TestCase):
    def test_synthesis_instruction_accepts_blueprint_payload_within_ai_contract_limit(self):
        base = {
            "name": "Mẫu yêu cầu từ tài liệu nguồn",
            "product_types": ["web"],
            "source_document_ids": ["RDOC-1"],
        }

        for length in (3000, 3948, 5000):
            with self.subTest(length=length):
                value = RequirementTemplateSynthesis(
                    **base,
                    instruction="x" * length,
                )
                self.assertEqual(len(value.instruction), length)

        with self.assertRaises(ValidationError):
            RequirementTemplateSynthesis(**base, instruction="x" * 5001)

    def test_template_synthesis_snapshot_tracks_source_document_revision_and_version(self):
        document = {
            "_id": "DOC-1",
            "revision": 4,
            "status": "READY",
            "ai_enabled": True,
            "source_version": "3",
            "source_version_sequence": 3,
            "source_series_id": "SERIES-1",
            "previous_source_version_id": "DOC-0",
            "content_hash": "source-hash-4",
            "authority": "APPROVED_SPECIFICATION",
            "source_type": "SRS",
            "format": "pdf",
            "index_status": "INDEXED",
            "normalized_content": "Yêu cầu hiện tại.",
        }

        snapshot = template_synthesis_source_snapshot(
            ["DOC-1"], [document], []
        )

        self.assertEqual(snapshot["source_document_ids"], ["DOC-1"])
        self.assertEqual(snapshot["documents"], {"DOC-1": requirement_document_synthesis_snapshot([document])["DOC-1"]})
        self.assertEqual(snapshot["templates"], {})
        self.assertEqual(
            snapshot["documents"]["DOC-1"]["normalized_content_sha256"],
            hashlib.sha256("Yêu cầu hiện tại.".encode("utf-8")).hexdigest(),
        )

    def test_business_rule_is_available_as_requirement_version_test_evidence(self):
        rule = "Khi mật khẩu sai, hệ thống từ chối đăng nhập."
        evidence = requirement_test_evidence_text({
            "plain_text_projection": "Đăng nhập bằng email và mật khẩu.",
            "actors": ["Người dùng đã đăng ký"],
            "business_rules": [rule],
            "details": {},
        })

        self.assertIn(rule, evidence)
        self.assertIn("Quy tắc nghiệp vụ", evidence)

    def test_source_quotes_are_stored_as_individual_exact_spans(self):
        source_text = (
            "Actor: Người dùng.\n"
            "AC: Khi thông tin đúng, người dùng đăng nhập thành công.\n"
            "Rule: Khi mật khẩu sai, hệ thống từ chối đăng nhập."
        )
        suggestion = {
            "content": "Khi thông tin đúng, người dùng đăng nhập thành công.",
            "evidence_refs": ["doc-v1"],
            "source_quotes": {"doc-v1": "AC: Khi thông tin đúng, người dùng đăng nhập thành công."},
            "acceptance_criteria": [
                "Khi thông tin đúng, người dùng đăng nhập thành công."
            ],
        }
        source = {
            "_id": "doc-1",
            "content_hash": "hash-1",
            "source_version": "1",
        }
        refs = requirement_source_refs_from_suggestion(
            suggestion, {"doc-v1": (source, 0, source_text)}
        )

        self.assertEqual(
            [item["source_quote"] for item in refs],
            [
                "AC: Khi thông tin đúng, người dùng đăng nhập thành công.",
                "Khi thông tin đúng, người dùng đăng nhập thành công.",
            ],
        )
        for ref in refs:
            self.assertEqual(
                source_text[ref["source_start"]:ref["source_end"]],
                ref["source_quote"],
            )
        self.assertTrue(
            all("Rule: Khi mật khẩu sai" not in ref["source_quote"] for ref in refs)
        )

    def test_exact_source_field_can_replace_an_invalid_model_anchor(self):
        source_text = "AC: Khi mật khẩu sai, hệ thống từ chối đăng nhập."
        suggestion = {
            "title": "Từ chối đăng nhập khi mật khẩu sai",
            "content": "Khi mật khẩu sai, hệ thống từ chối đăng nhập.",
            "evidence_refs": ["doc-v1"],
            "source_quotes": {"doc-v1": "Khi thông tin không hợp lệ, đăng nhập thất bại."},
            "acceptance_criteria": [
                "Khi mật khẩu sai, hệ thống từ chối đăng nhập."
            ],
        }
        source = {
            "_id": "doc-1",
            "content_hash": "hash-1",
            "source_version": "1",
        }

        refs = requirement_source_refs_from_suggestion(
            suggestion, {"doc-v1": (source, 0, source_text)}
        )

        self.assertTrue(refs)
        self.assertNotIn("Khi thông tin không hợp lệ", " ".join(
            item["source_quote"] for item in refs
        ))
        self.assertTrue(all(
            source_text[item["source_start"]:item["source_end"]]
            == item["source_quote"]
            for item in refs
        ))

    def test_invalid_anchor_without_exact_source_fields_is_rejected(self):
        source_text = "Yêu cầu đăng nhập bằng email."
        suggestion = {
            "title": "Từ chối thiết bị lạ",
            "content": "Người dùng phải xác nhận thiết bị lạ.",
            "evidence_refs": ["doc-v1"],
            "source_quotes": {"doc-v1": "Thiết bị lạ luôn cần xác nhận."},
        }
        source = {
            "_id": "doc-1",
            "content_hash": "hash-1",
            "source_version": "1",
        }

        with self.assertRaises(HTTPException) as raised:
            requirement_source_refs_from_suggestion(
                suggestion, {"doc-v1": (source, 0, source_text)}
            )

        self.assertEqual(raised.exception.detail["code"], "TEMPLATE_SOURCE_QUOTE_INVALID")


class TemplateSynthesisSnapshotTests(unittest.IsolatedAsyncioTestCase):
    async def test_context_only_template_merge_revalidates_before_persisting(self):
        template = {
            "_id": "TPL-1",
            "project_id": "PRJ-1",
            "version": 2,
            "revision": 5,
            "status": "DRAFT",
            "context": {"objectives": "Improve secure access"},
            "requirements": [],
            "source_document_ids": [],
            "source_template_ids": [],
            "source_template_versions": {},
            "source_template_public_ids": [],
        }
        payload = SimpleNamespace(
            source_document_ids=[],
            source_template_ids=["TPL-1"],
            name="Combined template",
            product_types=["web"],
            instruction=None,
        )
        user = SimpleNamespace(id="BA-1")
        with (
            patch("src.modules.requirements.services.requirement_templates.get_project", new=AsyncMock()),
            patch(
                "src.modules.requirements.services.requirement_templates.validate_template_documents",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.modules.requirements.services.requirement_templates.visible_template",
                new=AsyncMock(return_value=template),
            ),
            patch(
                "src.modules.requirements.services.requirement_templates.validate_template_ai_sources",
                new=AsyncMock(return_value=set()),
            ),
            patch(
                "src.modules.requirements.services.requirement_templates.revalidate_template_synthesis_sources",
                new=AsyncMock(),
            ) as revalidate,
            patch(
                "src.modules.requirements.services.requirement_templates.create_template",
                new=AsyncMock(return_value={"_id": "TPL-NEW"}),
            ) as create,
        ):
            result = await synthesize_template("PRJ-1", payload, user)

        self.assertEqual(result["_id"], "TPL-NEW")
        revalidate.assert_awaited_once_with("PRJ-1", payload, user, {}, [template])
        create.assert_awaited_once()

    async def test_context_only_template_merge_does_not_persist_if_source_changed(self):
        template = {
            "_id": "TPL-1",
            "project_id": "PRJ-1",
            "version": 2,
            "revision": 5,
            "status": "DRAFT",
            "context": {"objectives": "Improve secure access"},
            "requirements": [],
            "source_document_ids": [],
            "source_template_ids": [],
            "source_template_versions": {},
            "source_template_public_ids": [],
        }
        payload = SimpleNamespace(
            source_document_ids=[],
            source_template_ids=["TPL-1"],
            name="Combined template",
            product_types=["web"],
            instruction=None,
        )
        conflict = HTTPException(
            status_code=409,
            detail={"code": "TEMPLATE_SOURCE_SNAPSHOT_CHANGED"},
        )
        with (
            patch("src.modules.requirements.services.requirement_templates.get_project", new=AsyncMock()),
            patch(
                "src.modules.requirements.services.requirement_templates.validate_template_documents",
                new=AsyncMock(return_value=[]),
            ),
            patch(
                "src.modules.requirements.services.requirement_templates.visible_template",
                new=AsyncMock(return_value=template),
            ),
            patch(
                "src.modules.requirements.services.requirement_templates.validate_template_ai_sources",
                new=AsyncMock(return_value=set()),
            ),
            patch(
                "src.modules.requirements.services.requirement_templates.revalidate_template_synthesis_sources",
                new=AsyncMock(side_effect=conflict),
            ),
            patch(
                "src.modules.requirements.services.requirement_templates.create_template",
                new=AsyncMock(),
            ) as create,
        ):
            with self.assertRaises(HTTPException) as raised:
                await synthesize_template("PRJ-1", payload, SimpleNamespace(id="BA-1"))

        self.assertEqual(raised.exception.status_code, 409)
        create.assert_not_awaited()

    async def test_unchanged_source_snapshot_remains_eligible_for_persistence(self):
        document = {
            "_id": "DOC-1",
            "project_id": "PRJ-1",
            "revision": 3,
            "status": "READY",
            "ai_enabled": True,
            "normalized_content": "Password must be at least eight characters.",
            "content_hash": "hash-3",
            "source_version": "2",
            "source_version_sequence": 2,
            "source_series_id": "SERIES-1",
            "previous_source_version_id": "DOC-0",
            "authority": "APPROVED_SPECIFICATION",
            "source_type": "SRS",
            "format": "pdf",
            "visibility": "project",
            "shared_with": [],
            "created_by": "BA-1",
        }
        payload = SimpleNamespace(source_document_ids=["DOC-1"], source_template_ids=[])
        with (
            patch("src.modules.requirements.services.requirement_templates.get_project", new=AsyncMock()),
            patch(
                "src.modules.requirements.services.requirement_templates.validate_template_documents",
                new=AsyncMock(return_value=[document.copy()]),
            ),
            patch("src.modules.requirements.services.requirement_templates.visible_template", new=AsyncMock()),
        ):
            await revalidate_template_synthesis_sources(
                "PRJ-1", payload, SimpleNamespace(id="BA-1"), {"DOC-1": document}, []
            )

    async def test_source_content_or_revision_change_rejects_synthesis_output(self):
        original = {
            "_id": "DOC-1",
            "project_id": "PRJ-1",
            "revision": 3,
            "status": "READY",
            "ai_enabled": True,
            "normalized_content": "Password must be at least eight characters.",
            "content_hash": "hash-3",
            "source_version": "2",
            "source_version_sequence": 2,
            "source_series_id": "SERIES-1",
            "previous_source_version_id": "DOC-0",
            "authority": "APPROVED_SPECIFICATION",
            "source_type": "SRS",
            "format": "pdf",
            "visibility": "project",
            "shared_with": [],
            "created_by": "BA-1",
        }
        changed = {**original, "revision": 4, "normalized_content": "Password must be at least twelve characters."}
        payload = SimpleNamespace(source_document_ids=["DOC-1"], source_template_ids=[])
        with (
            patch("src.modules.requirements.services.requirement_templates.get_project", new=AsyncMock()),
            patch(
                "src.modules.requirements.services.requirement_templates.validate_template_documents",
                new=AsyncMock(return_value=[changed]),
            ),
            patch("src.modules.requirements.services.requirement_templates.visible_template", new=AsyncMock()),
        ):
            with self.assertRaises(HTTPException) as raised:
                await revalidate_template_synthesis_sources(
                    "PRJ-1", payload, SimpleNamespace(id="BA-1"), {"DOC-1": original}, []
                )
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "TEMPLATE_SOURCE_SNAPSHOT_CHANGED")

    async def test_source_template_version_change_rejects_synthesis_output(self):
        original = {
            "_id": "TPL-1",
            "project_id": "PRJ-1",
            "version": 2,
            "revision": 5,
            "status": "DRAFT",
            "context": {"objectives": "Secure access"},
            "requirements": [],
            "source_document_ids": [],
            "source_template_ids": [],
            "source_template_versions": {},
            "source_template_public_ids": [],
        }
        changed = {**original, "version": 3, "revision": 6}
        payload = SimpleNamespace(source_document_ids=[], source_template_ids=["TPL-1"])
        with (
            patch("src.modules.requirements.services.requirement_templates.get_project", new=AsyncMock()),
            patch(
                "src.modules.requirements.services.requirement_templates.visible_template",
                new=AsyncMock(return_value=changed),
            ),
            patch(
                "src.modules.requirements.services.requirement_templates.validate_template_ai_sources",
                new=AsyncMock(return_value=set()),
            ),
            patch(
                "src.modules.requirements.services.requirement_templates.validate_template_documents",
                new=AsyncMock(return_value=[]),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                await revalidate_template_synthesis_sources(
                    "PRJ-1", payload, SimpleNamespace(id="BA-1"), {}, [original]
                )
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(raised.exception.detail["code"], "TEMPLATE_SOURCE_SNAPSHOT_CHANGED")


if __name__ == "__main__":
    unittest.main()
