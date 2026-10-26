from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field


class StructuredRouting(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ContextQuery(StructuredRouting):
    question: str = Field(
        description="Standalone question with contextual references resolved"
    )


class GraphRoute(StructuredRouting):
    route: Literal["knowledge", "direct"] = Field(
        description="knowledge when evidence retrieval is required and direct otherwise"
    )


class RetrievalStrategy(StructuredRouting):
    is_simple: bool = Field(
        description="True when one vector query is sufficient to retrieve the answer"
    )
    queries: List[str] = Field(
        description="One to five concise vector search queries"
    )


class QueryOptimization(StructuredRouting):
    question: str = Field(
        description="Concise search query that preserves the original intent"
    )


class RouteDecision(StructuredRouting):
    reasoning: str = Field(
        description="Concise reason for the selected route"
    )
    route: Literal["action", "knowledge", "chat"] = Field(
        description="action for tool use knowledge for retrieval and chat for a direct answer"
    )
    answer: str = Field(
        default="",
        description="Direct answer for the chat route and empty for other routes",
    )


class CrossDocumentQueries(StructuredRouting):
    queries: List[str] = Field(
        min_length=2,
        max_length=100,
    )
