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

# Import log capture
from utils.log_capture import LogCapture, get_log_storage, parse_logs_to_json

# Import for SVG/PNG conversion
import cairosvg
import asyncio



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


# SVG → PNG → SVG Conversion Functions
def convert_svg_to_png_for_flatten(svg_path: str, png_path: str) -> bool:
    """Convert SVG to PNG using cairosvg (flattens all layers)"""
    try:
        print(f"  🔄 Converting SVG to PNG: {svg_path} → {png_path}")
        cairosvg.svg2png(url=svg_path, write_to=png_path)
        if os.path.exists(png_path):
            print(f"  ✅ PNG created: {png_path} ({os.path.getsize(png_path)} bytes)")
            return True
        return False
    except Exception as e:
        print(f"  ❌ SVG to PNG conversion failed: {e}")
        return False


async def convert_png_to_svg_async(png_path: str, svg_path: str) -> bool:
    """Convert PNG back to SVG using Convertio API"""
    try:
        print(f"  🔄 Converting PNG to SVG: {png_path} → {svg_path}")

        # Use the same Convertio converter
        from api.pdf_to_svg_converter import ConvertioConverter

        converter = ConvertioConverter()

        # Start conversion (set output format to SVG)
        conv_id = await converter.start_conversion()
        print(f"  📤 Conversion started with ID: {conv_id}")

        # Upload the PNG file
        await converter.upload_file(conv_id, png_path)
        print(f"  📤 PNG uploaded to Convertio")

        # Wait for conversion to complete
        download_url = await converter.check_status(conv_id)
        print(f"  ✅ Conversion complete, downloading SVG...")

        # Download the converted SVG
        await converter.download_file(download_url, svg_path)

        if os.path.exists(svg_path):
            print(f"  ✅ SVG created: {svg_path} ({os.path.getsize(svg_path)} bytes)")
            return True
        return False

    except Exception as e:
        print(f"  ❌ PNG to SVG conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def convert_png_to_svg_sync(png_path: str, svg_path: str) -> bool:
    """Synchronous wrapper for PNG to SVG conversion"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(convert_png_to_svg_async(png_path, svg_path))
        loop.close()
        return result
    except Exception as e:
        print(f"  ❌ PNG to SVG sync conversion failed: {e}")
        return False


def flatten_svg_via_png(input_svg: str, output_svg: str) -> bool:
    """
    Flatten SVG by converting to PNG and back to SVG.
    This rasterizes all layers, making overlapping elements truly overlap.
    """
    try:
        print(f"\n🔄 FLATTENING SVG (SVG → PNG → SVG)")
        print(f"   Input:  {input_svg}")
        print(f"   Output: {output_svg}")

        # Create temp PNG path
        temp_png = input_svg.replace('.svg', '_temp.png')

        # Step 1: SVG → PNG
        if not convert_svg_to_png_for_flatten(input_svg, temp_png):
            print("  ❌ Failed to convert SVG to PNG")
            return False

        # Step 2: PNG → SVG
        if not convert_png_to_svg_sync(temp_png, output_svg):
            print("  ❌ Failed to convert PNG back to SVG")
            # Clean up temp file
            if os.path.exists(temp_png):
                os.remove(temp_png)
            return False

        # Clean up temp PNG
        if os.path.exists(temp_png):
            os.remove(temp_png)
            print(f"  🧹 Cleaned up temp file: {temp_png}")

        print(f"✅ SVG flattening complete: {output_svg}")
        return True

    except Exception as e:
        print(f"❌ SVG flattening failed: {e}")
        return False


def compare_branch_results(results_no_slab: dict, results_with_slab: dict) -> dict:
    """
    Compare results between no slab band and with slab band branches.
    Calculate the difference for each detection type.
    """
    difference = {}

    # Get all keys from both result sets
    all_keys = set(results_no_slab.keys()) | set(results_with_slab.keys())

    for key in all_keys:
        no_slab_val = results_no_slab.get(key, 0)
        with_slab_val = results_with_slab.get(key, 0)
        diff = with_slab_val - no_slab_val

        difference[key] = {
            "no_slab_band": no_slab_val,
            "with_slab_band": with_slab_val,
            "difference": diff,
            "change": "increased" if diff > 0 else ("decreased" if diff < 0 else "no change")
        }

    return difference


# Helper function to run a single step
def run_single_step(step_name: str, step_file: str = None):
    """Run a single processing step and return success status"""
    import importlib.util

    if step_file is None:
        step_file = f"processors/{step_name}.py"

    if not os.path.exists(step_file):
        print(f"❌ Step file {step_file} not found")
        return False

    print(f"\n{'='*50}")
    print(f"Running {step_name}...")
    print(f"{'='*50}")

    # Add processors directory to Python path
    processors_dir = os.path.abspath("processors")
    if processors_dir not in sys.path:
        sys.path.insert(0, processors_dir)

    try:
        # Import and run the step
        spec = importlib.util.spec_from_file_location(step_name, step_file)
        step_module = importlib.util.module_from_spec(spec)
        sys.modules[step_name] = step_module
        spec.loader.exec_module(step_module)

        run_function_name = f'run_{step_name.lower()}'
        if hasattr(step_module, run_function_name):
            run_function = getattr(step_module, run_function_name)
            success = run_function()

            if success:
                print(f"✅ {step_name} completed successfully")
                return True
            else:
                print(f"❌ {step_name} execution returned False")
                return False
        else:
            print(f"❌ No run function found for {step_name}")
            return False

    except Exception as e:
        print(f"❌ Exception in {step_name}: {str(e)}")
        return False


def run_detection_steps_for_branch(branch_name: str, source_svg: str, output_prefix: str = ""):
    """
    Run detection steps (4-10) for a specific branch.

    Args:
        branch_name: Name of the branch (e.g., "no_slab_band" or "with_slab_band")
        source_svg: Path to the source SVG file to use as Step3 input
        output_prefix: Prefix for output files (e.g., "slab_" for slab band branch)

    Returns:
        tuple: (success, step_counts)
    """
    import shutil

    print(f"\n{'='*60}")
    print(f"🔄 Running detection pipeline for: {branch_name}")
    print(f"   Source: {source_svg}")
    print(f"{'='*60}")

    # Copy source SVG to Step3.svg so Steps 4-10 use the correct input
    step3_path = "files/Step3.svg"
    try:
        shutil.copy(source_svg, step3_path)
        print(f"✅ Copied {source_svg} to {step3_path}")
    except Exception as e:
        print(f"❌ Failed to copy source SVG: {e}")
        return False, {}

    # Detection steps (Step4 through Step10)
    detection_steps = [
        "Step4",  # Apply color coding to specific patterns
        "Step5",  # Detect blue X shapes
        "Step6",  # Detect red squares
        "Step7",  # Detect pink shapes
        "Step8",  # Detect green rectangles
        "Step9",  # Detect orange rectangles
        "Step10", # Draw all containers onto Step2.svg
    ]

    step_counts = {}

    for step in detection_steps:
        success = run_single_step(step)
        if not success:
            print(f"❌ Branch '{branch_name}' failed at {step}")
            return False, step_counts

    # Read counts from JSON files
    json_files = {
        'files/tempData/x-shores.json': ('step5_blue_X_shapes', 'total_x_shapes'),
        'files/tempData/square-shores.json': ('step6_red_squares', 'total_red_squares'),
        'files/tempData/pinkFrames.json': ('step7_pink_shapes', 'total_pink_shapes'),
        'files/tempData/greenFrames.json': ('step8_green_rectangles', 'total_rectangles'),
        'files/tempData/orangeFrames.json': ('step9_orange_rectangles', 'total_rectangles'),
        'files/tempData/yellowFrames.json': ('step11_yellow_shapes', 'total_shapes')
    }

    for json_file, (result_key, json_field) in json_files.items():
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and json_field in data:
                        step_counts[result_key] = data[json_field]
                    else:
                        step_counts[result_key] = 0
            except Exception as e:
                step_counts[result_key] = 0
        else:
            step_counts[result_key] = 0

    print(f"\n✅ Branch '{branch_name}' completed successfully")
    print(f"   Results: {step_counts}")

    return True, step_counts


def save_json_results_for_comparison(branch_name: str):
    """
    Save JSON detection results to a branch-specific directory for later comparison.
    This allows us to compare no_slab_band vs with_slab_band results.
    """
    import shutil

    temp_data = "files/tempData"
    branch_dir = f"{temp_data}/{branch_name}"

    # Create branch directory
    os.makedirs(branch_dir, exist_ok=True)

    # Copy all JSON files to branch directory
    json_files = [
        "x-shores.json",
        "square-shores.json",
        "pinkFrames.json",
        "greenFrames.json",
        "orangeFrames.json"
    ]

    for json_file in json_files:
        src = f"{temp_data}/{json_file}"
        dst = f"{branch_dir}/{json_file}"
        if os.path.exists(src):
            shutil.copy(src, dst)

    print(f"  ✅ Saved {branch_name} JSON results to {branch_dir}")


def save_branch_results(branch_name: str, step_counts: dict, data: dict):
    """Save branch results to data.json and copy output files"""
    import shutil

    # Note: We don't store individual branch results here anymore
    # The main pipeline stores step_results (no slab) and slab_band (with slab) directly

    # Copy Step10.svg to branch-specific file
    step10_source = "files/Step10.svg"
    step10_dest = f"files/Step10_{branch_name}.svg"

    if os.path.exists(step10_source):
        try:
            shutil.copy(step10_source, step10_dest)
            print(f"✅ Saved {step10_dest}")
        except Exception as e:
            print(f"⚠️  Could not save {step10_dest}: {e}")

    # Copy Step10-results.png to branch-specific file
    png_source = "files/Step10-results.png"
    png_dest = f"files/Step10_{branch_name}-results.png"

    if os.path.exists(png_source):
        try:
            shutil.copy(png_source, png_dest)
            print(f"✅ Saved {png_dest}")
        except Exception as e:
            print(f"⚠️  Could not save {png_dest}: {e}")

    return data


# Modified pipeline runner with logging support
def run_pipeline_with_logging(upload_id: str):
    """Run the processing pipeline with logging and detailed error tracking.

    This pipeline runs TWO branches after Step 3:
    1. NO SLAB BAND: Uses Step3.svg directly
    2. WITH SLAB BAND: Uses Step3_with_slab_band.svg (black elements on top)

    Both branches run Steps 4-10 and produce separate results.
    """
    import sys
    import os
    import importlib.util
    import json
    import shutil

    # Phase 1: Run Steps 1-3 (common to both branches)
    initial_steps = [
        "Step1",  # Remove duplicate paths
        "Step2",  # Modify colors (lightgray and black)
        "Step3",  # Add background
    ]

    successful_steps = 0
    total_steps = len(initial_steps)
    failed_step = None
    error_details = None
    tracking_url = None

    print(f"\n{'='*60}")
    print("📋 PHASE 1: Running initial steps (1-3)")
    print(f"{'='*60}")

    # Run initial steps
    for step in initial_steps:
        success = run_single_step(step)
        if success:
            successful_steps += 1
        else:
            failed_step = step
            error_details = f"{step} failed"
            break

    if failed_step:
        print(f"\n{'='*60}")
        print(f"❌ Pipeline failed at {failed_step}: {error_details}")
        return False, failed_step, error_details

    # Save a backup of Step3.svg (no slab band version)
    step3_original = "files/Step3.svg"
    step3_no_slab = "files/Step3_no_slab_band.svg"

    try:
        shutil.copy(step3_original, step3_no_slab)
        print(f"✅ Saved backup: {step3_no_slab}")
    except Exception as e:
        print(f"⚠️  Could not backup Step3.svg: {e}")

    # Phase 2: Create slab band version
    print(f"\n{'='*60}")
    print("📋 PHASE 2: Creating slab band version")
    print(f"{'='*60}")

    success = run_single_step("Step3_with_slab_band")
    if not success:
        print("⚠️  Step3_with_slab_band failed, continuing with no slab band only")
        # Continue with just the no slab band version

    # Phase 3: Run detection for NO SLAB BAND branch
    print(f"\n{'='*60}")
    print("📋 PHASE 3A: Running detection pipeline (NO SLAB BAND)")
    print(f"{'='*60}")

    # Load existing data.json
    data_file = "data.json"
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            data = json.load(f)
    else:
        data = {}

    success_no_slab, counts_no_slab = run_detection_steps_for_branch(
        "no_slab_band",
        step3_no_slab,
        ""
    )

    if success_no_slab:
        data = save_branch_results("no_slab_band", counts_no_slab, data)
        successful_steps += 7  # Steps 4-10

        # Save no_slab_band JSON results for later comparison
        save_json_results_for_comparison("no_slab_band")
    else:
        print("❌ No slab band detection failed")
        return False, "detection_no_slab_band", "Detection pipeline failed"

    # Phase 4: Run detection for WITH SLAB BAND branch (if available)
    step3_slab = "files/Step3_with_slab_band.svg"

    if os.path.exists(step3_slab):
        print(f"\n{'='*60}")
        print("📋 PHASE 3B: Running detection pipeline (WITH SLAB BAND)")
        print(f"{'='*60}")

        # NOTE: No explicit SVG→PNG→SVG flattening needed!
        # Steps 4-10 already convert SVG→PNG internally using cairosvg for OpenCV processing.
        # When cairosvg renders the SVG to PNG, layers are automatically flattened,
        # and the black elements appended at the end render ON TOP.
        print(f"\n📝 Using slab band SVG directly (flattening happens during detection)")
        print(f"   Source: {step3_slab}")

        success_with_slab, counts_with_slab = run_detection_steps_for_branch(
            "with_slab_band",
            step3_slab,
            "slab_"
        )

        if success_with_slab:
            data = save_branch_results("with_slab_band", counts_with_slab, data)
            successful_steps += 7  # Steps 4-10 again
        else:
            print("⚠️  With slab band detection failed, but no slab band succeeded")
    else:
        print("⚠️  Slab band SVG not found, skipping slab band detection")
        counts_with_slab = {}

    # Use the no_slab_band results as the primary step_results
    data["step_results"] = counts_no_slab

    # Keep slab_band and under_slab_band in data.json for internal analysis
    # but don't send to database
    if counts_with_slab:
        data["slab_band"] = counts_with_slab

        # Print comparison summary
        print(f"\n{'='*60}")
        print("📊 RESULTS COMPARISON (for analysis only)")
        print(f"{'='*60}")
        print(f"\n{'Detection Type':<30} {'No Slab':<10} {'With Slab':<12} {'Hidden':<8}")
        print("-" * 60)

        for key in counts_no_slab.keys():
            no_slab = counts_no_slab.get(key, 0)
            with_slab = counts_with_slab.get(key, 0)
            hidden = no_slab - with_slab  # Elements covered by slab
            hidden_str = str(hidden) if hidden > 0 else "0"
            print(f"{key:<30} {no_slab:<10} {with_slab:<12} {hidden_str:<8}")

        print("-" * 60)
        total_no_slab = sum(counts_no_slab.values())
        total_with_slab = sum(counts_with_slab.values())
        total_hidden = total_no_slab - total_with_slab
        hidden_str = str(total_hidden) if total_hidden > 0 else "0"
        print(f"{'TOTAL':<30} {total_no_slab:<10} {total_with_slab:<12} {hidden_str:<8}")
        print("=" * 60)
        print("Note: Slab band data kept in data.json for internal use only")

        # Mark elements hidden by slab band with * in the final SVG
        print(f"\n{'='*60}")
        print("📝 Marking slab band differences in SVG")
        print(f"{'='*60}")
        try:
            from processors.mark_slab_band_differences import mark_differences
            mark_differences()
        except Exception as e:
            print(f"⚠️  Could not mark slab band differences: {e}")
    else:
        print("⚠️  No slab band results available")

    # Write data.json
    with open(data_file, 'w') as f:
        json.dump(data, f, indent=4)

    print(f"\n✅ Both branches completed!")
    print(f"   Results saved to data.json")

    # Summary
    print(f"\n{'='*60}")
    print(f"📊 PIPELINE SUMMARY")
    print(f"{'='*60}")

    # Print results
    if 'step_results' in data:
        print(f"\n📋 Regular Results (step_results):")
        for key, val in data['step_results'].items():
            print(f"   - {key}: {val}")

    if 'slab_band' in data:
        print(f"\n📋 Slab Band Results (slab_band):")
        for key, val in data['slab_band'].items():
            print(f"   - {key}: {val}")

    print(f"\n🎉 Pipeline completed successfully!")

    # Upload BOTH Step10 SVGs to TTF SVG API
    try:
        print(f"\n📤 Uploading SVGs to TTF API...")
        from api.cloudinary_manager import upload_svg_to_api

        if 'svg_urls' not in data:
            data['svg_urls'] = {}

        # Upload no slab band version
        svg_no_slab = "files/Step10_no_slab_band.svg"
        if os.path.exists(svg_no_slab):
            svg_url = upload_svg_to_api(svg_no_slab)
            if svg_url:
                data['svg_urls']['step10_no_slab_band'] = svg_url
                data['svg_urls']['step10'] = svg_url  # Backwards compatibility
                print(f"✅ Step10_no_slab_band.svg uploaded: {svg_url}")
            else:
                print("⚠️  Failed to upload Step10_no_slab_band.svg")
        else:
            print(f"⚠️  {svg_no_slab} not found")

        # Upload with slab band version
        svg_with_slab = "files/Step10_with_slab_band.svg"
        if os.path.exists(svg_with_slab):
            svg_url = upload_svg_to_api(svg_with_slab)
            if svg_url:
                data['svg_urls']['step10_with_slab_band'] = svg_url
                print(f"✅ Step10_with_slab_band.svg uploaded: {svg_url}")
            else:
                print("⚠️  Failed to upload Step10_with_slab_band.svg")
        else:
            print(f"⚠️  {svg_with_slab} not found")

        # Write updated data.json with SVG URLs
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=4)

    except Exception as e:
        print(f"⚠️  Error uploading SVGs to TTF API: {str(e)}")

    # Now run Step11 (Step12 will run later after logs are saved)
    print(f"\n{'='*60}")
    print("📋 PHASE 4: Running Step11 (text extraction)")
    print(f"{'='*60}")

    success = run_single_step("Step11")
    if success:
        successful_steps += 1
    else:
        print(f"⚠️  Step11 failed, but pipeline will continue")

    # SVG URL updates will happen after Step12 in process_ai_takeoff_sync
    return True, None, None

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
async def get_ai_takeoff_result(
    upload_id: str,
    company: str = None,
    jobsite: str = None,
    background_tasks: BackgroundTasks = None,
    sync: bool = True
):
    # Store the Google Drive file ID in JSON as google_drive_file_id
    config_manager.set_file_id(upload_id)

    print(f"🔍 AI-Takeoff Request for upload_id: {upload_id}")
    print(f"📝 Stored Google Drive file ID in JSON as google_drive_file_id: {upload_id}")
    if company:
        print(f"🏢 Company: {company}")
    if jobsite:
        print(f"📍 Jobsite: {jobsite}")

    # Force synchronous processing by default, or if sync=True
    if sync:
        print(f"🔄 Running in synchronous mode...")
        return await process_ai_takeoff_sync(upload_id, company, jobsite)
    else:
        # Fallback to synchronous processing
        return await process_ai_takeoff_sync(upload_id, company, jobsite)

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


async def process_ai_takeoff_sync(upload_id: str, company: str = None, jobsite: str = None):
    """Synchronous processing"""
    try:
        await log_to_client(upload_id, f"📄 Starting PDF download for upload_id: {upload_id}")

        # Store company and jobsite in data.json early
        if company or jobsite:
            data_json_path = os.path.join('data.json')
            data = {}
            if os.path.exists(data_json_path):
                try:
                    with open(data_json_path, 'r') as f:
                        data = json.load(f)
                except:
                    data = {}
            if company:
                data['company'] = company
            if jobsite:
                data['jobsite'] = jobsite
            data['upload_id'] = upload_id
            with open(data_json_path, 'w') as f:
                json.dump(data, f, indent=4)
        
        # Step 1: Download the PDF
        try:
            file_path = download_pdf_from_drive(upload_id)
            if not file_path or not os.path.exists(file_path):
                error_msg = f"Failed to download PDF for upload_id: {upload_id}"
                await log_to_client(upload_id, f"❌ {error_msg}", "error")
                print(f"🚨 PDF DOWNLOAD FAILURE - Upload ID: {upload_id}")
                print(f"🚨 Error: {error_msg}")

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

                    # Parse logs into structured JSON format with timestamps
                    structured_logs = parse_logs_to_json(captured_logs, log_capture.start_time)

                    # Save structured logs to data.json
                    data_json_path = os.path.join('data.json')
                    if os.path.exists(data_json_path):
                        try:
                            with open(data_json_path, 'r') as f:
                                data = json.load(f)

                            data['processing_logs'] = structured_logs
                            data['processing_duration'] = processing_duration
                            data['processing_start_time'] = log_capture.start_time.isoformat()
                            data['processing_end_time'] = log_capture.end_time.isoformat()

                            with open(data_json_path, 'w') as f:
                                json.dump(data, f, indent=4)

                            print(f"✅ Saved {len(structured_logs)} log entries to data.json")
                        except Exception as log_error:
                            print(f"⚠️  Could not save logs to data.json: {log_error}")

                    # Now run Step12 to send data (including logs) to database
                    if pipeline_success:
                        print(f"\n{'='*60}")
                        print("📋 PHASE 5: Sending results to database (Step12)")
                        print(f"{'='*60}")
                        try:
                            from processors.Step12 import run_step12
                            step12_success = run_step12()
                            if step12_success:
                                print("✅ Step12 completed - Results sent to database")

                                # After Step12 creates the database record, update it with SVG URLs
                                try:
                                    # Re-read data.json to get the tracking_url created by Step12
                                    with open('data.json', 'r') as f:
                                        data_updated = json.load(f)

                                    tracking_url = data_updated.get('tracking_url')

                                    if tracking_url:
                                        print(f"\n📝 Updating database with SVG URLs...")
                                        from api.cloudinary_manager import update_svg_in_database

                                        # Update with no slab band SVG (primary)
                                        svg_url_no_slab = data_updated.get('svg_urls', {}).get('step10_no_slab_band')
                                        if svg_url_no_slab:
                                            if update_svg_in_database(tracking_url, svg_url_no_slab):
                                                print(f"✅ No slab band SVG URL saved to database")
                                            else:
                                                print(f"⚠️  Failed to update no slab band SVG URL in database")

                                        # Also update with slab band SVG if available
                                        svg_url_with_slab = data_updated.get('svg_urls', {}).get('step10_with_slab_band')
                                        if svg_url_with_slab:
                                            print(f"✅ With slab band SVG URL: {svg_url_with_slab}")
                                    else:
                                        print(f"⚠️  No tracking_url found - cannot update SVG in database")
                                except Exception as svg_update_error:
                                    print(f"⚠️  Error updating SVG URL in database: {svg_update_error}")
                            else:
                                print("⚠️  Step12 failed - Results not sent to database")
                        except Exception as step12_error:
                            print(f"⚠️  Step12 exception: {step12_error}")

                    if pipeline_success:
                        await log_to_client(upload_id, f"✅ Processing pipeline completed successfully")
                    else:
                        error_msg = f"❌ Processing pipeline failed at {failed_step}: {error_details}"
                        await log_to_client(upload_id, error_msg, "error")
                        print(f"🚨 PIPELINE FAILURE - Upload ID: {upload_id}")
                        print(f"🚨 Failed Step: {failed_step}")
                        print(f"🚨 Error Details: {error_details}")
                        print(f"🚨 Steps completed before failure: {failed_step}")

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
                    data_results = json.load(f)

                # Get result URL from tracking_url
                if 'tracking_url' in data_results:
                    # Use tracking URL from Step11
                    tracking_url = data_results['tracking_url']
                    api_url = os.environ.get('API_URL', 'https://ttfconstruction.com/ai-takeoff-results/create.php')
                    api_base = api_url.replace('/create.php', '')
                    result_url = f"{api_base}/read.php?tracking_url={tracking_url}"

                # Get SVG URL if available
                svg_url = None
                if 'svg_urls' in data_results and 'step10' in data_results['svg_urls']:
                    svg_url = data_results['svg_urls']['step10']

                # Return result with SVG URL
                result = {
                    "result_url": result_url,
                    "svg_url": svg_url
                }
            except Exception as e:
                await log_to_client(upload_id, f"❌ Error reading data.json: {e}", "error")
                print(f"Error reading data.json: {e}")
                result = None
        else:
            await log_to_client(upload_id, f"⚠️  data.json not found", "warning")
            result = None

        # Clear logs from storage
        get_log_storage().clear_log(upload_id)

    except Exception as e:
        error_msg = f"❌ Unexpected error in AI processing: {e}"
        await log_to_client(upload_id, error_msg, "error")
        print(f"🚨 UNEXPECTED ERROR - Upload ID: {upload_id}")
        print(f"🚨 Exception: {e}")
        print(f"🚨 Exception Type: {type(e).__name__}")

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
