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
        
        status = processor.get_status()
        print(f"\n📊 Status Report:")
        print(f"  - Overall Status: {status['status']}")
        print(f"  - ChromaDB: {status['components']['chromadb']['status']}")
        print(f"  - Collections: {status['components']['chromadb']['collections']}")
        print(f"  - Vision Analyzer: {status['components']['vision_analyzer']['status']}")
        print(f"  - Vision Model: {status['components']['vision_analyzer']['model']}")
        print(f"  - Supported Images: {status['supported_formats']['images']}")

        return True
    except Exception as e:
        print(f"Error getting status: {e}")
        return False

if __name__ == "__main__":
    test()
    