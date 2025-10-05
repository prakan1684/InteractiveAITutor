import os
import sys
from pathlib import Path




sys.path.append(str(Path(__file__).parent.parent))

from multimodel_processor import MultimodelProcessor


def test_multimodal_pipeline():
    """
    Tests for the multimodal pipeline

    """


    processor = MultimodelProcessor()
    
    test_image = "dog.jpeg"
    if not os.path.exists(test_image):
        raise FileNotFoundError(f"Test image not found: {test_image}")
    
    #process image
    print("Processing image...")
    image_result = processor.process_image(test_image)

    if image_result["status"] != "success":
        print(f"Error processing image: {image_result['error']}")
        return False
    

    print("storing in chromadb...")
    collection_name = processor.store_image_analysis(image_result)
    if not collection_name:
        print("Error storing image analysis")
        return False
    
    print(f"Image analysis stored successfully in {collection_name}")


    queries = [
        "What is the dog doing?",
        "what breed is the dog?",
        "describe the appearance"
    ]

    for query in queries:
        print(f"\n\nQuery: {query}")
        search_results = processor.search_content(query, top_k=2)
        if search_results['status'] == "success":
            print(f"found {search_results['total_results']} results from {search_results['total_collections_searched']} collections")


            for result in search_results['results']:
                if result['content_type'] == 'image':
                    print(f"relevance score: {result['similarity_score']:.3f}") 
                    print(f"content: {result['content'][:100]}...")       
                    break
        else:
            print("search failed")
    #clean up

    processor.chroma_client.delete_collection(name=collection_name)
    return True




if __name__ == "__main__":
    test_multimodal_pipeline()

            



