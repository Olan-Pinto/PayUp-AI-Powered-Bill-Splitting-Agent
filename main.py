from fastapi import FastAPI, File, Form, UploadFile, Depends
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import tempfile
import os


from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession
from models import BillData
from database import AsyncSessionLocal
from bill_splitting_agent import BillSplitSystem

# Load environment variables
load_dotenv()
app = FastAPI(title="Bill Splitting API", version="1.0")

# DB session dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

system = BillSplitSystem(
    api_key=os.getenv("GEMINI_API_KEY"),
    gcs_credentials_path='gcloud-key/bill_upload_bucket_key.json',
    gcs_bucket_name='uploaded_bills'
)

@app.post("/process-bill")
async def process_bill(
    file: UploadFile = File(...),
    instruction: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a bill image and an instruction.
    Returns structured bill data and split results. Also stores bill data as JSON in PostgreSQL.
    """
    try:
        # Save uploaded image temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name

        # Process bill and split
        bill_data, split_result = system.process_and_split(temp_file_path, instruction)

        # Clean up temp file
        os.remove(temp_file_path)

        # Store parsed bill data in PostgreSQL as JSON
        bill_json = jsonable_encoder(bill_data.raw_data)
        db_obj = BillData(file_name=file.filename, bill_json=bill_json)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        return JSONResponse(content={
            "message": "Bill processed and stored successfully",
            "bill_data": bill_data.raw_data,
            "split_result": split_result.raw_data
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
