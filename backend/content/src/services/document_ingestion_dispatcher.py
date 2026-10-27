import asyncio
from contextlib import suppress
from uuid import uuid4

from loguru import logger

from src.clients.knowledge import knowledge_client
from src.core.infrastructure.configuration import settings
from src.repositories.document_ingestion_outbox import (
    DocumentIngestionOutboxRepository,
    DocumentIngestionSourceChanged,
    document_ingestion_outbox,
)


class DocumentIngestionDispatcher:
    def __init__(self):
        self._task: asyncio.Task | None = None
        self._stopping = False

    async def start(self):
        if self._task and not self._task.done():
            return
        self._stopping = False
        self._task = asyncio.create_task(self._run(), name="content-document-ingestion-outbox")

    async def stop(self):
        self._stopping = True
        task, self._task = self._task, None
        if task and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    async def _run(self):
        next_reconcile = 0.0
        while not self._stopping:
            try:
                loop_time = asyncio.get_running_loop().time()
                if loop_time >= next_reconcile:
                    await self._reconcile_unqueued_documents()
                    next_reconcile = (
                        loop_time
                        + settings.DOCUMENT_INGESTION_RECONCILE_INTERVAL_SECONDS
                    )

                lease_token = str(uuid4())
                event = await document_ingestion_outbox.claim(lease_token)
                if event:
                    await self._dispatch(event, lease_token)
                else:
                    await asyncio.sleep(
                        settings.DOCUMENT_INGESTION_POLL_INTERVAL_SECONDS
                    )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Document ingestion outbox worker iteration failed")
                await asyncio.sleep(
                    settings.DOCUMENT_INGESTION_RECONCILE_INTERVAL_SECONDS
                )

    async def _reconcile_unqueued_documents(self):
        recovered = await document_ingestion_outbox.recover_expired_indexing_claims()
        if recovered:
            logger.warning(
                "Recovered expired document indexing claims count={}", recovered
            )
        rows = await document_ingestion_outbox.list_documents_requiring_dispatch()
        for document in rows:
            document_id = str(document.get("_id") or "")
            if not document_id:
                continue
            source_snapshot = DocumentIngestionOutboxRepository.source_snapshot_from_document(
                document
            )
            try:
                await document_ingestion_outbox.enqueue(
                    document,
                    user_id=str(document.get("creator_id") or ""),
                    superseded_document_id=str(document.get("previous_version_id") or ""),
                    force_new=True,
                    expected_source_snapshot=source_snapshot,
                )
            except DocumentIngestionSourceChanged:
                logger.info(
                    "Skipped stale document during ingestion reconciliation document_id={}",
                    document_id,
                )

    async def _dispatch(self, event: dict, lease_token: str):
        try:
            response = await knowledge_client.index_document(
                str(event["document_id"]),
                str(event.get("user_id") or ""),
                str(event.get("superseded_document_id") or ""),
                event_id=str(event["event_id"]),
            )
            if response.get("status") != "accepted":
                raise RuntimeError("ai_document_ingestion_not_accepted")
        except asyncio.CancelledError:
            raise
        except Exception as error:
            await document_ingestion_outbox.retry(event, lease_token, error)
            logger.warning(
                "Document ingestion dispatch will retry document_id={} error_type={}",
                event.get("document_id"),
                type(error).__name__,
            )
            return

        completed = await document_ingestion_outbox.complete(
            str(event["event_id"]), lease_token
        )
        if not completed:
            logger.warning(
                "Document ingestion outbox lease changed after dispatch event_id={}",
                event.get("event_id"),
            )


document_ingestion_dispatcher = DocumentIngestionDispatcher()
