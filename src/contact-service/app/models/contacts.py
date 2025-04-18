from sqlalchemy import Column, Integer, String, UniqueConstraint
from sqlalchemy.orm import validates

from .database import Base

# SQLAlchemy model
class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    user_tg_id = Column(String, index=True, nullable=False)
    contact_name = Column(String, index=True, nullable=False)
    wallet_id = Column(String, index=True, nullable=False)

    # Unique constraint for user_tg_id and contact_name pair
    __table_args__ = (
        UniqueConstraint('user_tg_id', 'contact_name', name='uix_telegram_user'),
    )

    @validates('user_tg_id', 'contact_name', 'wallet_id')
    def validate_not_empty(self, key, value):
        if not value:
            raise ValueError(f"{key} cannot be empty")
        return value