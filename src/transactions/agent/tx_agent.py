import logfire
from pydantic_ai import Agent
from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.providers.mistral import MistralProvider
from pydantic_ai.usage import UsageLimits
from schemas.transaction_schemas import (
    TransactionModel,
    MessageRequest,
)
from agent.prompts import TX_AGENT_PROMPT

class TransactionAgent:
    def __init__(self, model: str, llm_token: str, logifre_token: str = None):
        self.model = MistralModel(
            model_name=model,
            provider=MistralProvider(
                api_key=llm_token,
            ),
        )
        logfire.configure(token=logifre_token)
        logfire.instrument()

        self.agent = Agent(
            self.model,
            result_type=TransactionModel,
            system_prompt=TX_AGENT_PROMPT,
            retries=5,
            instrument=True,
        )

        
    async def process_message(self, message: MessageRequest)-> TransactionModel:
        decision_response = await self.agent.run(user_prompt=message,
                                                     usage_limits=UsageLimits(response_tokens_limit=1000))
        decision = decision_response.data
        return decision