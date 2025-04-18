from sqlalchemy import Column, Integer, String, UniqueConstraint
from sqlalchemy.orm import validates

from .database import Base

# SQLAlchemy model
class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, index=True, nullable=False)
    user_name = Column(String, index=True, nullable=False)
    wallet_id = Column(String, index=True, nullable=False)

    # Unique constraint for telegram_id and user_name pair
    __table_args__ = (
        UniqueConstraint('telegram_id', 'user_name', name='uix_telegram_user'),
    )

    @validates('telegram_id', 'user_name', 'wallet_id')
    def validate_not_empty(self, key, value):
        if not value:
            raise ValueError(f"{key} cannot be empty")
        return value