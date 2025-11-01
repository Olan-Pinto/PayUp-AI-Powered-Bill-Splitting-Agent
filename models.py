from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class BillData(Base):
    __tablename__ = "bill_data"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    bill_id = Column(String, nullable=False, unique=True, index=True)
    file_name = Column(String, nullable=False)
    bill_json = Column(JSONB, nullable=False)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=True)
    google_id = Column(String, nullable=True, unique=True)
    password_hash = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
