import os
import sys
import importlib.util
import json
from pathlib import Path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def run_step(step_name, capture_output=False):
    """
    Dynamically import and run a processing step
    """
    try:
        # Construct the path to the step file
        step_file = f"processors/{step_name}.py"
        
        if not os.path.exists(step_file):
            print(f"Step file {step_file} not found. Skipping...")
            return False, None
        
        print(f"\n{'='*50}")
        print(f"Running {step_name}...")
        print(f"{'='*50}")
        
        # Add processors directory to Python path so step modules can import from each other
        processors_dir = os.path.abspath("processors")
        if processors_dir not in sys.path:
            sys.path.insert(0, processors_dir)
        
        # Import and run the step
        spec = importlib.util.spec_from_file_location(step_name, step_file)
        step_module = importlib.util.module_from_spec(spec)
        
        # Add the module to sys.modules so it can be imported by other modules
        sys.modules[step_name] = step_module
        
        spec.loader.exec_module(step_module)
        
        # Call the run function for the step
        run_function_name = f'run_{step_name.lower()}'
        if hasattr(step_module, run_function_name):
            run_function = getattr(step_module, run_function_name)
            
            if capture_output:
                # Capture output while also displaying it to console
                import io
                import contextlib
                
                # Create a custom stream that writes to both console and buffer
                class TeeOutput:
                    def __init__(self, original_stdout):
                        self.original_stdout = original_stdout
                        self.buffer = io.StringIO()
                    
                    def write(self, text):
                        self.original_stdout.write(text)
                        self.buffer.write(text)
                    
                    def flush(self):
                        self.original_stdout.flush()
                        self.buffer.flush()
                
                # Replace stdout with our tee stream
                original_stdout = sys.stdout
                tee_output = TeeOutput(original_stdout)
                sys.stdout = tee_output
                
                try:
                    success = run_function()
                    output = tee_output.buffer.getvalue()
                    
                    # Extract count based on step
                    count = extract_count_from_output(step_name, output)
                    
                    if success:
                        print(f"✅ {step_name} completed successfully")
                        return True, count
                    else:
                        print(f"❌ {step_name} failed")
                        return False, None
                finally:
                    # Restore original stdout
                    sys.stdout = original_stdout
            else:
                success = run_function()
                if success:
                    print(f"✅ {step_name} completed successfully")
                    return True, None
                else:
                    print(f"❌ {step_name} failed")
                    return False, None
        else:
            print(f"⚠️  No run function found for {step_name}")
            return False, None
        
    except Exception as e:
        print(f"❌ Error running {step_name}: {str(e)}")
        return False, None

def extract_count_from_output(step_name, output):
    """
    Extract count from step output based on step name
    Only Steps 5-8 have count patterns to extract
    """
    count_patterns = {
        "Step5": "Final count: ",
        "Step6": "Total squares detected: ",
        "Step7": "Final count: ",
        "Step8": "Total rectangles detected: "
    }
    
    # Only extract counts for Steps 5-8
    if step_name not in count_patterns:
        return None
    
    pattern = count_patterns.get(step_name)
    if not pattern:
        return None
    
    for line in output.split('\n'):
        if pattern in line:
            try:
                count = int(line.split(pattern)[1].split()[0])
                return count
            except (IndexError, ValueError):
                continue
    
    return None



def update_data_json(step_counts):
    """
    Update data.json with the collected step counts and Cloudinary URLs
    """
    try:
        # Read existing data.json
        data_file = "data.json"
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
        else:
            data = {}
        
        # Add step results section
        data["step_results"] = step_counts
        
        # Upload images to Cloudinary and get URLs
        try:
            # Add the parent directory to sys.path to find the api module
            parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)
            
            from api.cloudinary_manager import get_cloudinary_manager
            cloudinary_manager = get_cloudinary_manager()
            
            if cloudinary_manager:
                print("☁️  Uploading processing results to Cloudinary...")
                cloudinary_urls = cloudinary_manager.upload_processing_results(step_counts)
                
                if cloudinary_urls:
                    data["cloudinary_urls"] = cloudinary_urls
                    print(f"✅ Successfully uploaded {len(cloudinary_urls)} images to Cloudinary")
                else:
                    print("⚠️  No images were uploaded to Cloudinary")
            else:
                print("⚠️  Cloudinary not configured - skipping image uploads")
                
        except Exception as e:
            print(f"⚠️  Error uploading to Cloudinary: {str(e)}")
        
        # Write back to data.json
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=4)
        
        print(f"✅ Updated {data_file} with step results and Cloudinary URLs")
        return True
        
    except Exception as e:
        print(f"❌ Error updating data.json: {str(e)}")
        return False

def check_prerequisites():
    """
    Check if required files exist before starting processing
    """
    required_files = [
        "files/original.svg",
        "utils/config.json"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing required files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False
    
    print("✅ All required files found")
    return True

def main():
    """
    Main orchestrator function that runs all processing steps
    """
    print("🚀 Starting AI TakeOff Processing Pipeline")
    print("=" * 60)
    
    # Check prerequisites
    if not check_prerequisites():
        print("❌ Prerequisites not met. Exiting.")
        return False
    
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
    for step in steps:
        # Capture output for all steps to show progress and extract counts from Steps 5-8
        capture_output = True
        success, count = run_step(step, capture_output)
        
        if success:
            successful_steps += 1
            # Store count if captured (only for Steps 5-8)
            if count is not None:
                step_descriptions = {
                    "Step5": "blue_X_shapes",
                    "Step6": "red_squares", 
                    "Step7": "pink_shapes",
                    "Step8": "green_rectangles"
                }
                step_number = step.lower().replace("step", "step")
                step_counts[f"{step_number}_{step_descriptions[step]}"] = count
        else:
            print(f"⚠️  Pipeline stopped due to failure in {step}")
            break
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 Processing Summary")
    print(f"{'='*60}")
    print(f"Steps completed: {successful_steps}/{total_steps}")
    
    if successful_steps == total_steps:
        print("🎉 All steps completed successfully!")
        
        # Update data.json with the collected counts
        if step_counts:
            if update_data_json(step_counts):
                print("✅ Step counts successfully stored in data.json")
            else:
                print("⚠️  Failed to store step counts in data.json")
        
        # Check if data.json was created/updated
        if os.path.exists("data.json"):
            try:
                with open("data.json", 'r') as f:
                    data = json.load(f)
                print("📄 data.json updated with processing results")
                if 'original_drawing' in data:
                    print(f"   - Original drawing URL: {data['original_drawing']}")
                if 'step_results' in data:
                    print("   - Step results:")
                    for step, count in data['step_results'].items():
                        print(f"     * {step}: {count}")
                if 'cloudinary_urls' in data:
                    print("   - Cloudinary URLs:")
                    for step, url in data['cloudinary_urls'].items():
                        print(f"     * {step}: {url}")
            except Exception as e:
                print(f"⚠️  Could not read data.json: {e}")
    else:
        print("⚠️  Pipeline completed with some failures")
        # Don't exit the server, just return False to indicate failure
        return False
    
    return True

if __name__ == "__main__":
    # Change to the server directory to ensure proper file paths
    server_dir = Path(__file__).parent.parent
    os.chdir(server_dir)
    
    main()