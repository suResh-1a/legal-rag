import os
import shutil
import json
import time
from datetime import datetime
from database.manager import DatabaseManager
from ingestion.pdf_processor import convert_pdf_to_images
from ingestion.gemini_extractor import GeminiExtractor
from ingestion.stitcher import stitch_sections
from database.loader import load_json_to_db
from utils.minio_client import minio_db

db_manager = DatabaseManager()

def process_pdf_background(job_id: str, file_path: str, original_filename: str):
    db_manager.db["extraction_jobs"].update_one(
        {"job_id": job_id},
        {"$set": {"status": "processing", "progress_message": "Converting PDF to images..."}}
    )
    
    try:
        temp_img_folder = f"uploads/temp_images/{job_id}"
        os.makedirs(temp_img_folder, exist_ok=True)
        image_paths = convert_pdf_to_images(file_path, temp_img_folder)
        
        total_pages = len(image_paths)
        db_manager.db["extraction_jobs"].update_one(
            {"job_id": job_id},
            {"$set": {"total_pages": total_pages, "progress_message": "Extracting text from images..."}}
        )
        
        extractor = GeminiExtractor()
        all_pages_raw_data = []
        
        for i, img_path in enumerate(image_paths):
            page_num = i + 1
            db_manager.db["extraction_jobs"].update_one(
                {"job_id": job_id},
                {"$set": {"progress_message": f"Extracting page {page_num} of {total_pages}..."}}
            )
            
            # Rate Limit Resilience Wrapper with Exponential Backoff
            max_retries = 6
            base_delay = 10
            
            for attempt in range(max_retries):
                try:
                    page_data = extractor.extract_legal_data(img_path, page_num)
                    
                    # Upload original scanned page to MinIO cloud storage
                    object_name = f"scans/{job_id}/page_{page_num}.png"
                    minio_db.upload_file(object_name=object_name, file_path=img_path)
                    
                    # Inject job, document, and minio object details
                    for item in page_data:
                        item["job_id"] = job_id
                        item["document_filename"] = original_filename
                        item["source_image_path"] = object_name # Store the MinIO object name, not local path
                        item["page_num"] = page_num
                        
                    all_pages_raw_data.append(page_data)
                    break
                except Exception as e:
                    err_str = str(e).lower()
                    if "429" in err_str or "resourceexhausted" in err_str or "quota" in err_str:
                        wait_time = base_delay * (2 ** attempt)
                        msg = f"Rate limited on page {page_num}. Retrying in {wait_time}s... (Attempt {attempt+1}/{max_retries})"
                        print(f"[{job_id}] {msg}")
                        db_manager.db["extraction_jobs"].update_one(
                            {"job_id": job_id},
                            {"$set": {"progress_message": msg}}
                        )
                        time.sleep(wait_time)
                    else:
                        raise e # Re-raise if it's a completely different error
            else:
                raise Exception(f"Failed to process page {page_num} after {max_retries} retries due to Gemini API rate limits.")
            
            db_manager.db["extraction_jobs"].update_one(
                {"job_id": job_id},
                {"$set": {"processed_pages": page_num}}
            )
            # Base delay to prevent bursting the RPM limits (e.g. 15 RPM)
            time.sleep(3)
            
        db_manager.db["extraction_jobs"].update_one(
            {"job_id": job_id},
            {"$set": {"progress_message": "Stitching hierarchical references..."}}
        )
        stitched_data = stitch_sections(all_pages_raw_data)
        
        db_manager.db["extraction_jobs"].update_one(
            {"job_id": job_id},
            {"$set": {"progress_message": "Indexing to database (Qdrant & MongoDB)..."}}
        )
        
        raw_output_path = f"data/per_page_raw_data_{job_id}.json"
        stitched_output_path = f"data/raw_extracted_legal_data_{job_id}.json"
        
        flat_raw_data = [item for sublist in all_pages_raw_data for item in sublist]
        with open(raw_output_path, "w", encoding="utf-8") as f:
            json.dump(flat_raw_data, f, ensure_ascii=False, indent=2)
            
        with open(stitched_output_path, "w", encoding="utf-8") as f:
            json.dump(stitched_data, f, ensure_ascii=False, indent=2)
            
        load_json_to_db(stitched_output_path, "legal_sections_vectors")
        load_json_to_db(raw_output_path, "legal_pages_vectors")
        
        # Cleanup artifacts
        try:
            os.remove(file_path)
            os.remove(raw_output_path)
            os.remove(stitched_output_path)
            # DO NOT remove temp_img_folder because the Verification UI uses it
        except Exception as cleanup_err:
            print(f"[{job_id}] Cleanup warning: {cleanup_err}")
        
        db_manager.db["extraction_jobs"].update_one(
            {"job_id": job_id},
            {"$set": {
                "status": "completed", 
                "progress_message": "Extraction and indexing completed successfully.",
                "completed_at": datetime.utcnow()
            }}
        )
        print(f"[{job_id}] Full Background Extraction pipeline completed successfully.")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        db_manager.db["extraction_jobs"].update_one(
            {"job_id": job_id},
            {"$set": {
                "status": "failed", 
                "progress_message": f"Error: {str(e)}",
                "completed_at": datetime.utcnow()
            }}
        )
