from fastapi import APIRouter, HTTPException
from schemas.transaction_schemas import TransactionResult
from services.agent_service import build_transaction_service

router = APIRouter()


@router.post("/build_transaction")
async def build_transaction(message: str) -> TransactionResult:
    try:
        tx = await build_transaction_service(message=message)
        return tx
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
