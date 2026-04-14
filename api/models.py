"""
SQLAlchemy ORM models.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, String

from api.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: str = Column(String, primary_key=True, default=_new_uuid)
    name: str = Column(String, nullable=False)
    email: str = Column(String, unique=True, index=True, nullable=False)
    hashed_password: str = Column(String, nullable=True)  # nullable for social logins
    is_confirmed: bool = Column(Boolean, default=False)
    confirmation_token: str = Column(String, nullable=True)
    created_at: datetime = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Social login support (set by Auth0 callback)
    auth0_sub: str = Column(String, nullable=True, unique=True)
