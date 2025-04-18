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
    
    - user_tg_id: Telegram user identifier
    - contact_name: Contact name
    - wallet_id: Wallet identifier
    """
    try:
        # Validate required fields
        for field in ['user_tg_id', 'contact_name', 'wallet_id']:
            if field not in data or not data[field]:
                return {
                    "success": False,
                    "message": f"Missing required field: {field}",
                    "data": {}
                }
        
        repo = ContactRepository(db)
        result = repo.create_contact(
            user_tg_id=data['user_tg_id'],
            contact_name=data['contact_name'],
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
@app.post("/contacts/find")
async def find_contact(data: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Get contact data by user_tg_id and contact_name:
    
    - user_tg_id: Telegram user identifier
    - contact_name: Contact name
    """
    try:
        # Validate required fields
        for field in ['user_tg_id', 'contact_name']:
            if field not in data or not data[field]:
                return {
                    "success": False,
                    "message": f"Missing required field: {field}",
                    "data": {}
                }
        
        repo = ContactRepository(db)
        result = repo.get_contact(
            user_tg_id=data['user_tg_id'],
            contact_name=data['contact_name']
        )
        
        return result
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to find contact: {str(e)}",
            "data": {}
        }

# Delete contact endpoint
@app.post("/contacts/delete")
async def delete_contact(data: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Delete contact by user_tg_id and contact_name:
    
    - user_tg_id: Telegram user identifier
    - contact_name: Contact name
    """
    try:
        # Validate required fields
        for field in ['user_tg_id', 'contact_name']:
            if field not in data or not data[field]:
                return {
                    "success": False,
                    "message": f"Missing required field: {field}",
                    "data": {}
                }
        
        repo = ContactRepository(db)
        result = repo.delete_contact(
            user_tg_id=data['user_tg_id'],
            contact_name=data['contact_name']
        )
        
        return result
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to delete contact: {str(e)}",
            "data": {}
        }

# Get user contacts endpoint
@app.post("/contacts/list")
async def list_user_contacts(data: Dict[str, Any], db: Session = Depends(get_db)):
    """
    Get all contacts for a specific user
    
    - user_tg_id: Telegram user identifier
    """
    try:
        # Validate required fields
        if 'user_tg_id' not in data or not data['user_tg_id']:
            return {
                "success": False,
                "message": "Missing required field: user_tg_id",
                "data": {}
            }
        
        repo = ContactRepository(db)
        result = repo.get_user_contacts(user_tg_id=data['user_tg_id'])
        
        return result
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to retrieve contacts: {str(e)}",
            "data": {}
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8002, reload=True)