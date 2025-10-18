#!/usr/bin/env python3
"""
Step 12: Extract Text from Original PDF
Extracts text from the original.pdf using OCR and prints it to console
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from api.pdf_text_extractor import extract_text_from_pdf, store_text_in_data_json

def run_step12():
    """
    Run Step12 processing - extract text from PDF
    """
    try:
        print("🚀 Step 12: Extracting Text from PDF")
        print("=" * 60)
        
        # Get the current working directory to determine the correct paths
        current_dir = os.getcwd()
        
        # If we're in the processors directory, use relative paths
        if current_dir.endswith('processors'):
            pdf_path = "../files/original.pdf"
        else:
            # If we're in the server directory (when called from pipeline), use direct paths
            pdf_path = "files/original.pdf"
        
        # Check if PDF exists
        if not os.path.exists(pdf_path):
            print(f"❌ Error: {pdf_path} not found")
            print("   Please ensure the PDF has been downloaded")
            return False
        
        print(f"📄 Processing PDF: {pdf_path}")
        
        # Extract text from the PDF
        extracted_text = extract_text_from_pdf(pdf_path)
        
        if extracted_text:
            print("\n" + "=" * 60)
            print("📝 EXTRACTED TEXT FROM PDF")
            print("=" * 60)
            print(extracted_text)
            print("=" * 60)
            
            # Store the extracted text in data.json
            print("\n💾 Storing extracted text in data.json...")
            store_text_in_data_json(extracted_text, pdf_path)
            
            print(f"\n✅ Step12 completed successfully")
            print(f"   - Characters extracted: {len(extracted_text)}")
            return True
        else:
            print("\n⚠️  No text was extracted from the PDF")
            print("   This might be a scanned document with poor quality or no text content")
            # Still return True as this is not a critical failure
            return True
        
    except Exception as e:
        print(f"❌ Error in Step 12: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function for standalone execution"""
    return run_step12()

if __name__ == "__main__":
    # Change to the server directory to ensure proper file paths
    server_dir = Path(__file__).parent.parent
    os.chdir(server_dir)
    
    success = main()
    sys.exit(0 if success else 1)

