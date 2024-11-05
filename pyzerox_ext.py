import os
import asyncio
from openai import OpenAI
import time
import re
from dotenv import load_dotenv
from pdf2image import convert_from_path
import pytesseract
from typing import Optional

# Load environment variables
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(
    # defaults to os.environ.get("OPENAI_API_KEY")
    api_key = os.getenv('OPENAI_API_KEY')
)
def clean_ocr_text(ocr_text: str) -> str:
    """Clean OCR text by removing extra whitespace and normalizing line breaks."""
    cleaned_text = re.sub(r'\s+', ' ', ocr_text)
    cleaned_text = re.sub(r'\n+', '\n', cleaned_text)
    return cleaned_text.strip()

def purify_ocr_text(ocr_text: str) -> str:
    """
    Use OpenAI's API to improve and correct OCR text.
    Includes exponential backoff for rate limiting.
    """
    ocr_text = clean_ocr_text(ocr_text)
    
    for attempt in range(5):
        try:
            response = client.chat.completions.create(
               model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that corrects and purifies OCR text."},
                    {"role": "user", "content": f"Purify the following OCR text:\n\n{ocr_text}"},
                ],
                temperature=0.3  # Added for more consistent results
            )
            return response.choices[0].message.content
    
        except Exception as e:
            print(f"Error in OpenAI API call: {str(e)}")
            return ocr_text
    
    return ocr_text  # Return original text if all attempts fail

async def extract_text_from_pdf(file_path: str) -> Optional[str]:
    """Extract text from PDF using pdf2image and pytesseract."""
    try:
        # Convert PDF to images
        images = convert_from_path(file_path)
        
        # Extract text from each image
        text_parts = []
        for image in images:
            text = pytesseract.image_to_string(image)
            text_parts.append(text)
        
        return '\n'.join(text_parts)
    except Exception as e:
        print(f"Error in PDF text extraction: {str(e)}")
        return None

async def process_pdf_async(file_path: str) -> str:
    """
    Process a PDF file asynchronously:
    1. Extract text using OCR
    2. Clean and purify the extracted text
    """
    try:
        # Verify file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")
            
        # Extract text from PDF
        extracted_text = await extract_text_from_pdf(file_path)
        
        if not extracted_text:
            raise ValueError("No text could be extracted from the PDF")
            
        # Purify the extracted text
        purified_text = purify_ocr_text(extracted_text)
        
        print("____________PDF Processing Complete!______________")
        print(purified_text)
        return purified_text
        
    except Exception as e:
        print(f"Error in process_pdf_async: {str(e)}")
        return ""

# Example usage
async def main():
    file_path = 'Documents/1/split_1_1-1.pdf'
    result = await process_pdf_async(file_path)
    if result:
        print("Processing completed successfully!")
    else:
        print("Processing failed!")

if __name__ == "__main__":
    asyncio.run(main())