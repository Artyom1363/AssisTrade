from typing import Literal, Optional, List
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

    user_tg_id: Optional[int] = None
    message: str
    # contacts: Optional[ContactsResponseModel] = None


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


class SmallTalkModel(BaseModel):
    """
    Модель для ответа small talk
    """

    response: str


class OffTopicModel(BaseModel):
    response: str


class ImageModel(BaseModel):
    path: str
    title: str


class RagResponseModel(BaseModel):
    """
    Модель для ответа RAG
    """

    answer: str
    images: Optional[List[ImageModel]] = None


class SupervisorModel(BaseModel):
    """
    Модель супервизора для принятия решения о том,
    какой тул вызвать / что ответить пользователю
    """

    reasoning: str
    act: str
    tx: Optional[TransactionModel] = None
    small_talk: Optional[SmallTalkModel] = None
    off_topic: Optional[OffTopicModel] = None
    rag_response: Optional[RagResponseModel] = None
