import asyncio
import unittest
from unittest.mock import patch

from src.services.inference import inspect_chunks


class ChunkInspectionBatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_inspection_creates_only_bounded_concurrent_batches(self):
        active = 0
        maximum_active = 0
        inspected = []

        async def scan(text):
            nonlocal active, maximum_active
            active += 1
            maximum_active = max(maximum_active, active)
            inspected.append(text)
            await asyncio.sleep(0)
            active -= 1
            return type("ScanResult", (), {"passed": text != "reject"})()

        texts = ["first", "second", "reject", "fourth", "fifth"]
        with (
            patch("src.services.inference.settings.DOCUMENT_CHUNK_INSPECTION_BATCH_SIZE", 2),
            patch("src.services.inference.security.ascan_input", side_effect=scan),
        ):
            accepted = await inspect_chunks(texts)

        self.assertLessEqual(maximum_active, 2)
        self.assertEqual(inspected, texts)
        self.assertEqual(accepted, {0, 1, 3, 4})
