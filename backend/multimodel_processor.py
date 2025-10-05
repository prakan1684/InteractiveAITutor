"""
Multimodel Processor for the Interactive AI Tutor

This class is responsible for processing the input from the user and handling the response from the multimodel.

It should handle both text and image input and return a response.

"""

import os
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

import chromadb
from dotenv import load_dotenv

from vision_analyzer import VisionAnalyzer
from document_processor import chroma_client

load_dotenv()

class MultimodelProcessor:
    """
    MultimodelProcessor for the Interactive AI Tutor
    """

    def __init__(self):
        self.chroma_client = chroma_client
        self.vision_analyzer = VisionAnalyzer()
        self.supported_image_types = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'
        }

    def store_image_analysis(self, image_data: Dict) -> Optional[str]:
        """
        Stores image analysis in chromadb for semantic search

        1. takes in processed image data from process_image method
        2. creates or gets collection in chromadb
        3. stores gpt4 vision analysis as searchable text
        4. adds metadata for tracking content

        """
        try:
            if image_data["status"] != "success":
                print(f"Failed to store image analysis: {image_data['error']}")
                return None

            document_name = image_data["document_name"]

            #create or get collection name
            collection_name = document_name.replace(" ", "_").replace(".", "_").replace("-", "_").lower()

            #create or get collection
            collection = self.chroma_client.get_or_create_collection(
                name=collection_name,
                metadata={
                    "document_name": document_name,
                    "content_types": "multimodal",
                    "created_at": datetime.now().isoformat()
                }
            )

            #generate unique id for image

            import uuid
            image_id = f"{document_name}_image_{uuid.uuid4().hex[:8]}"
            #store the analysis as searchable text


            collection.add(
                documents=[image_data["analysis"]],
                ids=[image_id],
                metadatas=[{
                    "content_type": "image",
                    "source_type": "vision_analysis",
                    "image_path": image_data["image_path"],
                    "file_name": image_data["file_name"],
                    "file_size": image_data["file_size"],
                    "model_used": image_data["model_used"],
                    "document_name": document_name,
                    "processed_at": datetime.now().isoformat()
                }]
            )

            return collection_name
        except Exception as e:
            print(f"Error storing image analysis: {e}")
            return None
    

    def search_content(self, query:str, top_k:int=5) -> Dict:
        """
        Search across both text and image content in unified method


        1. Gets all collections from chromadb
        2. Searches each collection for query
        3. combines and ranks results from all sources
        4. returns unified results from all documents and images.
        """

        try:
            #get all collections

            all_collections = self.chroma_client.list_collections()
            if not all_collections:
                return {
                    "status": "error",
                    "message": "No collections found",
                    "error_code": "NO_COLLECTIONS_FOUND"
                }

            all_results = []
            for collection_info in all_collections:
                # search collection -> process results -> append  to all_results
                
                try:
                    collection = self.chroma_client.get_collection(name=collection_info.name)

                    #search the collection
                    results = collection.query(
                        query_texts=[query],
                        n_results=min(top_k, 10)
                    )

                    documents = results["documents"][0]
                    metadatas = results["metadatas"][0]
                    distances = results.get("distances", [None])[0]


                    for i in range(len(documents)):
                        # loop through the results and get the metadata for each result
                        # metadatas is a list of dictionaries where each dictionary contains
                        # the metadata for a single result (e.g. document name, content type, etc.)
                        # we use the index i to access the metadata for the current result
                        metadata = metadatas[i]
                        content_type = metadata.get("content_type", "text")
                        result_item = {
                            "content": documents[i],
                            "content_type": content_type,
                            "similarity_score": 1 - distances[i] if distances and distances[i] is not None else None,
                            "collection_name": collection_info.name,
                            "document_name": metadata.get("document_name", collection_info.name),
                            "metadata": metadata
                        }
                        if content_type == "image":
                            result_item['source_info'] = {
                                "type":"Image Analysis",
                                "file_name": metadata.get("file_name", "Unknown"),
                                "model_used": metadata.get("model_used", "Unknown"),
                                "image_path": metadata.get("image_path", "Unknown")
                            }
                        else:
                            result_item['source_info'] = {
                                "type":"Text Chunk",
                                "chunk_id": metadata.get("chunk_id", "Unknown"),
                            }
                        all_results.append(result_item)

                except Exception as e:
                    print(f"Error searching collection {collection_info.name}: {e}")
            #sort all results by similarity score
            all_results.sort(key=lambda x: x['similarity_score'] or 0, reverse=True)
            final_results = all_results[:top_k]


            for i, results in enumerate(final_results):
                results['rank'] = i + 1
            
            return{
                "status": "success",
                "query": query,
                "total_collections_searched": len(all_collections),
                "total_results": len(all_results),
                "results": final_results
            }
        except Exception as e:
            return {
                "status": "error",
                "query": query,
                "error": str(e),
                "error_code": "SEARCH_ERROR"
            }
            
            
                    
            
    
    def get_status(self) -> Dict:
        """
        Returns the status of the multimodal processor.
        """
        try:
            collections = self.chroma_client.list_collections()
            chroma_status = "connected" if collections else "not connected"
            collection_count = len(collections) if collections else 0
        except Exception as e:
            chroma_status = "error: " + str(e)
            collection_count = 0
        
        try:
            vision_status = "connected" if self.vision_analyzer else "not connected"
        except Exception as e:
            vision_status = "error: " + str(e)
        
        return {
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "chromadb": {
                    "status": chroma_status,
                    "collections": collection_count
                },
                "vision_analyzer": {
                    "status": vision_status,
                    "model": getattr(self.vision_analyzer, 'model_name', 'unknown')
                }
            },
            "supported_formats": {
                "images": list(self.supported_image_types)
            }
        }


    def process_image(self, image_path:str, document_name:Optional[str] = None) -> Dict:
        """
        Processes an image and returns the analysis results.

        Args:
            image_path (str): Path to the image file.
            document_name (Optional[str], optional): Name of the document. Defaults to None.

        Returns:
            Dict: Analysis results.

        1. validate image file
        2. use gpt4.1 mini vision model to analyze the image
        3. extracts file metadata
        4. returns structured results

        """
        try:
            if not os.path.exists(image_path):
                return {
                    "status":"error",
                    "message":f"Image file not found : {image_path}",
                    "error_code": "FILE_NOT_FOUND"
                }
            

            #check if file type is supported

            image_path_obj = Path(image_path)

            if image_path_obj.suffix.lower() not in self.supported_image_types:
                return {
                    "status":"error",
                    "message":f"Unsupported image format: {image_path_obj.suffix}",
                    "error_code": "UNSUPPORTED_IMAGE_FORMAT"
                }
                
            #get image metadata
            file_size = image_path_obj.stat().st_size
            file_name = image_path_obj.name

            if not document_name:
                document_name = image_path_obj.stem
            
            print(f"Image file: {file_name}")
            print(f"File size: {file_size}")
            print(f"Document name: {document_name}")


            #analyze image
            analysis_result = self.vision_analyzer.analyze_image(image_path)

            if not analysis_result["success"]:
                return {
                    "status":"error",
                    "message":f"Failed to analyze image: {image_path}",
                    "error_code": "IMAGE_ANALYSIS_FAILED"
                }
            return {
                "status": "success",
                "content_type": "image",
                "image_path": str(image_path),
                "file_name": file_name,
                "file_size": file_size,
                "document_name": document_name,
                "analysis": analysis_result["analysis"],
                "model_used": analysis_result["model"],
                "processed_at": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status":"error",
                "message":f"Failed to process image: {image_path}",
                "error_code": "IMAGE_PROCESSING_FAILED"
            }
            
            


def test():
    try:
        processor = MultimodelProcessor()
        
        test_image = "./tests/dog.jpeg"
        result = processor.process_image(test_image)
        print(f"Image processed successfully {test_image}")

        #store in chromadb
        collection_name = processor.store_image_analysis(result)

        if not collection_name:
            print("Failed to store image analysis")
            return False

        #test global search
        test_queries = [
            "What is this?",
            "What breed of dog is this?",
            "What animal is shown?",
            "Describe the appearance",
            "What can students learn?"
        ]
        for i, query in enumerate(test_queries, 1):
            print(f"Test {i}: {query}")

            search_result = processor.search_content(query, top_k=3)

            if search_result["status"] == "success":
                print(f"  ✅ Found {search_result['total_results']} results from {search_result['total_collections_searched']} collections")
                
                for result in search_result["results"]:
                    print(f"    - {result['source_info']['type']} (from {result['document_name']}): {result['content'][:80]}...")
                    print(f"      Similarity: {result['similarity_score']:.3f}")
            else:
                print(f"  ❌ Search failed: {search_result['message']}")
        processor.chroma_client.delete_collection(collection_name)

        return True
    except Exception as e:
        print(f"Error getting status: {e}")
        return False

if __name__ == "__main__":
    test()
    