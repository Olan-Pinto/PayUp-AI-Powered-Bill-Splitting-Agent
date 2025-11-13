from fastapi import FastAPI, File, Form, UploadFile, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

import tempfile
import os
import json
import uuid
import re
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import storage

# Existing imports
from bill_splitting_agent import BillSplitSystem
from models import BillData
from database import AsyncSessionLocal

# NEW: RabbitMQ and Redis imports
from celery import Celery
from redis import Redis
import asyncio

from auth import router as auth_router



# Load environment variables
load_dotenv()

app = FastAPI(title="Bill Splitting API", version="1.0")

# Folders
DATA_DIR = Path("data/processed_bills")
DATA_DIR.mkdir(parents=True, exist_ok=True)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Local development
        "https://payup-frontend-332078128555.us-central1.run.app",  # Production frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

# Database session dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# Existing system
system = BillSplitSystem(
    api_key=os.getenv("GEMINI_API_KEY"),
    gcs_credentials_path=None,
    gcs_bucket_name=os.getenv("GCS_BUCKET_NAME", "uploaded_bills")
)

# ============ NEW: Celery + Redis Configuration ============

celery_app = Celery(
    'bill_processor',
    broker=os.getenv('CELERY_BROKER_URL', 'amqp://guest:guest@rabbitmq:5672//'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    broker_heartbeat=60,  
    broker_heartbeat_checkrate=2,  
)

# Redis client for progress tracking
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')
redis_client = Redis.from_url(REDIS_URL, decode_responses=True)


# ============ NEW: Celery Background Task ============

@celery_app.task(bind=True)
def process_bill_async(self, bill_id: str, gcs_path: str, instruction: str):
    """
    Celery task to process bill from GCS with detailed progress updates.
    """
    import time
    import psycopg2
    from psycopg2.extras import Json
    import os
    from google.cloud import storage
    
    def publish_progress(stage, message, progress):
        """Publish progress to Redis for WebSocket"""
        redis_client.publish(
            f'bill_progress:{bill_id}',
            json.dumps({
                "stage": stage,
                "message": message,
                "progress": progress
            })
        )
    
    temp_file_path = None
    
    try:
        # Step 1: Download from GCS
        publish_progress('uploading', 'Downloading bill from storage...', 10)
        
        # Parse GCS path: gs://bucket/path
        gcs_path_parts = gcs_path.replace("gs://", "").split("/", 1)
        bucket_name = gcs_path_parts[0]
        blob_name = gcs_path_parts[1]
        
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        # Download to local temp file
        # temp_file_path = f"/tmp/{bill_id}_temp.jpg"
        import tempfile
        temp_dir = tempfile.gettempdir()  # Works on both Windows and Linux
        temp_file_path = os.path.join(temp_dir, f"{bill_id}_temp.jpg")
        blob.download_to_filename(temp_file_path)
        
        publish_progress('uploading', 'Download complete! Starting OCR...', 20)
        
        # Step 2: OCR Processing
        publish_progress('ocr', 'Initializing OCR engine...', 25)
        
        publish_progress('ocr', 'Scanning bill image...', 30)
        
        publish_progress('ocr', 'Extracting text from bill...', 40)
        
        # Process bill (actual AI work happens here)
        bill_data, split_result = system.process_and_split(temp_file_path, instruction)
        
        # Get item count
        item_count = len(bill_data.raw_data.get('items', []))
        publish_progress('ocr', f'Found {item_count} line items on bill', 50)
        
        publish_progress('ocr', 'Parsing prices and totals...', 55)
        
        # Step 3: Bill Splitting
        publish_progress('splitting', 'Analyzing bill structure...', 60)
        
        person_count = len(split_result.raw_data.get('breakdown', []))
        publish_progress('splitting', f'Calculating split for {person_count} people...', 65)
        
        # Get per-person amount
        if person_count > 0:
            per_person = split_result.raw_data['breakdown'][0].get('total', 0)
            publish_progress('splitting', f'Each person owes ${per_person:.2f}', 70)
        else:
            publish_progress('splitting', 'Calculating amounts...', 70)
        
        publish_progress('splitting', 'Applying tax and tip distribution...', 75)
        
        publish_progress('splitting', 'Verifying calculations...', 80)
        
        # Step 4: Saving to Database
        publish_progress('saving', 'Preparing data for storage...', 85)
        
        publish_progress('saving', 'Connecting to database...', 88)
        
        publish_progress('saving', 'Writing to database...', 92)
        
        # Save to PostgreSQL using psycopg2 (sync)
        database_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(database_url.replace('+asyncpg', ''))
        cur = conn.cursor()
        
        # Insert data
        bill_json = {
            "bill_data": bill_data.raw_data,
            "split_result": split_result.raw_data
        }
        
        cur.execute(
            """
            INSERT INTO bill_data (bill_id, file_name, bill_json)
            VALUES (%s, %s, %s)
            ON CONFLICT (bill_id) DO UPDATE
            SET file_name = EXCLUDED.file_name,
                bill_json = EXCLUDED.bill_json
            """,
            (bill_id, gcs_path, Json(bill_json))  # ✅ Use the gcs_path parameter
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
        publish_progress('saving', 'Finalizing...', 96)
        
        # Clean up temp file
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        
        publish_progress('completed', 'Bill processed successfully!', 100)
        
        return {
            "bill_id": bill_id,
            "status": "completed",
            "file_name": bill_data.gcs_uri
        }
        
    except Exception as e:
        publish_progress('error', f'Error: {str(e)}', 0)
        
        # Clean up temp file on error
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        
        raise e

# ============ MODIFIED: Process Bill Endpoint (Now Async) ============

@app.post("/process-bill")
async def process_bill(
    file: UploadFile = File(...),
    instruction: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a bill image and queue it for async processing.
    """
    try:
        # Generate unique ID
        bill_id = str(uuid.uuid4())
        print(f"🔵 Generated bill_id: {bill_id}")
        
        # Save to temporary file first
        uploads_dir = os.getenv("UPLOADS_DIR", "/tmp/uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        
        temp_file_path = os.path.join(uploads_dir, f"{bill_id}_{file.filename}")
        with open(temp_file_path, "wb") as f:
            f.write(await file.read())
        print(f"🔵 File saved temporarily to: {temp_file_path}")
        
        # Upload to Google Cloud Storage
        bucket_name = os.getenv("GCS_BUCKET_NAME", "uploaded_bills")
        
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob_name = f"pending/{bill_id}_{file.filename}"
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(temp_file_path)
        
        gcs_path = f"gs://{bucket_name}/{blob_name}"
        print(f"🔵 File uploaded to GCS: {gcs_path}")
        
        # Clean up local temp file
        os.remove(temp_file_path)
        
        # Queue the processing job with GCS path
        process_bill_async.delay(bill_id, gcs_path, instruction)
        print(f"🔵 Task queued")
        
        return JSONResponse(content={
            "message": "Bill queued for processing",
            "bill_id": bill_id,
            "status": "queued"
        })
        
    except Exception as e:
        print(f"❌ Error in process_bill: {str(e)}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# ============ NEW: WebSocket for Real-time Progress ============

@app.websocket("/ws/progress/{bill_id}")
async def websocket_progress(websocket: WebSocket, bill_id: str):
    """
    WebSocket endpoint for real-time progress updates.
    Frontend connects to this to receive live updates.
    """
    await websocket.accept()
    
    # Subscribe to Redis pub/sub for this bill
    pubsub = redis_client.pubsub()
    pubsub.subscribe(f'bill_progress:{bill_id}')
    
    try:
        # Listen for messages
        for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                await websocket.send_json(data)
                
                # Close connection when complete
                if data['stage'] in ['completed', 'error']:
                    break
                    
    except WebSocketDisconnect:
        pubsub.unsubscribe(f'bill_progress:{bill_id}')
    finally:
        await websocket.close()


# ============ NEW: Check Processing Status ============

@app.get("/bill/{bill_id}/status")
async def get_bill_status(bill_id: str):
    """
    Get current processing status of a bill.
    Useful for polling if WebSocket is not available.
    """
    # Check Celery task result
    task_result = celery_app.AsyncResult(bill_id)
    
    return JSONResponse(content={
        "bill_id": bill_id,
        "status": task_result.state,
        "info": task_result.info if task_result.info else {}
    })


# ============ EXISTING ENDPOINTS (Unchanged) ============

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
    """Download the original bill image from GCS"""
    try:
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

        match = re.match(r"(?:gs://|https://storage\.googleapis\.com/)([^/]+)/(.+)", gcs_uri)
        if not match:
            return JSONResponse(
                content={"error": "Invalid GCS URI format."},
                status_code=400
            )

        bucket_name, blob_name = match.groups()

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
    """Display the original bill image from GCS"""
    try:
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

        match = re.match(r"(?:gs://|https://storage\.googleapis\.com/)([^/]+)/(.+)", gcs_uri)
        if not match:
            return JSONResponse(
                content={"error": "Invalid GCS URI format."},
                status_code=400
            )

        bucket_name, blob_name = match.groups()

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