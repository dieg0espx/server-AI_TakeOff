import os
import sys
import importlib.util
import json
from pathlib import Path

def run_step(step_name):
    """
    Dynamically import and run a processing step
    """
    try:
        # Construct the path to the step file
        step_file = f"processors/{step_name}.py"
        
        if not os.path.exists(step_file):
            print(f"Step file {step_file} not found. Skipping...")
            return False
        
        print(f"\n{'='*50}")
        print(f"Running {step_name}...")
        print(f"{'='*50}")
        
        # Import and run the step
        spec = importlib.util.spec_from_file_location(step_name, step_file)
        step_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(step_module)
        
        # Call the run function for the step
        if hasattr(step_module, f'run_{step_name.lower()}'):
            success = step_module.run_step1()
            if success:
                print(f"✅ {step_name} completed successfully")
                return True
            else:
                print(f"❌ {step_name} failed")
                return False
        else:
            print(f"⚠️  No run function found for {step_name}")
            return False
        
    except Exception as e:
        print(f"❌ Error running {step_name}: {str(e)}")
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
        "Step1",  # Remove duplicate paths and convert to PNG
        # Add future steps here as they are created:
        # "Step2",  # Example: Color analysis
        # "Step3",  # Example: Shape detection
        # "Step4",  # Example: Pattern recognition
    ]
    
    successful_steps = 0
    total_steps = len(steps)
    
    # Run each step in sequence
    for step in steps:
        if run_step(step):
            successful_steps += 1
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
        
        # Check if data.json was created/updated
        if os.path.exists("data.json"):
            try:
                with open("data.json", 'r') as f:
                    data = json.load(f)
                print("📄 data.json updated with processing results")
                if 'original_drawing' in data:
                    print(f"   - Original drawing URL: {data['original_drawing']}")
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