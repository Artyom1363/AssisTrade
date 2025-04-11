import os

from agent.tx_agent import TransactionAgent
from dotenv import load_dotenv
from schemas.transaction_schemas import TransactionModel

load_dotenv()


async def build_transaction_service(message: str) -> TransactionModel:
    agent = TransactionAgent(
        model=os.getenv("MISTRAL_SMALL"),
        llm_token=os.getenv("MISTRAL_API_KEY"),
        logifre_token=os.getenv("LOGFIRE_TOKEN"),
    )
    response = await agent.process_message(message=message)
    return response
