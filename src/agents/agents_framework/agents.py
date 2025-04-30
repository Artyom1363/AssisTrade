import os
import httpx
import logfire
from dotenv import load_dotenv
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider
from pydantic_ai.usage import UsageLimits
from schemas.models import (
    ContactsResponseModel,
    MessageRequest,
    RagResponseModel,
    SearchModel,
    SmallTalkModel,
    SupervisorModel,
    TransactionModel,
    ChatHistoryItem,
    ChatHistoryModel
)
from utils.logger import get_logger

from agents_framework.agents_tool_card import agents_and_tool_catalog
from agents_framework.prompts import (
    SEARCH_PROMPT,
    SMALL_TALK_PROMPT,
    SUPERVISOR_PROMPT,
    TX_AGENT_PROMPT,
)

load_dotenv()
logger = get_logger(__name__)


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

        build_transaction_tool = Tool(
            function=self.build_transaction,
            description="tool to build a transaction, following the user's intent",
            takes_ctx=True,
        )
        small_talk_tool = Tool(
            function=self.small_talk,
            description="tool for small talking with user",
        )

        search_tool = Tool(
            function=self.search,
            description="tool for web search about real-time data",
        )

        chat_history_tool = Tool(
            function=self.get_chat_history,
            description="tool to get chat history for 3 previous messages from user",
        )


        metamask_rag_tool = Tool(
            function=self.metamask_rag,
            description="tool for MetamaskRAGAgent for Metamask QA",
        )
        self.tx_agent = Agent(
            self.model,
            result_type=TransactionModel,
            system_prompt=TX_AGENT_PROMPT,
            tools=[chat_history_tool],
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
        self.search_agent = Agent(
            self.model,
            result_type=SearchModel,
            system_prompt=SEARCH_PROMPT,
            tools=[duckduckgo_search_tool()],
            retries=5,
            instrument=True,
        )
        self.supervisor_agent = Agent(
            self.model,
            result_type=SupervisorModel,
            system_prompt=SUPERVISOR_PROMPT.format(
                agents_and_tool_catalog=str(
                    agents_and_tool_catalog.model_dump_json(indent=2)
                )
            ),
            tools=[
                build_transaction_tool,
                small_talk_tool,
                metamask_rag_tool,
                search_tool,
            ],
            retries=5,
            instrument=True,
        )

    async def build_transaction(
        self, ctx: RunContext[MessageRequest], message: MessageRequest
    ) -> TransactionModel:
        print(f"[build_transaction] message.contacts = {ctx.deps}")
        response = await self.tx_agent.run(
            user_prompt=(f"user message:{message.message} contacts: {ctx.deps}"),
            usage_limits=UsageLimits(response_tokens_limit=1000),
        )
        print(response.all_messages)
        return response.data

    async def small_talk(self, message: MessageRequest) -> SmallTalkModel:
        logger.info(message.message)
        response = await self.small_talk_agent.run(
            user_prompt=message.message,
            usage_limits=UsageLimits(response_tokens_limit=1000),
        )
        logger.info(response)
        return response.data

    async def search(self, message: MessageRequest) -> SearchModel:
        logger.info(message.message)
        response = await self.search_agent.run(
            user_prompt=message.message,
            usage_limits=UsageLimits(response_tokens_limit=1000),
        )
        logger.info(response)
        return response.data

    async def process_message(self, message: MessageRequest) -> SupervisorModel:
        logger.info(f"deps: {message.contacts}")
        logger.info(f"message: {message.message}")
        response = await self.supervisor_agent.run(
            user_prompt=message.message,
            deps=message.contacts,
            usage_limits=UsageLimits(response_tokens_limit=1000),
        )
        logger.info(response)
        return response.data

    async def metamask_rag(self, url: str, query: MessageRequest) -> RagResponseModel:
        url = os.getenv("RAG_URL")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json={"query": query.message})
                response.raise_for_status()
                logger.info(response.json())
                return RagResponseModel.model_validate(response.json())
        except httpx.RequestError as exc:
            print(f"[Request Error] {exc}")
        except httpx.HTTPzStatusError as exc:
            print(f"[HTTP Status Error] {exc.response.status_code}")
        return None

    async def get_contacts(self, url: str, user_tg_id: int) -> ContactsResponseModel:
        url = f"{url}?user_tg_id={user_tg_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                contacts_data = data.get("data", {}).get("contacts", [])
                logger.info(ContactsResponseModel(contacts=contacts_data))
                return ContactsResponseModel(contacts=contacts_data)
        except httpx.RequestError as exc:
            logger.info(f"[Request Error] {exc}")
        except httpx.HTTPStatusError as exc:
            logger.info(f"[HTTP Status Error] {exc.response.status_code}")
        return None

    async def get_chat_history(self, message: MessageRequest, limit: int = 3) -> ChatHistoryModel | None:
        db_server_url = os.getenv("CHAT_HISTORY_URL")
        url = f"{db_server_url}/api/chat_history/{message.user_tg_id}?limit={limit}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                logger.info(f"Chat history for user {user_tg_id}: {data}")
                
                history_items = [ChatHistoryItem(**item) for item in data]
                logger.info(f"history:\n{history_items}")
                return ChatHistoryModel(history=history_items)

        except (httpx.RequestError, httpx.HTTPStatusError, Exception) as exc:
            logger.info(f"[Chat history error] {exc}")
        return None
