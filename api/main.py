import os
import sys
# Allow running as a script from the root directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Optional
import json
import asyncio
from database.manager import DatabaseManager
from agent.graph import graph
from bson import ObjectId

app = FastAPI(title="Nepalese Legal RAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the scan images statically
app.mount("/scans", StaticFiles(directory="uploads/temp_images"), name="scans")

db_manager = DatabaseManager()

class VerificationUpdate(BaseModel):
    mongo_id: str
    content: str
    amendment_history: Optional[str] = None

class ChatRequest(BaseModel):
    question: str

@app.get("/api/sections/pending")
async def get_pending_sections():
    """Fetch sections that need verification."""
    cursor = db_manager.sections_col.find({"verification_status": "pending"})
    sections = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        # Convert local path to reachable URL
        if doc.get("source_image_path"):
            filename = os.path.basename(doc["source_image_path"])
            doc["source_image_path"] = f"http://localhost:8000/scans/{filename}"
        sections.append(doc)
    return sections

@app.post("/api/verify")
async def verify_section(update: VerificationUpdate):
    """Update and verify a section."""
    try:
        oid = ObjectId(update.mongo_id)
        db_manager.sections_col.update_one(
            {"_id": oid},
            {"$set": {
                "content": update.content,
                "amendment_history": update.amendment_history,
                "verification_status": "verified"
            }}
        )
        # Update vector DB
        db_manager.mark_as_verified(update.mongo_id)
        return {"status": "success", "message": f"Section {update.mongo_id} verified."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_stream(request: ChatRequest):
    """Stream LangGraph reasoning steps and final answer."""
    async def event_generator():
        inputs = {"question": request.question}
        # graph.stream returns an iterator of events
        for event in graph.stream(inputs):
            # event is a dict like {'node_name': {state_updates}}
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.1) # Small delay for smoother UI streaming
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
