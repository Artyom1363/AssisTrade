from typing import Any, Dict

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models.contacts import Contact


class ContactRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_contact(
        self, user_tg_id: str, contact_name: str, wallet_id: str
    ) -> Dict[str, Any]:
        """
        Create a new contact

        Returns dict with success status and contact data or error message
        """
        try:
            db_contact = Contact(
                user_tg_id=user_tg_id, contact_name=contact_name, wallet_id=wallet_id
            )
            self.db.add(db_contact)
            self.db.commit()
            self.db.refresh(db_contact)

            return {
                "success": True,
                "message": "Contact added successfully",
                "data": {
                    "user_tg_id": db_contact.user_tg_id,
                    "contact_name": db_contact.contact_name,
                    "wallet_id": db_contact.wallet_id,
                },
            }
        except IntegrityError:
            self.db.rollback()
            return {
                "success": False,
                "message": f"Contact with user_tg_id={user_tg_id} and contact_name={contact_name} already exists",
                "data": {},
            }
        except Exception as e:
            self.db.rollback()
            return {
                "success": False,
                "message": f"Error creating contact: {str(e)}",
                "data": {},
            }

    def get_contact(self, user_tg_id: str, contact_name: str) -> Dict[str, Any]:
        """
        Get contact by user_tg_id and contact_name

        Returns dict with success status and contact data or error message
        """
        contact = (
            self.db.query(Contact)
            .filter(
                Contact.user_tg_id == user_tg_id, Contact.contact_name == contact_name
            )
            .first()
        )

        if not contact:
            return {
                "success": False,
                "message": f"Contact with user_tg_id={user_tg_id} and contact_name={contact_name} not found",
                "data": {},
            }

        return {
            "success": True,
            "message": "Contact found",
            "data": {
                "user_tg_id": contact.user_tg_id,
                "contact_name": contact.contact_name,
                "wallet_id": contact.wallet_id,
            },
        }

    def get_user_contacts(self, user_tg_id: str) -> Dict[str, Any]:
        """
        Get all contacts for a specific user by user_tg_id

        Returns dict with success status and list of contacts
        """
        try:
            contacts = (
                self.db.query(Contact).filter(Contact.user_tg_id == user_tg_id).all()
            )

            contacts_list = []
            for contact in contacts:
                contacts_list.append(
                    {
                        "user_tg_id": contact.user_tg_id,
                        "contact_name": contact.contact_name,
                        "wallet_id": contact.wallet_id,
                    }
                )

            return {
                "success": True,
                "message": f"Found {len(contacts_list)} contacts for user {user_tg_id}",
                "data": {"contacts": contacts_list},
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error retrieving contacts: {str(e)}",
                "data": {},
            }

    def get_all_contacts(self) -> Dict[str, Any]:
        """
        Get all contacts from database

        Returns dict with success status and list of contacts
        """
        try:
            contacts = self.db.query(Contact).all()

            contacts_list = []
            for contact in contacts:
                contacts_list.append(
                    {
                        "user_tg_id": contact.user_tg_id,
                        "contact_name": contact.contact_name,
                        "wallet_id": contact.wallet_id,
                    }
                )

            return {
                "success": True,
                "message": f"Found {len(contacts_list)} contacts",
                "data": {"contacts": contacts_list},
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error retrieving contacts: {str(e)}",
                "data": {},
            }

    def delete_contact(self, user_tg_id: str, contact_name: str) -> Dict[str, Any]:
        """
        Delete contact by user_tg_id and contact_name

        Returns dict with success status and message
        """
        contact = (
            self.db.query(Contact)
            .filter(
                Contact.user_tg_id == user_tg_id, Contact.contact_name == contact_name
            )
            .first()
        )

        if not contact:
            return {
                "success": False,
                "message": f"Contact with user_tg_id={user_tg_id} and contact_name={contact_name} not found",
                "data": {},
            }

        try:
            self.db.delete(contact)
            self.db.commit()

            return {
                "success": True,
                "message": "Contact deleted successfully",
                "data": {},
            }
        except Exception as e:
            self.db.rollback()
            return {
                "success": False,
                "message": f"Error deleting contact: {str(e)}",
                "data": {},
            }
