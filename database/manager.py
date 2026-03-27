import os
import uuid
from pymongo import MongoClient
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from bson import ObjectId
from typing import Dict, Any, List
from dotenv import load_dotenv
from database.models import LegalSection
from database.embeddings import EmbeddingManager

load_dotenv()

class DatabaseManager:
    def __init__(self):
        # MongoDB Setup
        self.mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.mongo_client = MongoClient(self.mongo_uri)
        self.db = self.mongo_client["legal_rag_db"]
        self.sections_col = self.db["LegalSections"]
        
        # Qdrant Setup
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
        
        try:
            print(f"Connecting to Qdrant at {self.qdrant_host}:{self.qdrant_port}...")
            self.qdrant_client = QdrantClient(
                host=self.qdrant_host, 
                port=self.qdrant_port,
                timeout=30, # Increased timeout
                check_compatibility=False
            )
            self.collection_name = "legal_sections_vectors"
            self._ensure_qdrant_collection()
        except Exception as e:
            print(f" CRITICAL ERROR: Could not connect to Qdrant at {self.qdrant_host}:{self.qdrant_port}")
            print(f" Reason: {e}")
            print(" Ensure Qdrant is running and reachable. If using a remote IP, check your VPN/Network.")
            raise e
        
        self.embedding_manager = EmbeddingManager()
        self.namespace_uuid = uuid.NAMESPACE_DNS # Use a stable namespace

    def _get_qdrant_id(self, mongo_id: str) -> str:
        """Converts a 24-character hex MongoDB ID to a stable UUID for Qdrant."""
        return str(uuid.uuid5(self.namespace_uuid, mongo_id))

    def _ensure_qdrant_collection(self):
        target_dim = 3072
        collections = self.qdrant_client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        recreate = False
        if exists:
            info = self.qdrant_client.get_collection(self.collection_name)
            current_dim = info.config.params.vectors.size
            if current_dim != target_dim:
                print(f"Dimension mismatch in {self.collection_name}: expected {target_dim}, got {current_dim}. Recreating...")
                self.qdrant_client.delete_collection(self.collection_name)
                recreate = True
        
        if not exists or recreate:
            from qdrant_client.http import models as rest_models
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=rest_models.VectorParams(
                    size=target_dim,
                    distance=rest_models.Distance.COSINE
                )
            )
            print(f"Created Qdrant collection: {self.collection_name} with dim {target_dim}")

    def upsert_to_knowledge_base(self, section_data: Dict[str, Any]):
        """
        a. Saves the full JSON to MongoDB.
        b. Generates a vector embedding for the content.
        c. Upserts the vector into Qdrant.
        """
        # 1. MongoDB Upsert
        section_data["verification_status"] = section_data.get("verification_status", "pending")
        
        query = {
            "act_name": section_data.get("act_name"),
            "dafa_no": section_data.get("dafa_no"),
            "page_num": section_data.get("page_num")
        }
        
        result = self.sections_col.update_one(query, {"$set": section_data}, upsert=True)
        
        if result.upserted_id:
            mongo_id = str(result.upserted_id)
        else:
            doc = self.sections_col.find_one(query)
            mongo_id = str(doc["_id"])

        # 2. Embedding Generation
        embedding = self.embedding_manager.get_embedding(section_data["content"])
        
        # 3. Qdrant Upsert - Use a stable UUID for Qdrant ID
        point_id = self._get_qdrant_id(mongo_id)
        has_amendment = bool(section_data.get("symbol_found"))
        
        payload = {
            "mongo_id": mongo_id,
            "act_name": section_data.get("act_name"),
            "dafa_no": section_data.get("dafa_no"),
            "has_amendment": has_amendment,
            "page_num": section_data.get("page_num")
        }
        
        self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )
            ]
        )
        return mongo_id

    def mark_as_verified(self, mongo_id: str):
        """
        Updates the MongoDB status and refreshes the Qdrant payload.
        """
        oid = ObjectId(mongo_id)
        doc = self.sections_col.find_one({"_id": oid})
        if not doc:
            raise ValueError("Document not found")
            
        self.sections_col.update_one({"_id": oid}, {"$set": {"verification_status": "verified"}})
        
        point_id = self._get_qdrant_id(mongo_id)
        self.qdrant_client.set_payload(
            collection_name=self.collection_name,
            payload={"verification_status": "verified"},
            points=[point_id]
        )

if __name__ == "__main__":
    # Test DB Manager
    # db = DatabaseManager()
    # db.upsert_to_knowledge_base({...})
    pass
