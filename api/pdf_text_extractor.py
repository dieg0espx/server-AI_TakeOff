import os
import json
import datetime
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from pdf2image import convert_from_path
import pytesseract

def extract_text_from_pdf(pdf_path: str = None) -> str:
    """
    Extract text from a PDF file using OCR, print it to console, and store in data.json
    
    Args:
        pdf_path (str): Path to the PDF file. If None, uses 'files/original.pdf'
    
    Returns:
        str: Extracted text from the PDF
    """
    global extracted_text
    
    # Default to the original.pdf file if no path provided
    if pdf_path is None:
        pdf_path = os.path.join('files', 'original.pdf')
    
    # Check if file exists
    if not os.path.exists(pdf_path):
        
        print(f"❌ PDF file not found: {pdf_path}", "error")
        return ""
    
    try:
        
        print(f"📄 Extracting text from: {pdf_path}")
        
        # Convert PDF to images
        print("🔄 Converting PDF to images for OCR processing...")
        images = convert_from_path(pdf_path)
        
        print(f"📊 PDF has {len(images)} pages")
        extracted_text = ""
        
        # Extract text from each page using OCR
        for i, image in enumerate(images):
            print(f"📖 Processing page {i + 1}/{len(images)} with OCR...")
            
            # Extract text from image using pytesseract
            text = pytesseract.image_to_string(image)
            
            if text.strip():
                print(f"📄 Page {i + 1} extracted text:")
                print("-" * 50)
                print(text)
                print("-" * 50)
                extracted_text += f"\n--- Page {i + 1} ---\n{text}\n"
            else:
                print(f"⚠️  Page {i + 1} appears to be empty or contains no extractable text", "warning")
        
        # Print summary
        total_chars = len(extracted_text)
        print(f"\n📊 OCR Text extraction summary:")
        print(f"   - Total pages: {len(images)}")
        print(f"   - Total characters extracted: {total_chars}")
        print(f"   - File size: {os.path.getsize(pdf_path)} bytes")
        
        if total_chars == 0:
            print("⚠️  No text was extracted. This might be a scanned document with poor quality.", "warning")
        
        # Store the extracted text in data.json
        if extracted_text:
            print("💾 Storing extracted text in data.json...")
            store_text_in_data_json(extracted_text, pdf_path)
        
        return extracted_text
        
    except Exception as e:
        
        print(f"❌ Error extracting text from PDF: {str(e)}", "error")
        return ""

def store_text_in_data_json(extracted_text: str, pdf_path: str):
    """
    Store the extracted text in data.json file
    
    Args:
        extracted_text (str): The text extracted from the PDF
        pdf_path (str): Path to the original PDF file
    """
    try:
        # Read existing data.json if it exists
        if os.path.exists('data.json'):
            with open('data.json', 'r') as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    data = {}
        else:
            data = {}
        
        # Update the data with only the extracted text
        data['extracted_text'] = extracted_text
        
        # Write updated data back to data.json
        with open('data.json', 'w') as file:
            json.dump(data, file, indent=4)
        
        
        print(f"✅ Extracted text successfully stored in data.json")
        print(f"   - Text length: {len(extracted_text)} characters")
        print(f"   - PDF file: {pdf_path}")
        
    except Exception as e:
        
        print(f"❌ Error storing text in data.json: {str(e)}", "error")

def main():
    """Main function to run text extraction"""
    
    print("🔍 PDF Text Extractor (OCR)")
    print("=" * 50)
    
    # Extract text from the original.pdf file
    text = extract_text_from_pdf()
    
    if text:
        print("\n✅ OCR text extraction completed successfully!")
    else:
        print("\n❌ OCR text extraction failed or no text found.", "error")

if __name__ == "__main__":
    main()
