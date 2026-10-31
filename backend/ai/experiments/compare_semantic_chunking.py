import asyncio
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getenv("VERIQ_AI_SOURCE_ROOT", str(Path(__file__).resolve().parents[1])))
from src.services.chunking import ChunkingService, embedder

OUT = Path(os.getenv("RESULTS_PATH", "/tmp/semantic_chunking_ab_results.json"))

TOPICS = [
    ("Dang nhap va khoa tai khoan", [
        ("login_success", "When a user submits a valid email and password, the identity service verifies the credentials, creates a session with a fifteen minute idle timeout, records the authentication event, and redirects the user to the project dashboard. The session identifier is rotated after authentication so a previous anonymous browser session cannot be reused."),
        ("login_lockout", "When a user submits an incorrect password five times in a row, the identity service locks that account for fifteen minutes, records the failed attempts, and returns the same public error used for an unknown email. Other accounts and active sessions remain available while the affected account is locked."),
    ]),
    ("Import tai lieu va trich xuat", [
        ("document_tables", "During document import, table extraction preserves the table title, column headers, row order, cell text, page number, and source block identifier. A table continuing onto another page is represented as linked table segments with the repeated header retained, so a retrieved value can be traced to its original page and row."),
        ("document_ocr", "For scanned pages, OCR stores the recognized text together with page number, confidence, and the bounding region when the parser provides it. Low confidence or unreadable regions are reported as extraction warnings and are not silently replaced with guessed requirements or expected results."),
    ]),
    ("Phan quyen va duyet yeu cau", [
        ("requirement_ba_edit", "A Business Analyst creates and edits a draft requirement and may attach source evidence. The analyst can submit the draft for review but cannot approve the requirement. Edits remain in the draft revision and do not overwrite an approved revision used by an existing test run."),
        ("requirement_qa_approve", "A Quality Assurance member reviews a submitted requirement, checks its source links and acceptance criteria, and can approve it or return it with a reason. Approval is recorded with the reviewer identity and revision. A user who has only the Tester role receives a forbidden response when attempting approval."),
    ]),
    ("Sinh va thuc thi ca kiem thu", [
        ("case_generation", "After a requirement is approved, a user may start test case generation. The proposed case contains preconditions, ordered steps, test data, expected results, risk, and links to the requirement version and cited source blocks. The generated proposal remains a draft until a QA reviewer accepts it."),
        ("case_execution", "When a tester starts an assigned execution, the run records the frozen test case version, build, environment, executor, step outcomes, actual result, and evidence. Reusing the same test case in another run creates a separate execution record and never copies the previous pass or fail result."),
    ]),
]
QUESTIONS = [
    ("How long is an authenticated session idle before timeout?", "login_success"),
    ("What happens after five consecutive incorrect password attempts?", "login_lockout"),
    ("Which table details must survive a multi-page import?", "document_tables"),
    ("How does the system treat low confidence OCR text?", "document_ocr"),
    ("Can a BA approve a requirement they drafted?", "requirement_ba_edit"),
    ("What does QA record when returning a requirement for changes?", "requirement_qa_approve"),
    ("Which fields and trace links should AI include in a proposed test case?", "case_generation"),
    ("Does a test case reused in a new run retain its previous result?", "case_execution"),
]


def build_structure(include_headings):
    blocks = []
    markdown = []
    for section_index, (heading, entries) in enumerate(TOPICS, 1):
        heading_id = f"heading-{section_index}"
        if include_headings:
            blocks.append({"block_id": heading_id, "type": "section_header", "level": 1, "text": heading, "page_no": section_index})
            markdown.append(f"# {heading}")
        for block_id, body in entries:
            block = {"block_id": block_id, "type": "paragraph", "text": body, "page_no": section_index}
            if include_headings:
                block["parent_block_id"] = heading_id
            blocks.append(block)
            markdown.append(body)
    return "\n\n".join(markdown), blocks


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def chunk_has_block(chunk, expected):
    spans = chunk.get("metadata", {}).get("source_spans") or []
    return any(span.get("block_id") == expected for span in spans)


async def main():
    service = ChunkingService()
    original_embed_batch = embedder.embed_batch
    usage = []

    async def counted_embed_batch(texts):
        unique = list(dict.fromkeys(texts))
        cache = getattr(embedder, "_cache", None)
        cache_hits = 0
        if cache:
            for text in unique:
                try:
                    if cache.get(embedder._cache_key(text, "passage")):
                        cache_hits += 1
                except Exception:
                    pass
        vectors = await original_embed_batch(texts)
        usage.append({"texts": len(texts), "unique_texts": len(unique), "cache_hits": cache_hits})
        return vectors

    embedder.embed_batch = counted_embed_batch
    all_cases = {}
    for case_name, include_headings in (("structured_headings", True), ("prose_without_headings", False)):
        markdown, structure = build_structure(include_headings)
        case_runs = {}
        for mode, semantic in (("current_semantic", True), ("without_semantic_cosine", False)):
            usage.clear()
            chunks = [chunk async for chunk in service.iter_chunk_document(
                markdown,
                {"document_id": f"synthetic-{case_name}", "source_version": "v1"},
                structure,
                semantic=semantic,
            )]
            chunk_texts = [chunk["text"] for chunk in chunks]
            chunk_vectors = await counted_embed_batch(chunk_texts)
            final_stats = usage[-1] if usage else {"texts": len(chunk_texts), "unique_texts": len(set(chunk_texts)), "cache_hits": 0}
            unit_stats = usage[:-1]
            query_vectors = [await embedder.embed_query(question) for question, _ in QUESTIONS]
            query_results = []
            for (question, expected_block), query_vector in zip(QUESTIONS, query_vectors):
                ranked = sorted(range(len(chunks)), key=lambda i: cosine(query_vector, chunk_vectors[i]), reverse=True)
                top1, top3 = ranked[:1], ranked[:3]
                query_results.append({
                    "question": question,
                    "expected_source_block": expected_block,
                    "top1_contains_source": any(chunk_has_block(chunks[i], expected_block) for i in top1),
                    "top3_contains_source": any(chunk_has_block(chunks[i], expected_block) for i in top3),
                    "top1_source_blocks": [span.get("block_id") for span in chunks[top1[0]].get("metadata", {}).get("source_spans", [])],
                    "top1_score": round(cosine(query_vector, chunk_vectors[top1[0]]), 6),
                })
            case_runs[mode] = {
                "chunk_count": len(chunks),
                "chunk_sizes_chars": [len(text) for text in chunk_texts],
                "chunks": [{"index": i, "text": chunk["text"], "source_blocks": [span.get("block_id") for span in chunk.get("metadata", {}).get("source_spans", [])], "chunk_type": chunk.get("metadata", {}).get("chunk_type")} for i, chunk in enumerate(chunks)],
                "unit_embedding_batches": unit_stats,
                "final_chunk_embedding": final_stats,
                "queries": query_results,
                "recall_at_1": round(sum(row["top1_contains_source"] for row in query_results) / len(query_results), 4),
                "recall_at_3": round(sum(row["top3_contains_source"] for row in query_results) / len(query_results), 4),
            }
        all_cases[case_name] = case_runs

    embedder.embed_batch = original_embed_batch
    OUT.write_text(json.dumps({
        "corpus": {"scenarios": 2, "section_count": len(TOPICS), "source_paragraph_count": len(QUESTIONS), "query_count_per_scenario": len(QUESTIONS)},
        "metric_note": "Fixed synthetic corpus with explicit source-block ground truth. Queries and final chunks used the configured production embedding model; chunk vectors were ranked by cosine locally. No Qdrant writes, reranker, LLM, or real project data were used. The prose-only scenario removes headings but preserves paragraph order and source ids.",
        "cases": all_cases,
    }, ensure_ascii=False, indent=2))
    summary = {}
    for case_name, modes in all_cases.items():
        summary[case_name] = {}
        for name, value in modes.items():
            summary[case_name][name] = {
                "chunks": value["chunk_count"],
                "recall@1": value["recall_at_1"],
                "recall@3": value["recall_at_3"],
                "unit_embed_inputs": sum(batch["texts"] for batch in value["unit_embedding_batches"]),
                "final_chunk_embed_inputs": value["final_chunk_embedding"]["texts"],
            }
    print(OUT)
    print(json.dumps(summary, ensure_ascii=False, indent=2))

asyncio.run(main())
