from typing import Literal, Optional, List
from dataclasses import dataclass
from pydantic import BaseModel

class Contact(BaseModel):
    user_tg_id: str
    contact_name: str
    wallet_id: str

class ContactsResponseModel(BaseModel):
    contacts: List[Contact]

class MessageRequest(BaseModel):
    """
    Модель для получения запроса пользователя
    """
    user_tg_id: Optional[int]=None
    message: str
    contacts: Optional[ContactsResponseModel]=None

class TransactionDict(BaseModel):
    """
    Модель для формирования транзакции
    """

    to: Optional[str] = None
    value: Optional[float] = None
    currency: Optional[str] = None


class TransactionModel(BaseModel):
    """
    Модель build transaction tool response
    """

    decision: Literal["BuildTransaction", "RejectTransaction"]
    reasoning: str
    db_match: Optional[str] = None
    transaction: Optional[TransactionDict] = None


class SmallTalkModel(BaseModel):
    """
    Модель для small talk с пользователем
    """
    response: str

class OffTopicModel(BaseModel):
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
    off_topic: Optional[OffTopicModel] = None
