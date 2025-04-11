from typing import Literal, Optional

from pydantic import BaseModel


class MessageRequest(BaseModel):
    """
    Модель для получения запроса пользователя
    """

    message: str


class TransactionDict(BaseModel):
    """
    Модель для формирования транзакции
    """

    to: Optional[str] = None
    value: Optional[float] = None
    currency: Optional[str] = None


class TransactionModel(BaseModel):
    """
    Модель для получения ответа о решении агента о выполнении транзакции
    """

    decision: Literal["BuildTransaction", "RejectTransaction"]
    reasoning: str
    transaction: Optional[TransactionDict] = None
