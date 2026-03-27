import google.generativeai as genai
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class EmbeddingManager:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY NOT FOUND")
        genai.configure(api_key=self.api_key)

    def get_embedding(self, text: str) -> List[float]:
        """
        Generates a vector embedding for the content using Gemini's gemini-embedding-001.
        """
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            task_type="retrieval_document",
            title="Legal Section"
        )
        return result['embedding']

if __name__ == "__main__":
    em = EmbeddingManager()
    embedding = em.get_embedding("नयाँ ऐनको मस्यौदा")
    print(f"Embedding size: {len(embedding)}")
