import os
import httpx
from agents_framework.agents import SupervisorAgent
from dotenv import load_dotenv
from schemas.models import MessageRequest, SupervisorModel
import asyncio
from utils.logger import get_logger

load_dotenv()
logger = get_logger(__name__)

async def agent_service(message: str, user_tg_id: str) -> SupervisorModel:
    agent = SupervisorAgent(
        model=os.getenv("GEMINI_MODEL"),
        llm_token=os.getenv("GEMINI_API_KEY"),
        logifre_token=os.getenv("LOGFIRE_TOKEN"),
    )
    contacts = await agent.get_contacts(
        url=os.getenv("CONTACTS_URL"), user_tg_id=user_tg_id
    )
    response = await agent.process_message(
        MessageRequest(message=message, contacts=contacts)
    )

    asyncio.create_task(
        save_message_to_db(
            message=MessageRequest(user_tg_id=user_tg_id, message=message),
            supervisor=response
        )
    )
    return response

async def save_message_to_db(message: MessageRequest, supervisor: SupervisorModel):
    db_server_url = os.getenv("CHAT_HISTORY_URL")
    save_message_url = f"{db_server_url}/api/save_message/"
    try:
        supervisor_data = {
            "reasoning": supervisor.reasoning,
            "tx": supervisor.tx and {
                "decision": supervisor.tx.decision,
                "reasoning": supervisor.tx.reasoning,
                "transaction": supervisor.tx.transaction and {
                    "to": supervisor.tx.transaction.to,
                    "value": supervisor.tx.transaction.value,
                    "currency": supervisor.tx.transaction.currency
                }
            } or None
        }

        message_data = message.dict()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                save_message_url,
                json={
                    "message": message_data,
                    "supervisor": supervisor_data
                }
            )
            response.raise_for_status()
    except Exception as e:
        logger.info(f"Failed to save message to DB: {e}")

