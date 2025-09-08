import os
import asyncio
import requests
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from typing import Optional
import json
from pydantic import BaseModel

# Load environment variables
load_dotenv()

app = FastAPI(title="PDF to SVG Converter", description="Convert PDF files to SVG format using Convertio API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
CONVERTIO_API_KEY = os.getenv('CONVERTIO_API_KEY')
CONVERTIO_BASE_URL = "https://api.convertio.co/convert"

class ConvertioConverter:
    def __init__(self, api_key: str = None):
        if not api_key:
            api_key = CONVERTIO_API_KEY
        if not api_key:
            raise ValueError("CONVERTIO_API_KEY environment variable is required")
        self.api_key = api_key
        self.base_url = CONVERTIO_BASE_URL
    
    async def start_conversion(self) -> str:
        """Start a new conversion job"""
        data = {
            "apikey": self.api_key,
            "input": "upload",
            "outputformat": "svg"
        }
        
        response = requests.post(self.base_url, json=data)
        result = response.json()
        
        if result.get('code') == 200:
            return result['data']['id']
        else:
            raise Exception(f"Error starting conversion: {result.get('error')}")
    
    async def upload_file(self, conv_id: str, file_path: str) -> None:
        """Upload file to the conversion job"""
        upload_url = f"{self.base_url}/{conv_id}/upload"
        
        with open(file_path, 'rb') as file:
            response = requests.put(upload_url, data=file)
            result = response.json()
            
            if result.get('code') != 200:
                raise Exception(f"File upload failed: {result.get('error')}")
    
    async def check_status(self, conv_id: str) -> str:
        """Check conversion status and return download URL when complete"""
        status_url = f"{self.base_url}/{conv_id}/status"
        
        while True:
            response = requests.get(status_url)
            result = response.json()
            
            if 'data' in result:
                status = result['data'].get('step')
                
                if status == "finish" and result['data'].get('output'):
                    return result['data']['output']['url']
                elif status in ["failed", "error"]:
                    raise Exception("Conversion failed")
            
            await asyncio.sleep(5)
    
    async def download_file(self, download_url: str, output_path: str) -> None:
        """Download the converted file"""
        response = requests.get(download_url)
        
        with open(output_path, 'wb') as file:
            file.write(response.content)

# Initialize converter
converter = ConvertioConverter(CONVERTIO_API_KEY)

# Import the Google Drive downloader
from gdrive_pdf_downloader import download_pdf_from_drive

class FileConversionRequest(BaseModel):
    file_id: str

@app.post("/convert-pdf-to-svg")
async def convert_pdf_to_svg(file_path: str, background_tasks: BackgroundTasks):
    """
    Convert a PDF file to SVG format using Convertio API
    
    Args:
        file_path: Path to the PDF file to convert
        background_tasks: FastAPI background tasks
    
    Returns:
        JSON response with conversion status and file path
    """
    try:
        # Validate file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="PDF file not found")
        
        # Validate file is a PDF
        if not file_path.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        # Generate output path - store in files folder as original.svg
        output_path = os.path.join('files', 'original.svg')
        
        # Start conversion process
        conv_id = await converter.start_conversion()
        
        # Upload the file
        await converter.upload_file(conv_id, file_path)
        
        # Wait for conversion to complete
        download_url = await converter.check_status(conv_id)
        
        # Download the converted file
        await converter.download_file(download_url, output_path)
        
        # Return success response
        return JSONResponse(content={
            "status": "success",
            "message": "PDF successfully converted to SVG",
            "original_file": file_path,
            "converted_file": output_path,
            "file_size": os.path.getsize(output_path) if os.path.exists(output_path) else 0
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")

@app.post("/convert-drive-pdf-to-svg")
async def convert_drive_pdf_to_svg(request: FileConversionRequest, background_tasks: BackgroundTasks):
    """
    Complete pipeline: Download PDF from Google Drive and convert to SVG
    
    Args:
        request: FileConversionRequest containing the Google Drive file ID
        background_tasks: FastAPI background tasks
    
    Returns:
        JSON response with conversion status and file paths
    """
    try:
        # Step 1: Download PDF from Google Drive
        
        print(f"Downloading PDF from Google Drive with file ID: {request.file_id}")
        pdf_path = download_pdf_from_drive(file_id=request.file_id, output_folder="files")
        
        # Step 2: Convert PDF to SVG
        print(f"Converting PDF to SVG: {pdf_path}")
        output_path = os.path.join('files', 'original.svg')
        
        # Start conversion process
        conv_id = await converter.start_conversion()
        
        # Upload the file
        await converter.upload_file(conv_id, pdf_path)
        
        # Wait for conversion to complete
        download_url = await converter.check_status(conv_id)
        
        # Download the converted file
        await converter.download_file(download_url, output_path)
        
        # Return success response
        return JSONResponse(content={
            "status": "success",
            "message": "PDF successfully downloaded from Google Drive and converted to SVG",
            "file_id": request.file_id,
            "downloaded_pdf": pdf_path,
            "converted_svg": output_path,
            "svg_file_size": os.path.getsize(output_path) if os.path.exists(output_path) else 0
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")

@app.get("/convert-status/{conv_id}")
async def get_conversion_status(conv_id: str):
    """
    Check the status of a conversion job
    
    Args:
        conv_id: Conversion ID from Convertio
    
    Returns:
        JSON response with current status
    """
    try:
        status_url = f"{CONVERTIO_BASE_URL}/{conv_id}/status"
        response = requests.get(status_url)
        result = response.json()
        
        return JSONResponse(content=result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "PDF to SVG Converter"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
