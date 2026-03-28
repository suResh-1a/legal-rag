import os
from pdf2image import convert_from_path, pdfinfo_from_path
from PIL import Image
from typing import List

def convert_pdf_to_images(pdf_path: str, output_folder: str, dpi: int = 300) -> List[str]:
    """
    Converts PDF pages to high-resolution PNG images one-by-one to save memory.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    info = pdfinfo_from_path(pdf_path)
    total_pages = info["Pages"]
    
    print(f"Converting {pdf_path} ({total_pages} pages) to images at {dpi} DPI sequentially...")
    
    image_paths = []
    # Process only the first few for testing, or all if needed. 
    # The calling script ingestion/main.py will decide how many pages to extract from this list.
    # However, to be extra safe, we only convert what we actually need if we can.
    # For now, let's keep it robust and convert all but one-by-one.
    
    for i in range(1, total_pages + 1):
        image_name = f"page_{i}.png"
        image_path = os.path.join(output_folder, image_name)
        
        # Skip if already exists to save time/CPU
        if os.path.exists(image_path):
            image_paths.append(image_path)
            continue
            
        print(f"Converting Page {i}/{total_pages}...")
        page_images = convert_from_path(pdf_path, dpi=dpi, first_page=i, last_page=i)
        if page_images:
            page_images[0].save(image_path, "PNG")
            image_paths.append(image_path)
            print(f"Saved {image_path}")
        
        # Explicitly free memory if possible (though Python's GC should handle it)
        del page_images
        
    return image_paths

if __name__ == "__main__":
    pdf_path = "/home/suresh/Desktop/trash/legal-rag/pdf_data_extraction/seed_act_nepal.pdf"
    output_folder = "/home/suresh/Desktop/trash/legal-rag/uploads/temp_images"
    if os.path.exists(pdf_path):
        convert_pdf_to_images(pdf_path, output_folder)
    else:
        print(f"PDF not found at {pdf_path}")
