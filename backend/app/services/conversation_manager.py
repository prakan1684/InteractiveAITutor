from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from typing import List, Dict, Optional
from datetime import datetime
import os
import uuid
import json
from app.core.logger import get_logger

logger = get_logger(__name__)


class ConversationManager:
    """Manages conversation history in Azure Search"""
    
    def __init__(self):
        endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        key = os.getenv("AZURE_SEARCH_KEY")
        
        if not endpoint or not key:
            raise ValueError("Missing Azure Search credentials")
        
        self.client = SearchClient(
            endpoint=str(endpoint),
            index_name="chat-history",
            credential=AzureKeyCredential(key)
        )
    
    def store_message(
        self,
        conversation_id: str,
        student_id: str,
        role: str,  # 'user' or 'assistant'
        content: str,
        mode: str = "fast",
        metadata: Optional[Dict] = None
    ) -> str:
        """Store a single message in conversation history"""
        
        message_id = str(uuid.uuid4())
        
        document = {
            "id": message_id,
            "conversation_id": conversation_id,
            "student_id": student_id,
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "mode": mode,
            "metadata": json.dumps(metadata) if metadata else "{}"
        }
        
        try:
            self.client.upload_documents([document])
            logger.info(f"Stored message {message_id} in conversation {conversation_id}")
            return message_id
        except Exception as e:
            logger.error(f"Error storing message: {e}")
            raise
    
    def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """Retrieve conversation history sorted by timestamp"""
        
        try:
            results = self.client.search(
                search_text="*",
                filter=f"conversation_id eq '{conversation_id}'",
                order_by=["timestamp asc"],
                top=limit
            )
            
            messages = []
            for result in results:
                try:
                    metadata_str = result.get("metadata", "{}")
                    metadata = json.loads(metadata_str) if metadata_str else {}
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse metadata: {e}, using empty dict")
                    metadata = {}
                
                messages.append({
                    "role": result["role"],
                    "content": result["content"],
                    "timestamp": result["timestamp"],
                    "mode": result.get("mode", "fast"),
                    "metadata": metadata
                })
            
            logger.info(f"Retrieved {len(messages)} messages for conversation {conversation_id}")
            return messages
            
        except Exception as e:
            logger.error(f"Error retrieving conversation: {e}")
            return []
    
    def get_student_conversations(
        self,
        student_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """Get list of conversations for a student"""
        
        try:
            # Get unique conversation IDs with latest message
            results = self.client.search(
                search_text="*",
                filter=f"student_id eq '{student_id}'",
                order_by=["timestamp desc"],
                top=100
            )
            
            # Group by conversation_id and get latest message
            conversations = {}
            for result in results:
                conv_id = result["conversation_id"]
                if conv_id not in conversations:
                    conversations[conv_id] = {
                        "conversation_id": conv_id,
                        "last_message": result["content"][:100],
                        "timestamp": result["timestamp"],
                        "message_count": 1
                    }
                else:
                    conversations[conv_id]["message_count"] += 1
            
            # Sort by timestamp and limit
            conv_list = sorted(
                conversations.values(),
                key=lambda x: x["timestamp"],
                reverse=True
            )[:limit]
            
            logger.info(f"Found {len(conv_list)} conversations for student {student_id}")
            return conv_list
            
        except Exception as e:
            logger.error(f"Error retrieving conversations: {e}")
            return []
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete all messages in a conversation"""
        
        try:
            results = self.client.search(
                search_text="*",
                filter=f"conversation_id eq '{conversation_id}'",
                select=["id"]
            )
            
            message_ids = [{"id": r["id"]} for r in results]
            
            if message_ids:
                self.client.delete_documents(message_ids)
                logger.info(f"Deleted {len(message_ids)} messages from conversation {conversation_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting conversation: {e}")
            return False


# Singleton instance
conversation_manager = ConversationManager()