import unittest

from src.schemas.project import ProjectSourceBlock, validate_project_source_structure


class ProjectSourceStructureValidationTests(unittest.TestCase):
    def test_reuse_input_list_replaces_source_dicts_with_validated_blocks(self):
        source = [
            {
                "block_id": "heading-1",
                "text": "Authentication",
                "type": "section_header",
                "level": 1,
            },
            {
                "block_id": "paragraph-1",
                "parent_block_id": "heading-1",
                "text": "Users sign in with valid credentials.",
                "type": "text",
                "page_no": 2,
            },
        ]

        result = validate_project_source_structure(source, reuse_input_list=True)

        self.assertIs(result, source)
        self.assertTrue(all(isinstance(block, ProjectSourceBlock) for block in result))
        self.assertEqual(result[1].parent_block_id, "heading-1")
        self.assertEqual(result[1].page_no, 2)

    def test_reused_validation_keeps_duplicate_and_cycle_checks(self):
        duplicate_ids = [
            {"block_id": "same", "text": "one", "type": "text"},
            {"block_id": "same", "text": "two", "type": "text"},
        ]
        cyclic_parentage = [
            {
                "block_id": "first",
                "parent_block_id": "second",
                "text": "one",
                "type": "text",
            },
            {
                "block_id": "second",
                "parent_block_id": "first",
                "text": "two",
                "type": "text",
            },
        ]

        with self.assertRaisesRegex(ValueError, "source_structure_block_id_ambiguous"):
            validate_project_source_structure(duplicate_ids, reuse_input_list=True)
        with self.assertRaisesRegex(ValueError, "source_structure_parent_cycle"):
            validate_project_source_structure(cyclic_parentage, reuse_input_list=True)
