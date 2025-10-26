import uuid, os, json
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, String, Float, JSON
from sqlalchemy.orm import sessionmaker, declarative_base
from google.cloud import storage
from tempfile import NamedTemporaryFile
from pydantic import BaseModel
from bill_ocr_split_core import BillSplitSystem, BillData
from datetime import datetime
from typing import List

# ENV
GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
GCS_BUCKET_NAME = os.getenv("GC-BUCKET")
DB_URL = os.getenv("DB_LINK")

# Database setup
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Bill model
class Bill(Base):
    __tablename__ = "bills"
    id = Column(String(50), primary_key=True)
    gcs_url = Column(String(255))
    ocr_data = Column(JSON)
    split_data = Column(JSON)
    total = Column(Float)
    status = Column(String(50))

class Group(Base):
    __tablename__ = "groups"
    id = Column(String(50), primary_key=True)
    name = Column(String(100))
    members = Column(JSON)     # list of members, e.g. ["Alice", "Bob", "Charlie"]
    created_at = Column(String(50))
    settled = Column(String(10), default="no")

class GroupBill(Base):
    __tablename__ = "group_bills"
    id = Column(String(50), primary_key=True)
    group_id = Column(String(50))
    bill_id = Column(String(50))
    split_data = Column(JSON)
    created_at = Column(String(50))

Base.metadata.create_all(engine)

# Google Cloud upload helper
def upload_to_gcs(file_path: str, blob_name: str) -> str:
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(file_path)
    blob.make_public()
    return blob.public_url

# FastAPI app
app = FastAPI(title="Bill Split API")

split_system = BillSplitSystem(api_key=GOOGLE_API_KEY)

class SplitRequest(BaseModel):
    instruction: str


class GroupCreateRequest(BaseModel):
    name: str
    members: List[str]

class GroupSettleRequest(BaseModel):
    settled_by: str
    notes: Optional[str] = None



@app.post("/bill/upload")
async def upload_bill(file: UploadFile, group_id: Optional[str] = Form(None)):
    """
    Upload a bill image, run OCR, save to GCS + MySQL and optionally link it to a group.
    """
    try:
        bill_id = str(uuid.uuid4())

        # Save the uploaded image temporarily
        with NamedTemporaryFile(delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        # Upload image to Google Cloud
        gcs_url = upload_to_gcs(temp_path, f"bills/{bill_id}.jpg")

        # Process the bill with OCR + LLM
        bill_data, _ = split_system.process_and_split(temp_path, "Split equally among all")
        ocr_json = bill_data.raw_data

        # Remove temp file from local storage
        os.remove(temp_path)

        # Save to database
        db = SessionLocal()
        db_bill = Bill(
            id=bill_id,
            gcs_url=gcs_url,
            ocr_data=ocr_json,
            total=bill_data.total,
            status="uploaded"
        )
        db.add(db_bill)
        db.commit()

        # ✅ If a group ID is provided, link this bill to the group
        if group_id:
            group_bill = GroupBill(
                id=str(uuid.uuid4()),
                group_id=group_id,
                bill_id=bill_id,
                split_data=None,
                created_at=datetime.now().isoformat()
            )
            db.add(group_bill)
            db.commit()

        return {
            "bill_id": bill_id,
            "gcs_url": gcs_url,
            "ocr_data": ocr_json,
            "linked_group": group_id if group_id else None,
            "message": "Bill uploaded and processed successfully."
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/bill/{bill_id}/split")
async def split_bill(bill_id: str, body: SplitRequest):
    """Split an existing bill based on instruction"""
    db = SessionLocal()
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        return JSONResponse({"error": "Bill not found"}, status_code=404)

    bill_data = BillData(bill.ocr_data)
    split_result = split_system.expense_splitter.split(bill_data, body.instruction)
    bill.split_data = split_result
    bill.status = "split_done"
    db.commit()
    return {"bill_id": bill_id, "split_result": split_result}


@app.get("/bill/{bill_id}")
def get_bill(bill_id: str):
    """Retrieve stored bill data"""
    db = SessionLocal()
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        return JSONResponse({"error": "Bill not found"}, status_code=404)
    return {
        "bill_id": bill.id,
        "status": bill.status,
        "ocr_data": bill.ocr_data,
        "split_data": bill.split_data,
        "gcs_url": bill.gcs_url,
    }



@app.post("/group/create")
def create_group(body: GroupCreateRequest):
    """Create a new expense group"""
    try:
        group_id = str(uuid.uuid4())
        db = SessionLocal()
        new_group = Group(
            id=group_id,
            name=body.name,
            members=body.members,
            created_at=datetime.now().isoformat(),
            settled="no"
        )
        db.add(new_group)
        db.commit()
        return {
            "group_id": group_id,
            "name": body.name,
            "members": body.members,
            "message": "Group created successfully"
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    


@app.post("/group/{group_id}/settle")
def settle_group(group_id: str, body: GroupSettleRequest):
    """Mark all expenses in a group as settled"""
    db = SessionLocal()
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        return JSONResponse({"error": "Group not found"}, status_code=404)

    group.settled = "yes"
    db.commit()
    return {
        "group_id": group_id,
        "status": "settled",
        "settled_by": body.settled_by,
        "notes": body.notes or "",
        "message": f"Group '{group.name}' marked as settled."
    }


@app.get("/bill/{bill_id}/history")
def get_bill_history(bill_id: str):
    """Retrieve complete bill history (OCR + splits + group linkage)"""
    db = SessionLocal()
    bill = db.query(Bill).filter(Bill.id == bill_id).first()
    if not bill:
        return JSONResponse({"error": "Bill not found"}, status_code=404)

    group_bill = db.query(GroupBill).filter(GroupBill.bill_id == bill_id).first()

    return {
        "bill_id": bill.id,
        "status": bill.status,
        "total": bill.total,
        "ocr_data": bill.ocr_data,
        "split_data": bill.split_data,
        "gcs_url": bill.gcs_url,
        "group": group_bill.group_id if group_bill else None,
        "created_at": getattr(group_bill, "created_at", None)
    }