#!/usr/bin/env python3
"""
Test script to verify JSON file reading is working correctly
"""

import json
import os

# Test reading the JSON files with correct paths
json_files = {
    'files/tempData/x-shores.json': ('step5_blue_X_shapes', 'total_x_shapes'),
    'files/tempData/square-shores.json': ('step6_red_squares', 'total_red_squares'),
    'files/tempData/pinkFrames.json': ('step7_pink_shapes', 'total_pink_shapes'),
    'files/tempData/greenFrames.json': ('step8_green_rectangles', 'total_rectangles'),
    'files/tempData/orangeFrames.json': ('step9_orange_rectangles', 'total_rectangles')
}

print("=" * 60)
print("Testing JSON File Reading")
print("=" * 60)

step_counts = {}

for json_file, (result_key, json_field) in json_files.items():
    print(f"\nChecking: {json_file}")
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
                    print(f"   Available fields: {list(data.keys())}")
                    step_counts[result_key] = 0
        except Exception as e:
            print(f"   ❌ Error reading {json_file}: {e}")
            step_counts[result_key] = 0
    else:
        print(f"   ❌ File not found: {json_file}")
        step_counts[result_key] = 0

print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
for key, value in step_counts.items():
    print(f"{key}: {value}")
print(f"\nTotal detections: {sum(step_counts.values())}")
print("=" * 60)
