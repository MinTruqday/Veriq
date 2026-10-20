import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse

from src.core.dependency import verify_internal_token
from src.schemas.evaluation import (
    TestabilityBenchmarkDatasetCreate,
    TestabilityBenchmarkReport,
    TestabilityBenchmarkRequest,
    TestabilityBenchmarkRequest,
)
from src.schemas.inference import (
    CrossDocumentExpansionRequest,
    KnowledgeChunkSafetyRequest,
    KnowledgeDocumentSummaryRequest,
    TestingAutomationRequest,
    TestingAutomationResult,
)
from src.services.inference import (
    decompose_retrieval,
    inspect_chunks,
    stream_sink,
    summarize_document,
)
from src.services.ai_automation import generate_ai_automation
from src.services.testability_benchmark import testability_benchmark
from src.repositories.testability_benchmark import testability_benchmark_repository
from pymongo.errors import DuplicateKeyError

router = APIRouter(prefix="/suy-luan")


@router.post(
    "/noi-bo/danh-gia/trinh-bien-dich-kha-nang-kiem-thu",
    dependencies=[Depends(verify_internal_token)],
    response_model=TestabilityBenchmarkReport,
    description=(
        "Đánh giá đầu ra compiler có dẫn nguồn so với sinh test trực tiếp bằng bộ "
        "tình huống và đáp án chuẩn do người thực hiện cung cấp"
    ),
)
async def evaluate_testability_compiler(req: TestabilityBenchmarkRequest):
    return await testability_benchmark.evaluate(req)


@router.post(
    "/noi-bo/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/bo-du-lieu",
    dependencies=[Depends(verify_internal_token)],
    status_code=201,
)
async def create_testability_benchmark_dataset(
    req: TestabilityBenchmarkDatasetCreate,
):
    try:
        return await testability_benchmark_repository.create(req)
    except DuplicateKeyError as error:
        raise HTTPException(status_code=409, detail={"code": "BENCHMARK_DATASET_EXISTS"}) from error


@router.get(
    "/noi-bo/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/bo-du-lieu",
    dependencies=[Depends(verify_internal_token)],
)
async def list_testability_benchmark_datasets(limit: int = 100):
    return await testability_benchmark_repository.list(max(1, min(limit, 100)))


@router.post(
    "/noi-bo/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/bo-du-lieu/{dataset_id}/chay",
    dependencies=[Depends(verify_internal_token)],
    response_model=TestabilityBenchmarkReport,
)
async def evaluate_testability_benchmark_dataset(dataset_id: str):
    dataset = await testability_benchmark_repository.get(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail={"code": "BENCHMARK_DATASET_NOT_FOUND"})
    return await testability_benchmark.evaluate(
        TestabilityBenchmarkRequest(cases=dataset.cases)
    )


@router.post(
    "/noi-bo/phan-ra-lien-tai-lieu",
    dependencies=[Depends(verify_internal_token)],
    description="Phân rã truy vấn theo từng tài liệu đã được chỉ định",
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
    "/noi-bo/kiem-tra-doan-tri-thuc",
    dependencies=[Depends(verify_internal_token)],
    description="Kiểm tra prompt injection và độ an toàn của các đoạn knowledge",
)
async def inspect_knowledge_chunks(req: KnowledgeChunkSafetyRequest):
    return {"safe_indices": sorted(await inspect_chunks(req.texts))}


@router.post(
    "/noi-bo/tom-tat-tai-lieu-tri-thuc",
    dependencies=[Depends(verify_internal_token)],
    description="Tóm tắt tài liệu knowledge sau khi kiểm tra an toàn",
)
async def summarize_knowledge_document(req: KnowledgeDocumentSummaryRequest):
    try:
        summary = await summarize_document(req.text)
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"code": str(error)}) from error
    return {"summary": summary}


@router.post(
    "/noi-bo/kiem-thu/tao-ket-qua",
    dependencies=[Depends(verify_internal_token)],
    response_model=TestingAutomationResult,
    description="Tạo kết quả có cấu trúc cho một bước xử lý nội bộ của AI agent",
)
async def ai_automation(req: TestingAutomationRequest):
    return await generate_ai_automation(req)


@router.post("/noi-bo/kiem-thu/tao-ket-qua/stream", dependencies=[Depends(verify_internal_token)])
async def stream_ai_automation(req: TestingAutomationRequest):
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
            result = await ai_automation(req)
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
