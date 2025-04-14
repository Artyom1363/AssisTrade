import os

from agent.agents import SupervisorAgent
from dotenv import load_dotenv
from schemas.models import SupervisorModel, MessageRequest

load_dotenv()


async def agent_service(message: str) -> SupervisorModel:
    agent = SupervisorAgent(
        model=os.getenv("GEMINI_MODEL"),
        llm_token=os.getenv("GEMINI_API_KEY"),
        logifre_token=os.getenv("LOGFIRE_TOKEN"),
    )
    response = await agent.process_message(message=message)
    return response
