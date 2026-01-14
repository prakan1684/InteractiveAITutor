from azure.storage.blob import BlobServiceClient
import os
from dotenv import load_dotenv

load_dotenv()

def test_blob_upload():
    """Test uploading to Azure Blob Storage"""
    
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    
    # Get container
    container_client = blob_service.get_container_client("canvas-images")
    
    # Upload test file
    test_data = b"Hello from AI Tutor!"
    blob_client = container_client.get_blob_client("test.txt")
    blob_client.upload_blob(test_data, overwrite=True)
    
    print(f"✅ Uploaded to: {blob_client.url}")
    
    # Download to verify
    downloaded = blob_client.download_blob().readall()
    assert downloaded == test_data
    print("✅ Download verified!")
    
    # Clean up
    blob_client.delete_blob()
    print("✅ Test complete!")
if __name__ == "__main__":
    test_blob_upload()