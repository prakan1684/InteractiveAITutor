import PyPDF2
from pathlib import Path
import json
from typing import List, Dict

import chromadb
from chromadb.api.collection_configuration import collection_configuration_to_json
from chromadb.config import Settings
import uuid

chroma_client = chromadb.PersistentClient(path="./vector_db")

def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file.

    Args:
        file_path (str): Path to the PDF file.

    Returns:
        str: Extracted text from the PDF.
    """

    try:
        text = ""
        reader = PyPDF2.PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text()
            text += "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""
    




    


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[Dict]:
    """
    Process a document into chunks for processing.

    Args:
        text (str): Text to process.
        chunk_size (int): Size of each chunk.
        overlap (int): Overlap between chunks.

    Returns:
        List[Dict]: List of processed chunks.


    Each chunk is a dictionary with the following keys:
    - "id": unique identifier for the chunk
    - "text": text of the chunk
    - "start_pos": starting position of the chunk in the original text
    - "end_pos": ending position of the chunk in the original text
    - "length": length of the chunk
    """

    if not text:
        return []
    
    chunks = []
    start_pos = 0
    chunk_id = 0


    while start_pos < len(text):
        end = start_pos + chunk_size
        chunk_text = text[start_pos:end]
        
        chunks.append({
            "id": chunk_id,
            "text": chunk_text,
            "start_pos": start_pos,
            "end_pos": end,
            "length": len(chunk_text)
        })

        start_pos += chunk_size - overlap
        chunk_id += 1
    
    return chunks



def store_chunks_in_vector_db(chunks: List[Dict], document_name:str) -> str:
    """
    1. Create collection for this document
    2. prepare data (texts, ids, metadata)
    3. store in chromadb with automatic embedding
    4. return collection name


    Args:
        chunks (List[Dict]): List of processed chunks.
        document_name (str): Name of the document.
    
    Returns:
        collection_name: Name of the collection created in chromadb.
    """

    try:
        print(f"Storing {len(chunks)} chunks in chromadb for document: {document_name}")


        #creating collection name
        collection_name = document_name.replace(" ", "_").replace(".", "_").replace("-", "_").lower()

        print(f"Creating collection: {collection_name}")


        #create or get the collection
        collection = chroma_client.get_or_create_collection(
            name=collection_name,
            metadata={
                "document_name": document_name,
                "total_chunks": len(chunks),
                "created_at": str(uuid.uuid4())  #using uuid to generate unique collection name
            }
        )
        print(f"Collection created: {collection_name}")


        #prepare data for storage in chromadb

        documents = [] #text content
        ids = [] #unique identifier for each chunk
        metadatas = [] #metadata for each chunk


        for chunk in chunks:
            documents.append(chunk["text"])
            ids.append(f"{document_name}_chunk_{chunk['id']}")
            metadatas.append({
                "chunk_id": chunk["id"],
                "start_pos": chunk["start_pos"],
                "end_pos": chunk["end_pos"],
                "length": chunk["length"],
                "document_name": document_name
            })

        print(f"prepared {len(documents)} documents for storage in chromadb")

        #store in chromadb
        collection.add(
            documents=documents,
            ids=ids,
            metadatas=metadatas
        )
        print(f"stored {len(documents)} documents in chromadb")


        #verify storage in chromadb
        count = collection.count()
        print(f"Collection now contains {count} chunks")

        return collection_name
    except Exception as e:
        print(f"Error storing chunks in chromadb: {e}")
        return None

        
def retrieve_relevant_chunks(query: str, top_k: int = 3) -> List[Dict]:
    try:

        #get all collections from chroma
        all_collections = chroma_client.list_collections()

        if not all_collections:
            return[]
        

        all_chunks = []
        for collection_info in all_collections:
            try:    
                collection = chroma_client.get_collection(name=collection_info.name)


                results = collection.query(
                    query_texts = [query],
                    n_results = min(top_k, 10)
                )

                documents = results["documents"][0]
                metadatas = results["metadatas"][0]
                distances = results.get('distances', [None])[0]

                for i in range(len(documents)):
                    chunk_data = {
                        "text": documents[i],
                        "metadata": metadatas[i],
                        "similarity_score": 1- distances[i] if distances and distances[i] is not None else None,
                        "collection_name": collection_info.name,
                        "document_name": metadatas[i].get("document_name", collection_info.name),
                        "content_type": metadatas[i].get("content_type", "text")
                    }
                    all_chunks.append(chunk_data)
            except Exception as e:
                print(f"Error retrieving chunks from collection {collection_info.name}: {e}")
                continue
    
        all_chunks.sort(key=lambda x: x['similarity_score'] or 0, reverse=True)

        # Take top_k results and add rank
        final_chunks = all_chunks[:top_k]
        for i, chunk in enumerate(final_chunks):
            chunk["rank"] = i + 1
        
        print(f"✅ Found {len(final_chunks)} relevant chunks from {len(all_collections)} collections")
        return final_chunks
    except Exception as e:
        print(f"Error retrieving relevant chunks: {e}")
        return []
    


def get_available_documents() -> List[str]:
    try:
        collections = chroma_client.list_collections()
        documents = []
        for collection in collections:
            if hasattr(collection, "metadata") and collection.metadata:
                doc_name = collection.metadata.get("document_name", collection.name)
                documents.append(doc_name)
            else:
                documents.append(collection.name)
        return documents
    except Exception as e:
        print(f"Error getting available documents: {e}")
        return []
    

def process_document(file_path: str) -> Dict:
    """
    complete document processing pipeline.
    1. Extract text from PDF
    2. Chunk text into smaller segments
    3. save chunks to a json file

    Args:
        file_path (str): Path to the PDF file.

    Returns:
        processing results with chunks and metadata
    """


    try:
        #extract text from pdf

        print(f"starting RAG pipeline for {file_path}")

        text = extract_text_from_pdf(file_path)

        if not text:
            return{
                "status": "error",
                "message": "Failed to extract text from PDF"
            }
        

        #chunk text
        chunks = chunk_text(text)

        if not chunks:
            return{
                "status": "error",
                "message": "Failed to chunk text"
            }

        #embed and store in vector DB

        filename = Path(file_path).stem
        collection_name = store_chunks_in_vector_db(chunks, filename)

        if not collection_name:
            return{
                "status": "error",
                "message": "Failed to store chunks in chromadb"
            }
        


        
        #create processed directory
        processed_dir = Path("processed")
        processed_dir.mkdir(exist_ok=True)



        #save processed data
        processed_file = processed_dir / f"{filename}_processed.json"

        processed_data = {
            "original_file":str(file_path),
            "total_text_length": len(text),
            "num_chunks": len(chunks),
            "vector_collection": collection_name,
            "chunks": chunks,
            "processed_at": str(Path(file_path).stat().st_mtime)
        }

        #save to json file

        with open(processed_file, "w", encoding="utf-8") as f:
            json.dump(processed_data, f, indent=2)

        return {
            "status": "success",
            "message": "Document processed successfully",
            "text_length": len(text),
            "num_chunks": len(chunks),
            "vector_collection": collection_name,
            "processed_file": str(processed_file)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
        


def test_retrieval_system():
    """Test semantic retrieval with sample data."""
    try:
        print("\n🧪 Testing retrieval system...")
        
        # First, store some test data
        test_chunks = [
            {
                "id": 0,
                "text": "Pranav Kandikonda is a software engineer with experience in AI and machine learning.",
                "start_pos": 0,
                "end_pos": 80,
                "length": 80
            },
            {
                "id": 1,
                "text": "He worked as a Software Engineer Intern at Spicyfy Ventures developing AI applications.",
                "start_pos": 70,
                "end_pos": 150,
                "length": 80
            },
            {
                "id": 2,
                "text": "His skills include Python, machine learning, and mobile app development.",
                "start_pos": 140,
                "end_pos": 210,
                "length": 70
            }
        ]
        
        # Store test data
        collection_name = store_chunks_in_vector_db(test_chunks, "test_resume")
        
        if collection_name:
            # Test different types of queries
            test_queries = [
                "What programming languages does he know?",
                "Where did he work?",
                "What is his experience with AI?"
            ]
            
            for query in test_queries:
                print(f"\n🔍 Query: {query}")
                results = retrieve_relevant_chunks(query, "test_resume", top_k=2)
                
                if results:
                    print("✅ Retrieval successful!")
                else:
                    print("❌ No results found")
            
            # Cleanup
            chroma_client.delete_collection(name=collection_name)
            print("\n🧹 Test cleanup completed")
            return True
        
    except Exception as e:
        print(f"❌ Retrieval test failed: {e}")
        return False

def test_vector_storage():
    try:
        print("Testing vector storage...")
        test_chunks = [
            {
                "id": 0,
                "text": "Photosynthesis is the process by which plants convert sunlight into energy.",
                "start_pos": 0,
                "end_pos": 71,
                "length": 71
            },
            {
                "id": 1,
                "text": "Chloroplasts are the organelles where photosynthesis occurs in plant cells.",
                "start_pos": 60,
                "end_pos": 135,
                "length": 75
            }
        ]

        #test storing chunks
        collection_name = store_chunks_in_vector_db(test_chunks, "test_document")

        if collection_name:
            print(f"✅ Vector storage successful! Collection name: {collection_name}")

            #test retrieving chunks
            collection = chroma_client.get_or_create_collection(name=collection_name)
            results = collection.query(
                query_texts=["what is photosynthesis"],
                n_results=2
            )
            print("test query results:")
            for i, doc in enumerate(results["documents"][0]):
                print(f"{i+1}. {doc[:50]}...")
            #clean up
            chroma_client.delete_collection(name=collection_name)
            print("✅ Collection deleted successfully!")

            return True
        
    except Exception as e:
        print(f"❌ Vector storage test failed: {e}")
        return False


def test_chromadb_connection():
    """Test basic ChromaDB functionality."""
    try:
        print("Testing ChromaDB connection...")
        
        # Test creating a simple collection
        test_collection = chroma_client.get_or_create_collection(name="test_collection")
        print("✅ ChromaDB connection successful!")
        
        # Test adding a simple document
        test_collection.add(
            documents=["This is a test document"],
            ids=["test_1"]
        )
        print("✅ Document storage successful!")
        
        # Test querying
        results = test_collection.query(
            query_texts=["test document"],
            n_results=1
        )
        print("✅ Query successful!")
        print(f"Retrieved: {results['documents'][0][0]}")
        
        # Clean up
        chroma_client.delete_collection(name="test_collection")
        print("✅ Cleanup successful!")
        
        return True
        
    except Exception as e:
        print(f"❌ ChromaDB test failed: {e}")
        return False

if __name__ == "__main__":
    test_chromadb_connection()
    test_vector_storage() 
    test_retrieval_system()