from celery import Task
from workers.celery_app import celery_app
import time

class ProgressTask(Task):
    def update_progress(self, bill_id, stage, message, progress):
        # Publish progress to Redis for WebSocket
        from redis import Redis
        redis_client = Redis(host='localhost', port=6379, decode_responses=True)
        redis_client.publish(
            f'bill_progress:{bill_id}',
            f'{{"stage": "{stage}", "message": "{message}", "progress": {progress}}}'
        )

@celery_app.task(base=ProgressTask, bind=True)
def process_bill_ocr(self, bill_id, file_path, instruction):
    """Process bill OCR in background"""
    
    # Update: Uploading
    self.update_progress(bill_id, 'uploading', 'Uploading bill...', 10)
    time.sleep(1)
    
    # Update: OCR
    self.update_progress(bill_id, 'ocr', 'Extracting text from bill...', 30)
    from utils.ocr import extract_text_from_image
    extracted_text = extract_text_from_image(file_path)
    
    # Update: Parsing
    self.update_progress(bill_id, 'parsing', 'Parsing bill items...', 50)
    from utils.parser import parse_bill
    bill_data = parse_bill(extracted_text)
    
    # Update: Splitting
    self.update_progress(bill_id, 'splitting', 'Calculating splits...', 70)
    from utils.splitter import split_bill
    split_result = split_bill(bill_data, instruction)
    
    # Update: Saving
    self.update_progress(bill_id, 'saving', 'Saving to database...', 90)
    from database import save_bill_data
    save_bill_data(bill_id, file_path, bill_data, split_result)
    
    # Update: Complete
    self.update_progress(bill_id, 'completed', 'Processing complete!', 100)
    
    return {'bill_id': bill_id, 'status': 'completed'}
