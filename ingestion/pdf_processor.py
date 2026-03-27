import os
from pdf2image import convert_from_path
from PIL import Image
from typing import List

def convert_pdf_to_images(pdf_path: str, output_folder: str, dpi: int = 300) -> List[str]:
    """
    Converts PDF pages to high-resolution PNG images.
    Returns a list of paths to the generated images.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    print(f"Converting {pdf_path} to images at {dpi} DPI...")
    images = convert_from_path(pdf_path, dpi=dpi)
    
    image_paths = []
    for i, image in enumerate(images):
        image_name = f"page_{i+1}.png"
        image_path = os.path.join(output_folder, image_name)
        image.save(image_path, "PNG")
        image_paths.append(image_path)
        print(f"Saved {image_path}")
        
    return image_paths

if __name__ == "__main__":
    pdf_path = "/home/suresh/Desktop/trash/legal-rag/pdf_data_extraction/seed_act_nepal.pdf"
    output_folder = "/home/suresh/Desktop/trash/legal-rag/uploads/temp_images"
    if os.path.exists(pdf_path):
        convert_pdf_to_images(pdf_path, output_folder)
    else:
        print(f"PDF not found at {pdf_path}")
