import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from pymongo.errors import DuplicateKeyError

from src.core.dependency import require_system_admin, verify_internal_token
from src.repositories.testability_benchmark import testability_benchmark_repository
from src.schemas.auth import CurrentUser
from src.schemas.evaluation import (
    TestabilityBenchmarkDataset,
    TestabilityBenchmarkDatasetCreate,
    TestabilityBenchmarkDatasetReview,
    TestabilityBenchmarkDatasetUpdate,
    TestabilityBenchmarkRepeatedReport,
    TestabilityBenchmarkReport,
    TestabilityBenchmarkRequest,
    benchmark_answer_key_review_covers_cases,
)
from src.schemas.inference_requests import (
    CrossDocumentExpansionRequest,
    KnowledgeChunkSafetyRequest,
    KnowledgeDocumentSummaryRequest,
    TestingAutomationRequest,
    TestingAutomationResult,
)
from src.services.ai_automation import generate_ai_automation
from src.services.inference import (
    decompose_retrieval,
    inspect_chunks,
    stream_sink,
    summarize_document,
)
from src.services.testability_benchmark import testability_benchmark

router = APIRouter(prefix="/suy-luan")


def _require_scoreable_benchmark_dataset(cases):
    try:
        testability_benchmark.validate_cases_for_scoring(cases)
    except ValueError as error:
        reason_code = str(error)
        if reason_code in {
            "benchmark_case_requires_answer_key",
            "benchmark_case_requires_source_quote_answer_key",
        }:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "BENCHMARK_DATASET_ANSWER_KEY_INCOMPLETE",
                    "reason_code": reason_code,
                },
            ) from error
        raise


def _require_independently_reviewed_benchmark_dataset(dataset):
    review = dataset.answer_key_review
    if (
        not dataset.creator_identity_verified
        or not review
        or not review.reviewer_identity_verified
        or review.reviewer_id == dataset.created_by
        or review.decision != "APPROVE"
        or not benchmark_answer_key_review_covers_cases(dataset.cases, review)
    ):
        raise HTTPException(
            status_code=409,
            detail={"code": "BENCHMARK_COMPLETE_INDEPENDENT_CASE_REVIEW_REQUIRED"},
        )


@router.post(
    "/noi-bo/danh-gia/trinh-bien-dich-kha-nang-kiem-thu",
    dependencies=[Depends(verify_internal_token)],
    response_model=TestabilityBenchmarkReport,
    description=(
        "Chỉ chấm các đầu ra đã cung cấp; không gọi model. Dùng endpoint chạy bộ dữ liệu "
        "để thực thi các pipeline AI thật"
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
    current_user: CurrentUser = Depends(require_system_admin),
):
    try:
        return await testability_benchmark_repository.create(req, str(current_user.id))
    except DuplicateKeyError as error:
        raise HTTPException(status_code=409, detail={"code": "BENCHMARK_DATASET_EXISTS"}) from error


@router.get(
    "/noi-bo/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/bo-du-lieu",
    dependencies=[Depends(verify_internal_token)],
)
async def list_testability_benchmark_datasets(limit: int = 100):
    return await testability_benchmark_repository.list(max(1, min(limit, 100)))


@router.get(
    "/noi-bo/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/bo-du-lieu/{dataset_id}",
    dependencies=[Depends(verify_internal_token)],
    response_model=TestabilityBenchmarkDataset,
)
async def get_testability_benchmark_dataset(dataset_id: str):
    dataset = await testability_benchmark_repository.get(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail={"code": "BENCHMARK_DATASET_NOT_FOUND"})
    return dataset


@router.put(
    "/noi-bo/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/bo-du-lieu/{dataset_id}",
    dependencies=[Depends(verify_internal_token)],
    response_model=TestabilityBenchmarkDataset,
    description=(
        "Cập nhật bộ dữ liệu theo revision hiện tại. Mọi thay đổi làm mất rà soát đáp án cũ; "
        "cần một Admin khác rà lại trước lần chạy kế tiếp."
    ),
)
async def update_testability_benchmark_dataset(
    dataset_id: str,
    req: TestabilityBenchmarkDatasetUpdate,
    current_user: CurrentUser = Depends(require_system_admin),
):
    try:
        return await testability_benchmark_repository.update(
            dataset_id, req, str(current_user.id)
        )
    except ValueError as error:
        reason_code = str(error)
        status = 404 if reason_code == "benchmark_dataset_not_found" else 409
        raise HTTPException(status_code=status, detail={"code": reason_code}) from error


@router.post(
    "/noi-bo/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/bo-du-lieu/{dataset_id}/ra-soat-dap-an",
    dependencies=[Depends(verify_internal_token)],
    response_model=TestabilityBenchmarkDataset,
    description=(
        "Ghi nhận rà soát đáp án chuẩn bởi Admin đã xác thực, khác người tạo bộ dữ liệu. "
        "Danh tính được lấy từ phiên đăng nhập, không nhận reviewer_id từ request."
    ),
)
async def review_testability_benchmark_answer_key(
    dataset_id: str,
    req: TestabilityBenchmarkDatasetReview,
    current_user: CurrentUser = Depends(require_system_admin),
):
    try:
        return await testability_benchmark_repository.review_answer_key(
            dataset_id, req, str(current_user.id)
        )
    except ValueError as error:
        reason_code = str(error)
        status = 404 if reason_code == "benchmark_dataset_not_found" else 409
        raise HTTPException(status_code=status, detail={"code": reason_code}) from error


@router.post(
    "/noi-bo/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/bo-du-lieu/{dataset_id}/chay",
    dependencies=[Depends(verify_internal_token)],
    response_model=TestabilityBenchmarkReport,
)
async def evaluate_testability_benchmark_dataset(dataset_id: str):
    dataset = await testability_benchmark_repository.get(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail={"code": "BENCHMARK_DATASET_NOT_FOUND"})
    _require_scoreable_benchmark_dataset(dataset.cases)
    _require_independently_reviewed_benchmark_dataset(dataset)
    report = await testability_benchmark.run_dataset(dataset_id, dataset.cases)
    report.dataset_revision = dataset.revision
    report.answer_key_review = dataset.answer_key_review
    serialized = report.model_dump(mode="json")
    await testability_benchmark_repository.save_run(serialized)
    return report


@router.post(
    "/noi-bo/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/bo-du-lieu/{dataset_id}/chay-lap",
    dependencies=[Depends(verify_internal_token)],
    response_model=TestabilityBenchmarkRepeatedReport,
    description=(
        "Chạy lại các pipeline AI thật theo thứ tự để đo độ biến thiên mô tả; "
        "mỗi lần chạy được lưu riêng để có thể truy xuất đầu ra và lỗi."
    ),
)
async def repeat_testability_benchmark_dataset(
    dataset_id: str,
    repetitions: int = Query(default=3, ge=1, le=5),
):
    dataset = await testability_benchmark_repository.get(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail={"code": "BENCHMARK_DATASET_NOT_FOUND"})
    _require_scoreable_benchmark_dataset(dataset.cases)
    _require_independently_reviewed_benchmark_dataset(dataset)
    async def save_report(report):
        report.dataset_revision = dataset.revision
        report.answer_key_review = dataset.answer_key_review
        await testability_benchmark_repository.save_run(report.model_dump(mode="json"))

    report = await testability_benchmark.run_repeated_dataset(
        dataset_id, dataset.cases, repetitions, on_report=save_report
    )
    report.dataset_revision = dataset.revision
    report.answer_key_review = dataset.answer_key_review
    return report


@router.post(
    "/noi-bo/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/bo-du-lieu-tong-hop/chay-lap",
    dependencies=[Depends(verify_internal_token)],
    response_model=TestabilityBenchmarkRepeatedReport,
    description=(
        "Chạy bộ tình huống tổng hợp có đáp án được sinh theo quy tắc xác định. "
        "Đây là kiểm tra kỹ thuật, không thay thế rà soát độc lập hoặc dữ liệu thực nghiệm."
    ),
)
async def run_synthetic_testability_benchmark(
    current_user: CurrentUser = Depends(require_system_admin),
):
    async def save_report(report):
        await testability_benchmark_repository.save_run(
            report.model_dump(mode="json")
        )

    return await testability_benchmark.run_synthetic_benchmark(
        repetitions=3,
        on_report=save_report,
    )


@router.get(
    "/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/tong-hop/lan-chay",
    response_model=list[dict],
)
async def list_synthetic_testability_benchmark_runs(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_system_admin),
):
    return await testability_benchmark_repository.list_runs(
        list(testability_benchmark.SYNTHETIC_DATASET_IDS),
        limit,
    )


@router.post(
    "/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/tong-hop/chay-lap",
    response_model=TestabilityBenchmarkRepeatedReport,
    description=(
        "Chạy ba pipeline AI trên 30 tình huống tổng hợp có đáp án sinh theo quy tắc công khai. "
        "Kết quả chỉ kiểm tra kỹ thuật trên bộ tình huống này, không chứng minh ưu thế tổng quát."
    ),
)
async def run_synthetic_testability_benchmark_for_admin(
    current_user: CurrentUser = Depends(require_system_admin),
):
    async def save_report(report):
        await testability_benchmark_repository.save_run(
            report.model_dump(mode="json")
        )

    return await testability_benchmark.run_synthetic_benchmark(
        repetitions=3,
        on_report=save_report,
    )


@router.get(
    "/noi-bo/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/bo-du-lieu/{dataset_id}/lan-chay",
    dependencies=[Depends(verify_internal_token)],
)
async def list_testability_benchmark_runs(dataset_id: str, limit: int = 20):
    dataset = await testability_benchmark_repository.get(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail={"code": "BENCHMARK_DATASET_NOT_FOUND"})
    return await testability_benchmark_repository.list_runs(
        dataset_id, max(1, min(limit, 100))
    )


@router.get(
    "/noi-bo/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/bo-du-lieu/{dataset_id}/lan-chay/{run_id}",
    dependencies=[Depends(verify_internal_token)],
    response_model=TestabilityBenchmarkReport,
)
async def get_testability_benchmark_run(dataset_id: str, run_id: str):
    report = await testability_benchmark_repository.get_run(dataset_id, run_id)
    if not report:
        raise HTTPException(status_code=404, detail={"code": "BENCHMARK_RUN_NOT_FOUND"})
    return report


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
