from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class BillData(Base):
    __tablename__ = "bill_data"
    bill_id = Column(String, primary_key=True)
    file_name = Column(String, nullable=False)
    bill_json = Column(JSONB, nullable=False)
