from fastapi import APIRouter, HTTPException, Query
from typing import List
from schemas.models import MessageRequest, SupervisorModel
from services.db_service import get_chat_history, handle_message

router = APIRouter()

# Эндпоинт для получения истории сообщений
@router.get("/chat_history/{user_tg_id}", response_model=List[dict])
async def get_chat_history_endpoint(user_tg_id: int, limit: int = Query(3, ge=1)):
    try:
        history = get_chat_history(user_tg_id, limit)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Эндпоинт для сохранения сообщения
@router.post("/save_message/")
async def save_message_endpoint(message: MessageRequest, supervisor: SupervisorModel):
    try:
        handle_message(message, supervisor)
        return {"status": "Message saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))