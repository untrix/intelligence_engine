"""SQLAlchemy ORM models."""

from sqlalchemy import Column, Integer, String, Text

from app.database import Base


class AppSettings(Base):
    """Key-value store for application configuration persisted in the database."""

    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(Text, nullable=True)
