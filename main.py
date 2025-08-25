# source venv/bin/activate
# uvicorn main:app --host 0.0.0.0 --port 5001 --reload

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sys
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the api directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'api'))

# Import the PDF downloader and config manager
from gdrive_pdf_downloader import download_pdf_from_drive
from utils.config_manager import config_manager

# Import the PDF to SVG converter
from pdf_to_svg_converter import ConvertioConverter

# Import the processing pipeline
from processors.index import main as run_pipeline

# Create FastAPI instance
app = FastAPI(
    title="AI-Takeoff Server",
    description="AI-Takeoff API server",
    version="1.0.0"
)

# Initialize the PDF to SVG converter
try:
    converter = ConvertioConverter()
    print("✅ PDF to SVG converter initialized successfully")
except ValueError as e:
    print(f"⚠️  Warning: {e}. SVG conversion will not work.")
    converter = None

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "AI-Takeoff Server is running!", "status": "running"}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}

# AI-Takeoff specific endpoint
@app.get("/AI-Takeoff/{upload_id}")
async def get_ai_takeoff_result(upload_id: str, background_tasks: BackgroundTasks = None):
    # Store the Google Drive file ID in JSON as google_drive_file_id
    config_manager.set_file_id(upload_id)
    
    print(f"🔍 AI-Takeoff Request for upload_id: {upload_id}")
    print(f"📝 Stored Google Drive file ID in JSON as google_drive_file_id: {upload_id}")
    
    # Start background processing
    if background_tasks:
        background_tasks.add_task(process_ai_takeoff, upload_id)
        
        return {
            "id": upload_id,
            "status": "processing",
            "message": "AI-Takeoff processing started."
        }
    else:
        # Fallback to synchronous processing
        return await process_ai_takeoff_sync(upload_id)

async def process_ai_takeoff(upload_id: str):
    """Process AI-Takeoff request"""
    try:
        print(f"📄 Starting PDF download for upload_id: {upload_id}")
        
        # Step 1: Download the PDF
        file_path = download_pdf_from_drive(upload_id)
        print(f"📄 PDF downloaded successfully to: {file_path}")
        
        # Step 2: Convert PDF to SVG
        if converter:
            print(f"🔄 Starting PDF to SVG conversion...")
            try:
                # Start conversion process
                conv_id = await converter.start_conversion()
                print(f"🔄 Conversion started with ID: {conv_id}")
                
                # Upload the file
                await converter.upload_file(conv_id, file_path)
                print(f"📤 PDF uploaded to conversion service")
                
                # Wait for conversion to complete
                download_url = await converter.check_status(conv_id)
                print(f"✅ Conversion completed, downloading SVG...")
                
                # Download the converted file
                svg_path = os.path.join('files', 'original.svg')
                await converter.download_file(download_url, svg_path)
                print(f"✅ SVG saved to: {svg_path}")
                
                # Get file sizes
                pdf_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                svg_size = os.path.getsize(svg_path) if os.path.exists(svg_path) else 0
                
                print(f"📊 File sizes - PDF: {pdf_size} bytes, SVG: {svg_size} bytes")
                
                # Start the processing pipeline
                print(f"🚀 Starting AI processing pipeline...")
                try:
                    pipeline_success = run_pipeline()
                    if pipeline_success:
                        print(f"✅ Processing pipeline completed successfully")
                    else:
                        print(f"⚠️  Processing pipeline completed with some failures")
                except Exception as pipeline_error:
                    print(f"❌ Error in processing pipeline: {pipeline_error}")
                
            except Exception as conversion_error:
                print(f"❌ Error in SVG conversion: {conversion_error}")
        else:
            print("⚠️  Skipping SVG conversion - CONVERTIO_API_KEY not set")
        
        print(f"✅ AI-Takeoff processing completed for upload_id: {upload_id}")
        
    except Exception as e:
        print(f"❌ Error in AI-Takeoff processing: {e}")

async def process_ai_takeoff_sync(upload_id: str):
    """Synchronous processing"""
    try:
        print(f"📄 Starting PDF download for upload_id: {upload_id}")
        
        # Step 1: Download the PDF
        file_path = download_pdf_from_drive(upload_id)
        print(f"📄 PDF downloaded successfully to: {file_path}")
        
        # Step 2: Convert PDF to SVG
        svg_path = None
        svg_size = None
        
        if converter:
            print(f"🔄 Starting PDF to SVG conversion...")
            try:
                # Start conversion process
                conv_id = await converter.start_conversion()
                print(f"🔄 Conversion started with ID: {conv_id}")
                
                # Upload the file
                await converter.upload_file(conv_id, file_path)
                print(f"📤 PDF uploaded to conversion service")
                
                # Wait for conversion to complete
                download_url = await converter.check_status(conv_id)
                print(f"✅ Conversion completed, downloading SVG...")
                
                # Download the converted file
                svg_path = os.path.join('files', 'original.svg')
                await converter.download_file(download_url, svg_path)
                print(f"✅ SVG saved to: {svg_path}")
                
                svg_size = os.path.getsize(svg_path) if os.path.exists(svg_path) else 0
                
                # Start the processing pipeline
                print(f"🚀 Starting AI processing pipeline...")
                try:
                    pipeline_success = run_pipeline()
                    if pipeline_success:
                        print(f"✅ Processing pipeline completed successfully")
                    else:
                        print(f"⚠️  Processing pipeline completed with some failures")
                except Exception as pipeline_error:
                    print(f"❌ Error in processing pipeline: {pipeline_error}")
                
            except Exception as conversion_error:
                print(f"❌ Error in SVG conversion: {conversion_error}")
        else:
            print("⚠️  Skipping SVG conversion - CONVERTIO_API_KEY not set")
        
        # Get file sizes
        pdf_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        
        result = {
            "id": upload_id,
            "status": "completed",
            "pdf_path": file_path,
            "pdf_size": pdf_size,
            "svg_path": svg_path,
            "svg_size": svg_size,
            "message": "PDF downloaded and converted to SVG successfully"
        }
        
    except Exception as e:
        print(f"❌ Error downloading PDF: {e}")
        
        result = {
            "id": upload_id,
            "status": "error",
            "error": str(e),
            "message": "Failed to download PDF from Google Drive"
        }
    
    # Print to console
    print(f"📊 Result: {result}")
    print("-" * 50)
    
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)
