from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse
import tempfile
import os
from bill_splitting_agent import BillSplitSystem
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
app = FastAPI(title="Bill Splitting API", version="1.0")

# Initialize main system
system = BillSplitSystem(
    api_key=os.getenv("GEMINI_API_KEY"),
    gcs_credentials_path=os.getenv("GCS_CREDENTIALS_PATH"),  # optional
    gcs_bucket_name=os.getenv("GCS_BUCKET_NAME")              # optional
)

@app.post("/process-bill")
async def process_bill(
    file: UploadFile = File(...),
    instruction: str = Form(...)
):
    """
    Upload a bill image and a split instruction.
    Returns structured bill data and split results.
    """
    try:
        # Save uploaded image temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name

        # Process and split
        bill_data, split_result = system.process_and_split(temp_file_path, instruction)

        # Clean up temporary file
        os.remove(temp_file_path)

        return JSONResponse(content={
            "message": "Bill processed successfully",
            "bill_data": bill_data.raw_data,
            "split_result": split_result.raw_data
        })

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
