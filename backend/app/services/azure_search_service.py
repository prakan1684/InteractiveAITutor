from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
)
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from typing import List, Dict, Optional
from datetime import datetime
import os
from openai import OpenAI
from app.core.logger import get_logger
logger = get_logger(__name__)



class AzureSearchService:
    def __init__(self):
        endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        key = os.getenv("AZURE_SEARCH_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if not endpoint or not key or not openai_key:
            raise ValueError("Missing Azure Search or OpenAI API key")
        
        self.endpoint = endpoint
        self.credential = AzureKeyCredential(key)
        self.index_client = SearchIndexClient(
            endpoint = str(endpoint),
            credential = self.credential
        )

        self.openai_client = OpenAI(api_key = openai_key)
        self._ensure_indexes()


    def _ensure_indexes(self):
        self._create_canvas_sessions_index()
        self._create_course_materials_index()
        self._create_chat_history_index()
    

    def _create_canvas_sessions_index(self):
        index_name = "canvas-sessions"
        

        try:
            self.index_client.get_index(index_name)
            logger.info(f"Index {index_name} already exists")
            return
        except:
            logger.info(f"Index {index_name} does not exist, creating...")

        # Rich structured fields for precise querying and analytics
        
        fields = [
            # Identity fields
            SimpleField(
                name="id",
                type=SearchFieldDataType.String,
                key=True
            ),
            SimpleField(
                name="session_id",
                type=SearchFieldDataType.String,
                filterable=True
            ),
            SimpleField(
                name="student_id",
                type=SearchFieldDataType.String,
                filterable=True
            ),
            SimpleField(
                name="timestamp",
                type=SearchFieldDataType.DateTimeOffset,
                filterable=True,
                sortable=True
            ),
            
            # Content fields (searchable text)
            SearchableField(
                name="content",
                type=SearchFieldDataType.String,
            ),
            SearchableField(
                name="latex_expressions",
                type=SearchFieldDataType.String,
            ),
            SearchableField(
                name="agent_feedback",
                type=SearchFieldDataType.String,
            ),
            
            # Problem classification (filterable for precise queries)
            SimpleField(
                name="problem_type",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            SimpleField(
                name="topic",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            SimpleField(
                name="subtopic",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            SimpleField(
                name="difficulty_level",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            
            # Answer data
            SearchableField(
                name="student_answer",
                type=SearchFieldDataType.String,
            ),
            SearchableField(
                name="expected_answer",
                type=SearchFieldDataType.String,
            ),
            SimpleField(
                name="is_correct",
                type=SearchFieldDataType.Boolean,
                filterable=True,
                facetable=True
            ),
            
            # Work quality metrics
            SimpleField(
                name="shows_work",
                type=SearchFieldDataType.Boolean,
                filterable=True
            ),
            SimpleField(
                name="work_clarity",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            SimpleField(
                name="num_steps_shown",
                type=SearchFieldDataType.Int32,
                filterable=True,
                sortable=True
            ),
            
            # Metadata
            SimpleField(
                name="confidence",
                type=SearchFieldDataType.Double,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="visual_quality",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            SimpleField(
                name="num_regions",
                type=SearchFieldDataType.Int32,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="symbol_count",
                type=SearchFieldDataType.Int32,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="needs_help",
                type=SearchFieldDataType.Boolean,
                filterable=True
            ),
            
            # Vector search field
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=1536,
                vector_search_profile_name="vector-profile",
            ),
        ]

        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="hnsw-config")],
            profiles=[VectorSearchProfile(name="vector-profile", algorithm_configuration_name="hnsw-config")]
        )

        index = SearchIndex(
            name=index_name,
            fields = fields,
            vector_search = vector_search
        )
        self.index_client.create_index(index)
        logger.info(f"Index {index_name} created")
    
    def _create_course_materials_index(self):
        index_name = "course-materials"

        try:
            self.index_client.get_index(index_name)
            logger.info(f"Index {index_name} already exists")
            return
        except:
            logger.info(f"Index {index_name} does not exist, creating...")

        
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SimpleField(name="content_type", type=SearchFieldDataType.String, filterable=True),
            SearchableField(name="source_file", type=SearchFieldDataType.String),
            SimpleField(name="page_number", type=SearchFieldDataType.Int32, filterable=True),
            SimpleField(name="timestamp", type=SearchFieldDataType.DateTimeOffset, sortable=True),
            SimpleField(name="chunk_index", type=SearchFieldDataType.Int32, filterable=True),
            
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=1536,
                vector_search_profile_name="vector-profile"
            ),
        ]
        vector_search = VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="hnsw-config")],
            profiles=[VectorSearchProfile(name="vector-profile", algorithm_configuration_name="hnsw-config")]
        )
        
        index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
        self.index_client.create_index(index)
        logger.info(f"Created index: {index_name}")
    

    def _get_embedding(self, text: str) -> List[float]:
        """ user openai to get embedding for text"""
        try:
            response = self.openai_client.embeddings.create(
            input=text,
            model="text-embedding-ada-002"
        )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            raise
    
    def _create_chat_history_index(self):
        """
        Create index for storing conversation history
        """

        index_name = "chat-history"
        

        try:
            self.index_client.get_index(index_name)
            logger.info(f"Index {index_name} already exists")
            return
        except:
            logger.info(f"Index {index_name} does not exist, creating...")

        
        fields = [
            SimpleField(
                name="id",
                type=SearchFieldDataType.String,
                key=True
            ),
            SimpleField(
                name="conversation_id",
                type=SearchFieldDataType.String,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="student_id",
                type=SearchFieldDataType.String,
                filterable=True
            ),
            SimpleField(
                name="role",  # 'user' or 'assistant'
                type=SearchFieldDataType.String,
                filterable=True
            ),
            SearchableField(
                name="content",
                type=SearchFieldDataType.String
            ),
            SimpleField(
                name="timestamp",
                type=SearchFieldDataType.DateTimeOffset,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="mode",  # 'simple', 'fast', 'full'
                type=SearchFieldDataType.String,
                filterable=True
            ),
            SearchableField(
                name="metadata",  # JSON string for intent, confidence, etc.
                type=SearchFieldDataType.String
            )
        ]
    
        index = SearchIndex(name=index_name, fields=fields)
        self.index_client.create_index(index)
        logger.info(f"Created index: {index_name}")




    def store_canvas_session(
        self,
        session_id: str,
        student_id: str,
        content: str,
        latex_expressions: List[str],
        agent_feedback: str,
        # Rich structured fields from Vision Agent
        problem_type: str,
        topic: str,
        subtopic: str,
        difficulty_level: str,
        student_answer: str = None,
        expected_answer: str = None,
        is_correct: bool = None,
        shows_work: bool = False,
        work_clarity: str = "unclear",
        num_steps_shown: int = 0,
        confidence: float = 0.0,
        visual_quality: str = "unknown",
        num_regions: int = 0,
        symbol_count: int = 0,
        needs_help: bool = False
    ) -> bool:
        """Store canvas session with rich structured data in Azure Search"""
        try:
            client = SearchClient(
                endpoint = self.endpoint,
                index_name = "canvas-sessions",
                credential = self.credential
            )
            embedding = self._get_embedding(content)

            document = {
                # Identity
                "id": f"{student_id}_{session_id}",
                "session_id": session_id,
                "student_id": student_id,
                "timestamp": datetime.now(),
                
                # Content (searchable)
                "content": content,
                "latex_expressions": ", ".join(latex_expressions) if latex_expressions else "",
                "agent_feedback": agent_feedback,
                
                # Problem classification (filterable)
                "problem_type": problem_type,
                "topic": topic,
                "subtopic": subtopic,
                "difficulty_level": difficulty_level,
                
                # Answer data
                "student_answer": student_answer or "",
                "expected_answer": expected_answer or "",
                "is_correct": is_correct if is_correct is not None else False,
                
                # Work quality
                "shows_work": shows_work,
                "work_clarity": work_clarity,
                "num_steps_shown": num_steps_shown,
                
                # Metadata
                "confidence": confidence,
                "visual_quality": visual_quality,
                "num_regions": num_regions,
                "symbol_count": symbol_count,
                "needs_help": needs_help,
                
                # Vector search
                "content_vector": embedding,
            }

            client.upload_documents(documents=[document])
            logger.info(f"✅ Stored canvas session: {session_id} | Type: {problem_type} | Topic: {topic}")
            return True
        except Exception as e:
            logger.error(f"❌ Error storing canvas session: {e}")
            return False
    
    def search_canvas_sessions(
        self,
        student_id: str,
        query: str,
        top_k: int = 5
    ) -> List[Dict]:
        try:
            client = SearchClient(
                endpoint = self.endpoint,
                index_name = "canvas-sessions",
                credential = self.credential
            )

            query_vector = self._get_embedding(query)
            vector_query = VectorizedQuery(
                vector=query_vector,
                fields="content_vector",
                k_nearest_neighbors = top_k
            )
            results = client.search(
                search_text=query,
                vector_queries=[vector_query],
                filter=f"student_id eq '{student_id}'",
                select=["id, session_id, student_id, content, latex_expressions, agent_feedback, symbol_count, needs_help, timestamp"]
            )

            formatted = []
            for result in results:
                formatted.append({
                    "session_id": result["session_id"],
                    "content": result["content"],
                    "latex_expressions": result["latex_expressions"],
                    "agent_feedback": result["agent_feedback"],
                    "timestamp": result["timestamp"],
                    "needs_help": result["needs_help"],
                    "score": result["@search.score"]
                })
            
            logger.info(f"Found {len(formatted)} results for query: {query}")
            return formatted
        except Exception as e:
            logger.error(f"Error searching canvas sessions: {e}")
            return []
            


        



