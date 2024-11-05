# app.py
import streamlit as st
import os
import asyncio
from openai import OpenAI
from dotenv import load_dotenv
import pytess  # Import your pytess.py
import pyzerox_ext  # Import your first OCR method file
import tempfile
from pathlib import Path

# Load environment variables
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)

# Create output directory if it doesn't exist
output_dir = Path("ocr_results")
output_dir.mkdir(exist_ok=True)

async def get_best_ocr_result(file_path: str) -> str:
    """
    Get OCR results from both methods and combine them intelligently.
    """
    try:
        # Get results from both methods
        with st.spinner('Processing with Pyzerox...'):
            pyzerox_output = await pyzerox_ext.process_pdf_async(file_path)
            st.success('Pyzerox processing completed!')
        
        with st.spinner('Processing with Pytesseract...'):
            pytess_output = pytess.purify_and_extract_text_from_pdf(file_path)
            st.success('Pytesseract processing completed!')
        
        # If either method failed, return the successful one
        if not pyzerox_output and not pytess_output:
            raise ValueError("Both OCR methods failed to extract text")
        elif not pyzerox_output:
            return pytess_output
        elif not pytess_output:
            return pyzerox_output
            
        # Combine results using GPT-4
        with st.spinner('Combining results using GPT-4...'):
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
            verification_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at verifying and cleaning up OCR text."},
                    {"role": "user", "content": f"Verify and clean up this combined OCR text, ensuring proper formatting, correcting obvious errors, and maintaining data integrity:\n\n{combined_text}"}
                ],
                temperature=0.2
            )
            final_text = verification_response.choices[0].message.content
            st.success('Text combination and verification completed!')
            
            return final_text
        
    except Exception as e:
        st.error(f"Error in OCR processing: {str(e)}")
        return pyzerox_output or pytess_output or ""

def save_text_file(text: str, original_filename: str) -> Path:
    """Save the OCR result as a text file."""
    base_name = Path(original_filename).stem
    output_path = output_dir / f"{base_name}_ocr.txt"
    
    # Write the text to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)
    
    return output_path

def main():
    st.title("PDF OCR Processor")
    st.write("""
    Upload a PDF file to extract and process its text using multiple OCR methods.
    The results will be combined and saved as a text file.
    """)
    
    # File uploader
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file:
        st.write("File uploaded successfully!")
        
        # Create a temporary file for the PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        
        # Process button
        if st.button("Process PDF"):
            try:
                # Process the PDF
                result = asyncio.run(get_best_ocr_result(tmp_path))
                
                if result:
                    # Save the result
                    output_path = save_text_file(result, uploaded_file.name)
                    
                    # Display success message and download button
                    st.success(f"Processing completed! File saved as: {output_path}")
                    
                    # Create download button
                    with open(output_path, 'r', encoding='utf-8') as f:
                        st.download_button(
                            label="Download Result",
                            data=f.read(),
                            file_name=output_path.name,
                            mime='text/plain'
                        )
                    
                    # Preview the result
                    with st.expander("Preview Result"):
                        st.text(result)
                else:
                    st.error("Processing failed - no text could be extracted!")
            
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
            
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_path)
                except:
                    pass

if __name__ == "__main__":
    main()