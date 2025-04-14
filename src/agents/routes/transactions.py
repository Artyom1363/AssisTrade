from fastapi import APIRouter, HTTPException
from schemas.models import SupervisorModel
from services.agent_service import agent_service

router = APIRouter()


@router.post("/call_agent")
async def call_agent(message: str) -> SupervisorModel:
    try:
        response = await agent_service(message=message)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
