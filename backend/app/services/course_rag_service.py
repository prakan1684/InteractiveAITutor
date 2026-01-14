from app.services.azure_search_service import AzureSearchService
from datetime import timedelta
from typing import Dict, List
from app.core.logger import get_logger
import re
import pdfplumber
from datetime import datetime

logger = get_logger(__name__)

class CourseRAGService:
    def __init__(self):
        self.azure_search = AzureSearchService()
        self.chunk_size = 500
        self.chunk_overlap = 100
        self.max_tokens = 8000
    

    def upload_pdf(self, pdf_path:str, metadata: Dict = None) -> Dict:
        """
        Process a PDF file and store its content in Azure Search
        
        Args:
            pdf_path (str): Path to the PDF file
            metadata (Dict, optional): Metadata to store (course name, chapter, etc.). Defaults to None.

        Returns:
            {
                "success": bool,
                "chunks_uploaded": int,
                "pages_processed": int,
                "errors": List[str]
            }
        """

        errors = []
        total_chunks = 0


        try:
            #first extract pages
            pages = self._extract_pages(pdf_path)

            if not pages:
                return {
                    "success": False,
                    "chunks_uploaded": 0,
                    "pages_processed": 0,
                    "errors": ["Failed to extract pages"]
                }
            all_chunks = []
            source_file = pdf_path.split("/")[-1]

            for page_data in pages:
                try:
                    chunks = self._chunk_page(page_data, source_file)
                    all_chunks.extend(chunks)
                except Exception as e:
                    error_msg = f"Failed to chunk page {page_data['page']}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            #upload to azure 
            for chunk in all_chunks:
                try:
                    success = self._upload_chunk(chunk, metadata)

                    if success:
                        total_chunks += 1
                    else:
                        errors.append(f"Failed to upload chunk: {chunk['page_number']}")
                except Exception as e:
                    error_msg = f"Failed to upload chunk {chunk['page_number']}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            return {
                "success": True,
                "chunks_uploaded": total_chunks,
                "pages_processed": len(pages),
                "errors": errors
            }

        except Exception as e:
            logger.error(f"upload PDF failed{e}")
            return {
                "success": False,
                "chunks_uploaded": 0,
                "pages_processed": 0,
                "errors": [str(e)]
            }
    

    def _upload_chunk(
        self,
        chunk: Dict,
        metadata:Dict = None,
    ) -> bool:

        try:
            embedding = self.azure_search._get_embedding(chunk['content'])

            #build document

            # Build document
            doc_id = f"{chunk['source_file']}_p{chunk['page_number']}_c{chunk['chunk_index']}"
            doc_id = doc_id.replace(" ", "_").replace(".", "_")  # Clean ID

            document = {
                "id": doc_id,
                "content": chunk['content'],
                "content_type": "text",
                "source_file": chunk['source_file'],
                "page_number": chunk['page_number'],
                "chunk_index": chunk['chunk_index'],
                "timestamp": datetime.now(),
                "content_vector": embedding
            }


            if metadata:
                document.update(metadata)

            
            from azure.search.documents import SearchClient

            client = SearchClient(
                endpoint=self.azure_search.endpoint,
                index_name="course-materials",
                credential=self.azure_search.credential
            )

            client.upload_documents([document])
            return True
        except Exception as e:
            logger.error(f"Failed to upload chunk: {str(e)}")
            return False
    


    def search_materials(
        self,
        query: str,
        top_k:int=5
    ) -> List[Dict]:
        try:
            from azure.search.documents import SearchClient
            from azure.search.documents.models import VectorizedQuery

            client = SearchClient(
                endpoint = self.azure_search.endpoint,
                index_name = "course-materials",
                credential = self.azure_search.credential
            )

            query_vector = self.azure_search._get_embedding(query) 


            vector_query = VectorizedQuery(
                vector=query_vector,
                k_nearest_neighbors=top_k,
                fields="content_vector"
            )

            results = client.search(
                search_text=query,
                vector_queries=[vector_query],
                select=["content", "source_file", "page_number", "chunk_index"],
                top=top_k
            )

            formatted = []

            for result in results:
                formatted.append({
                    "content": result["content"],
                    "source_file": result["source_file"],
                    "page_number": result["page_number"],
                    "chunk_index": result["chunk_index"],
                    "score": result["@search.score"]
                })
            logger.info("Found %s results for query: %s", len(formatted), query)
            return formatted
        except Exception as e:
            logger.error(f"Failed to search course materials: {str(e)}")
            return []



    def _split_into_paragraphs(self, text: str) -> List[str]:
        """
        Simple paragraph splitting with equation preservation
        Focus: Math equations only
        """
    
    # Step 1: Protect LaTeX equations
        equations = []
        protected_text = text
    
    # Match $...$ and $$...$$
        latex_patterns = [
            (r'\$\$.*?\$\$', 'DISPLAY'),  # Display equations
            (r'\$.*?\$', 'INLINE'),        # Inline equations
        ]
    
        for pattern, eq_type in latex_patterns:
            matches = list(re.finditer(pattern, protected_text, re.DOTALL))
            for i, match in enumerate(matches):
                placeholder = f"___{eq_type}_EQ_{len(equations)}___"
                equations.append(match.group(0))
                protected_text = protected_text.replace(match.group(0), placeholder, 1)
    
    # Step 2: Split by double newlines
        paragraphs = re.split(r'\n\s*\n', protected_text)
    
    # Step 3: Restore equations
        restored = []
        for para in paragraphs:
            for i, eq in enumerate(equations):
                para = para.replace(f"___DISPLAY_EQ_{i}___", eq)
                para = para.replace(f"___INLINE_EQ_{i}___", eq)
        
            para = para.strip()
            if para:  # Only keep non-empty paragraphs
                restored.append(para)
    
        return restored
    
    def _chunk_page(self, page_data: Dict, source_file: str) -> List[Dict]:
        """
        Create overlapping chunks from page text
        """
        text = page_data["text"]
        page_num = page_data["page"]
    
        # Get paragraphs
        paragraphs = self._split_into_paragraphs(text)
    
        chunks = []
        current_chunk = ""
        chunk_index = 0
    
        for para in paragraphs:
            # Check if adding this paragraph exceeds chunk size
            potential_length = len(current_chunk) + len(para) + 2  # +2 for \n\n
        
            if potential_length > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append({
                "content": current_chunk.strip(),
                "page_number": page_num,
                "chunk_index": chunk_index,
                "source_file": source_file,
                "char_count": len(current_chunk)
            })
                chunk_index += 1
            
            # Start new chunk with overlap
                words = current_chunk.split()
                overlap_words = words[-20:] if len(words) > 20 else words  # Last ~20 words
                current_chunk = " ".join(overlap_words) + "\n\n" + para
        
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
    
            # Don't forget the last chunk
            if current_chunk:
                chunks.append({
                "content": current_chunk.strip(),
                "page_number": page_num,
                "chunk_index": chunk_index,
                "source_file": source_file,
                "char_count": len(current_chunk)
            })
    
            return chunks
    
    def _extract_pages(self, pdf_path: str) -> List[Dict]:
        """
        Extract text from PDF using pdfplumber
    
        Returns:
            [
                {"page": 1, "text": "...", "has_tables": False},
                {"page": 2, "text": "...", "has_tables": True},
            ]
    """
        pages = []
    
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages, start=1):
                    # Extract text
                    text = page.extract_text()
                
                    if not text:
                        logger.warning(f"Page {i} has no extractable text")
                        continue
                
                # Check for tables
                    tables = page.extract_tables()
                    has_tables = len(tables) > 0
                
                    pages.append({
                        "page": i,
                        "text": text,
                        "has_tables": has_tables
                    })
                
                logger.info(f"Extracted page {i}: {len(text)} chars, {len(tables)} tables")
            
            return pages
        
        except Exception as e:
            logger.error(f"Failed to extract PDF: {e}")
            raise