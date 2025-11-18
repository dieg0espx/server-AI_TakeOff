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

# Import the email notifier
from utils.email_notifier import notify_error, notify_success

# Import log capture
from utils.log_capture import LogCapture, get_log_storage



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
    """Run the processing pipeline with logging and detailed error tracking"""
    import sys
    import os
    import importlib.util
    import json
    
    # Define the processing steps in order (Steps 1-10 only, 11-12 run separately)
    steps = [
        "Step1",  # Remove duplicate paths
        "Step2",  # Modify colors (lightgray and black)
        "Step3",  # Add background
        "Step4",  # Apply color coding to specific patterns
        "Step5",  # Detect blue X shapes
        "Step6",  # Detect red squares
        "Step7",  # Detect pink shapes
        "Step8",  # Detect green rectangles
        "Step9",  # Detect orange rectangles
        "Step10", # Draw all containers onto Step2.svg
    ]
    
    successful_steps = 0
    total_steps = len(steps)
    step_counts = {}
    failed_step = None
    error_details = None
    tracking_url = None
    
    # Run each step in sequence
    for i, step in enumerate(steps):
        try:
            # Construct the path to the step file
            step_file = f"processors/{step}.py"
            
            if not os.path.exists(step_file):
                error_msg = f"Step file {step_file} not found"
                print(f"❌ {error_msg}")
                failed_step = step
                error_details = error_msg
                break
            
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
                    error_msg = f"{step} execution returned False"
                    print(f"❌ {error_msg}")
                    failed_step = step
                    error_details = error_msg
                    break
            else:
                error_msg = f"No run function found for {step}"
                print(f"❌ {error_msg}")
                failed_step = step
                error_details = error_msg
                break
                
        except Exception as e:
            error_msg = f"Exception in {step}: {str(e)}"
            print(f"❌ {error_msg}")
            failed_step = step
            error_details = error_msg
            break
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 Processing Summary")
    print(f"{'='*60}")
    print(f"Steps completed: {successful_steps}/{total_steps}")
    
    if successful_steps == total_steps:
        print(f"🎉 All steps completed successfully!")
        
        # Update data.json with step counts before running Step11
        try:
            print(f"\n{'='*60}")
            print("📝 Updating data.json with processing results...")
            print(f"{'='*60}")
            
            # Read existing JSON result files to get counts
            step_counts = {}
            
            # Read counts from individual JSON files created by each step
            # Each step creates a JSON file with a specific structure
            json_files = {
                'files/tempData/x-shores.json': ('step5_blue_X_shapes', 'total_x_shapes'),
                'files/tempData/square-shores.json': ('step6_red_squares', 'total_red_squares'),
                'files/tempData/pinkFrames.json': ('step7_pink_shapes', 'total_pink_shapes'),
                'files/tempData/greenFrames.json': ('step8_green_rectangles', 'total_rectangles'),
                'files/tempData/orangeFrames.json': ('step9_orange_rectangles', 'total_rectangles')
            }

            for json_file, (result_key, json_field) in json_files.items():
                if os.path.exists(json_file):
                    try:
                        with open(json_file, 'r') as f:
                            data = json.load(f)
                            if isinstance(data, dict) and json_field in data:
                                count = data[json_field]
                                step_counts[result_key] = count
                                print(f"   ✅ {result_key}: {count}")
                            else:
                                print(f"   ⚠️  {json_file} missing field '{json_field}'")
                                step_counts[result_key] = 0
                    except Exception as e:
                        print(f"   ⚠️  Could not read {json_file}: {e}")
                        step_counts[result_key] = 0
                else:
                    print(f"   ⚠️  {json_file} not found")
                    step_counts[result_key] = 0
            
            # Update data.json with the collected counts
            data_file = "data.json"
            if os.path.exists(data_file):
                with open(data_file, 'r') as f:
                    data = json.load(f)
            else:
                data = {}
            
            data["step_results"] = step_counts
            
            print(f"✅ data.json updated with step results")
            print(f"   Total results: {sum(step_counts.values())} detections")
            
            # Upload result images to Cloudinary
            try:
                print(f"\n☁️  Uploading processing results to Cloudinary...")
                from api.cloudinary_manager import get_cloudinary_manager
                cloudinary_manager = get_cloudinary_manager()
                
                if cloudinary_manager:
                    cloudinary_urls = cloudinary_manager.upload_processing_results(step_counts)
                    
                    if cloudinary_urls:
                        # Merge with existing cloudinary_urls (preserve 'original' if it exists)
                        if 'cloudinary_urls' not in data:
                            data['cloudinary_urls'] = {}
                        data['cloudinary_urls'].update(cloudinary_urls)
                        print(f"✅ Successfully uploaded {len(cloudinary_urls)} images to Cloudinary")
                    else:
                        print("⚠️  No images were uploaded to Cloudinary")
                else:
                    print("⚠️  Cloudinary not configured - skipping image uploads")
                    
            except Exception as e:
                print(f"⚠️  Error uploading to Cloudinary: {str(e)}")
            
            # Write back to data.json with Cloudinary URLs
            with open(data_file, 'w') as f:
                json.dump(data, f, indent=4)
            
        except Exception as e:
            print(f"⚠️  Error updating data.json: {e}")
        
        # Now run Step11 and Step12 after data is prepared
        final_steps = ["Step11", "Step12"]
        
        for step in final_steps:
            try:
                print(f"\n{'='*50}")
                print(f"Running {step}...")
                print(f"{'='*50}")
                
                step_file = f"processors/{step}.py"
                if os.path.exists(step_file):
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
                            print(f"⚠️  {step} failed, but pipeline will continue")
                    else:
                        print(f"⚠️  No run function found for {step}")
                else:
                    print(f"⚠️  {step_file} not found")
                    
            except Exception as e:
                print(f"⚠️  Exception in {step}: {e}")
        
        return True, None, None
    else:
        print(f"❌ Pipeline failed at {failed_step}: {error_details}")
        return False, failed_step, error_details

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

# Health check endpoint for Railway
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "AI-Takeoff Server"}


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
        try:
            file_path = download_pdf_from_drive(upload_id)
            if not file_path or not os.path.exists(file_path):
                error_msg = f"Failed to download PDF for upload_id: {upload_id}"
                await log_to_client(upload_id, f"❌ {error_msg}", "error")
                print(f"🚨 PDF DOWNLOAD FAILURE - Upload ID: {upload_id}")
                print(f"🚨 Error: {error_msg}")

                # Send email notification
                notify_error(
                    error_title="PDF Download Failed",
                    error_message=error_msg,
                    error_details={
                        "upload_id": upload_id,
                        "file_path": file_path if file_path else "None",
                        "stage": "PDF Download from Google Drive"
                    },
                    upload_id=upload_id
                )

                return {
                    "id": upload_id,
                    "status": "error",
                    "error": "PDF download failed",
                    "error_details": error_msg,
                    "message": f"Failed to download PDF from Google Drive for upload_id: {upload_id}"
                }
            await log_to_client(upload_id, f"📄 PDF downloaded successfully to: {file_path}")
        except Exception as download_error:
            error_msg = f"Exception during PDF download: {download_error}"
            await log_to_client(upload_id, f"❌ {error_msg}", "error")
            print(f"🚨 PDF DOWNLOAD EXCEPTION - Upload ID: {upload_id}")
            print(f"🚨 Exception: {download_error}")

            # Send email notification
            notify_error(
                error_title="PDF Download Exception",
                error_message=error_msg,
                error_details={
                    "upload_id": upload_id,
                    "stage": "PDF Download from Google Drive",
                    "exception_type": type(download_error).__name__
                },
                exception=download_error,
                upload_id=upload_id
            )

            return {
                "id": upload_id,
                "status": "error",
                "error": "PDF download exception",
                "error_details": str(download_error),
                "message": f"Exception occurred while downloading PDF: {download_error}"
            }
        
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
                
                # Extract text from PDF BEFORE starting the pipeline
                await log_to_client(upload_id, f"📄 Extracting text from PDF...")
                try:
                    extracted_text = extract_text_from_pdf(file_path)
                    if extracted_text:
                        await log_to_client(upload_id, f"✅ Text extracted successfully ({len(extracted_text)} characters)")
                    else:
                        await log_to_client(upload_id, f"⚠️  No text extracted from PDF", "warning")
                except Exception as text_error:
                    await log_to_client(upload_id, f"⚠️  Text extraction failed: {text_error}", "warning")
                    print(f"Warning: Text extraction failed: {text_error}")

                # Start the processing pipeline with log capture
                await log_to_client(upload_id, f"🚀 Starting AI processing pipeline...")

                # Capture all console logs during pipeline execution
                log_capture = LogCapture()
                try:
                    with log_capture:
                        pipeline_success, failed_step, error_details = run_pipeline_with_logging(upload_id)

                    # Store the captured logs
                    captured_logs = log_capture.get_logs()
                    processing_duration = log_capture.get_duration()
                    get_log_storage().store_log(upload_id, captured_logs, processing_duration)
                    if pipeline_success:
                        await log_to_client(upload_id, f"✅ Processing pipeline completed successfully")
                    else:
                        error_msg = f"❌ Processing pipeline failed at {failed_step}: {error_details}"
                        await log_to_client(upload_id, error_msg, "error")
                        print(f"🚨 PIPELINE FAILURE - Upload ID: {upload_id}")
                        print(f"🚨 Failed Step: {failed_step}")
                        print(f"🚨 Error Details: {error_details}")
                        print(f"🚨 Steps completed before failure: {failed_step}")

                        # Get captured logs for error notification
                        log_data = get_log_storage().get_log(upload_id)
                        error_logs = log_data['logs'] if log_data else None

                        # Send email notification with logs
                        notify_error(
                            error_title=f"Pipeline Failed at {failed_step}",
                            error_message=f"{error_details}\n\nConsole Logs:\n{error_logs}" if error_logs else error_details,
                            error_details={
                                "upload_id": upload_id,
                                "failed_step": failed_step,
                                "stage": "AI Processing Pipeline",
                                "pdf_path": file_path,
                                "svg_path": svg_path
                            },
                            upload_id=upload_id
                        )

                        # Return error response to client
                        return {
                            "id": upload_id,
                            "status": "error",
                            "error": f"Pipeline failed at {failed_step}",
                            "error_details": error_details,
                            "failed_step": failed_step,
                            "message": f"AI processing failed at step {failed_step}. Check server logs for details.",
                            "pdf_path": file_path,
                            "pdf_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                            "svg_path": svg_path,
                            "svg_size": svg_size
                        }
                except Exception as pipeline_error:
                    error_msg = f"❌ Exception in processing pipeline: {pipeline_error}"
                    await log_to_client(upload_id, error_msg, "error")
                    print(f"🚨 PIPELINE EXCEPTION - Upload ID: {upload_id}")
                    print(f"🚨 Exception: {pipeline_error}")

                    # Send email notification
                    notify_error(
                        error_title="Pipeline Exception",
                        error_message=error_msg,
                        error_details={
                            "upload_id": upload_id,
                            "stage": "AI Processing Pipeline",
                            "exception_type": type(pipeline_error).__name__,
                            "pdf_path": file_path,
                            "svg_path": svg_path
                        },
                        exception=pipeline_error,
                        upload_id=upload_id
                    )

                    # Return error response to client
                    return {
                        "id": upload_id,
                        "status": "error",
                        "error": "Pipeline exception",
                        "error_details": str(pipeline_error),
                        "message": f"AI processing failed with exception: {pipeline_error}",
                        "pdf_path": file_path,
                        "pdf_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                        "svg_path": svg_path,
                        "svg_size": svg_size
                    }
                
            except Exception as conversion_error:
                error_msg = f"❌ Error in SVG conversion: {conversion_error}"
                await log_to_client(upload_id, error_msg, "error")
                print(f"🚨 SVG CONVERSION FAILURE - Upload ID: {upload_id}")
                print(f"🚨 Exception: {conversion_error}")

                # Send email notification
                notify_error(
                    error_title="SVG Conversion Failed",
                    error_message=error_msg,
                    error_details={
                        "upload_id": upload_id,
                        "stage": "PDF to SVG Conversion (Convertio)",
                        "exception_type": type(conversion_error).__name__,
                        "pdf_path": file_path
                    },
                    exception=conversion_error,
                    upload_id=upload_id
                )

                # Return error response to client
                return {
                    "id": upload_id,
                    "status": "error",
                    "error": "SVG conversion failed",
                    "error_details": str(conversion_error),
                    "message": f"Failed to convert PDF to SVG: {conversion_error}",
                    "pdf_path": file_path,
                    "pdf_size": os.path.getsize(file_path) if os.path.exists(file_path) else 0
                }
        else:
            await log_to_client(upload_id, f"⚠️  Skipping SVG conversion - CONVERTIO_API_KEY not set", "warning")
        
        # Get file sizes
        pdf_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        
        # Read the data.json file that was generated by the pipeline
        data_json_path = os.path.join('data.json')
        result_url = None
        data_results = None

        if os.path.exists(data_json_path):
            try:
                with open(data_json_path, 'r') as f:
                    import json
                    data_results = json.load(f)

                # Get result URL - priority: tracking_url > step10_results > step8_results
                if 'tracking_url' in data_results:
                    # Use tracking URL from Step11
                    tracking_url = data_results['tracking_url']
                    api_url = os.environ.get('API_URL', 'https://ttfconstruction.com/ai-takeoff-results/create.php')
                    api_base = api_url.replace('/create.php', '')
                    result_url = f"{api_base}/read.php?tracking_url={tracking_url}"
                elif 'cloudinary_urls' in data_results:
                    # Use the final image URL from Cloudinary (step10 or step8)
                    cloudinary_urls = data_results['cloudinary_urls']
                    if 'step10_results' in cloudinary_urls:
                        result_url = cloudinary_urls['step10_results']
                    elif 'step8_results' in cloudinary_urls:
                        result_url = cloudinary_urls['step8_results']

                # Return just the result URL
                result = result_url
            except Exception as e:
                await log_to_client(upload_id, f"❌ Error reading data.json: {e}", "error")
                print(f"Error reading data.json: {e}")
                result = None
        else:
            await log_to_client(upload_id, f"⚠️  data.json not found", "warning")
            result = None

        # ALWAYS send success notification email (even if data.json has issues)
        # This ensures you get notified of every takeoff attempt
        await log_to_client(upload_id, f"📧 Sending success notification email...")
        try:
            log_data = get_log_storage().get_log(upload_id)
            success_logs = log_data['logs'] if log_data else None
            success_duration = log_data['duration'] if log_data else None

            # Use data_results if available, otherwise create a minimal results dict
            if data_results is None:
                data_results = {
                    'upload_id': upload_id,
                    'step_results': {},
                    'cloudinary_urls': {}
                }

            email_sent = notify_success(upload_id, data_results, success_logs, success_duration)

            if email_sent:
                await log_to_client(upload_id, f"✅ Success notification email sent to {os.getenv('NOTIFICATION_EMAIL')}")
            else:
                await log_to_client(upload_id, f"⚠️  Failed to send success notification email", "warning")
                print(f"Warning: Email notification was not sent for upload_id: {upload_id}")
        except Exception as email_error:
            await log_to_client(upload_id, f"❌ Error sending email notification: {email_error}", "error")
            print(f"Email notification error: {email_error}")
            import traceback
            traceback.print_exc()

        # Clear logs from storage after attempting email
        get_log_storage().clear_log(upload_id)
        
    except Exception as e:
        error_msg = f"❌ Unexpected error in AI processing: {e}"
        await log_to_client(upload_id, error_msg, "error")
        print(f"🚨 UNEXPECTED ERROR - Upload ID: {upload_id}")
        print(f"🚨 Exception: {e}")
        print(f"🚨 Exception Type: {type(e).__name__}")

        # Send email notification
        notify_error(
            error_title="Unexpected Processing Error",
            error_message=error_msg,
            error_details={
                "upload_id": upload_id,
                "stage": "General AI Processing",
                "exception_type": type(e).__name__
            },
            exception=e,
            upload_id=upload_id
        )

        result = {
            "id": upload_id,
            "status": "error",
            "error": "Unexpected processing error",
            "error_details": str(e),
            "error_type": type(e).__name__,
            "message": f"An unexpected error occurred during AI processing: {e}"
        }
    
    # Log final result
    await log_to_client(upload_id, f"📊 Result: {result}")
    await log_to_client(upload_id, "-" * 50)
    
    return result

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 AI-Takeoff Server Starting...")
    print("=" * 60)
    
    # Debug environment
    print(f"📋 Environment Variables:")
    print(f"  PORT: {os.getenv('PORT', 'NOT SET')}")
    print(f"  PYTHONPATH: {os.getenv('PYTHONPATH', 'NOT SET')}")
    print(f"  PWD: {os.getcwd()}")
    
    # Debug file system
    print(f"📂 Current Directory Contents:")
    try:
        for item in os.listdir('.'):
            print(f"  - {item}")
    except Exception as e:
        print(f"  Error listing directory: {e}")
    
    # Debug Python path
    print(f"🐍 Python Path:")
    import sys
    for path in sys.path[:5]:  # Show first 5 paths
        print(f"  - {path}")
    
    # Get port
    port = int(os.getenv("PORT", 5001))
    print(f"🌐 Starting server on port {port}")
    print(f"📋 Server will be available at: http://0.0.0.0:{port}")
    print(f"📋 Health check endpoint: http://0.0.0.0:{port}/health")
    print(f"📚 API documentation: http://0.0.0.0:{port}/docs")
    print("=" * 60)
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise
