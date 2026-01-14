# app/services/azure_blob_storage.py

from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.core.exceptions import ResourceNotFoundError
from datetime import datetime, timedelta
from typing import Optional
import os
from app.core.logger import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class AzureBlobStorage:
    """
    Azure Blob Storage service for storing canvas images, debug images, and PDFs
    

    """
    
    def __init__(self):
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not connection_string:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING not set in environment")
        
        self.blob_service = BlobServiceClient.from_connection_string(connection_string)
        self.account_name = self.blob_service.account_name
        
        # Container names
        self.canvas_container = "canvas-images"
        self.debug_container = "debug-images"
        self.uploads_container = "uploads"
        
        # Ensure containers exist
        self._ensure_containers()
    
    def _ensure_containers(self):
        """Create containers if they don't exist"""
        for container_name in [self.canvas_container, self.debug_container, self.uploads_container]:
            try:
                self.blob_service.create_container(container_name)
                logger.info(f"Created container: {container_name}")
            except Exception as e:
                # Container might already exist
                logger.debug(f"Container {container_name} already exists or error: {e}")
    
    def upload_canvas_image(
        self,
        image_data: bytes,
        filename: str,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload canvas image from iOS app
        
        Args:
            image_data: Image bytes
            filename: Filename (e.g., "canvas_abc123.png")
            metadata: Optional metadata (session_id, student_id, etc.)
            
        Returns:
            Public URL to the blob
            
        """
        try:
            blob_client = self.blob_service.get_blob_client(
                container=self.canvas_container,
                blob=filename
            )
            
            # Upload with metadata
            blob_client.upload_blob(
                image_data,
                overwrite=True,
                metadata=metadata or {}
            )
            
            logger.info(f"Uploaded canvas image: {filename} ({len(image_data)} bytes)")
            return blob_client.url
            
        except Exception as e:
            logger.error(f"Failed to upload canvas image {filename}: {e}")
            raise
    
    def upload_debug_image(
        self,
        image_data: bytes,
        filename: str,
        session_id: str
    ) -> str:
        """
        Upload debug image (with symbol boxes drawn)
        
        Args:
            image_data: Image bytes
            filename: Filename (e.g., "debug_abc123.png")
            session_id: Session ID for tracking
            
        Returns:
            Public URL to the blob
        """
        try:
            blob_client = self.blob_service.get_blob_client(
                container=self.debug_container,
                blob=filename
            )
            
            blob_client.upload_blob(
                image_data,
                overwrite=True,
                metadata={"session_id": session_id}
            )
            
            logger.info(f"Uploaded debug image: {filename}")
            return blob_client.url
            
        except Exception as e:
            logger.error(f"Failed to upload debug image {filename}: {e}")
            raise
    
    def get_signed_url(
        self,
        container: str,
        blob_name: str,
        expiry_hours: int = 1
    ) -> str:
        """
        Generate a signed URL for private blob access
        
        Args:
            container: Container name
            blob_name: Blob name
            expiry_hours: How long the URL is valid
            
        Returns:
            Signed URL with SAS token
            
        """
        try:
            blob_client = self.blob_service.get_blob_client(
                container=container,
                blob=blob_name
            )
            
            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=self.account_name,
                container_name=container,
                blob_name=blob_name,
                account_key=self._get_account_key(),
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
            )
            
            return f"{blob_client.url}?{sas_token}"
            
        except Exception as e:
            logger.error(f"Failed to generate signed URL for {blob_name}: {e}")
            raise
    
    def _get_account_key(self) -> str:
        """Extract account key from connection string"""
        conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        for part in conn_str.split(";"):
            if part.startswith("AccountKey="):
                return part.split("=", 1)[1]
        raise ValueError("AccountKey not found in connection string")
    
    def delete_blob(self, container: str, blob_name: str) -> bool:
        """
        Delete a blob
        
        Args:
            container: Container name
            blob_name: Blob name
            
        Returns:
            True if deleted, False if not found
        """
        try:
            blob_client = self.blob_service.get_blob_client(
                container=container,
                blob=blob_name
            )
            blob_client.delete_blob()
            logger.info(f"Deleted blob: {container}/{blob_name}")
            return True
            
        except ResourceNotFoundError:
            logger.warning(f"Blob not found: {container}/{blob_name}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete blob {blob_name}: {e}")
            raise


# Global singleton
azure_blob_storage = AzureBlobStorage()