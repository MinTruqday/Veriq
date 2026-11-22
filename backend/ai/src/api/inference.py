import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse

from src.core.dependency import verify_internal_token
from src.schemas.inference_requests import (
    CrossDocumentExpansionRequest,
    KnowledgeDocumentSummaryRequest,
    TestingCapabilityRequest,
    TestingCapabilityResult,
)
from src.services.ai_capabilities import generate_ai_capability
from src.services.inference import (
    decompose_retrieval,
    stream_sink,
    summarize_document,
)

router = APIRouter(prefix="/suy-luan")


@router.post(
    "/noi-bo/phan-ra-lien-tai-lieu",
    dependencies=[Depends(verify_internal_token)],
    description="Decompose a query across the specified documents",
)
async def decompose_cross_document_query(req: CrossDocumentExpansionRequest):
    try:
        queries = await decompose_retrieval(req.question, req.document_ids)
    except Exception as error:
        raise HTTPException(
            status_code=502, detail={"code": "cross_document_query_unavailable"}
        ) from error
    return {"queries": queries}


@router.post(
    "/noi-bo/tom-tat-tai-lieu-tri-thuc",
    dependencies=[Depends(verify_internal_token)],
    description="Summarize a knowledge document after safety inspection",
)
async def summarize_knowledge_document(req: KnowledgeDocumentSummaryRequest):
    try:
        summary = await summarize_document(req.text, req.output_language)
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": str(error)}) from error
    return {"summary": summary}


@router.post(
    "/noi-bo/kiem-thu/tao-ket-qua",
    dependencies=[Depends(verify_internal_token)],
    response_model=TestingCapabilityResult,
    description="Generate structured output for an internal AI agent step",
)
async def ai_capability(req: TestingCapabilityRequest):
    return await generate_ai_capability(req)


@router.post("/noi-bo/kiem-thu/tao-ket-qua/stream", dependencies=[Depends(verify_internal_token)])
async def stream_ai_capability(req: TestingCapabilityRequest):
    queue = asyncio.Queue()

    async def emit(piece):
        from src.core.security.guardrails import guardrails_engine

        assessment = guardrails_engine.inspect_output(piece)
        if not assessment.get("is_safe", False):
            raise ValueError("AI_STREAM_OUTPUT_UNSAFE")
        safe_piece = str(assessment.get("sanitized_text") or "")
        if safe_piece:
            await queue.put({"type": "delta", "delta": safe_piece})

    async def run():
        token = stream_sink.set(emit)
        try:
            result = await ai_capability(req)
            await queue.put({"type": "result", "data": jsonable_encoder(result)})
        except Exception as error:
            await queue.put({"type": "error", "code": type(error).__name__})
        finally:
            stream_sink.reset(token)
            await queue.put(None)

    async def events():
        task = asyncio.create_task(run())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
