from typing import Any, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.runnables import RunnableLambda
from langchain_core.utils.function_calling import convert_to_openai_tool
from loguru import logger
from pydantic import Field
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from src.core.infrastructure.configuration import settings
from src.core.model_runtime import run_chat_completion
from src.prompts.model_output import correction_instruction, schema_instruction
from src.prompts.tool_selection import (
    tool_selection_correction_instruction,
    tool_selection_instruction,
)
from src.utils.structured_output import (
    extract_json_value,
    extract_json_values,
    validate_structured_output,
)


def resolve_model_revision(model_id: str, token: Optional[str] = None) -> str:
    from huggingface_hub import HfApi

    info = HfApi(token=token).model_info(model_id)
    if not info.sha:
        raise RuntimeError(f"Unable to resolve an immutable revision for model {model_id}")
    return info.sha


def create_chat_model(model: Optional[str] = None):
    from src.utils.model_provider import model_client

    return HFInferenceChat(client=model_client, model=model or settings.LLM_MODEL)


def _merge_system_messages(messages: List[dict]) -> List[dict]:
    system_content = [
        str(message.get("content", "")) for message in messages if message.get("role") == "system"
    ]
    remaining = [message for message in messages if message.get("role") != "system"]
    if not system_content:
        return remaining
    return [{"role": "system", "content": "\n\n".join(system_content)}, *remaining]


class HFInferenceChat(BaseChatModel):
    client: Any = Field(default=None)
    model: str = Field(default="")

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        import asyncio

        import nest_asyncio

        nest_asyncio.apply()
        return asyncio.run(self._agenerate(messages, stop, run_manager, **kwargs))

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            f"Retrying _agenerate due to error: {retry_state.outcome.exception()} (Attempt {retry_state.attempt_number})"
        ),
    )
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        hf_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = "user"
            elif isinstance(msg, SystemMessage):
                role = "system"
            else:
                role = "assistant"
            hf_messages.append({"role": role, "content": msg.content})
        hf_messages = _merge_system_messages(hf_messages)

        effective_model = self.model or settings.LLM_MODEL
        chat_kwargs = {
            "model": effective_model,
            "messages": hf_messages,
            "max_tokens": kwargs.get("max_tokens", 4096),
            "temperature": kwargs.get("temperature", 0.1),
        }
        from src.utils.model_provider import model_client

        client = self.client or model_client
        content = await run_chat_completion(
            client=client,
            messages=hf_messages,
            model=effective_model,
            max_tokens=chat_kwargs["max_tokens"],
            temperature=chat_kwargs["temperature"],
            attempts=1,
            timeout_seconds=settings.MODEL_TIMEOUT_SECONDS,
        )
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content=content,
                        response_metadata={"model": effective_model},
                    )
                )
            ]
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(
            f"Retrying _astream due to error: {retry_state.outcome.exception()} (Attempt {retry_state.attempt_number})"
        ),
    )
    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ):
        hf_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = "user"
            elif isinstance(msg, SystemMessage):
                role = "system"
            else:
                role = "assistant"
            hf_messages.append({"role": role, "content": msg.content})
        hf_messages = _merge_system_messages(hf_messages)

        from src.utils.model_provider import model_client

        effective_model = self.model or settings.LLM_MODEL
        client = self.client or model_client
        stream = await client.chat_completion(
            model=effective_model,
            messages=hf_messages,
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.1),
            stream=True,
        )

        async for chunk in stream:
            if (
                hasattr(chunk, "choices")
                and len(chunk.choices) > 0
                and hasattr(chunk.choices[0], "delta")
                and chunk.choices[0].delta.content
            ):
                token = chunk.choices[0].delta.content
                chunk_obj = ChatGenerationChunk(message=AIMessageChunk(content=token))
                if run_manager:
                    await run_manager.on_llm_new_token(token, chunk=chunk_obj)
                yield chunk_obj

    @property
    def _llm_type(self) -> str:
        return "hf_inference_chat"

    def with_structured_output(self, schema, **kwargs):
        async def _ainvoke(messages, **kwargs_inner):
            schema_json = (
                schema.model_json_schema()
                if hasattr(schema, "model_json_schema")
                else schema.schema()
            )
            sys_msg = SystemMessage(content=schema_instruction(schema_json))
            msgs = [sys_msg] + (messages if isinstance(messages, list) else [messages])
            maximum_attempts = 3
            for attempt in range(maximum_attempts):
                res = await self.ainvoke(msgs, **kwargs_inner)
                try:
                    return validate_structured_output(res.content, schema)
                except Exception as error:
                    logger.warning(
                        "Structured output validation failed attempt={} error_type={}",
                        attempt + 1,
                        type(error).__name__,
                    )
                    if attempt == maximum_attempts - 1:
                        raise
                    msgs.extend(
                        [
                            AIMessage(content=str(res.content)[:4000]),
                            HumanMessage(content=correction_instruction(error)),
                        ]
                    )
            raise RuntimeError("structured_output_retry_exhausted")

        def _invoke(messages, **kwargs_inner):
            schema_json = (
                schema.model_json_schema()
                if hasattr(schema, "model_json_schema")
                else schema.schema()
            )
            sys_msg = SystemMessage(content=schema_instruction(schema_json))
            msgs = [sys_msg] + (messages if isinstance(messages, list) else [messages])
            maximum_attempts = 3
            for attempt in range(maximum_attempts):
                res = self.invoke(msgs, **kwargs_inner)
                try:
                    return validate_structured_output(res.content, schema)
                except Exception as error:
                    logger.warning(
                        "Structured output validation failed attempt={} error_type={}",
                        attempt + 1,
                        type(error).__name__,
                    )
                    if attempt == maximum_attempts - 1:
                        raise
                    msgs.extend(
                        [
                            AIMessage(content=str(res.content)[:4000]),
                            HumanMessage(content=correction_instruction(error)),
                        ]
                    )
            raise RuntimeError("structured_output_retry_exhausted")

        return RunnableLambda(_invoke, afunc=_ainvoke)

    def bind_tools(self, tools, *, tool_choice=None, **kwargs):
        tool_definitions = [convert_to_openai_tool(tool) for tool in tools]
        tool_map = {tool.name: tool for tool in tools}
        allowed_names = set(tool_map)
        if isinstance(tool_choice, str) and tool_choice not in {"auto", "any", "required", "none"}:
            allowed_names &= {tool_choice}
        forced_name = (
            tool_choice
            if isinstance(tool_choice, str)
            and tool_choice not in {"auto", "any", "required", "none"}
            else None
        )
        selection_prompt = SystemMessage(
            content=tool_selection_instruction(tool_definitions, forced_name)
        )

        def parse_tool_call(content):
            errors = []
            for original_payload in extract_json_values(content):
                try:
                    payload = original_payload
                    if isinstance(payload, dict) and isinstance(payload.get("tool_calls"), list):
                        calls = payload["tool_calls"]
                        payload = calls[0] if calls else {}
                    if isinstance(payload, dict) and isinstance(payload.get("function"), dict):
                        payload = payload["function"]
                    if not isinstance(payload, dict):
                        raise ValueError("Tool selection must be a JSON object")
                    name = payload.get("name") or payload.get("tool")
                    arguments = payload.get(
                        "arguments", payload.get("args", payload.get("parameters", {}))
                    )
                    if isinstance(arguments, str):
                        arguments = extract_json_value(arguments)
                    if name not in allowed_names:
                        raise ValueError("Model selected an unavailable tool")
                    if not isinstance(arguments, dict):
                        raise ValueError("Tool arguments must be a JSON object")
                    selected_tool = tool_map[name]
                    schema = getattr(selected_tool, "args_schema", None)
                    if schema:
                        validated = (
                            schema.model_validate(arguments, strict=True)
                            if hasattr(schema, "model_validate")
                            else schema.parse_obj(arguments)
                        )
                        arguments = (
                            validated.model_dump()
                            if hasattr(validated, "model_dump")
                            else validated.dict()
                        )
                    return AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": name,
                                "args": arguments,
                                "id": f"call_{name}",
                                "type": "tool_call",
                            }
                        ],
                    )
                except Exception as error:
                    errors.append(error)
            if errors:
                raise ValueError(str(errors[-1])) from errors[-1]
            raise ValueError("Model did not return a tool selection")

        async def _ainvoke(messages, **kwargs_inner):
            source_messages = messages if isinstance(messages, list) else [messages]
            corrective_messages = [selection_prompt, *source_messages]
            maximum_attempts = 3
            for attempt in range(maximum_attempts):
                result = await self.ainvoke(corrective_messages, **kwargs_inner)
                try:
                    return parse_tool_call(result.content)
                except Exception as error:
                    logger.warning(
                        "Tool selection validation failed attempt={} error_type={}",
                        attempt + 1,
                        type(error).__name__,
                    )
                    if attempt == maximum_attempts - 1:
                        raise
                    corrective_messages.extend(
                        [
                            AIMessage(content=str(result.content)[:4000]),
                            HumanMessage(
                                content=tool_selection_correction_instruction(error)
                            ),
                        ]
                    )
            raise RuntimeError("tool_selection_retry_exhausted")

        def _invoke(messages, **kwargs_inner):
            source_messages = messages if isinstance(messages, list) else [messages]
            corrective_messages = [selection_prompt, *source_messages]
            maximum_attempts = 3
            for attempt in range(maximum_attempts):
                result = self.invoke(corrective_messages, **kwargs_inner)
                try:
                    return parse_tool_call(result.content)
                except Exception as error:
                    logger.warning(
                        "Tool selection validation failed attempt={} error_type={}",
                        attempt + 1,
                        type(error).__name__,
                    )
                    if attempt == maximum_attempts - 1:
                        raise
                    corrective_messages.extend(
                        [
                            AIMessage(content=str(result.content)[:4000]),
                            HumanMessage(
                                content=tool_selection_correction_instruction(error)
                            ),
                        ]
                    )
            raise RuntimeError("tool_selection_retry_exhausted")

        return RunnableLambda(_invoke, afunc=_ainvoke)
