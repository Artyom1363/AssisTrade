from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
import json
from typing import Dict, Any

from .models.database import engine, Base, get_db
from .models.contacts import Contact
from .repositories.contacts import ContactRepository

# Create tables in the database
Base.metadata.create_all(bind=engine)

# Initialize FastAPI application
app = FastAPI(
    title="Telegram Transactions API",
    description="API for processing transactions through NLP interface for Telegram bot",
    version="0.1.0"
)

# Root endpoint for API health check
@app.get("/")
async def root():
    """
    Root endpoint to check API status
    """
    return {
        "name": "Telegram Transactions API",
        "version": "0.1.0",
        "description": "API for processing transactions through NLP interface for Telegram bot"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Endpoint to check service health
    """
    return {"status": "healthy"}

# Add contact endpoint
@app.post("/contacts/add", status_code=status.HTTP_201_CREATED)
async def add_contact(data: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Add a new contact with specified data:
    
    - telegram_id: Telegram user identifier
    - user_name: Username
    - wallet_id: Wallet identifier
    """
    try:
        # Validate required fields
        for field in ['telegram_id', 'user_name', 'wallet_id']:
            if field not in data or not data[field]:
                return {
                    "success": False,
                    "message": f"Missing required field: {field}",
                    "data": {}
                }
        
        repo = ContactRepository(db)
        result = repo.create_contact(
            telegram_id=data['telegram_id'],
            user_name=data['user_name'],
            wallet_id=data['wallet_id']
        )
        
        if not result["success"]:
            return result
            
        return result
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to add contact: {str(e)}",
            "data": {}
        }

# Get contact endpoint
@app.post("/contacts/get")
async def get_contact(data: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Get contact data by telegram_id and user_name:
    
    - telegram_id: Telegram user identifier
    - user_name: Username
    """
    try:
        # Validate required fields
        for field in ['telegram_id', 'user_name']:
            if field not in data or not data[field]:
                return {
                    "success": False,
                    "message": f"Missing required field: {field}",
                    "data": {}
                }
        
        repo = ContactRepository(db)
        result = repo.get_contact(
            telegram_id=data['telegram_id'],
            user_name=data['user_name']
        )
        
        return result
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to get contact: {str(e)}",
            "data": {}
        }

# Delete contact endpoint
@app.post("/contacts/delete")
async def delete_contact(data: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Delete contact by telegram_id and user_name:
    
    - telegram_id: Telegram user identifier
    - user_name: Username
    """
    try:
        # Validate required fields
        for field in ['telegram_id', 'user_name']:
            if field not in data or not data[field]:
                return {
                    "success": False,
                    "message": f"Missing required field: {field}",
                    "data": {}
                }
        
        repo = ContactRepository(db)
        result = repo.delete_contact(
            telegram_id=data['telegram_id'],
            user_name=data['user_name']
        )
        
        return result
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to delete contact: {str(e)}",
            "data": {}
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)