from google.cloud import storage
import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcloud-key/bill_upload_bucket_key.json"

def get_gcs_metadata(bucket_name, blob_name):
    """Fetches metadata for an object in Google Cloud Storage."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.get_blob(blob_name)

    if not blob:
        print("Object not found.")
        return

    print(f"Metadata for gs://{bucket_name}/{blob_name}")
    print(f"Content-Type: {blob.content_type}")
    print(f"Size: {blob.size} bytes")
    print(f"Created: {blob.time_created}")
    print(f"Updated: {blob.updated}")
    print(f"Storage Class: {blob.storage_class}")
    print(f"Custom Metadata: {blob.metadata}")

# Example usage
get_gcs_metadata("uploaded_bills", "bills/test_img.jpg")
