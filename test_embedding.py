import os
import asyncio
from dotenv import load_dotenv

# Try to import the new google-genai library
try:
    from google import genai
except ImportError:
    print("Error: google-genai library not installed. Please install it with 'pip install google-genai'.")
    exit(1)

# Load environment variables from .env
load_dotenv()

async def test_embedding():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment variables.")
        return

    print(f"Initializing Gemini client with API key: {api_key[:5]}...{api_key[-5:]}")
    
    try:
        client = genai.Client(api_key=api_key)
        
        test_text = "This is a test sentence for medical triage embedding."
        model_id = "gemini-embedding-001"
        
        print(f"Generating embedding using model: {model_id}")
        
        result = client.models.embed_content(
            model=model_id,
            contents=test_text
        )
        
        embeddings = result.embeddings[0].values
        print(f"Successfully generated embedding!")
        print(f"Embedding dimension: {len(embeddings)}")
        print(f"First 5 values: {embeddings[:5]}")
        
    except Exception as e:
        print(f"Failed to generate embedding: {e}")

if __name__ == "__main__":
    asyncio.run(test_embedding())
