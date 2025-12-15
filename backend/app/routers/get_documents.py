

from fastapi import APIRouter
from document_processor import get_available_documents
from document_processor import chroma_client
from logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/documents")
async def get_documents():
    #get list of documents from processed directory
    try:
        documents = get_available_documents()

        #collection info for debugging purposes
        collections = chroma_client.list_collections()
        collection_info = []
        for collection in collections:
            info = {
                "name":collection.name,
                "id": collection.id if hasattr(collection, "id") else None,
                "metadata": collection.metadata if hasattr(collection, "metadata") else {},
            }

            try:
                count = collection.count()
                info["document_count"] = count
            except:
                info["document_count"] = "Unknown"

            collection_info.append(info)

        return {
            "documents": documents,
            "collections": collection_info,
            "status": "success"
        }       
    except Exception as e:
        return {
            "error":str(e),
            "status":"error"
        }
    

