from typing import List, Optional
from pydantic import BaseModel, Field
import uuid

class AgentCard(BaseModel):
    """
    Описание одного агента — его имя, id,
    краткое описание и поддерживаемые действия.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    tool: Optional[str] = None
    response: str

class ToolCard(BaseModel):
    """
    Описание одного тула — его имя, id,
    краткое описание и поддерживаемые действия.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    tool: Optional[str] = None
    response: str

class AgentandToolCatalog(BaseModel):
    """
    Коллекция всех карточек.
    """
    agents: Optional[List[AgentCard]]=None
    tools: Optional[List[ToolCard]]=None


agents_and_tool_catalog = AgentandToolCatalog(
    agents=[
        AgentCard(
            name="TransactionAgent",
            description="Agent for building the transaction, following the users requst",
            tool="build_transaction_tool",
            response="tx"
        ),
        AgentCard(
            name="SmallTalkAgent",
            description="Small talk agent for casual simple QA and jokes",
            tool="small_talk_tool",
            response="small_talk"
        ),
        AgentCard(
            name="MetamaskRAGAgent",
            description="MetamaskRAGAgent provides information about metamask specific QA",
            tool="metamask_rag_tool",
            response="rag_response"
        ),
        AgentCard(
            name="SearchAgent",
            description="Search agent for real-time Blockchain only data QA, e.g. token actual price",
            tool="search_tool",
            response="search_response"
        ),
    ],
)