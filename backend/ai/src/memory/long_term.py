from datetime import datetime, timezone
from uuid import uuid4

from src.repositories.memory import memory_repository
from src.schemas.agent import AgentApprovalStatus, AgentRunStatus, AgentTaskStatus, VeriqRunState


class LongTermMemory:
    async def list(self, project_id: str, requester_id: str, limit: int = 20):
        return await memory_repository.list_long_term(project_id, requester_id, limit)

    async def record_verified(self, state: VeriqRunState):
        if not (
            state.status == AgentRunStatus.COMPLETED
            and state.proposal is not None
            and state.proposal.get("verification", {}).get("verified") is True
            and state.approval_status
            in {None, AgentApprovalStatus.APPROVED, AgentApprovalStatus.REJECTED}
            and all(
                result.get("status") == AgentTaskStatus.COMPLETED
                for result in state.agent_results
            )
        ):
            return None
        value = {
            "_id": f"MEM-{uuid4().hex}",
            "project_id": state.project_id,
            "owner_id": state.user_id,
            "run_id": state.run_id,
            "objective": state.objective,
            "intent": state.intent,
            "proposal": state.proposal,
            "approval_decision": state.approval_decision,
            "evidence_refs": state.evidence_refs,
            "trusted": True,
            "created_at": datetime.now(timezone.utc),
        }
        await memory_repository.record_long_term(state.run_id, value)
        return value


long_term_memory = LongTermMemory()
