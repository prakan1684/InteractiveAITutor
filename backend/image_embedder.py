import open_clip
import torch
from PIL import Image
from typing import Optional
import numpy as np






class ImageEmbedder:
    """
    Converts images to vector embeddings using OpenCLIP
    This allows us to search images based on their content


    """

    def __init__(self, model_name:str = "ViT-B-32"):
        """
        Initialize the image embedder

        Args:
            model_name (str, optional): Name of the model to use. Defaults to "ViT-B-32".
        
        1. Loading clip model
        2. set up image preprocessing
        3. Detect if we can use GPU or need CPU
        4. put model in eval mode


        """

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            model_name,
            pretrained="openai",
            device=self.device
        )

        self.model.eval()
        self.model_name = model_name
    

    def _get_embedding_dimension(self) -> int:
        """
        Get the embedding dimension of the model
        """

        dummy_input = torch.randn(1, 3, 224, 224).to(self.device)
        with torch.no_grad():
            embeddings = self.model.encode_image(dummy_input)
        return embeddings.shape[1]
    
    def embed_image(self, image_path:str) -> np.ndarray:
        """
        Embed an image

        Args:
            image_path (str): Path to the image file.

        Returns:
            np.ndarray: Embedding of the image.
        """
        try:
            #open image
            image = Image.open(image_path).convert("RGB")

            #preprocess image
            image = self.preprocess(image).unsqueeze(0).to(self.device)

            #get embedding
            with torch.no_grad():
                embedding = self.model.encode_image(image)
                #normalize embedding
                image_features = embedding / embedding.norm(dim=-1, keepdim=True)
            return image_features.cpu().numpy().flatten()
            
        except Exception as e:
            print(f"Error embedding image: {e}")
            return np.zeros(self._get_embedding_dimension())
            
            





def test_image_embedder():
    print("testing image embedder...")
    try:
        image_embedder = ImageEmbedder()
        print(f"Model name: {image_embedder.model_name}")
        print(f"Device: {image_embedder.device}")
        print(f"Embedding dimension: {image_embedder._get_embedding_dimension()}")


        #test embedding
        test_image_path = "tests/dog.jpeg"
        embedding = image_embedder.embed_image(test_image_path)
        
        if embedding is not None and len(embedding) > 0:
            print("Embedding generated successfully.")
            print(f"Embedding shape: {embedding.shape}")
            print(f"Range: {embedding.min():.3f} to {embedding.max():.3f}")

        else:
            print("Failed to generate embedding")
    except Exception as e:
        print(f"Error testing image embedder: {e}")



if __name__ == "__main__":
    test_image_embedder()
    
