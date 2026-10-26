from fastapi import APIRouter, Depends, HTTPException, Query

from src.core.dependency import CurrentUser, get_current_user_optional, verify_internal_token
from src.core.metrics import metrics_collector
from src.knowledge.metadata import public_retrieval_metadata
from src.schemas.response import APIResponse
from src.schemas.retrieval import (
    CitationItem,
    CrossDocRetrieveRequest,
    RetrievedDocument,
    RetrieveRequest,
    RetrieveResponse,
)
from src.services.retrieval import RetrievalUnavailableError, retriever
from src.services.retrieval_audit import RetrievalAuditService

router = APIRouter(dependencies=[Depends(verify_internal_token)])


@router.get(
    "/nhat-ky/truy-cap-truy-xuat", description="Truy vấn audit access của knowledge retrieval"
)
async def list_retrieval_access_audit(
    requester_id: str | None = None,
    project_id: str | None = None,
    document_id: str | None = None,
    limit: int = Query(default=500, ge=1, le=5000),
):
    return await RetrievalAuditService.list(
        requester_id, project_id, document_id, limit
    )


@router.post(
    "/truy-xuat",
    response_model=APIResponse[RetrieveResponse],
    description="Truy xuất knowledge bằng dense sparse fusion và rerank",
)
async def retrieve_documents(
    req: RetrieveRequest, user: CurrentUser = Depends(get_current_user_optional)
):
    requester_id = str(user.id) if user else req.requester_id
    is_admin = user.is_admin() if user else req.is_admin
    try:
        docs = await retriever.retrieve(
            query=req.query,
            document_ids=req.document_ids,
            k=req.k,
            query_vector_override=req.query_vector_override,
            requester_id=requester_id,
            is_admin=is_admin,
            metadata_filters=req.metadata_filters.model_dump(exclude_none=True),
        )
    except RetrievalUnavailableError as error:
        raise HTTPException(status_code=503, detail={"code": str(error)}) from error
    await RetrievalAuditService.record("retrieve", req.query, requester_id, is_admin, docs)
    metrics_collector.record_artifact_retrieval(docs, req.metadata_filters.artifact_type)
    citations_data = retriever.get_citations(docs)
    retrieved_docs = [
        RetrievedDocument(
            text=d.get("text", ""),
            metadata=public_retrieval_metadata(d.get("metadata", {})),
            score=float(d.get("score", 0.0)),
        )
        for d in docs
    ]
    citations = [
        CitationItem(
            point_id=c.get("point_id", ""),
            chunk_id=c.get("chunk_id", ""),
            document_id=c.get("document_id", ""),
            title=c.get("title", ""),
            chunk_index=c.get("chunk_index", ""),
            label=c.get("label", ""),
            artifact_type=c.get("artifact_type", ""),
            artifact_id=c.get("artifact_id", ""),
            artifact_version_id=c.get("artifact_version_id", ""),
            source_version=c.get("source_version"),
            page_numbers=c.get("page_numbers", []),
            source_spans=c.get("source_spans", []),
        )
        for c in citations_data
    ]
    return APIResponse(
        data=RetrieveResponse(
            documents=retrieved_docs,
            citations=citations,
            conflicts=retriever.detect_source_conflicts(docs),
        ),
        message="Truy xuất tài liệu thành công",
    )


@router.post(
    "/truy-xuat-lien-tai-lieu",
    response_model=APIResponse[RetrieveResponse],
    description="Truy xuất knowledge liên tài liệu",
)
async def cross_document_retrieve(
    req: CrossDocRetrieveRequest, user: CurrentUser = Depends(get_current_user_optional)
):
    requester_id = str(user.id) if user else req.requester_id
    is_admin = user.is_admin() if user else req.is_admin
    try:
        docs = await retriever.cross_document_retrieve(
            question=req.question,
            document_ids=req.document_ids,
            k=req.k,
            requester_id=requester_id,
            is_admin=is_admin,
            metadata_filters=req.metadata_filters.model_dump(exclude_none=True),
        )
    except RetrievalUnavailableError as error:
        raise HTTPException(status_code=503, detail={"code": str(error)}) from error
    await RetrievalAuditService.record(
        "cross_document_retrieve", req.question, requester_id, is_admin, docs
    )
    metrics_collector.record_artifact_retrieval(docs, req.metadata_filters.artifact_type)
    citations_data = retriever.get_citations(docs)
    retrieved_docs = [
        RetrievedDocument(
            text=d.get("text", ""),
            metadata=public_retrieval_metadata(d.get("metadata", {})),
            score=float(d.get("score", 0.0)),
        )
        for d in docs
    ]
    citations = [
        CitationItem(
            point_id=c.get("point_id", ""),
            chunk_id=c.get("chunk_id", ""),
            document_id=c.get("document_id", ""),
            title=c.get("title", ""),
            chunk_index=c.get("chunk_index", ""),
            label=c.get("label", ""),
            artifact_type=c.get("artifact_type", ""),
            artifact_id=c.get("artifact_id", ""),
            artifact_version_id=c.get("artifact_version_id", ""),
            source_version=c.get("source_version"),
            page_numbers=c.get("page_numbers", []),
            source_spans=c.get("source_spans", []),
        )
        for c in citations_data
    ]
    return APIResponse(
        data=RetrieveResponse(
            documents=retrieved_docs,
            citations=citations,
            conflicts=retriever.detect_source_conflicts(docs),
        ),
        message="Truy xuất liên tài liệu thành công",
    )
