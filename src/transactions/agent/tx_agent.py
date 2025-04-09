import logfire
from pydantic_ai import Agent
from pydantic_ai.models.mistral import MistralModel
from pydantic_ai.providers.mistral import MistralProvider
from schemas.transaction_schemas import (
    SupervisorResponse,
    TransactionDict,
    TransactionNER,
    TransactionResult,
)

from agent.prompts import SupervisorPrompt, TransactionNERPrompt


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

        self.supervisor = Agent(
            self.model,
            result_type=SupervisorResponse,
            system_prompt=SupervisorPrompt,
            retries=5,
            instrument=True,
        )
        self.ner_agent = Agent(
            self.model,
            result_type=TransactionNER,
            system_prompt=TransactionNERPrompt,
            retries=5,
            instrument=True,
        )

    async def process_message(self, message: str):
        decision_response = await self.supervisor.run(user_prompt=message)
        decision = decision_response.data

        if decision.decision == "@BuildTransaction":
            ner_response = await self.ner_agent.run(user_prompt=message)
            ner = ner_response.data
            transaction = TransactionDict(to=ner.receiver, value=ner.value)
            return TransactionResult(
                status="Build", transaction=transaction, reasoning=decision.reasoning
            )
        else:
            return TransactionResult(status="Reject", reasoning=decision.reasoning)
