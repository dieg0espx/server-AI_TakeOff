# source venv/bin/activate
# uvicorn main:app --host 0.0.0.0 --port 5001 --reload

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import sys
import os
import json
import asyncio
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
load_dotenv()


# Add the api directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'api'))

# Import the PDF downloader and config manager
from gdrive_pdf_downloader import download_pdf_from_drive
from utils.config_manager import config_manager

# Import the PDF to SVG converter
from pdf_to_svg_converter import ConvertioConverter

# Import the PDF text extractor
from api.pdf_text_extractor import extract_text_from_pdf

# Import the Cloudinary manager
from api.cloudinary_manager import get_cloudinary_manager



# Create FastAPI instance
app = FastAPI(
    title="AI-Takeoff Server",
    description="AI-Takeoff API server",
    version="1.0.0"
)


# Custom logging function
async def log_to_client(upload_id: str, message: str, log_type: str = "info"):
    """Log message to console"""
    print(message)


# SVG to PNG conversion function
def convert_svg_to_png(svg_path: str, png_path: str) -> bool:
    """
    Convert SVG file to PNG format
    
    Args:
        svg_path: Path to the input SVG file
        png_path: Path where the PNG file should be saved
        
    Returns:
        True if conversion successful, False otherwise
    """
    try:
        import cairosvg
        from PIL import Image
        import io
        
        print(f"🔄 Converting SVG to PNG: {svg_path} -> {png_path}")
        
        # Convert SVG to PNG using cairosvg
        png_data = cairosvg.svg2png(url=svg_path)
        
        # Save the PNG data to file
        with open(png_path, 'wb') as f:
            f.write(png_data)
        
        print(f"✅ SVG to PNG conversion successful: {png_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error converting SVG to PNG: {str(e)}")
        return False


# Function to upload original PNG to Cloudinary and update data.json
async def upload_original_png_to_cloudinary(upload_id: str, svg_path: str) -> str:
    """
    Convert original SVG to PNG, upload to Cloudinary, and store URL in data.json
    
    Args:
        upload_id: The upload ID for this request
        svg_path: Path to the original SVG file
        
    Returns:
        Cloudinary URL of the uploaded PNG or None if failed
    """
    try:
        # Convert SVG to PNG
        png_path = os.path.join('files', 'original.png')
        if not convert_svg_to_png(svg_path, png_path):
            return None
        
        # Get Cloudinary manager
        cloudinary_manager = get_cloudinary_manager()
        if not cloudinary_manager:
            print("⚠️  Cloudinary manager not available")
            return None
        
        # Upload PNG to Cloudinary
        public_id = f"original_{upload_id}"
        cloudinary_url = cloudinary_manager.upload_image(png_path, public_id)
        
        if cloudinary_url:
            # Update data.json with the original PNG URL
            data_json_path = os.path.join('data.json')
            data = {}
            
            # Load existing data if file exists
            if os.path.exists(data_json_path):
                try:
                    with open(data_json_path, 'r') as f:
                        data = json.load(f)
                except Exception as e:
                    print(f"⚠️  Error reading existing data.json: {e}")
                    data = {}
            
            # Add the original PNG URL
            if 'cloudinary_urls' not in data:
                data['cloudinary_urls'] = {}
            data['cloudinary_urls']['original'] = cloudinary_url
            data['upload_id'] = upload_id
            
            # Save updated data.json
            with open(data_json_path, 'w') as f:
                json.dump(data, f, indent=4)
            
            print(f"✅ Original PNG uploaded and URL stored in data.json: {cloudinary_url}")
            return cloudinary_url
        else:
            print("❌ Failed to upload original PNG to Cloudinary")
            return None
            
    except Exception as e:
        print(f"❌ Error in upload_original_png_to_cloudinary: {str(e)}")
        return None



# Modified pipeline runner with logging support
def run_pipeline_with_logging(upload_id: str):
    """Run the processing pipeline with logging"""
    import sys
    import os
    import importlib.util
    import json
    
    # Define the processing steps in order
    steps = [
        "Step1",  # Remove duplicate paths
        "Step2",  # Modify colors (lightgray and black)
        "Step3",  # Add background
        "Step4",  # Apply color coding to specific patterns
        "Step5",  # Detect blue X shapes
        "Step6",  # Detect red squares
        "Step7",  # Detect pink shapes
        "Step8",  # Detect green rectangles
    ]
    
    successful_steps = 0
    total_steps = len(steps)
    step_counts = {}
    
    # Run each step in sequence
    for i, step in enumerate(steps):
        try:
            # Construct the path to the step file
            step_file = f"processors/{step}.py"
            
            if not os.path.exists(step_file):
                print(f"Step file {step_file} not found. Skipping...")
                continue
            
            print(f"\n{'='*50}")
            print(f"Running {step}...")
            print(f"{'='*50}")
            
            # Add processors directory to Python path
            processors_dir = os.path.abspath("processors")
            if processors_dir not in sys.path:
                sys.path.insert(0, processors_dir)
            
            # Import and run the step
            spec = importlib.util.spec_from_file_location(step, step_file)
            step_module = importlib.util.module_from_spec(spec)
            sys.modules[step] = step_module
            spec.loader.exec_module(step_module)
            
            run_function_name = f'run_{step.lower()}'
            if hasattr(step_module, run_function_name):
                run_function = getattr(step_module, run_function_name)
                success = run_function()
                
                if success:
                    successful_steps += 1
                    print(f"✅ {step} completed successfully")
                else:
                    print(f"❌ {step} failed")
                    break
            else:
                print(f"⚠️  No run function found for {step}")
                break
                
        except Exception as e:
            print(f"❌ Error running {step}: {str(e)}")
            break
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 Processing Summary")
    print(f"{'='*60}")
    print(f"Steps completed: {successful_steps}/{total_steps}")
    
    if successful_steps == total_steps:
        print(f"🎉 All steps completed successfully!")
    else:
        print(f"⚠️  Pipeline completed with some failures")
    
    return successful_steps == total_steps

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


# AI-Takeoff specific endpoint
@app.get("/AI-Takeoff/{upload_id}")
async def get_ai_takeoff_result(upload_id: str, background_tasks: BackgroundTasks = None, sync: bool = True):
    # Store the Google Drive file ID in JSON as google_drive_file_id
    config_manager.set_file_id(upload_id)
    
    print(f"🔍 AI-Takeoff Request for upload_id: {upload_id}")
    print(f"📝 Stored Google Drive file ID in JSON as google_drive_file_id: {upload_id}")
    
    # Force synchronous processing by default, or if sync=True
    if sync:
        print(f"🔄 Running in synchronous mode...")
        return await process_ai_takeoff_sync(upload_id)
    else:
        # Fallback to synchronous processing
        return await process_ai_takeoff_sync(upload_id)

# Extract text from PDF endpoint
@app.get("/extract-text/{upload_id}")
async def extract_pdf_text(upload_id: str):
    """Extract text from the PDF file and print to console"""
    try:
        # Store the Google Drive file ID
        config_manager.set_file_id(upload_id)
        
        print(f"🔍 Text extraction request for upload_id: {upload_id}")
        
        # Download the PDF first
        file_path = download_pdf_from_drive(upload_id)
        print(f"📄 PDF downloaded successfully to: {file_path}")
        
        # Extract text from the PDF
        extracted_text = extract_text_from_pdf(file_path)
        
        if extracted_text:
            return {
                "id": upload_id,
                "status": "success",
                "message": "Text extracted successfully and printed to console",
                "text_length": len(extracted_text),
                "pdf_path": file_path
            }
        else:
            return {
                "id": upload_id,
                "status": "no_text",
                "message": "No text was extracted from the PDF",
                "pdf_path": file_path
            }
            
    except Exception as e:
        print(f"❌ Error in text extraction: {e}")
        return {
            "id": upload_id,
            "status": "error",
            "error": str(e),
            "message": "Failed to extract text from PDF"
        }

# Get results endpoint
@app.get("/AI-Takeoff/{upload_id}/results")
async def get_ai_takeoff_results(upload_id: str):
    """Get the results from data.json for a specific upload_id"""
    data_json_path = os.path.join('data.json')
    
    if not os.path.exists(data_json_path):
        return {
            "id": upload_id,
            "status": "not_found",
            "message": "No results found. Processing may not be complete."
        }
    
    try:
        with open(data_json_path, 'r') as f:
            import json
            data_results = json.load(f)
        
        # Check if this result belongs to the requested upload_id
        if data_results.get('upload_id') == upload_id:
            return {
                "id": upload_id,
                "status": "completed",
                "results": data_results
            }
        else:
            return {
                "id": upload_id,
                "status": "not_found",
                "message": "Results not found for this upload_id. Processing may not be complete."
            }
            
    except Exception as e:
        return {
            "id": upload_id,
            "status": "error",
            "error": str(e),
            "message": "Error reading results file"
        }


async def process_ai_takeoff_sync(upload_id: str):
    """Synchronous processing"""
    try:
        await log_to_client(upload_id, f"📄 Starting PDF download for upload_id: {upload_id}")
        
        # Step 1: Download the PDF
        file_path = download_pdf_from_drive(upload_id)
        await log_to_client(upload_id, f"📄 PDF downloaded successfully to: {file_path}")
        
        # Step 2: Convert PDF to SVG
        svg_path = None
        svg_size = None
        
        if converter:
            await log_to_client(upload_id, f"🔄 Starting PDF to SVG conversion...")
            try:
                # Start conversion process
                conv_id = await converter.start_conversion()
                await log_to_client(upload_id, f"🔄 Conversion started with ID: {conv_id}")
                
                # Upload the file
                await converter.upload_file(conv_id, file_path)
                await log_to_client(upload_id, f"📤 PDF uploaded to conversion service")
                
                # Wait for conversion to complete
                download_url = await converter.check_status(conv_id)
                await log_to_client(upload_id, f"✅ Conversion completed, downloading SVG...")
                
                # Download the converted file
                svg_path = os.path.join('files', 'original.svg')
                await converter.download_file(download_url, svg_path)
                await log_to_client(upload_id, f"✅ SVG saved to: {svg_path}")
                
                svg_size = os.path.getsize(svg_path) if os.path.exists(svg_path) else 0
                
                # Convert original SVG to PNG and upload to Cloudinary before pipeline
                await log_to_client(upload_id, f"🔄 Converting original SVG to PNG and uploading to Cloudinary...")
                original_png_url = await upload_original_png_to_cloudinary(upload_id, svg_path)
                if original_png_url:
                    await log_to_client(upload_id, f"✅ Original PNG uploaded successfully: {original_png_url}")
                else:
                    await log_to_client(upload_id, f"⚠️  Failed to upload original PNG to Cloudinary", "warning")
                
                # Start the processing pipeline
                await log_to_client(upload_id, f"🚀 Starting AI processing pipeline...")
                try:
                    pipeline_success = run_pipeline_with_logging(upload_id)
                    if pipeline_success:
                        await log_to_client(upload_id, f"✅ Processing pipeline completed successfully")
                    else:
                        await log_to_client(upload_id, f"⚠️  Processing pipeline completed with some failures")
                except Exception as pipeline_error:
                    await log_to_client(upload_id, f"❌ Error in processing pipeline: {pipeline_error}", "error")
                
            except Exception as conversion_error:
                await log_to_client(upload_id, f"❌ Error in SVG conversion: {conversion_error}", "error")
        else:
            await log_to_client(upload_id, f"⚠️  Skipping SVG conversion - CONVERTIO_API_KEY not set", "warning")
        
        # Get file sizes
        pdf_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        
        # Read the data.json file that was generated by the pipeline
        data_json_path = os.path.join('data.json')
        if os.path.exists(data_json_path):
            try:
                with open(data_json_path, 'r') as f:
                    import json
                    data_results = json.load(f)
                
                result = {
                    "id": upload_id,
                    "status": "completed",
                    "pdf_path": file_path,
                    "pdf_size": pdf_size,
                    "svg_path": svg_path,
                    "svg_size": svg_size,
                    "message": "AI-Takeoff processing completed successfully",
                    "results": data_results
                }
            except Exception as e:
                await log_to_client(upload_id, f"❌ Error reading data.json: {e}", "error")
                result = {
                    "id": upload_id,
                    "status": "completed",
                    "pdf_path": file_path,
                    "pdf_size": pdf_size,
                    "svg_path": svg_path,
                    "svg_size": svg_size,
                    "message": "PDF downloaded and converted to SVG successfully, but could not read results"
                }
        else:
            result = {
                "id": upload_id,
                "status": "completed",
                "pdf_path": file_path,
                "pdf_size": pdf_size,
                "svg_path": svg_path,
                "svg_size": svg_size,
                "message": "PDF downloaded and converted to SVG successfully, but no results file found"
            }
        
    except Exception as e:
        await log_to_client(upload_id, f"❌ Error downloading PDF: {e}", "error")
        
        result = {
            "id": upload_id,
            "status": "error",
            "error": str(e),
            "message": "Failed to download PDF from Google Drive"
        }
    
    # Log final result
    await log_to_client(upload_id, f"📊 Result: {result}")
    await log_to_client(upload_id, "-" * 50)
    
    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)
