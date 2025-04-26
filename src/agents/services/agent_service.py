import os

from agents_framework.agents import SupervisorAgent
from dotenv import load_dotenv
from schemas.models import MessageRequest, SupervisorModel

load_dotenv()


async def agent_service(message: str, user_tg_id: str) -> SupervisorModel:
    agent = SupervisorAgent(
        model=os.getenv("GEMINI_MODEL"),
        llm_token=os.getenv("GEMINI_API_KEY"),
        logifre_token=os.getenv("LOGFIRE_TOKEN"),
    )
    contacts = await agent.get_contacts(
        url=os.getenv("DB_SERVER_URL"), user_tg_id=user_tg_id
    )
    response = await agent.process_message(
        MessageRequest(message=message, contacts=contacts)
    )
    return response
