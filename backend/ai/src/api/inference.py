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
    TestabilityBlueprintBenchmarkRequest,
    benchmark_answer_key_review_covers_cases,
)
from src.schemas.inference_requests import (
    CrossDocumentExpansionRequest,
    KnowledgeDocumentSummaryRequest,
    TestingAutomationRequest,
    TestingAutomationResult,
)
from src.services.ai_automation import generate_ai_automation
from src.services.inference import (
    decompose_retrieval,
    stream_sink,
    summarize_document,
)
from src.benchmark import testability_benchmark

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


def _apply_reference_provenance(report, dataset):
    report.reference_provenance = dataset.reference_provenance
    report.answer_key_review = dataset.answer_key_review
    report.benchmark_design = {
        **(report.benchmark_design or {}),
        "answer_key_basis": (
            "self_prepared_experimental_answer_key"
            if dataset.reference_provenance == "SELF_PREPARED_REFERENCE"
            else "independently_reviewed_answer_key"
        ),
        "independently_validated": (
            dataset.reference_provenance == "INDEPENDENT_REFERENCE"
            and bool(dataset.answer_key_review)
        ),
    }


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
    "/noi-bo/danh-gia/blueprint",
    dependencies=[Depends(verify_internal_token)],
)
async def evaluate_blueprint_against_reference(req: TestabilityBlueprintBenchmarkRequest):
    source_signature = {
        item.artifact_version_id: item.text for item in req.sources
    }
    if len(source_signature) != len(req.sources):
        raise HTTPException(status_code=422, detail={"code": "BLUEPRINT_BENCHMARK_SOURCE_DUPLICATE"})
    datasets = await testability_benchmark_repository.list_reviewed_datasets_for_matching(
        req.project_id, req.requester_user_id
    )
    exact_matches = []
    for dataset in datasets:
        review = dataset.answer_key_review
        independently_reviewed = bool(
            review
            and dataset.creator_identity_verified
            and review.reviewer_identity_verified
            and review.decision == "APPROVE"
            and review.reviewer_id != dataset.created_by
            and benchmark_answer_key_review_covers_cases(dataset.cases, review)
        )
        self_prepared = dataset.reference_provenance == "SELF_PREPARED_REFERENCE"
        if not independently_reviewed and not self_prepared:
            continue
        for gold_case in dataset.cases:
            if not gold_case.sources:
                continue
            gold_sources = {
                source.artifact_version_id: source.text
                for source in gold_case.sources
            }
            if gold_sources == source_signature:
                exact_matches.append((dataset, gold_case, independently_reviewed))
    if len(exact_matches) != 1:
        return {
            "assessment_type": "NOT_AVAILABLE",
            "independently_validated": False,
            "reason": (
                "Không tìm thấy duy nhất một bộ tham chiếu phù hợp khớp chính xác với nguồn."
                if not exact_matches
                else "Có nhiều đáp án chuẩn khớp nguồn; cần chọn bộ tham chiếu rõ ràng trước khi chấm."
            ),
        }
    dataset, gold_case, independently_reviewed = exact_matches[0]
    try:
        testability_benchmark.validate_cases_for_scoring([gold_case])
        candidate_quotes = []
        quote_citations = []
        obligation_evidence = {}
        obligation_citations = {}
        for obligation in req.blueprint.get("obligations", []):
            key = str(obligation.get("key") or "").strip()
            quote = str(obligation.get("source_quote") or "").strip()
            ref = str(obligation.get("source_ref") or "").strip()
            if key and quote and ref in source_signature and quote in source_signature[ref]:
                candidate_quotes.append(quote)
                quote_citations.append({"quote": quote, "source_ref": ref})
                obligation_evidence[key] = [quote]
                obligation_citations[key] = [{"quote": quote, "source_ref": ref}]
        for clarification in req.blueprint.get("clarifications", []):
            quote = str(clarification.get("source_quote") or "").strip()
            refs = [str(item) for item in clarification.get("evidence_refs", [])]
            ref = next((item for item in refs if item in source_signature and quote in source_signature[item]), "")
            if quote and ref:
                candidate_quotes.append(quote)
                quote_citations.append({"quote": quote, "source_ref": ref})
        benchmark_case = gold_case.model_dump(mode="python")
        benchmark_case.update({
            "compiler": {
                "source_quotes": list(dict.fromkeys(candidate_quotes)),
                "source_quote_citations": quote_citations,
                "clarification_codes": [str(item.get("code") or "") for item in req.blueprint.get("clarifications", []) if item.get("code")],
                "clarification_categories": [str(item.get("category") or "") for item in req.blueprint.get("clarifications", []) if item.get("category")],
                "obligation_keys": [str(item.get("key") or "") for item in req.blueprint.get("obligations", []) if item.get("key")],
                "obligation_evidence": obligation_evidence,
                "obligation_citations": obligation_citations,
            },
        })
        report = await testability_benchmark.evaluate(
            TestabilityBenchmarkRequest(cases=[benchmark_case])
        )
    except (ValueError, TypeError) as error:
        raise HTTPException(status_code=422, detail={"code": "BLUEPRINT_BENCHMARK_INPUT_INVALID"}) from error
    return {
        "assessment_type": (
            "INDEPENDENT_REFERENCE"
            if independently_reviewed
            else "SELF_PREPARED_REFERENCE"
        ),
        "independently_validated": independently_reviewed,
        "dataset_id": dataset.dataset_id,
        "dataset_revision": dataset.revision,
        "case_id": gold_case.case_id,
        "metrics": report.compiler,
        "semantic_obligation_metrics": await testability_benchmark.evaluate_blueprint_semantics(
            dataset.dataset_id,
            gold_case,
            {},
            req.blueprint,
            [
                {
                    "artifact_type": source.artifact_type,
                    "artifact_id": source.source_id,
                    "artifact_version_id": source.artifact_version_id,
                    "authority": source.authority,
                    "text": source.text,
                }
                for source in req.sources
            ],
        ),
    }


@router.post(
    "/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/bo-du-lieu",
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
    "/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/bo-du-lieu",
)
async def list_testability_benchmark_datasets(
    limit: int = 100,
    current_user: CurrentUser = Depends(require_system_admin),
):
    return await testability_benchmark_repository.list(max(1, min(limit, 100)))


@router.get(
    "/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/bo-du-lieu/{dataset_id}",
    response_model=TestabilityBenchmarkDataset,
)
async def get_testability_benchmark_dataset(
    dataset_id: str,
    current_user: CurrentUser = Depends(require_system_admin),
):
    dataset = await testability_benchmark_repository.get(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail={"code": "BENCHMARK_DATASET_NOT_FOUND"})
    return dataset


@router.put(
    "/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/bo-du-lieu/{dataset_id}",
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
    "/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/bo-du-lieu/{dataset_id}/ra-soat-dap-an",
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
    "/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/bo-du-lieu/{dataset_id}/chay",
    response_model=TestabilityBenchmarkReport,
)
async def evaluate_testability_benchmark_dataset(
    dataset_id: str,
    current_user: CurrentUser = Depends(require_system_admin),
):
    dataset = await testability_benchmark_repository.get(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail={"code": "BENCHMARK_DATASET_NOT_FOUND"})
    _require_scoreable_benchmark_dataset(dataset.cases)
    if dataset.reference_provenance == "INDEPENDENT_REFERENCE":
        _require_independently_reviewed_benchmark_dataset(dataset)
    elif not dataset.project_id or not dataset.creator_identity_verified:
        raise HTTPException(
            status_code=409,
            detail={"code": "BENCHMARK_SELF_PREPARED_REFERENCE_SCOPE_INVALID"},
        )
    report = await testability_benchmark.run_dataset(dataset_id, dataset.cases)
    report.dataset_revision = dataset.revision
    _apply_reference_provenance(report, dataset)
    serialized = report.model_dump(mode="json")
    await testability_benchmark_repository.save_run(serialized)
    return report


@router.post(
    "/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/bo-du-lieu/{dataset_id}/chay-lap",
    response_model=TestabilityBenchmarkRepeatedReport,
    description=(
        "Chạy lại các pipeline AI thật theo thứ tự để đo độ biến thiên mô tả; "
        "mỗi lần chạy được lưu riêng để có thể truy xuất đầu ra và lỗi."
    ),
)
async def repeat_testability_benchmark_dataset(
    dataset_id: str,
    repetitions: int = Query(default=3, ge=1, le=5),
    current_user: CurrentUser = Depends(require_system_admin),
):
    dataset = await testability_benchmark_repository.get(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail={"code": "BENCHMARK_DATASET_NOT_FOUND"})
    _require_scoreable_benchmark_dataset(dataset.cases)
    if dataset.reference_provenance == "INDEPENDENT_REFERENCE":
        _require_independently_reviewed_benchmark_dataset(dataset)
    elif not dataset.project_id or not dataset.creator_identity_verified:
        raise HTTPException(
            status_code=409,
            detail={"code": "BENCHMARK_SELF_PREPARED_REFERENCE_SCOPE_INVALID"},
        )
    async def save_report(report):
        report.dataset_revision = dataset.revision
        _apply_reference_provenance(report, dataset)
        await testability_benchmark_repository.save_run(report.model_dump(mode="json"))

    report = await testability_benchmark.run_repeated_dataset(
        dataset_id, dataset.cases, repetitions, on_report=save_report
    )
    report.dataset_revision = dataset.revision
    _apply_reference_provenance(report, dataset)
    return report


@router.get(
    "/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/bo-du-lieu/{dataset_id}/lan-chay",
)
async def list_testability_benchmark_runs(
    dataset_id: str,
    limit: int = 20,
    current_user: CurrentUser = Depends(require_system_admin),
):
    dataset = await testability_benchmark_repository.get(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail={"code": "BENCHMARK_DATASET_NOT_FOUND"})
    return await testability_benchmark_repository.list_runs(
        dataset_id, max(1, min(limit, 100))
    )


@router.get(
    "/danh-gia/trinh-bien-dich-kha-nang-kiem-thu/bo-du-lieu/{dataset_id}/lan-chay/{run_id}",
    response_model=TestabilityBenchmarkReport,
)
async def get_testability_benchmark_run(
    dataset_id: str,
    run_id: str,
    current_user: CurrentUser = Depends(require_system_admin),
):
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
    "/noi-bo/tom-tat-tai-lieu-tri-thuc",
    dependencies=[Depends(verify_internal_token)],
    description="Tóm tắt tài liệu knowledge sau khi kiểm tra an toàn",
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
