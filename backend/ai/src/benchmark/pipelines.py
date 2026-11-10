import json

from loguru import logger

from src.agents.runner.automation_graph import extract_source_facts
from src.prompts.testability_benchmark import (
    clarification_baseline_instruction,
    direct_generation_baseline_instruction,
)
from src.schemas.automation import AutomationFact
from src.schemas.evaluation import (
    TestabilityBenchmarkCandidate,
    TestabilityBenchmarkGoldCase,
    TestabilityBenchmarkRequest,
)
from src.schemas.inference_requests import TestingAutomationRequest, TestingEvidence
from src.core.text_matching import source_quote_spans
from src.services.ai_automation import generate_ai_automation
from src.services.inference import model_metadata
from src.blueprint import compile_testability_blueprint


class TestabilityBenchmarkPipelines:
    """Run the real Blueprint, clarification, and direct-generation pipelines."""

    @staticmethod
    def _source_evidence(case, dataset_id):
        if case.sources:
            return [
                {
                    "artifact_type": source.artifact_type,
                    "artifact_id": f"{dataset_id}:{case.case_id}:{source.source_id}",
                    "artifact_version_id": source.artifact_version_id,
                    "source": "document",
                    "authority": source.authority,
                    "text": source.text,
                }
                for source in case.sources
            ]
        return [{
            "artifact_type": "benchmark_source",
            "artifact_id": f"{dataset_id}:{case.case_id}",
            "artifact_version_id": f"{dataset_id}:{case.case_id}:source-v1",
            "source": "document",
            "authority": "benchmark_answer_key_dataset",
            "text": case.source_text,
        }]

    @staticmethod
    def _candidate_from_blueprint(output):
        obligations = output.get("obligations", [])
        clarifications = output.get("clarifications", [])
        obligation_evidence = {
            str(item.get("key", "")): [str(item.get("source_quote", ""))]
            for item in obligations
            if item.get("key") and item.get("source_quote")
        }
        return TestabilityBenchmarkCandidate(
            source_quotes=list(dict.fromkeys(
                [item.get("source_quote", "") for item in obligations]
                + [item.get("source_quote", "") for item in clarifications]
            )),
            source_quote_citations=[
                {
                    "quote": str(item.get("source_quote", "")),
                    "source_ref": str(item.get("source_ref", "")),
                }
                for item in obligations
                if item.get("source_quote") and item.get("source_ref")
            ] + [
                {
                    "quote": str(item.get("source_quote", "")),
                    "source_ref": str(source_ref),
                }
                for item in clarifications
                if item.get("source_quote")
                for source_ref in item.get("evidence_refs", [])
                if source_ref
            ],
            clarification_codes=[item.get("code", "") for item in clarifications],
            clarification_categories=[item.get("category", "") for item in clarifications],
            obligation_keys=[item.get("key", "") for item in obligations],
            obligation_texts={
                str(item.get("key") or ""): str(item.get("obligation") or "")
                for item in obligations
                if item.get("key") and item.get("obligation")
            },
            obligation_evidence=obligation_evidence,
            obligation_citations={
                str(item.get("key", "")): [{
                    "quote": str(item.get("source_quote", "")),
                    "source_ref": str(item.get("source_ref", "")),
                }]
                for item in obligations
                if item.get("key") and item.get("source_ref") and item.get("source_quote")
            },
        )

    @staticmethod
    def _candidate_from_clarification(output):
        return TestabilityBenchmarkCandidate(
            source_quotes=[
                item.get("source_quote", "") for item in output.get("clarifications", [])
            ],
            source_quote_citations=[
                {
                    "quote": str(item.get("source_quote", "")),
                    "source_ref": str(source_ref),
                }
                for item in output.get("clarifications", [])
                if item.get("source_quote")
                for source_ref in item.get("evidence_refs", [])
                if source_ref
            ],
            clarification_codes=[
                item.get("code", "") for item in output.get("clarifications", [])
            ],
            clarification_categories=[
                item.get("category", "") for item in output.get("clarifications", [])
            ],
        )

    @staticmethod
    def _candidate_from_direct_generation(output):
        cases = output.get("suggestions", [])
        quotes = []
        quote_citations = []
        obligations = []
        obligation_evidence = {}
        obligation_citations = {}
        for case in cases:
            case_obligations = list(
                dict.fromkeys(
                    str(item)
                    for item in case.get("coverage_obligations", [])
                    if item
                )
            )
            obligations.extend(case_obligations)
            case_quotes = list(dict.fromkeys(
                item.get("quote", "") for item in case.get("evidence_quotes", [])
            ))
            quotes.extend(case_quotes)
            case_citations = [
                {
                    "quote": str(item.get("quote", "")),
                    "source_ref": str(item.get("evidence_ref", "")),
                }
                for item in case.get("evidence_quotes", [])
                if item.get("quote") and item.get("evidence_ref")
            ]
            quote_citations.extend(case_citations)
            for mapping in case.get("obligation_evidence", []):
                obligation = str(mapping.get("obligation_key") or "")
                linked_quotes = [
                    str(item.get("quote", ""))
                    for item in mapping.get("evidence_quotes", [])
                    if item.get("quote") and item.get("evidence_ref")
                ]
                linked_citations = [
                    {
                        "quote": str(item.get("quote", "")),
                        "source_ref": str(item.get("evidence_ref", "")),
                    }
                    for item in mapping.get("evidence_quotes", [])
                    if item.get("quote") and item.get("evidence_ref")
                ]
                if obligation in case_obligations and linked_quotes:
                    obligation_evidence.setdefault(obligation, [])
                    obligation_citations.setdefault(obligation, [])
                    obligation_evidence[obligation].extend(linked_quotes)
                    obligation_citations[obligation].extend(linked_citations)
            if len(case_obligations) == 1 and not case.get("obligation_evidence"):
                obligation = case_obligations[0]
                if case_citations:
                    obligation_evidence.setdefault(obligation, []).extend(
                        citation["quote"] for citation in case_citations
                    )
                    obligation_citations.setdefault(obligation, []).extend(case_citations)
        obligation_evidence = {
            obligation: list(dict.fromkeys(quotes))
            for obligation, quotes in obligation_evidence.items()
        }
        obligation_citations = {
            obligation: list({
                (citation["quote"], citation["source_ref"]): citation
                for citation in citations
            }.values())
            for obligation, citations in obligation_citations.items()
        }
        return TestabilityBenchmarkCandidate(
            source_quotes=list(dict.fromkeys(quotes)),
            source_quote_citations=list({
                (item["quote"], item["source_ref"]): item
                for item in quote_citations
            }.values()),
            obligation_keys=list(dict.fromkeys(obligations)),
            obligation_evidence=obligation_evidence,
            obligation_citations=obligation_citations,
        )

    async def _run_pipeline(self, capability, dataset_id, case, evidence, instruction):
        request = TestingAutomationRequest(
            capability=capability,
            project_id=f"benchmark:{dataset_id}",
            instruction=instruction,
            evidence=[TestingEvidence.model_validate(item) for item in evidence],
        )
        result = await generate_ai_automation(request)
        return result.model_dump(mode="json")

    @staticmethod
    def _verified_fact_evidence(facts, source_evidence):
        grouped = {}
        sources_by_ref = {
            str(item.get("artifact_version_id") or item.get("artifact_id")): item
            for item in source_evidence
            if item.get("artifact_id")
        }
        for fact in facts:
            reference = str(fact.get("artifact_version_id") or "")
            quote = str(fact.get("quote") or "").strip()
            source = sources_by_ref.get(reference)
            start = fact.get("source_start")
            end = fact.get("source_end")
            source_text = str((source or {}).get("text") or "")
            if (
                not reference
                or not source
                or str(source.get("artifact_id") or "") != str(fact.get("artifact_id") or "")
                or not quote
                or type(start) is not int
                or type(end) is not int
                or start < 0
                or end > len(source_text)
                or end <= start
                or end - start != len(quote)
                or source_text[start:end] != quote
                or (start, end) not in source_quote_spans(source_text, quote)
            ):
                continue
            entry = grouped.setdefault(reference, {
                "artifact_type": fact.get("artifact_type") or "benchmark_source",
                "artifact_id": fact.get("artifact_id"),
                "artifact_version_id": fact.get("artifact_version_id"),
                "authority": fact.get("authority") or "benchmark_answer_key_dataset",
                "text": [],
            })
            if quote not in entry["text"]:
                entry["text"].append(quote)
        return [
            {**value, "text": "\n".join(value["text"])}
            for value in grouped.values()
        ]

    async def _run_benchmark_pipeline(self, pipeline, dataset_id, gold_case, source_evidence):
        if pipeline == "compiler":
            extraction = await extract_source_facts(
                {
                    "evidence": source_evidence,
                    "task_instruction": gold_case.task_instruction,
                }
            )
            verified = self._verified_fact_evidence(
                extraction.get("source_facts", []), source_evidence
            )
            if not verified:
                raise RuntimeError("NO_VERIFIED_SOURCE_FACTS")
            evidence_by_ref = {
                str(item.get("artifact_version_id") or item.get("artifact_id")): item
                for item in source_evidence
            }
            source_facts = [
                AutomationFact.model_validate(item)
                for item in extraction.get("source_facts", [])
            ]
            output = await compile_testability_blueprint(
                f"benchmark:{dataset_id}",
                source_facts,
                evidence_by_ref,
                {str(item["artifact_id"]) for item in source_evidence},
                gold_case.task_instruction,
            )
            return self._candidate_from_blueprint(output), output, "compiler"
        if pipeline == "blueprint_self_review":
            extraction = await extract_source_facts(
                {
                    "evidence": source_evidence,
                    "task_instruction": gold_case.task_instruction,
                }
            )
            verified = self._verified_fact_evidence(
                extraction.get("source_facts", []), source_evidence
            )
            if not verified:
                raise RuntimeError("NO_VERIFIED_SOURCE_FACTS")
            evidence_by_ref = {
                str(item.get("artifact_version_id") or item.get("artifact_id")): item
                for item in source_evidence
            }
            source_facts = [
                AutomationFact.model_validate(item)
                for item in extraction.get("source_facts", [])
            ]
            allowed_document_ids = {
                str(item["artifact_id"]) for item in source_evidence
            }
            initial = await compile_testability_blueprint(
                f"benchmark:{dataset_id}",
                source_facts,
                evidence_by_ref,
                allowed_document_ids,
                gold_case.task_instruction,
            )
            if initial.get("status") != "SUCCESS" or initial.get("degraded_mode"):
                raise RuntimeError(
                    ";".join(initial.get("reason_codes") or ["BLUEPRINT_COMPILATION_FAILED"])
                )
            evidence = [TestingEvidence.model_validate(item) for item in source_evidence]
            review_request = TestingAutomationRequest(
                capability="testability_blueprint_self_review",
                project_id=f"benchmark:{dataset_id}",
                instruction=json.dumps(
                    {
                        "task_instruction": gold_case.task_instruction,
                        "blueprint": initial,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                evidence=evidence,
            )
            review_result = await generate_ai_automation(review_request)
            if review_result.status != "SUCCESS" or review_result.degraded_mode:
                raise RuntimeError("BLUEPRINT_SELF_REVIEW_UNAVAILABLE")
            review = {
                "summary": review_result.summary,
                "findings": review_result.findings,
                "improvement_suggestions": review_result.improvement_suggestions,
                "warnings": review_result.warnings,
            }
            allowed_refs = {
                str(item.get("artifact_version_id") or item.get("artifact_id"))
                for item in source_evidence
            }
            known_items = {
                str(item.get("key") or "") for item in initial.get("obligations", [])
            } | {
                str(item.get("code") or "") for item in initial.get("clarifications", [])
            }
            for finding in review["findings"]:
                item_ref = str(finding.get("item_ref") or "")
                refs = finding.get("evidence_refs") or []
                if (
                    (item_ref not in known_items and not item_ref.startswith("GAP:"))
                    or not refs
                    or any(str(ref) not in allowed_refs for ref in refs)
                ):
                    raise RuntimeError("BLUEPRINT_SELF_REVIEW_INVALID")
            suggestions = list(review.get("improvement_suggestions") or [])
            suggestions.extend(
                str(item.get("suggested_change") or "")
                for item in review["findings"]
                if item.get("suggested_change")
            )
            suggestions = list(
                dict.fromkeys(
                    str(item).strip() for item in suggestions if str(item).strip()
                )
            )[:50]
            refined = initial
            if suggestions:
                refinement_instruction = json.dumps(
                    {
                        "task_instruction": gold_case.task_instruction,
                        "task": "Refine the Blueprint once using only the cited source evidence and listed review suggestions. Preserve supported behavior and exact citations. Do not invent or resolve conflicting sources.",
                        "current_blueprint": initial,
                        "review_findings": review["findings"],
                        "improvement_suggestions": suggestions,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                refined = await compile_testability_blueprint(
                    f"benchmark:{dataset_id}",
                    source_facts,
                    evidence_by_ref,
                    allowed_document_ids,
                    refinement_instruction,
                )
                if refined.get("status") != "SUCCESS" or refined.get("degraded_mode"):
                    raise RuntimeError("BLUEPRINT_REFINEMENT_FAILED")
            output = {
                "status": "SUCCESS",
                "before_self_review": initial,
                "self_review": review,
                "after_self_review": refined,
                "refinement_performed": bool(suggestions),
                "model": {
                    "compiler": initial.get("model", {}),
                    "self_review": review_result.model,
                    "refinement": refined.get("model", {}) if suggestions else None,
                },
            }
            return (
                self._candidate_from_blueprint(refined),
                output,
                "blueprint_after_self_review",
            )
        if pipeline == "clarification_without_obligation_planning":
            output = await self._run_pipeline(
                "clarification_baseline",
                dataset_id,
                gold_case,
                source_evidence,
                clarification_baseline_instruction(gold_case.task_instruction),
            )
            return (
                self._candidate_from_clarification(output),
                output,
                "clarification_baseline",
            )
        if pipeline == "direct_generation":
            output = await self._run_pipeline(
                "test_generation",
                dataset_id,
                gold_case,
                source_evidence,
                direct_generation_baseline_instruction(gold_case.task_instruction),
            )
            return self._candidate_from_direct_generation(output), output, "test_generation"
        raise ValueError("BENCHMARK_PIPELINE_UNKNOWN")
