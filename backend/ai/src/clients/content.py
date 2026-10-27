import httpx

from src.core.infrastructure.configuration import settings


class ContentClient:
    @staticmethod
    async def exchange(action: str, **values):
        async with httpx.AsyncClient(
            timeout=20
        ) as client:
            response = await client.post(
                f"{settings.CONTENT_URL}/tai-lieu/noi-bo/trao-doi",
                json={"action": action, **values},
                headers={"X-Internal-Token": settings.SECRET_KEY},
            )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json().get("data")

    @classmethod
    async def accessible(cls, document_id: str, user_id: str, is_admin: bool):
        return await cls.exchange(
            "get_accessible_document",
            document_id=document_id,
            user_id=user_id,
            is_admin=is_admin,
            edit=True,
        )

    @classmethod
    async def authorize_document(
        cls, document_id: str, requester_id: str, is_admin: bool, allow_deleted: bool = False
    ):
        document = await cls.exchange(
            "get_accessible_document",
            document_id=document_id,
            user_id=requester_id,
            is_admin=is_admin,
            edit=True,
            allow_deleted=allow_deleted,
        )
        if not document:
            raise ValueError("Document not found")
        return document

    @classmethod
    async def authorize_read(cls, document_id: str, requester_id: str, is_admin: bool):
        document = await cls.exchange(
            "get_accessible_document",
            document_id=document_id,
            user_id=requester_id,
            is_admin=is_admin,
            edit=False,
        )
        if not document:
            raise ValueError("Document not found")
        return document

    @classmethod
    async def authorize_read_many(
        cls, document_ids: list[str], requester_id: str | None, is_admin: bool
    ) -> list[str]:
        records = await cls._read_accessible_documents_many(
            document_ids, requester_id, is_admin
        )
        return [str(item["_id"]) for item in records]

    @classmethod
    async def active_index_generations_many(
        cls, document_ids: list[str], requester_id: str | None, is_admin: bool
    ) -> dict[str, str | None]:
        records = await cls._read_accessible_documents_many(
            document_ids, requester_id, is_admin
        )
        generations = {}
        for item in records:
            value = item.get("active_index_generation")
            if value is None:
                generation = None
            elif (
                isinstance(value, str)
                and len(value) == 64
                and all(character in "0123456789abcdef" for character in value)
            ):
                generation = value
            else:
                raise RuntimeError("content_document_index_generation_invalid")
            generations[str(item["_id"])] = generation
        return generations

    @classmethod
    async def _read_accessible_documents_many(
        cls, document_ids: list[str], requester_id: str | None, is_admin: bool
    ) -> list[dict]:
        if not document_ids:
            return []
        unique_ids = list(dict.fromkeys(map(str, document_ids)))
        accessible = {}
        for offset in range(0, len(unique_ids), 100):
            result = await cls.exchange(
                "get_accessible_documents",
                document_ids=unique_ids[offset : offset + 100],
                user_id=str(requester_id or ""),
                is_admin=is_admin,
            )
            if not isinstance(result, dict) or not isinstance(result.get("documents"), list):
                raise RuntimeError("content_document_access_response_invalid")
            accessible.update(
                (str(item["_id"]), item)
                for item in result["documents"]
                if isinstance(item, dict) and item.get("_id")
            )
        return [accessible[document_id] for document_id in unique_ids if document_id in accessible]

    @classmethod
    async def get(cls, document_id: str):
        return await cls.exchange("get_document", document_id=document_id)

    @classmethod
    async def update_index(
        cls,
        document_id: str,
        indexed_chunks: int,
        extraction_method: str,
        index_report: dict | None = None,
        extracted_text: str = "",
        indexing_attempt_id: str = "",
        indexing_lease_token: str = "",
        index_generation: str = "",
        source_snapshot: dict | None = None,
        document_index_contract_version: int | None = None,
    ):
        return await cls.exchange(
            "update_index",
            document_id=document_id,
            indexing_attempt_id=indexing_attempt_id,
            indexing_lease_token=indexing_lease_token,
            index_generation=index_generation,
            document_index_contract_version=document_index_contract_version,
            source_snapshot=source_snapshot,
            indexed_chunks=indexed_chunks,
            extraction_method=extraction_method,
            index_report=index_report,
            extracted_text=extracted_text[:200000],
            extracted_text_truncated=len(extracted_text) > 200000,
        )

    @classmethod
    async def mark_indexed(
        cls,
        document_id: str,
        chunks_count: int,
        index_report: dict | None = None,
        extracted_text: str = "",
        extraction_method: str = "",
        indexing_attempt_id: str = "",
        indexing_lease_token: str = "",
        index_generation: str = "",
        source_snapshot: dict | None = None,
        document_index_contract_version: int | None = None,
    ):
        return await cls.update_index(
            document_id,
            chunks_count,
            extraction_method,
            index_report,
            extracted_text,
            indexing_attempt_id,
            indexing_lease_token,
            index_generation,
            source_snapshot,
            document_index_contract_version,
        )

    @classmethod
    async def mark_indexing(
        cls,
        document_id: str,
        indexing_attempt_id: str = "",
        indexing_lease_token: str = "",
        dispatch_event_id: str = "",
    ):
        return await cls.exchange(
            "mark_indexing",
            document_id=document_id,
            indexing_attempt_id=indexing_attempt_id,
            indexing_lease_token=indexing_lease_token,
            dispatch_event_id=dispatch_event_id,
        )

    @classmethod
    async def update_indexing_progress(
        cls,
        document_id: str,
        indexing_attempt_id: str,
        indexing_lease_token: str,
        processed_pages: int,
        total_pages: int,
        unprocessed_pages: int,
    ):
        return await cls.exchange(
            "update_indexing_progress",
            document_id=document_id,
            indexing_attempt_id=indexing_attempt_id,
            indexing_lease_token=indexing_lease_token,
            phase="parsing",
            processed_pages=processed_pages,
            total_pages=total_pages,
            unprocessed_pages=unprocessed_pages,
        )

    @classmethod
    async def mark_index_failed(
        cls,
        document_id: str,
        error_code: str,
        indexing_attempt_id: str = "",
        indexing_lease_token: str = "",
    ):
        return await cls.exchange(
            "mark_index_failed",
            document_id=document_id,
            error_code=error_code,
            indexing_attempt_id=indexing_attempt_id,
            indexing_lease_token=indexing_lease_token,
        )

    @classmethod
    async def renew_indexing_lease(
        cls, document_id: str, indexing_attempt_id: str, indexing_lease_token: str
    ):
        return await cls.exchange(
            "renew_indexing_lease",
            document_id=document_id,
            indexing_attempt_id=indexing_attempt_id,
            indexing_lease_token=indexing_lease_token,
        )

    @classmethod
    async def complete_indexing(
        cls, document_id: str, indexing_attempt_id: str, indexing_lease_token: str
    ):
        return await cls.exchange(
            "complete_indexing",
            document_id=document_id,
            indexing_attempt_id=indexing_attempt_id,
            indexing_lease_token=indexing_lease_token,
        )

    @classmethod
    async def mark_unindexed(cls, document_id: str):
        return await cls.exchange("mark_unindexed", document_id=document_id)

    @classmethod
    async def search(cls, query: str):
        return await cls.exchange("search_documents", query=query)
