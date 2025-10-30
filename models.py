from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class BillData(Base):
    __tablename__ = "bill_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    bill_id = Column(String, nullable=False, unique=True, index=True)  
    file_name = Column(String, nullable=False)
    bill_json = Column(JSONB, nullable=False)
