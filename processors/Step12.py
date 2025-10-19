#!/usr/bin/env python3
"""
Step 12: Send Results to API and Cleanup
Sends processing results to the database and cleans up temporary files
"""

import os
import sys
import json
from pathlib import Path
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def load_data_json(file_path='data.json'):
    """Load data from data.json file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: {file_path} not found")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in {file_path}: {e}")
        return None
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return None

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
    
    # Add text field from rewritten_text ONLY (for database storage)
    if 'rewritten_text' in data and data['rewritten_text']:
        data['text'] = data['rewritten_text']
        print(f"   ✅ Using rewritten_text for database ({len(data['text'])} chars)")
    else:
        # Only use rewritten text, not the raw extracted text
        data['text'] = ''
        print(f"   ⚠️  No rewritten_text found - text field will be empty")
    
    # Verify we're not accidentally using extracted_text
    if 'extracted_text' in data and 'rewritten_text' in data:
        if data['extracted_text'] == data['rewritten_text']:
            print(f"   ⚠️  WARNING: extracted_text and rewritten_text are identical!")
            print(f"   This means OpenAI did not properly rewrite the text in Step 11")
    
    return data

def send_to_api(data, api_url):
    """Send data to PHP API endpoint"""
    try:
        # Validate and prepare data
        data = validate_and_prepare_data(data)
        
        print(f"📤 Sending data to API: {api_url}")
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
                
                if 'data' in result:
                    data_info = result['data']
                    print(f"\n   Project Information:")
                    print(f"   - Company: {data_info.get('company')}")
                    print(f"   - Jobsite: {data_info.get('jobsite')}")
                    print(f"\n   Stored counts:")
                    print(f"   - Blue X Shapes: {data_info.get('blue_x_shapes')}")
                    print(f"   - Red Squares: {data_info.get('red_squares')}")
                    print(f"   - Pink Shapes: {data_info.get('pink_shapes')}")
                    print(f"   - Green Rectangles: {data_info.get('green_rectangles')}")
                    print(f"   - Orange Rectangles: {data_info.get('orange_rectangles')}")
                    print(f"   - Total Detections: {data_info.get('total_detections')}")
                
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
        print("   Please verify:")
        print("   - The API URL is correct")
        print("   - The server is running")
        print("   - You have internet connectivity")
        return False, None
    except Exception as e:
        print(f"❌ Error sending data to API: {e}")
        return False, None

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

def run_step12():
    """
    Run Step12 processing - send results to API and cleanup
    """
    try:
        print("🚀 Step 12: Sending Results to API and Cleanup")
        print("=" * 70)
        
        # API endpoint URL - get from environment or use default
        API_URL = os.environ.get('API_URL', 'https://ttfconstruction.com/ai-takeoff-results/create.php')
        
        # Get the current working directory to determine the correct paths
        current_dir = os.getcwd()
        
        # If we're in the processors directory, use relative paths
        if current_dir.endswith('processors'):
            data_file = "../data.json"
        else:
            # If we're in the server directory (when called from pipeline), use direct paths
            data_file = "data.json"
        
        # Check if data.json exists
        if not os.path.exists(data_file):
            print(f"❌ Error: {data_file} not found")
            print("   Please run the processing pipeline first to generate data.json")
            return False
        
        # Load data.json
        print(f"📄 Loading {data_file}...")
        data = load_data_json(data_file)
        if not data:
            return False
        
        print("✅ data.json loaded successfully")
        
        # Display data summary
        if 'step_results' in data:
            step_results = data['step_results']
            print("\n📊 Data to be sent:")
            print(f"   - Blue X Shapes: {step_results.get('step5_blue_X_shapes', 0)}")
            print(f"   - Red Squares: {step_results.get('step6_red_squares', 0)}")
            print(f"   - Pink Shapes: {step_results.get('step7_pink_shapes', 0)}")
            print(f"   - Green Rectangles: {step_results.get('step8_green_rectangles', 0)}")
            print(f"   - Orange Rectangles: {step_results.get('step9_orange_rectangles', 0)}")
        
        if 'cloudinary_urls' in data:
            cloudinary_urls = data['cloudinary_urls']
            print(f"\n☁️  Cloudinary URLs: {len(cloudinary_urls)} images")
        
        if 'rewritten_text' in data:
            print(f"\n📝 Rewritten text: {len(data['rewritten_text'])} characters")
        
        # Send to API
        print(f"\n📡 API Endpoint: {API_URL}")
        success, tracking_url = send_to_api(data, API_URL)
        
        if success:
            print("\n🎉 Results successfully sent to API and stored in database!")
            
            # Save tracking URL to data.json for later retrieval
            if tracking_url:
                try:
                    data['tracking_url'] = tracking_url
                    with open(data_file, 'w') as f:
                        json.dump(data, f, indent=4)
                    print(f"✅ Tracking URL saved to {data_file}")
                except Exception as e:
                    print(f"⚠️  Could not save tracking URL to data.json: {e}")
            
            # Clean up result files after successful storage
            cleanup_result_files()
            
            # Display final tracking URL prominently
            if tracking_url:
                api_base = API_URL.replace('/create.php', '')
                full_tracking_url = f"{api_base}/read.php?tracking_url={tracking_url}"
                
                print("\n" + "=" * 70)
                print("🔗 RESULTS URL (Share this link to view the results)")
                print("=" * 70)
                print(f"\n{full_tracking_url}\n")
                print("=" * 70)
            
            return True
        else:
            print("\n⚠️  Failed to send results to API")
            print("   The pipeline completed successfully, but results were not stored in the database")
            print("   Result files were NOT deleted (to allow retry)")
            return False
        
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
