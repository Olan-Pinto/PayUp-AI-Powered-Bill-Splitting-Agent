from google.cloud import storage
import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcloud-key/bill_upload_bucket_key.json"

def upload_to_gcs(bucket_name, source_file_path, destination_blob_name):
    """Uploads a file to the Google Cloud Storage bucket."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_path)

    print(f"File {source_file_path} uploaded to gs://{bucket_name}/{destination_blob_name}")

# Example usage
upload_to_gcs("uploaded_bills", "./test_img.jpg", "bills/test_img.jpg")
