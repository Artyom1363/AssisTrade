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
    Модель для получения ответа о решении агента супервизора
    и принятии решения об отправке
    """

    decision: Literal["BuildTransaction", "RejectTransaction"]
    reasoning: str
    transaction: Optional[TransactionDict] = None


class SmallTalkModel(BaseModel):
    response: str


class SupervisorModel(BaseModel):
    """
    Модель супервизора для принятия решения о том,
    какой тул вызвать / что ответить пользователю
    """

    reasoning: str
    act: Literal["build_transaction", "small_talk", "out_of_topic"]
    tx: Optional[TransactionModel] = None
    small_talk: Optional[SmallTalkModel] = None
