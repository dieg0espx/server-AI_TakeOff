#!/usr/bin/env python3
"""
Contour-based Object Detection for Blue X Shapes
Uses OpenCV contour detection to find individual blue X shapes
"""

import cv2
import numpy as np
from pathlib import Path
import argparse
import re
import os
import shutil
import sys
import json
from datetime import datetime
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import cairosvg
import io
from PIL import Image
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


def save_x_shapes_to_json(x_shapes_data, output_path):
    """Save X shapes data to JSON file"""
    try:
        # Create the JSON structure
        json_data = {
            "total_x_shapes": len(x_shapes_data),
            "x_shapes": x_shapes_data
        }
        
        # Write to JSON file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        print(f"X shapes data saved to: {output_path}")
        return True
    except Exception as e:
        print(f"Error saving X shapes data to JSON: {e}")
        return False

def svg_to_image(svg_path, output_path=None):
    """Convert SVG to PIL Image"""
    try:
        # Convert SVG to PNG bytes
        png_data = cairosvg.svg2png(url=svg_path)
        
        # Convert to PIL Image
        image = Image.open(io.BytesIO(png_data))
        
        if output_path:
            # Save as PNG if output path is provided
            image.save(output_path, 'PNG')
            
            print(f"SVG converted and saved as: {output_path}")
        
        return image
    except Exception as e:
        
        print(f"Error converting SVG to image: {e}", "error")
        return None

def detect_blue_x_shapes(image_path, output_path='results.png', json_output_path=None):
    """Detect individual blue X shapes using contour detection"""
    
    print(f"Processing image: {image_path}")
    
    # Check if input is SVG and convert if needed
    if str(image_path).lower().endswith('.svg'):
        
        print("Converting SVG to image for processing...")
        pil_image = svg_to_image(image_path)
        if pil_image is None:
            return 0, []
        
        # Convert PIL Image to OpenCV format
        img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    else:
        # Read image directly if it's not SVG
        img = cv2.imread(str(image_path))
    
    if img is None:
        
        print(f"Error: Could not read image {image_path}", "error")
        return 0, []
    
    # Convert to HSV for better color detection
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Define blue color range in HSV
    # Blue in HSV: H=120, S=255, V=255
    lower_blue = np.array([100, 50, 50])   # Darker blue
    upper_blue = np.array([130, 255, 255]) # Lighter blue
    
    # Create mask for blue objects
    blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
    
    # Apply morphological operations to clean up the mask
    kernel = np.ones((3,3), np.uint8)
    blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_CLOSE, kernel)
    blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_OPEN, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours based on area and shape
    valid_contours = []
    for contour in contours:
        area = cv2.contourArea(contour)
        
        # Filter by area (adjust these values based on your X shapes)
        if 30 < area < 2000:  # Broader range to catch all potential X shapes
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            
            # Check aspect ratio (X shapes should be roughly square)
            aspect_ratio = w / h if h > 0 else 0
            # Ensure width/height ratio is within 1.5 tolerance (max 1.5:1 or 1:1.5)
            if 0.67 < aspect_ratio < 1.5:  # 1/1.5 = 0.67, 1.5/1 = 1.5
                # Additional check: ensure reasonable size
                if w >= 5 and h >= 5:  # Minimum size requirement
                    valid_contours.append((contour, x, y, w, h, area))
    
    print(f"Found {len(valid_contours)} initial contours")
    
    # Group nearby contours to identify individual X shapes
    if len(valid_contours) > 0:
        # Sort by area to prioritize larger contours
        valid_contours.sort(key=lambda x: x[5], reverse=True)
        
        # Group contours that are close to each other
        grouped_contours = []
        used_indices = set()
        
        for i, (contour, x, y, w, h, area) in enumerate(valid_contours):
            if i in used_indices:
                continue
                
            # Find contours that are close to this one
            nearby_contours = [(contour, x, y, w, h, area)]
            used_indices.add(i)
            
            center_x = x + w/2
            center_y = y + h/2
            
            for j, (contour2, x2, y2, w2, h2, area2) in enumerate(valid_contours):
                if j in used_indices:
                    continue
                    
                center_x2 = x2 + w2/2
                center_y2 = y2 + h2/2
                
                # Calculate distance between centers
                distance = ((center_x - center_x2)**2 + (center_y - center_y2)**2)**0.5
                
                # If contours are very close, group them (much stricter for X shapes)
                if distance < 15:  # Reduced from 30 to 15 for tighter grouping
                    nearby_contours.append((contour2, x2, y2, w2, h2, area2))
                    used_indices.add(j)
            
            # Calculate combined bounding box for the group
            if nearby_contours:
                min_x = min(c[1] for c in nearby_contours)
                min_y = min(c[2] for c in nearby_contours)
                max_x = max(c[1] + c[3] for c in nearby_contours)
                max_y = max(c[2] + c[4] for c in nearby_contours)
                
                group_w = max_x - min_x
                group_h = max_y - min_y
                
                # Apply aspect ratio constraint to grouped bounding boxes too
                group_aspect_ratio = group_w / group_h if group_h > 0 else 0
                if 0.67 < group_aspect_ratio < 1.5:  # Same 1.5 tolerance as individual contours
                    grouped_contours.append((nearby_contours, min_x, min_y, group_w, group_h))
                else:
                    # If grouped bounding box doesn't meet aspect ratio, treat each contour individually
                    for contour, x, y, w, h, area in nearby_contours:
                        grouped_contours.append(([(contour, x, y, w, h, area)], x, y, w, h))
        
        valid_contours = grouped_contours
        print(f"Grouped into {len(valid_contours)} X shapes")
    
    # Collect X shapes data for JSON output
    x_shapes_data = []
    
    # Draw results
    result_img = img.copy()
    
    # Draw contours and bounding boxes
    for i, (contours_group, x, y, w, h) in enumerate(valid_contours):
        # Draw all contours in the group
        for contour, _, _, _, _, _ in contours_group:
            cv2.drawContours(result_img, [contour], -1, (0, 255, 0), 1)
        
        # Draw bounding box around the group
        cv2.rectangle(result_img, (int(x), int(y)), (int(x + w), int(y + h)), (0, 255, 0), 2)
        
        # Add label
        label = f"X{i+1}"
        cv2.putText(result_img, label, (int(x), int(y)-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Collect data for JSON
        x_shape_data = {
            "id": i + 1,
            "x": float(x),
            "y": float(y),
            "width": float(w),
            "height": float(h),
            "center_x": float(x + w / 2),
            "center_y": float(y + h / 2),
            "area": float(w * h),
            "contours_count": len(contours_group)
        }
        x_shapes_data.append(x_shape_data)
        
        print(f"X{i+1}: Size={w:.1f}x{h:.1f}, Contours={len(contours_group)}")
    
    # Save result image
    if output_path.lower().endswith('.svg'):
        # Convert back to PIL and save as SVG-compatible format
        result_pil = Image.fromarray(cv2.cvtColor(result_img, cv2.COLOR_BGR2RGB))
        # For now, save as PNG with SVG extension (you might want to convert back to SVG)
        png_path = output_path.replace('.svg', '.png')
        cv2.imwrite(png_path, result_img)
        print(f"Result saved as: {png_path} (PNG format)")
    else:
        cv2.imwrite(output_path, result_img)
        print(f"Result saved as: {output_path}")
    
    # Save X shapes data to JSON if path provided
    if json_output_path:
        save_x_shapes_to_json(x_shapes_data, json_output_path)
    
    print(f"Total X shapes detected: {len(valid_contours)}")
    
    return len(valid_contours), x_shapes_data

def process_svg_colors(input_svg, output_svg):
    """
    Process SVG colors by replacing most hex colors with #202124,
    while keeping #0000ff and #fb0505 unchanged.
    """
    try:
        # Read the SVG file
        with open(input_svg, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Find all hex color codes (#xxxxxx)
        hex_pattern = r'#([0-9a-fA-F]{6})'
        
        def replace_color(match):
            color = match.group(1).lower()
            # Keep #0000ff and #fb0505 unchanged, replace all others with #202124
            if color == '0000ff' or color == 'fb0505':
                return match.group(0)  # Return original match unchanged
            else:
                return '#202124'
        
        # Replace colors using the function
        processed_content = re.sub(hex_pattern, replace_color, content)
        
        # Write the processed content to a new file
        with open(output_svg, 'w', encoding='utf-8') as file:
            file.write(processed_content)
        
        
        print("SVG processing completed!")
        print("Original colors replaced with #202124 (except #0000ff)")
        print(f"Output saved to: {output_svg}")
        
    except FileNotFoundError:
        
        print(f"Error: Could not find input file {input_svg}", "error")
    except Exception as e:
        
        print(f"Error processing SVG: {e}", "error")

def run_step5():
    """
    Run Step5 processing - detect blue X shapes
    """
    try:
        # Get the current working directory to determine the correct paths
        current_dir = os.getcwd()
        
        # If we're in the processors directory, use relative paths
        if current_dir.endswith('processors'):
            input_svg = "../files/Step4.svg"
            output_svg = "../files/Step5.svg"
            output_results = "../files/Step5-results.svg"
            json_output = "../x-shores.json"
        else:
            # If we're in the server directory (when called from pipeline), use direct paths
            input_svg = "files/Step4.svg"
            output_svg = "files/Step5.svg"
            output_results = "files/Step5-results.svg"
            json_output = "x-shores.json"
        
        # First process SVG colors
        process_svg_colors(input_svg, output_svg)
        
        # Then detect blue X shapes on the processed SVG
        
        print(f"Detecting blue X shapes in: {output_svg}")
        count, x_shapes_data = detect_blue_x_shapes(output_svg, output_results, json_output)
        print(f"\nFinal count: {count} blue X shapes")
        
        return True
        
    except Exception as e:
        
        print(f"Error in processing: {e}", "error")
        return False

def main():
    parser = argparse.ArgumentParser(description='Contour-based Blue X Detection')
    parser.add_argument('--source', type=str, default='test-images/test1.png',
                       help='Path to image')
    parser.add_argument('--output', type=str, default='results.png',
                       help='Output image path')
    
    args = parser.parse_args()
    
    # Check if source exists
    source_path = Path(args.source)
    if not source_path.exists():
        
        print(f"Error: Source not found at {source_path}", "error")
        return
    
    # Detect X shapes
    count, x_shapes_data = detect_blue_x_shapes(source_path, args.output)
    
    print(f"\nFinal count: {count} blue X shapes")

if __name__ == "__main__":
    try:
        # Get the current working directory to determine the correct paths
        current_dir = os.getcwd()
        
        # If we're in the processors directory, use relative paths
        if current_dir.endswith('processors'):
            input_svg = "../files/Step4.svg"
            output_svg = "../files/Step5.svg"
            output_results = "../files/Step5-results.svg"
            json_output = "../x-shores.json"
        else:
            # If we're in the server directory (when called from pipeline), use direct paths
            input_svg = "files/Step4.svg"
            output_svg = "files/Step5.svg"
            output_results = "files/Step5-results.svg"
            json_output = "x-shores.json"
        
        # First process SVG colors
        process_svg_colors(input_svg, output_svg)
        
        # Then detect blue X shapes on the processed SVG
        
        print(f"Detecting blue X shapes in: {output_svg}")
        count, x_shapes_data = detect_blue_x_shapes(output_svg, output_results, json_output)
        print(f"\nFinal count: {count} blue X shapes")
        
    except Exception as e:
        
        print(f"Error in processing: {e}", "error")