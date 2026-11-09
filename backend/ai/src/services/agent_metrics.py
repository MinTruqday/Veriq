import asyncio
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal, Optional

from loguru import logger
from motor.motor_asyncio import AsyncIOMotorClient

from src.utils.background import create_background_task


@dataclass
class SessionMetrics:
    session_id: str
    user_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    status: Literal["running", "done", "waiting_input", "failed", "cancelled"] = "running"
    total_tool_calls: int = 0
    total_llm_calls: int = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_duration_ms: int = 0
    security_violations: int = 0
    tool_call_breakdown: dict = field(default_factory=dict)
    llm_latencies_ms: list = field(default_factory=list)


_current_session: ContextVar[str | None] = ContextVar("agent_session", default=None)


class AgentMetrics:
    def __init__(self):
        self._sessions: dict[str, SessionMetrics] = {}
        self._db_client = None
        self._lock = asyncio.Lock()
        self._pending_flush: list[dict] = []
        self._flush_task: Optional[asyncio.Task] = None

    def _get_db(self):
        if self._db_client is None:
            try:
                from src.core.infrastructure.configuration import settings

                client = AsyncIOMotorClient(settings.MONGODB_URI)
                self._db_client = client[settings.AI_DB_NAME]
            except Exception:
                logger.exception("MongoDB connection error")
        return self._db_client

    def record_session_start(self, session_id: str, user_id: str):
        metrics = SessionMetrics(
            session_id=session_id, user_id=user_id, started_at=datetime.now(timezone.utc)
        )
        self._sessions[session_id] = metrics
        _current_session.set(session_id)
        logger.info("Started recording session")

    def record_session_end(
        self,
        session_id: str,
        status: Literal["done", "waiting_input", "failed", "cancelled"] = "done",
    ):
        metrics = self._sessions.get(session_id)
        if not metrics:
            return
        metrics.ended_at = datetime.now(timezone.utc)
        metrics.status = status
        metrics.total_duration_ms = int(
            (metrics.ended_at - metrics.started_at).total_seconds() * 1000
        )
        logger.info("Finished recording session")
        create_background_task(self._flush_session(session_id), f"agentops-flush-{session_id}")
        if _current_session.get() == session_id:
            _current_session.set(None)

    def current_session_id(self):
        return _current_session.get()

    def record_tool_call(
        self, session_id: str, tool_name: str, duration_ms: int, success: bool, error: str = ""
    ):
        metrics = self._sessions.get(session_id)
        if metrics:
            metrics.total_tool_calls += 1
            breakdown = metrics.tool_call_breakdown.setdefault(
                tool_name, {"count": 0, "errors": 0, "total_ms": 0}
            )
            breakdown["count"] += 1
            breakdown["total_ms"] += duration_ms
            if not success:
                breakdown["errors"] += 1
        log_fn = logger.info if success else logger.warning
        log_fn("The system successfully recorded the execution event for the invoked utility")

    def record_llm_call(
        self,
        session_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration_ms: int,
    ):
        metrics = self._sessions.get(session_id)
        if metrics:
            metrics.total_llm_calls += 1
            metrics.total_tokens_in += prompt_tokens
            metrics.total_tokens_out += completion_tokens
            metrics.llm_latencies_ms.append(duration_ms)
        logger.info("Recorded language model call event")

    def record_security_event(
        self, session_id: str, event_type: str, risk_score: float, violations: list = None
    ):
        metrics = self._sessions.get(session_id)
        if metrics:
            metrics.security_violations += 1
        logger.warning(
            "Recorded security event type={} risk_score={} violations={}",
            event_type,
            risk_score,
            len(violations or []),
        )

    async def _flush_session(self, session_id: str):
        metrics = self._sessions.pop(session_id, None)
        if not metrics:
            return
        db = self._get_db()
        if db is None:
            return
        try:
            doc = {
                "session_id": metrics.session_id,
                "user_id": metrics.user_id,
                "status": metrics.status,
                "started_at": metrics.started_at,
                "ended_at": metrics.ended_at,
                "total_duration_ms": metrics.total_duration_ms,
                "total_tool_calls": metrics.total_tool_calls,
                "total_llm_calls": metrics.total_llm_calls,
                "total_tokens_in": metrics.total_tokens_in,
                "total_tokens_out": metrics.total_tokens_out,
                "security_violations": metrics.security_violations,
                "tool_call_breakdown": metrics.tool_call_breakdown,
                "avg_llm_latency_ms": (
                    int(sum(metrics.llm_latencies_ms) / len(metrics.llm_latencies_ms))
                    if metrics.llm_latencies_ms
                    else 0
                ),
            }
            await db["agent_traces"].insert_one(doc)
            logger.info("Saved session history")
        except Exception:
            logger.exception("Error saving session history")


agentops = AgentMetrics()
