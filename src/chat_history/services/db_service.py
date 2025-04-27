from db.database import save_message, get_last_chat_history
from schemas.models import MessageRequest, SupervisorModel
from typing import List

def handle_message(message: MessageRequest, supervisor: SupervisorModel):
    """
    Обрабатывает сообщение пользователя и ответ супервизора.
    Сохраняет сообщение и решение супервизора в базе данных.
    """
    reasoning = supervisor.reasoning
    tx = supervisor.tx
    
    save_message(
        user_tg_id=message.user_tg_id,
        message=message.message,
        decision=tx.decision,
        reasoning=reasoning,
        tx_reasoning=tx.reasoning if tx else None,
        to_address=tx.transaction.to if tx and tx.transaction else None,
        value=tx.transaction.value if tx and tx.transaction else None,
        currency=tx.transaction.currency if tx and tx.transaction else None
    )


def get_chat_history(user_tg_id: int, limit: int = 3) -> List[dict]:
    """
    Получает последние сообщения и их решение для указанного user_tg_id.
    """
    return get_last_chat_history(user_tg_id, limit)
