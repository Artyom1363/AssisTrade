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
    Модель для получения решения об отправке транзакции и её формирования
    """

    decision: Literal["BuildTransaction", "RejectTransaction"]
    reasoning: str
    transaction: Optional[TransactionDict] = None


class SmallTalkModel(BaseModel):
    response: str

class ChainDataModel(BaseModel):
    """
    Модель для получения ответа агента с MCP сервером
    и обращениями в блокчейн
    """

    reasoning: str
    act: str
    response: str

class SupervisorModel(BaseModel):
    """
    Модель супервизора для принятия решения о том,
    какой тул вызвать / что ответить пользователю
    """

    reasoning: str
    act: Literal["build_transaction", "small_talk", "out_of_topic", "chain_data"]
    tx: Optional[TransactionModel] = None
    small_talk: Optional[SmallTalkModel] = None
    chain_data: Optional[ChainDataModel] = None
