from fastapi import APIRouter, HTTPException
from schemas.models import SupervisorModel
from services.agent_service import agent_service

router = APIRouter()


@router.post("/call_agent")
async def call_agent(message: str, user_tg_id: int) -> SupervisorModel:
    try:
        response = await agent_service(message=message, user_tg_id=user_tg_id)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
