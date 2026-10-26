import asyncio
from contextvars import ContextVar
from typing import Awaitable, Callable, List

from src.core.infrastructure.configuration import settings
from src.core.model_runtime import run_chat_completion
from src.core.security.guardrails import guardrails_engine
from src.core.security.scanning import security
from src.prompts.model_output import correction_instruction, schema_instruction
from src.prompts.retrieval import cross_document_query, document_global_summary
from src.schemas.routing import CrossDocumentQueries
from src.utils.model_provider import model_client
from src.utils.structured_output import validate_structured_output

stream_sink: ContextVar[Callable[[str], Awaitable[None]] | None] = ContextVar(
    "stream_sink", default=None
)


def model_metadata():
    return {"provider": "huggingface", "model": settings.LLM_MODEL}


async def chat(
    messages: List[dict],
    max_tokens: int = 500,
    temperature: float = 0.2,
    attempts: int = 1,
    timeout_seconds: int = 60,
    response_schema: dict | None = None,
):
    sink = stream_sink.get()
    if sink:
        chunks = []
        async with asyncio.timeout(timeout_seconds):
            response = await model_client.chat_completion(
                messages=messages,
                model=settings.LLM_MODEL,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                response_schema=response_schema,
            )
            async for item in response:
                choices = getattr(item, "choices", [])
                piece = str(getattr(choices[0].delta, "content", "")) if choices else ""
                if piece:
                    chunks.append(piece)
                    await sink(piece)
        return "".join(chunks)
    return await run_chat_completion(
        client=model_client,
        messages=messages,
        model=settings.LLM_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        attempts=attempts,
        timeout_seconds=timeout_seconds,
        response_schema=response_schema,
    )


async def structured(
    prompt,
    schema,
    max_tokens=1200,
    timeout_seconds=90,
    provider_schema=True,
    initial_temperature=0.1,
    prompt_attempt_observer=None,
):
    response_schema = schema.model_json_schema()
    constrained_prompt = f"{prompt}\n{schema_instruction(response_schema)}"
    base_messages = [
        {"role": "system", "content": constrained_prompt},
        {"role": "user", "content": "Produce the required output"},
    ]
    messages = base_messages
    maximum_attempts = 4
    for attempt in range(maximum_attempts):
        if prompt_attempt_observer is not None:
            prompt_attempt_observer(
                [dict(message) for message in messages], attempt + 1
            )
        raw = await chat(
            messages,
            max_tokens=max_tokens,
            temperature=initial_temperature if attempt == 0 else 0,
            attempts=1,
            timeout_seconds=timeout_seconds,
            response_schema=response_schema if provider_schema else None,
        )
        try:
            return validate_structured_output(raw, schema)
        except Exception as error:
            if attempt == maximum_attempts - 1:
                raise
            messages = [
                *base_messages,
                {"role": "user", "content": correction_instruction(error)},
            ]
    raise RuntimeError("structured_output_attempts_exhausted")


def prompt_messages(prompt: str, instruction: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": prompt},
        {"role": "user", "content": instruction},
    ]


async def decompose_retrieval(question: str, document_ids: list[str]) -> list[str]:
    result = await structured(
        cross_document_query(question, document_ids),
        CrossDocumentQueries,
        max_tokens=min(1024, 96 * len(document_ids)),
        timeout_seconds=settings.MODEL_TIMEOUT_SECONDS,
    )
    queries = [value.strip() for value in result.queries if value.strip()]
    if len(queries) != len(document_ids):
        raise ValueError("cross_document_decomposition_invalid")
    return queries


async def inspect_chunks(texts: list[str]) -> set[int]:
    async def inspect(index, text):
        result = await security.ascan_input(text)
        return index if result.passed else None

    batch_size = settings.DOCUMENT_CHUNK_INSPECTION_BATCH_SIZE
    accepted = set()
    for batch_start in range(0, len(texts), batch_size):
        batch = texts[batch_start : batch_start + batch_size]
        values = await asyncio.gather(
            *(
                inspect(batch_start + offset, text)
                for offset, text in enumerate(batch)
            )
        )
        accepted.update(value for value in values if value is not None)
    return accepted


async def summarize_document(text: str) -> str:
    inspected = await guardrails_engine.async_inspect_input(text)
    if not inspected.get("is_safe", False):
        raise ValueError("knowledge_summary_input_unsafe")
    summary = await chat(
        prompt_messages(
            document_global_summary(inspected.get("sanitized_text") or text),
            "Produce the requested document summary",
        ),
        max_tokens=512,
    )
    return summary.strip()
