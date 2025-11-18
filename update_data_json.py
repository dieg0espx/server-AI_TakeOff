#!/usr/bin/env python3
"""
Update data.json with current step results from JSON files
"""
import json
import os
from pathlib import Path

def load_json_file(file_path):
    """Load JSON file and return data"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def update_step_results():
    """Update data.json with current counts from all JSON files"""
    base_dir = Path(__file__).parent

    # Load all the JSON files
    green_frames_path = base_dir / "files" / "tempData" / "greenFrames.json"
    pink_frames_path = base_dir / "files" / "tempData" / "pinkFrames.json"
    x_shapes_path = base_dir / "files" / "tempData" / "x-shores.json"
    red_squares_path = base_dir / "files" / "tempData" / "square-shores.json"
    orange_frames_path = base_dir / "files" / "tempData" / "orangeFrames.json"
    yellow_frames_path = base_dir / "files" / "tempData" / "yellowFrames.json"

    # Load data from JSON files
    green_data = load_json_file(green_frames_path)
    pink_data = load_json_file(pink_frames_path)
    x_data = load_json_file(x_shapes_path)
    red_data = load_json_file(red_squares_path)
    orange_data = load_json_file(orange_frames_path)
    yellow_data = load_json_file(yellow_frames_path)

    # Extract counts
    green_count = len(green_data.get('rectangles', [])) if green_data else 0
    pink_count = len(pink_data.get('pink_shapes', [])) if pink_data else 0
    x_count = len(x_data.get('x_shapes', [])) if x_data else 0
    red_count = len(red_data.get('red_squares', [])) if red_data else 0
    orange_count = len(orange_data.get('rectangles', [])) if orange_data else 0
    yellow_count = len(yellow_data.get('shapes', [])) if yellow_data else 0

    # Create step_results dictionary
    step_results = {
        "step5_blue_X_shapes": x_count,
        "step6_red_squares": red_count,
        "step7_pink_shapes": pink_count,
        "step8_green_rectangles": green_count,
        "step9_orange_rectangles": orange_count,
        "step11_yellow_shapes": yellow_count
    }

    # Load existing data.json
    data_file = base_dir / "data.json"
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            data = json.load(f)
    else:
        data = {}

    # Update step_results
    data["step_results"] = step_results

    # Write back to data.json
    with open(data_file, 'w') as f:
        json.dump(data, f, indent=4)

    print("✅ Updated data.json with current step results:")
    print(f"   - Blue X Shapes (Step 5): {x_count}")
    print(f"   - Red Squares (Step 6): {red_count}")
    print(f"   - Pink Shapes (Step 7): {pink_count}")
    print(f"   - Green Rectangles (Step 8): {green_count}")
    print(f"   - Orange Rectangles (Step 9): {orange_count}")
    print(f"   - Yellow Shapes (Step 11): {yellow_count}")
    print(f"   - TOTAL: {x_count + red_count + pink_count + green_count + orange_count + yellow_count}")

    return True

if __name__ == "__main__":
    update_step_results()
