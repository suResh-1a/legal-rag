import os
from qdrant_client import QdrantClient
from dotenv import load_dotenv, find_dotenv
env_path = os.path.join(os.getcwd(), '.env')
load_dotenv(env_path, override=True)
client = QdrantClient(host=os.getenv("QDRANT_HOST"), port=int(os.getenv("QDRANT_PORT")))
try:
    print("Sections:", client.count("legal_sections_vectors").count)
except Exception as e: print("Sections Error:", e)
try:
    print("Pages:", client.count("legal_pages_vectors").count)
except Exception as e: print("Pages Error:", e)
