from fastapi import FastAPI, File, Form, UploadFile, Depends
from fastapi.responses import JSONResponse
import tempfile
import os
from bill_splitting_agent import BillSplitSystem
from dotenv import load_dotenv
import json
import uuid
from pathlib import Path
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from models import BillData
from fastapi.encoders import jsonable_encoder
from database import AsyncSessionLocal
from sqlalchemy.future import select

from fastapi.responses import FileResponse
from google.cloud import storage
import tempfile
import re

# Load environment variables
load_dotenv()
app = FastAPI(title="Bill Splitting API", version="1.0")


DATA_DIR = Path("data/processed_bills")
DATA_DIR.mkdir(parents=True, exist_ok=True)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session



system = BillSplitSystem(
    api_key=os.getenv("GEMINI_API_KEY"),
    gcs_credentials_path='gcloud-key/bill_upload_bucket_key.json',
    gcs_bucket_name='uploaded_bills'
)

from fastapi import FastAPI, File, Form, UploadFile, Depends
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import tempfile
import os
import uuid
import json
from pathlib import Path
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import AsyncSession
from models import BillData
from database import AsyncSessionLocal
from bill_splitting_agent import BillSplitSystem

# Load environment variables
load_dotenv()

app = FastAPI(title="Bill Splitting API", version="1.0")

# Folder for local JSON backups
DATA_DIR = Path("data/processed_bills")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Database session dependency
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
    Upload a bill image and a split instruction.
    Processes it using AI + GCS, saves locally as JSON (for backup),
    and stores structured data in PostgreSQL with GCS link.
    """
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name

        # Process and split using the AI system
        bill_data, split_result = system.process_and_split(temp_file_path, instruction)

        # Generate unique ID
        bill_id = str(uuid.uuid4())
        print("Uploaded to GCS with URL:", bill_data.gcs_uri)
        # Construct record with full GCS URI (or HTTP UR
        bill_record = {
            "bill_id": bill_id,
            "file_name": bill_data.gcs_uri,
            "bill_data": bill_data.raw_data,
            "split_result": split_result.raw_data
        }

        # --- Local JSON backup (for redundancy) ---
        with open(DATA_DIR / f"{bill_id}.json", "w", encoding="utf-8") as f:
            json.dump(bill_record, f, indent=2)

        # --- Store in PostgreSQL ---
        bill_json = jsonable_encoder({
            "bill_data": bill_data.raw_data,
            "split_result": split_result.raw_data
        })

        db_obj = BillData(
            bill_id=bill_id,
            file_name=bill_record["file_name"],
            bill_json=bill_json
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        # Clean up temp file
        os.remove(temp_file_path)

        return JSONResponse(content={
            "message": "Bill processed and stored successfully",
            "bill_id": bill_id,
            "file_name": bill_record["file_name"],
            "bill_data": bill_data.raw_data,
            "split_result": split_result.raw_data
        })

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
    

@app.get("/bill/{bill_id}")
async def get_bill(bill_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BillData).where(BillData.bill_id == bill_id))
    bill = result.scalars().first()

    if not bill:
        return JSONResponse(
            content={"error": f"No bill found with ID {bill_id}"},
            status_code=404
        )

    return JSONResponse(
        content={
            "bill_id": bill.bill_id,
            "file_name": bill.file_name,
            "bill_data": bill.bill_json.get("bill_data"),
            "split_result": bill.bill_json.get("split_result")
        },
        status_code=200
    )



@app.get("/bill/{bill_id}/download")
async def download_bill(bill_id: str, db: AsyncSession = Depends(get_db)):
    """
    Download the original bill image from Google Cloud Storage.
    Fetches GCS URI from PostgreSQL and returns the file as a downloadable response.
    """
    try:
        # 1️⃣ Fetch from DB
        result = await db.execute(select(BillData).where(BillData.bill_id == bill_id))
        bill = result.scalars().first()

        if not bill:
            return JSONResponse(
                content={"error": f"No record found for Bill ID {bill_id}"},
                status_code=404
            )

        gcs_uri = bill.file_name
        if not gcs_uri:
            return JSONResponse(
                content={"error": "No GCS URI found for this bill."},
                status_code=400
            )

        # 2️⃣ Parse GCS URI (supports both gs:// and https:// formats)
        match = re.match(r"(?:gs://|https://storage\.googleapis\.com/)([^/]+)/(.+)", gcs_uri)
        if not match:
            return JSONResponse(
                content={"error": "Invalid GCS URI format."},
                status_code=400
            )

        bucket_name, blob_name = match.groups()

        # 3️⃣ Download from GCS
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        if not blob.exists():
            return JSONResponse(
                content={"error": "File not found in Google Cloud Storage."},
                status_code=404
            )

        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(blob_name)[1]) as tmp:
            blob.download_to_filename(tmp.name)
            temp_path = tmp.name

        # 4️⃣ Return downloadable file
        filename = os.path.basename(blob_name)
        return FileResponse(
            path=temp_path,
            filename=filename,
            media_type="image/jpeg"
        )

    except Exception as e:
        return JSONResponse(
            content={"error": f"Failed to fetch file from GCS: {str(e)}"},
            status_code=500
        )



@app.get("/bill/{bill_id}/view")
async def view_bill(bill_id: str, db: AsyncSession = Depends(get_db)):
    """
    Display the original bill image directly from Google Cloud Storage.
    Fetches from PostgreSQL and returns the image inline in the browser.
    """
    try:
        # 1️⃣ Fetch from DB
        result = await db.execute(select(BillData).where(BillData.bill_id == bill_id))
        bill = result.scalars().first()

        if not bill:
            return JSONResponse(
                content={"error": f"No record found for Bill ID {bill_id}"},
                status_code=404
            )

        gcs_uri = bill.file_name
        if not gcs_uri:
            return JSONResponse(
                content={"error": "No GCS URI found for this bill."},
                status_code=400
            )

        # 2️⃣ Parse URI (supports both gs:// and https://storage.googleapis.com/ formats)
        match = re.match(r"(?:gs://|https://storage\.googleapis\.com/)([^/]+)/(.+)", gcs_uri)
        if not match:
            return JSONResponse(
                content={"error": "Invalid GCS URI format."},
                status_code=400
            )

        bucket_name, blob_name = match.groups()

        # 3️⃣ Download from GCS (in-memory)
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        if not blob.exists():
            return JSONResponse(
                content={"error": "File not found in Google Cloud Storage."},
                status_code=404
            )

        image_bytes = blob.download_as_bytes()
        content_type = blob.content_type or "image/jpeg"

        # 4️⃣ Serve inline
        return Response(
            content=image_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{blob_name.split("/")[-1]}"'
            }
        )

    except Exception as e:
        return JSONResponse(
            content={"error": f"Failed to fetch image from GCS: {str(e)}"},
            status_code=500
        )
