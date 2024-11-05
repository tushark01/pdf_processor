# master.py
import os
import asyncio
from openai import OpenAI
from dotenv import load_dotenv
import pytess  # Import your pytess.py
import pyzerox_ext  # Import your first OCR method file (you might need to rename it)

# Load environment variables
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)

async def get_best_ocr_result(file_path: str) -> str:
    """
    Get OCR results from both methods and combine them intelligently.
    """
    try:
        # Get results from both methods
        print("Starting OCR processing with both methods...")
        
        # Method 1: Pyzerox
        pyzerox_output = await pyzerox_ext.process_pdf_async(file_path)
        print("\nPyzerox processing completed.")
        
        # Method 2: Pytesseract
        pytess_output = pytess.purify_and_extract_text_from_pdf(file_path)
        print("\nPytesseract processing completed.")
        
        # If either method failed, return the successful one
        if not pyzerox_output and not pytess_output:
            raise ValueError("Both OCR methods failed to extract text")
        elif not pyzerox_output:
            return pytess_output
        elif not pytess_output:
            return pyzerox_output
            
        # Combine results using GPT-4
        print("\nCombining results using GPT-4...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """You are an expert at combining OCR outputs. 
                Your task is to create the most accurate combined version following these rules:
                1. Choose the clearer and more coherent sentences from either source
                2. Preserve numerical values that appear more accurate or complete
                3. Keep technical terms, proper nouns, and specific identifiers intact
                4. Maintain proper paragraph structure and formatting
                5. For any Hindi text, select the clearer version
                6. If the same information appears in both sources, choose the more readable version
                7. Maintain chronological order if timestamps or dates are present
                8. Preserve any tables or structured data in their clearest form"""},
                {"role": "user", "content": f"""Combine these two OCR outputs into the most accurate single text:
                
                First OCR Output (Pyzerox):
                {pyzerox_output}
                
                Second OCR Output (Pytesseract):
                {pytess_output}
                
                Create a single, coherent text that takes the best elements from both outputs."""}
            ],
            temperature=0.3
        )
        
        combined_text = response.choices[0].message.content
        
        # Final verification and cleanup
        try:
            verification_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at verifying and cleaning up OCR text."},
                    {"role": "user", "content": f"Verify and clean up this combined OCR text, ensuring proper formatting, correcting obvious errors, and maintaining data integrity:\n\n{combined_text}"}
                ],
                temperature=0.2
            )
            final_text = verification_response.choices[0].message.content
        except Exception as e:
            print(f"Verification step failed, using combined text directly: {str(e)}")
            final_text = combined_text
        
        print("\n____________Master OCR Processing Complete!______________")
        return final_text
        
    except Exception as e:
        print(f"Error in master OCR processing: {str(e)}")
        # Return whichever output is available
        return pyzerox_output or pytess_output or ""

async def main():
    # Example usage
    file_path = 'Documents/1/split_1_1-1.pdf'
    
    print(f"Processing PDF: {file_path}")
    result = await get_best_ocr_result(file_path)
    
    if result:
        print("\nFinal Result:")
        print("=" * 50)
        print(result)
        print("=" * 50)
        print("\nProcessing completed successfully!")
    else:
        print("\nProcessing failed - no text could be extracted!")

if __name__ == "__main__":
    asyncio.run(main())