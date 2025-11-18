#!/usr/bin/env python3
"""
Step 11: Extract Text from Original PDF and Rewrite Professionally
Extracts text from the original.pdf using OCR and uses OpenAI to rewrite it professionally
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from api.pdf_text_extractor import extract_text_from_pdf

def rewrite_text_with_openai(extracted_text: str) -> str:
    """
    Use OpenAI API to rewrite the extracted text professionally for scaffolding drawings
    
    Args:
        extracted_text: Raw OCR text from the PDF
        
    Returns:
        Professionally rewritten text or original text if API call fails
    """
    try:
        from openai import OpenAI
        
        # Get API key from environment
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("⚠️  OPENAI_API_KEY not found in environment variables")
            print("   Skipping OpenAI rewriting, using extracted text as-is")
            return extracted_text
        
        print("\n🤖 Rewriting text with OpenAI API...")
        
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Create the prompt for professional rewriting
        prompt = f"""You are a professional construction documentation specialist. The text below was extracted from a scaffolding/shoring construction drawing using OCR and contains many errors, inconsistent formatting, and poor readability.

Your task: Rewrite this into a clean, professional, well-structured document that:
1. Fixes all OCR errors and typos
2. Organizes information into clear sections with headers
3. Standardizes measurements and technical terms
4. Removes gibberish and maintains only meaningful content
5. Uses proper construction industry terminology
6. Formats lists, specifications, and notes properly
7. Makes it easy to read and professional

RAW OCR TEXT:
{extracted_text}

REWRITTEN PROFESSIONAL VERSION:"""

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "You are an expert construction technical writer. You transform messy OCR text from construction drawings into clear, professional documentation. Always rewrite and restructure the content - never return the original text unchanged."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,  # Slightly higher for more creative rewriting
            max_tokens=3000   # Increased to allow for more detailed output
        )
        
        # Extract the rewritten text
        rewritten_text = response.choices[0].message.content.strip()
        
        # Validate that OpenAI actually rewrote the text (not just returned the same)
        if rewritten_text == extracted_text or len(rewritten_text) < 50:
            print("⚠️  OpenAI returned text that appears unchanged or too short")
            print("   Using extracted text as fallback")
            return extracted_text
        
        print("✅ Text successfully rewritten by OpenAI")
        print(f"   Original length: {len(extracted_text)} chars")
        print(f"   Rewritten length: {len(rewritten_text)} chars")
        return rewritten_text
        
    except ImportError:
        print("⚠️  OpenAI package not installed. Run: pip install openai")
        print("   Using extracted text as-is")
        return extracted_text
    except Exception as e:
        print(f"⚠️  Error calling OpenAI API: {e}")
        print("   Using extracted text as fallback")
        import traceback
        traceback.print_exc()
        return extracted_text

def store_text_in_data_json(extracted_text: str, rewritten_text: str, pdf_path: str):
    """
    Store both the extracted text and rewritten text in data.json file
    
    Args:
        extracted_text: Raw OCR text from the PDF
        rewritten_text: Professionally rewritten text from OpenAI
        pdf_path: Path to the original PDF file
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
        
        # Update the data with both texts
        data['extracted_text'] = extracted_text
        data['rewritten_text'] = rewritten_text
        
        # Write updated data back to data.json
        with open('data.json', 'w') as file:
            json.dump(data, file, indent=4)
        
        print(f"✅ Extracted and rewritten text successfully stored in data.json")
        print(f"   - Original text length: {len(extracted_text)} characters")
        print(f"   - Rewritten text length: {len(rewritten_text)} characters")
        print(f"   - PDF file: {pdf_path}")
        
    except Exception as e:
        print(f"❌ Error storing text in data.json: {str(e)}")

def run_step11():
    """
    Run Step11 processing - extract text from PDF and rewrite professionally
    """
    try:
        print("🚀 Step 11: Extracting and Rewriting Text from PDF")
        print("=" * 70)
        
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
            print("\n" + "=" * 70)
            print("📝 ORIGINAL EXTRACTED TEXT (OCR)")
            print("=" * 70)
            print(extracted_text)
            print("=" * 70)
            
            # Rewrite text with OpenAI
            rewritten_text = rewrite_text_with_openai(extracted_text)
            
            print("\n" + "=" * 70)
            print("✨ PROFESSIONALLY REWRITTEN TEXT (OpenAI)")
            print("=" * 70)
            print(rewritten_text)
            print("=" * 70)
            
            # Store both texts in data.json
            print("\n💾 Storing extracted and rewritten text in data.json...")
            store_text_in_data_json(extracted_text, rewritten_text, pdf_path)
            
            print(f"\n✅ Step11 completed successfully")
            print(f"   - Original text: {len(extracted_text)} characters")
            print(f"   - Rewritten text: {len(rewritten_text)} characters")
            return True
        else:
            print("\n⚠️  No text was extracted from the PDF")
            print("   This might be a scanned document with poor quality or no text content")
            # Still return True as this is not a critical failure
            return True
        
    except Exception as e:
        print(f"❌ Error in Step 11: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function for standalone execution"""
    return run_step11()

if __name__ == "__main__":
    # Change to the server directory to ensure proper file paths
    server_dir = Path(__file__).parent.parent
    os.chdir(server_dir)
    
    success = main()
    sys.exit(0 if success else 1)

