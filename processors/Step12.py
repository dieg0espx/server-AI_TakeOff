#!/usr/bin/env python3
"""
Step 12: Extract Text from Original PDF and Rewrite Professionally
Extracts text from the original.pdf using OCR and uses OpenAI to rewrite it professionally
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import requests

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
            return extracted_text
        
        print("\n🤖 Rewriting text with OpenAI API...")
        
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Create the prompt for professional rewriting
        prompt = f"""You are a professional technical writer specializing in construction and scaffolding documentation.

The following text was extracted using OCR from a scaffolding construction drawing. It contains technical specifications, measurements, and construction notes.

Please rewrite this text in a clear, professional, and well-organized manner suitable for scaffolding construction documentation. Organize the information logically, correct any OCR errors, standardize measurements and terminology, and present it in a professional format.

Original OCR Text:
{extracted_text}

Please provide a professionally written version:"""

        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional technical writer specializing in construction and scaffolding documentation. You rewrite OCR-extracted text from scaffolding drawings into clear, professional, and well-organized documentation."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        # Extract the rewritten text
        rewritten_text = response.choices[0].message.content.strip()
        
        print("✅ Text successfully rewritten by OpenAI")
        return rewritten_text
        
    except ImportError:
        print("⚠️  OpenAI package not installed. Run: pip install openai")
        return extracted_text
    except Exception as e:
        print(f"⚠️  Error calling OpenAI API: {e}")
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


def cleanup_result_files():
    """Delete all step result files from the files folder"""
    try:
        print(f"\n🧹 Cleaning up result files...")
        
        # Get the current working directory to determine the correct paths
        current_dir = os.getcwd()
        
        # If we're in the processors directory, use relative paths
        if current_dir.endswith('processors'):
            files_dir = "../files"
        else:
            files_dir = "files"
        
        # Determine the root directory (parent of files folder)
        if current_dir.endswith('processors'):
            root_dir = ".."
        else:
            root_dir = "."
        
        # List of files to delete
        files_to_delete = [
            # Step SVG files
            f"{files_dir}/Step1.svg",
            f"{files_dir}/Step2.svg",
            f"{files_dir}/Step3.svg",
            f"{files_dir}/Step4.svg",
            f"{files_dir}/Step5.svg",
            f"{files_dir}/Step6.svg",
            f"{files_dir}/Step7.svg",
            f"{files_dir}/Step8.svg",
            f"{files_dir}/Step9.svg",
            f"{files_dir}/step10.svg",
            # Result PNG files
            f"{files_dir}/Step4-results.png",
            f"{files_dir}/Step5-results.png",
            f"{files_dir}/Step6-results.png",
            f"{files_dir}/Step7-results.png",
            f"{files_dir}/Step8-results.png",
            f"{files_dir}/Step9-results.png",
            f"{files_dir}/Step10-results.png",
            # JSON result files
            f"{root_dir}/greenFrames.json",
            f"{root_dir}/pinkFrames.json",
            f"{root_dir}/x-shores.json",
            f"{root_dir}/square-shores.json",
            f"{root_dir}/orangeFrames.json",
        ]
        
        deleted_count = 0
        for file_path in files_to_delete:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    print(f"   ✅ Deleted: {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"   ⚠️  Could not delete {os.path.basename(file_path)}: {e}")
        
        print(f"\n✅ Cleaned up {deleted_count} result files")
        return True
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        return False

def validate_and_prepare_data(data):
    """Validate and prepare data with required fields"""
    # Ensure all required fields are present
    if 'company' not in data or not data['company']:
        data['company'] = 'Unknown Company'
    
    if 'jobsite' not in data or not data['jobsite']:
        data['jobsite'] = 'Unknown Jobsite'
    
    # Ensure step_results exists
    if 'step_results' not in data:
        data['step_results'] = {}
    
    # Ensure cloudinary_urls exists
    if 'cloudinary_urls' not in data:
        data['cloudinary_urls'] = {}
    
    # Ensure upload_id exists
    if 'upload_id' not in data:
        data['upload_id'] = 'unknown'
    
    # Add text field from rewritten_text (for database storage)
    if 'rewritten_text' in data and data['rewritten_text']:
        data['text'] = data['rewritten_text']
    elif 'extracted_text' in data and data['extracted_text']:
        # Fallback to extracted_text if rewritten_text is not available
        data['text'] = data['extracted_text']
    else:
        data['text'] = ''
    
    return data

def send_to_api(data, api_url):
    """Send data to PHP API endpoint"""
    try:
        # Validate and prepare data
        data = validate_and_prepare_data(data)
        
        print(f"\n📤 Sending data to API: {api_url}")
        print(f"📋 Data summary:")
        print(f"   - Company: {data.get('company')}")
        print(f"   - Jobsite: {data.get('jobsite')}")
        print(f"   - Upload ID: {data.get('upload_id')}")
        print(f"   - Step results: {len(data.get('step_results', {}))} items")
        print(f"   - Cloudinary URLs: {len(data.get('cloudinary_urls', {}))} items")
        print(f"   - Text (for DB): {len(data.get('text', ''))} characters")
        
        # Send POST request
        response = requests.post(
            api_url,
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        # Check response
        if response.status_code in [200, 201]:
            result = response.json()
            if result.get('success'):
                print(f"✅ Data successfully sent to API!")
                print(f"   Database Record ID: {result.get('id')}")
                
                # Display tracking URL
                tracking_url = result.get('tracking_url')
                if tracking_url:
                    # Extract base URL from API endpoint
                    api_base = api_url.replace('/create.php', '')
                    full_tracking_url = f"{api_base}/read.php?tracking_url={tracking_url}"
                    
                    print(f"\n🔗 TRACKING URL:")
                    print(f"   {full_tracking_url}")
                    print(f"\n   Share this URL to view the results!")
                
                return True, tracking_url
            else:
                print(f"❌ API returned error: {result.get('error')}")
                if 'errors' in result:
                    for error in result['errors']:
                        print(f"   - {error}")
                return False, None
        else:
            print(f"❌ API request failed with status code: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
                if 'errors' in error_data:
                    print("   Validation errors:")
                    if isinstance(error_data['errors'], list):
                        for error in error_data['errors']:
                            print(f"   - {error}")
                    else:
                        print(f"   - {error_data['errors']}")
            except json.JSONDecodeError:
                print(f"   Response (not JSON): {response.text[:500]}")
            except Exception as e:
                print(f"   Could not parse error response: {e}")
            return False, None
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out after 30 seconds")
        return False, None
    except requests.exceptions.ConnectionError:
        print("❌ Connection error - could not reach the API")
        return False, None
    except Exception as e:
        print(f"❌ Error sending data to API: {e}")
        return False, None

def run_step12():
    """
    Run Step12 processing - extract text from PDF and rewrite professionally
    """
    try:
        print("🚀 Step 12: Extracting and Rewriting Text from PDF")
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
            
            # Send data to API
            try:
                # Get API URL from environment or use default
                API_URL = os.environ.get('API_URL', 'https://ttfconstruction.com/ai-takeoff-results/create.php')
                
                # Load data.json to send to API
                data_file = "data.json" if not current_dir.endswith('processors') else "../data.json"
                if os.path.exists(data_file):
                    with open(data_file, 'r') as f:
                        data = json.load(f)
                    
                    # Send to API
                    success, tracking_url = send_to_api(data, API_URL)
                    
                    if success and tracking_url:
                        # Save tracking URL to data.json
                        data['tracking_url'] = tracking_url
                        with open(data_file, 'w') as f:
                            json.dump(data, f, indent=4)
                        
                        # Display final tracking URL prominently
                        api_base = API_URL.replace('/create.php', '')
                        full_tracking_url = f"{api_base}/read.php?tracking_url={tracking_url}"
                        
                        print("\n" + "=" * 70)
                        print("🔗 RESULTS URL (Share this link to view the results)")
                        print("=" * 70)
                        print(f"\n{full_tracking_url}\n")
                        print("=" * 70)
                    else:
                        print("\n⚠️  Failed to send results to API")
                        print("   Data is still available in data.json")
                else:
                    print("\n⚠️  data.json not found - cannot send to API")
                    
            except Exception as e:
                print(f"\n⚠️  Error sending to API: {e}")
            
            # Clean up result files after successful processing and API send
            cleanup_result_files()
            
            print(f"\n✅ Step12 completed successfully")
            print(f"   - Original text: {len(extracted_text)} characters")
            print(f"   - Rewritten text: {len(rewritten_text)} characters")
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

