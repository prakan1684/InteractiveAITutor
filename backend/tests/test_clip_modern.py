import open_clip
import torch
from PIL import Image
import requests
from io import BytesIO


def test_modern_clip():
    try:
        #loading lightweight clip model
        print("Loading lightweight clip model...")
        model, _, preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='openai')
        tokenizer = open_clip.get_tokenizer('ViT-B-32')

        print("Model loaded successfully.")
        print(f"Device: {next(model.parameters()).device}")


        #test with dummy data
        print("Testing with dummy data...")

        #testing with a dog image
        try:
            dog_image = Image.open("dog.jpeg")
            print(f"loaded dog image with size: {dog_image.size} pixels")

            #preprocess image for clip
            image_input = preprocess(dog_image).unsqueeze(0)
            print(f"Image input shape: {image_input.shape}")

            #create test descriptions
            text_descriptions = [
                "A photo of a dog",
                "A photo of a cat",
                "A photo of a horse",
                "A photo of a rabbit",
                "A photo of a monkey",
            ]

            text_input = tokenizer(text_descriptions)


            #get embeddings
            with torch.no_grad():
                image_features = model.encode_image(image_input)
                text_features = model.encode_text(text_input)
                print(f"Image features shape: {image_features.shape}")
                print(f"Text features shape: {text_features.shape}")

                #normalize features
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)

                #compute similarity
                similarities = (100.0* image_features @ text_features.T).softmax(dim=-1)

                print("Similarities:")
                for i, (desc, prob) in enumerate(zip(text_descriptions, similarities[0])):
                    print(f" {desc:12}: {prob:.4f} ({prob*100:.1f}%)")

                best_match_idx = similarities.argmax()
                best_match = text_descriptions[best_match_idx]
                confidence = similarities[0][best_match_idx]


                print(f"\n🏆 Best match: '{best_match}' with {confidence*100:.1f}% confidence")




                

        except Exception as e:
            print(f"Failed to preprocess image: {e}")
            return False

        
        return True
    except Exception as e:
        print("Failed to load model.")
        return False


if __name__ == "__main__":
    test_modern_clip()