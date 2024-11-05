import streamlit as st
import os
from PyPDF2 import PdfReader, PdfWriter
import tempfile
import shutil
import re

def clean_filename(filename):
    """Clean filename to remove invalid characters"""
    return re.sub(r'[<>:"/\\|?*]', '', filename)

def split_pdf(input_path, output_folder, splits):
    """
    Split PDF into multiple parts based on page ranges
    
    Args:
        input_path: Path to input PDF
        output_folder: Folder to save split PDFs
        splits: List of tuples containing (pages, output_filename, split_name)
    """
    os.makedirs(output_folder, exist_ok=True)
    
    pdf = PdfReader(input_path)
    total_pages = len(pdf.pages)
    
    # Save the original PDF to the output folder
    original_filename = os.path.basename(input_path)
    original_output_path = os.path.join(output_folder, original_filename)
    shutil.copy2(input_path, original_output_path)
    
    for pages, output_filename, split_name in splits:
        pdf_writer = PdfWriter()
        
        # Convert string of page numbers to list of integers
        try:
            # Handle both ranges (1-3) and individual pages (1,2,3)
            page_list = []
            for part in pages.split(','):
                if '-' in part:
                    start, end = map(int, part.strip().split('-'))
                    page_list.extend(range(start, end + 1))
                else:
                    page_list.append(int(part.strip()))
            
            # Remove duplicates and sort
            page_list = sorted(list(set(page_list)))
            
            # Validate page numbers
            if any(p < 1 or p > total_pages for p in page_list):
                st.error(f"Invalid page numbers in split {split_name}. Pages must be between 1 and {total_pages}")
                continue
            
            # Add selected pages to the new PDF
            for page_num in page_list:
                pdf_writer.add_page(pdf.pages[page_num - 1])
            
            # Use split_name in the filename if provided
            if split_name:
                base_name = clean_filename(split_name)
                output_filename = f"{base_name}_{pages.replace(',', '_').replace('-', 'to')}.pdf"
                
            output_path = os.path.join(output_folder, output_filename)
            with open(output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
                
        except ValueError as e:
            st.error(f"Invalid page range format for split {split_name}. Use format like '1-3,5,7-9'")
            continue

def main():
    st.title("PDF Splitter")
    st.write("Upload a PDF and split it into multiple parts")
    
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name
        
        pdf = PdfReader(tmp_path)
        total_pages = len(pdf.pages)
        
        st.write(f"Total pages in PDF: {total_pages}")
        st.write("Page format: Use comma-separated values and ranges (e.g., '1-3,5,7-9')")
        
        folder_name = os.path.splitext(uploaded_file.name)[0]
        
        st.subheader("Define PDF splits")
        st.write("Enter the page ranges and names for each split:")
        
        if 'num_splits' not in st.session_state:
            st.session_state.num_splits = 1
            
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Add Split"):
                st.session_state.num_splits += 1
        with col2:
            if st.button("Remove Split") and st.session_state.num_splits > 1:
                st.session_state.num_splits -= 1
        
        splits = []
        
        for i in range(st.session_state.num_splits):
            st.write(f"Split {i+1}")
            col1, col2 = st.columns(2)
            
            with col1:
                pages = st.text_input(
                    f"Pages for Split {i+1} (e.g., 1-3,5,7-9)",
                    value="1",
                    key=f"pages_{i}"
                )
            
            with col2:
                split_name = st.text_input(
                    f"Name for Split {i+1}",
                    value=f"Split_{i+1}",
                    key=f"name_{i}"
                )
            
            # Generate output filename (will be modified if split_name is provided)
            output_filename = f"split_{i+1}_{pages}.pdf"
            
            splits.append((pages, output_filename, split_name))
        
        if st.button("Process Splits"):
            try:
                output_folder = os.path.join(os.getcwd(), folder_name)
                
                # Split the PDF
                split_pdf(tmp_path, output_folder, splits)
                
                st.success(f"PDF successfully split! Files saved in folder: {folder_name}")
                
                # Show the files created, including the original
                st.write("Created files:")
                st.write(f"- {uploaded_file.name} (original)")
                for _, _, split_name in splits:
                    st.write(f"- {split_name}.pdf")
                    
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
            
            finally:
                os.unlink(tmp_path)

if __name__ == "__main__":
    main()