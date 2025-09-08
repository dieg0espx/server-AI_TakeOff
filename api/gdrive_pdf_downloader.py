import requests
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from typing import Optional

# Global variable to store upload_id (will be set from main.py)
global_upload_id = None

def set_global_upload_id(upload_id: str):
    """Set the global upload_id variable"""
    global global_upload_id
    global_upload_id = upload_id
    
    print(f"📝 Global upload_id set to: {global_upload_id}")

def get_global_upload_id() -> Optional[str]:
    """Get the current global upload_id"""
    global global_upload_id
    return global_upload_id

def download_pdf_from_drive(file_id: str = None, output_folder: str = "files") -> str:
    """
    Download a PDF file from Google Drive and save it as original.pdf
    
    Args:
        file_id (str): The Google Drive file ID (if None, uses global_upload_id)
        output_folder (str): The folder to save the file in (default: "files")
    
    Returns:
        str: Path to the downloaded file
    
    Raises:
        Exception: If download fails or file is not accessible
    """
    # Use global_upload_id if file_id is not provided
    if file_id is None:
        file_id = get_global_upload_id()
        if file_id is None:
            raise Exception("No file_id provided and no global upload_id set")
        
        print(f"Using global upload_id: {file_id}")
    
    # Google Drive download URL template
    GOOGLE_DRIVE_DOWNLOAD_URL = "https://drive.google.com/uc?export=download&id="
    
    try:
        
        print(f"Attempting to download file with ID: {file_id}")
        
        # Create output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        
        # Construct download URL
        download_url = f"{GOOGLE_DRIVE_DOWNLOAD_URL}{file_id}"
        print(f"Download URL: {download_url}")
        
        # Use a session to handle cookies and redirects
        session = requests.Session()
        response = session.get(download_url, allow_redirects=True)
        
        print(f"Response status code: {response.status_code}")
        
        if response.status_code != 200:
            raise Exception(f"File not found or not accessible. Status code: {response.status_code}")

        # Check if we got a PDF file
        content_type = response.headers.get('content-type', '')
        if 'application/pdf' not in content_type and 'application/octet-stream' not in content_type:
            print(f"Warning: Unexpected content type: {content_type}", "warning")

        # Save the file as original.pdf
        file_path = os.path.join(output_folder, "original.pdf")
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        print(f"File saved to: {file_path}")
        print(f"File size: {os.path.getsize(file_path)} bytes")
        
        return file_path

    except requests.exceptions.RequestException as e:
        
        print(f"Request error: {str(e)}", "error")
        raise Exception(f"Download failed: {str(e)}")
    except Exception as e:
        
        print(f"Unexpected error: {str(e)}", "error")
        raise Exception(str(e))

def download_with_global_id(output_folder: str = "files") -> str:
    """
    Download PDF using the global upload_id
    
    Args:
        output_folder (str): The folder to save the file in (default: "files")
    
    Returns:
        str: Path to the downloaded file
    """
    return download_pdf_from_drive(file_id=None, output_folder=output_folder)

def main():
    """
    Example usage of the download function
    """
    # Example file IDs from your reference code
    file_ids = [
        "1q-2eMWfbQx8ZlE_8EJFt-X_RTRmwfDVW",
        "1mApCM33bj2t4pg5mV-8u3FOWEPnr6hE6"
    ]
    
    # You can test with either file ID
    test_file_id = file_ids[0]  # Change this to test different files
    
    try:
        # Set global upload_id for testing
        set_global_upload_id(test_file_id)
        
        # Download using global ID
        file_path = download_with_global_id()
        
        print(f"Successfully downloaded PDF to: {file_path}")
        
        # Or download with specific file_id
        # file_path = download_pdf_from_drive(test_file_id)
        # print(f"Successfully downloaded PDF to: {file_path}")
        
    except Exception as e:
        
        print(f"Error downloading file: {e}", "error")

if __name__ == "__main__":
    main()