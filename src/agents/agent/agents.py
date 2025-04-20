import logfire
import httpx
from pydantic_ai import Agent, Tool, RunContext
from pydantic_ai.models.gemini import GeminiModel
from pydantic_ai.providers.google_gla import GoogleGLAProvider
from pydantic_ai.usage import UsageLimits
from schemas.models import (
    MessageRequest,
    SmallTalkModel,
    SupervisorModel,
    TransactionModel,
    ContactsResponseModel
)

from agent.prompts import SMALL_TALK_PROMPT, SUPERVISOR_PROMPT, TX_AGENT_PROMPT


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
            takes_ctx=True
        )
        small_talk_tool = Tool(
            function=self.small_talk,
            description="tool for small talking with user",
        )

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

        self.supervisor_agent = Agent(
            self.model,
            result_type=SupervisorModel,
            system_prompt=SUPERVISOR_PROMPT,
            tools=[build_transaction_tool, small_talk_tool],
            retries=5,
            instrument=True,
        )
    async def build_transaction(self, ctx: RunContext[MessageRequest], message: MessageRequest) -> TransactionModel:
        print(f"[build_transaction] message.contacts = {ctx.deps}") 
        response = await self.tx_agent.run(
            user_prompt=(f"user message:{message.message} contacts: {ctx.deps}"),
            usage_limits=UsageLimits(response_tokens_limit=1000),
        )
        print(response.all_messages)
        return response.data

    async def small_talk(self, message: MessageRequest) -> SmallTalkModel:
        response = await self.small_talk_agent.run(
            user_prompt=message.message,
            usage_limits=UsageLimits(response_tokens_limit=1000),
        )
        return response.data

    async def process_message(self, message: MessageRequest) -> SupervisorModel:
        response = await self.supervisor_agent.run(
            user_prompt=message.message, 
            deps=message.contacts,
            usage_limits=UsageLimits(response_tokens_limit=1000),
        )
        return response.data


    async def get_contacts(self, url: str, user_tg_id: int) -> ContactsResponseModel:
        url = f"{url}?user_tg_id={user_tg_id}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                contacts_data = data.get("data", {}).get("contacts", [])
                return ContactsResponseModel(contacts=contacts_data)
        except httpx.RequestError as exc:
            print(f"[Request Error] {exc}")
        except httpx.HTTPStatusError as exc:
            print(f"[HTTP Status Error] {exc.response.status_code}")
        return None

