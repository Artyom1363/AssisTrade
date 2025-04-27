from pydantic import BaseModel
from typing import Optional, Literal

class MessageRequest(BaseModel):
    """
    Модель для получения запроса пользователя
    """

    user_tg_id: Optional[int] = None
    message: str

class TransactionDict(BaseModel):
    """
    Модель для формирования транзакции
    """

    to: str
    value: float
    currency: str


class TransactionModel(BaseModel):
    """
    Модель для tx builder
    """

    decision: Literal["BuildTransaction", "RejectTransaction"]
    reasoning: str
    transaction: Optional[TransactionDict] = None



class SupervisorModel(BaseModel):
    """
    Модель супервизора для принятия решения о том,
    какой тул вызвать / что ответить пользователю
    """

    reasoning: str
    tx: Optional[TransactionModel] = None
