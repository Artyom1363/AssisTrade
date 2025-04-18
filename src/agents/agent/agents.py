import logfire
from pydantic_ai import Agent
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider
from pydantic_ai.usage import UsageLimits
from pydantic_ai.mcp import MCPServerStdio
from schemas.models import (
    MessageRequest,
    SmallTalkModel,
    SupervisorModel,
    TransactionModel,
    ChainDataModel
)

from agent.prompts import SMALL_TALK_PROMPT, SUPERVISOR_PROMPT, TX_AGENT_PROMPT, CHAIN_DATA_PROMPT


class SupervisorAgent:
    def __init__(self, model: str, llm_token: str, logifre_token: str = None):
        self.model = GeminiModel(
            model_name=model,
            provider=GoogleGLAProvider(
                api_key=llm_token,
            ),
        )
        logfire.configure(token=logifre_token)
        logfire.instrument()

        fetch_server = MCPServerStdio(command="uv", args=["run", "-m", "mcp_server_fetch"])

        self.tx_agent = Agent(
            self.model,
            result_type=TransactionModel,
            system_prompt=TX_AGENT_PROMPT,
            retries=5,
            instrument=True,
        )

        self.small_talk_agent = Agent(
            self.model,
            result_type=SmallTalkModel,
            system_prompt=SMALL_TALK_PROMPT,
            retries=5,
            instrument=True,
        )

        self.chain_data_agent = Agent(
            self.model,
            result_type=ChainDataModel,
            system_prompt=CHAIN_DATA_PROMPT,
            retries=5,
            mcp_servers=[fetch_server],
            instrument=True
        )

        self.supervisor_agent = Agent(
            self.model,
            result_type=SupervisorModel,
            system_prompt=SUPERVISOR_PROMPT,
            tools=[self.build_transaction, self.small_talk, self.chain_data],
            retries=5,
            instrument=True,
        )

    async def build_transaction(self, message: MessageRequest) -> TransactionModel:
        response = await self.tx_agent.run(
            user_prompt=message.message,
            usage_limits=UsageLimits(response_tokens_limit=1000),
        )
        return response.data

    async def small_talk(self, message: MessageRequest) -> SmallTalkModel:
        response = await self.small_talk_agent.run(
            user_prompt=message.message,
            usage_limits=UsageLimits(response_tokens_limit=1000),
        )
        return response.data
    
    async def chain_data(self, message: MessageRequest) -> ChainDataModel:
        response = await self.chain_data_agent.run(
            user_prompt=message.message,
            usage_limits=UsageLimits(response_tokens_limit=1000),
        )
        return response.data


    async def process_message(self, message: MessageRequest) -> SupervisorModel:
        response = await self.supervisor_agent.run(
            user_prompt=message, usage_limits=UsageLimits(response_tokens_limit=1000)
        )
        return response.data
