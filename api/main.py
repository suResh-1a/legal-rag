import os
import sys
# Allow running as a script from the root directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, UploadFile, File
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
import uuid
import shutil
from datetime import datetime
from api.tasks import process_pdf_background

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
    session_id: str = "default"

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
            job_id = doc.get("job_id", "")
            base_url = os.getenv("BASE_URL", "http://localhost:8000")
            if job_id:
                doc["source_image_path"] = f"{base_url}/scans/{job_id}/{filename}"
            else:
                doc["source_image_path"] = f"{base_url}/scans/{filename}"
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

@app.post("/api/upload-pdf")
async def upload_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    job_id = str(uuid.uuid4())
    os.makedirs("uploads/temp_pdfs", exist_ok=True)
    file_path = f"uploads/temp_pdfs/{job_id}_{file.filename}"
    
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    db_manager.db["extraction_jobs"].insert_one({
        "job_id": job_id,
        "filename": file.filename,
        "status": "pending",
        "progress_message": "Uploaded. Waiting for background worker...",
        "total_pages": 0,
        "processed_pages": 0,
        "created_at": datetime.utcnow()
    })
    
    background_tasks.add_task(process_pdf_background, job_id, file_path, file.filename)
    
    return {"status": "success", "job_id": job_id, "message": "Extraction started in background."}

@app.get("/api/extraction-jobs")
async def get_extraction_jobs():
    cursor = db_manager.db["extraction_jobs"].find().sort("created_at", -1).limit(20)
    jobs = []
    for doc in cursor:
        doc.pop("_id", None)
        jobs.append(doc)
    return jobs

@app.delete("/api/extraction-jobs/{job_id}")
async def delete_extraction_job(job_id: str):
    try:
        db_manager.delete_job_data(job_id)
        return {"status": "success", "message": f"Job {job_id} and all related data deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/history")
async def get_chat_history(session_id: str = "default"):
    return {"status": "success", "history": db_manager.get_chat_history(session_id)}

@app.delete("/api/chat/history")
async def clear_chat_history(session_id: str = "default"):
    try:
        db_manager.clear_chat_history(session_id)
        return {"status": "success", "message": "Chat history cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_stream(request: ChatRequest):
    """Stream LangGraph reasoning steps and final answer."""
    # Save user message
    db_manager.save_chat_message(role="user", content=request.question, session_id=request.session_id)
    # Fetch recent history (past 6 messages -> 3 turns)
    history = db_manager.get_chat_history(session_id=request.session_id, limit=6)
    
    async def event_generator():
        inputs = {
            "question": request.question,
            "chat_history": history[:-1] if history else [] # Pass history excluding the fresh user question 
        }
        try:
            # graph.stream returns an iterator of events
            for event in graph.stream(inputs):
                # Intercept final_answer to save it to DB
                if "synthesizer" in event and "final_answer" in event["synthesizer"]:
                    ans = event["synthesizer"]["final_answer"]
                    tokens = event["synthesizer"].get("token_usage")
                    db_manager.save_chat_message(role="assistant", content=ans, session_id=request.session_id, token_usage=tokens)

                # event is a dict like {'node_name': {state_updates}}
                try:
                    json_data = json.dumps(event, ensure_ascii=False)
                    yield f"data: {json_data}\n\n"
                except Exception as je:
                    print(f"JSON ERROR in stream: {je}")
                    yield f"data: {json.dumps({'error': 'JSON serialization error: ' + str(je)})}\n\n"
                await asyncio.sleep(0.1) # Small delay for smoother UI streaming
        except Exception as e:
            print(f"GRAPH ERROR in stream: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
