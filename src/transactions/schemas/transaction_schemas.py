from typing import Literal, Optional

from pydantic import BaseModel


class TransactionNER(BaseModel):
    receiver: str
    value: float


class SupervisorResponse(BaseModel):
    decision: Literal["@BuildTransaction", "@RejectTransaction"]
    reasoning: str


class TransactionDict(BaseModel):
    to: str
    value: float


class TransactionResult(BaseModel):
    status: str
    transaction: Optional[TransactionDict] = None
    reasoning: str
