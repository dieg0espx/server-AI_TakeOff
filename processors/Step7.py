#!/usr/bin/env python3
"""
Contour-based Object Detection for Irregular Pink Shapes
Uses OpenCV contour detection to find individual pink shapes of any form
"""

import re
import math
import os
import cv2
import numpy as np
from pathlib import Path
import argparse
import shutil
import sys
from datetime import datetime
import cairosvg
import io
from PIL import Image
import json
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


def save_pink_frames_to_json(pink_frames_data, output_path):
    """Save pink frame data to JSON file"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(pink_frames_data, f, indent=2, ensure_ascii=False)
        print(f"Pink frames data saved to: {output_path}")
    except Exception as e:
        print(f"Error saving pink frames to JSON: {e}")

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

def detect_pink_shapes(image_path, output_path='pink_results.png', save_json=True):
    """Detect individual pink shapes using contour detection"""
    
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
    
    # Define pink color range in HSV
    # Pink #ff00cd in RGB = (255, 0, 205) in BGR = (205, 0, 255)
    # Converting to HSV: H≈300, S≈100, V≈100
    # We need to account for HSV range: H=0-179, S=0-255, V=0-255
    # So H=300 becomes H=150 (300/2), S=100 becomes S=255, V=100 becomes V=255
    
    # Pink color range in HSV (adjusted for OpenCV's HSV range)
    lower_pink = np.array([140, 50, 50])   # Darker pink/magenta
    upper_pink = np.array([170, 255, 255]) # Lighter pink/magenta
    
    # Create mask for pink objects
    pink_mask = cv2.inRange(hsv, lower_pink, upper_pink)
    
    # Apply morphological operations to clean up the mask
    kernel = np.ones((3,3), np.uint8)
    pink_mask = cv2.morphologyEx(pink_mask, cv2.MORPH_CLOSE, kernel)
    pink_mask = cv2.morphologyEx(pink_mask, cv2.MORPH_OPEN, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(pink_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours based on area (removed shape constraints for irregular shapes)
    valid_contours = []
    for contour in contours:
        area = cv2.contourArea(contour)
        
        # Filter by area (adjust these values based on your pink shapes)
        if 20 < area < 5000:  # Broader range to catch all potential pink shapes
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            
            # Check minimum size requirement
            if w >= 3 and h >= 3:  # Minimum size requirement
                valid_contours.append((contour, x, y, w, h, area))
    
    print(f"Found {len(valid_contours)} initial pink contours")
    
    # Group nearby contours to identify individual pink shapes
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
                
                # If contours are very close, group them
                if distance < 20:  # Adjusted for pink shapes
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
                
                grouped_contours.append((nearby_contours, min_x, min_y, group_w, group_h))
        
        valid_contours = grouped_contours
        print(f"Grouped into {len(valid_contours)} pink shapes")
    
    # Prepare pink frames data for JSON storage
    pink_frames_data = {
        "total_pink_shapes": len(valid_contours),
        "pink_shapes": []
    }
    
    # Draw results and collect data
    result_img = img.copy()
    
    # Draw contours and bounding boxes
    for i, (contours_group, x, y, w, h) in enumerate(valid_contours):
        # Draw all contours in the group
        for contour, _, _, _, _, _ in contours_group:
            cv2.drawContours(result_img, [contour], -1, (0, 255, 0), 1)
        
        # Draw bounding box around the group
        cv2.rectangle(result_img, (int(x), int(y)), (int(x + w), int(y + h)), (0, 255, 0), 2)
        
        # Add label
        label = f"Pink{i+1}"
        cv2.putText(result_img, label, (int(x), int(y)-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Calculate total area for this shape
        total_area = sum(c[5] for c in contours_group)
        
        # Calculate center coordinates
        center_x = x + w / 2
        center_y = y + h / 2
        
        # Store pink shape data
        pink_shape_data = {
            "id": i + 1,
            "x": float(x),
            "y": float(y),
            "width": float(w),
            "height": float(h),
            "center_x": float(center_x),
            "center_y": float(center_y),
            "area": float(total_area),
            "contours_count": len(contours_group)
        }
        
        pink_frames_data["pink_shapes"].append(pink_shape_data)
        
        print(f"Pink{i+1}: Size={w:.1f}x{h:.1f}, Area={total_area:.1f}, Contours={len(contours_group)}")
    
    # Save result
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
    
    # Save pink frames data to JSON if requested
    if save_json:
        # Determine the JSON output path
        if output_path.lower().endswith('.svg'):
            json_path = output_path.replace('.svg', '_frames.json')
        else:
            json_path = output_path.replace('.png', '_frames.json')
        
        # If we're in processors directory, adjust path for JSON
        current_dir = os.getcwd()
        if current_dir.endswith('processors'):
            json_path = json_path.replace('../files/', '../')
        
        save_pink_frames_to_json(pink_frames_data, json_path)
    
    print(f"Total pink shapes detected: {len(valid_contours)}")
    
    return len(valid_contours), pink_frames_data

def parse_path_data(d):
    """Parse SVG path data to extract coordinates"""
    commands = []
    current = ""
    for char in d:
        if char in 'MmLlHhVvCcSsQqTtAaZz':
            if current:
                commands.append(current.strip())
            current = char
        else:
            current += char
    if current:
        commands.append(current.strip())
    
    coordinates = []
    x, y = 0, 0
    
    for cmd in commands:
        if not cmd:
            continue
        command = cmd[0]
        params = cmd[1:].strip()
        
        if command in 'MmLl':
            # Move or line to
            coords = [float(x) for x in re.findall(r'[-+]?\d*\.?\d+', params)]
            for i in range(0, len(coords), 2):
                if i + 1 < len(coords):
                    if command.isupper():
                        x, y = coords[i], coords[i + 1]
                    else:
                        x += coords[i]
                        y += coords[i + 1]
                    coordinates.append((x, y))
        elif command in 'Hh':
            # Horizontal line
            coords = [float(x) for x in re.findall(r'[-+]?\d*\.?\d+', params)]
            for coord in coords:
                if command.isupper():
                    x = coord
                else:
                    x += coord
                coordinates.append((x, y))
        elif command in 'Vv':
            # Vertical line
            coords = [float(x) for x in re.findall(r'[-+]?\d*\.?\d+', params)]
            for coord in coords:
                if command.isupper():
                    y = coord
                else:
                    y += coord
                coordinates.append((x, y))
    
    return coordinates

def calculate_bounding_box(coordinates):
    """Calculate the bounding box of coordinates"""
    if not coordinates:
        return None
    
    min_x = min(coord[0] for coord in coordinates)
    max_x = max(coord[0] for coord in coordinates)
    min_y = min(coord[1] for coord in coordinates)
    max_y = max(coord[1] for coord in coordinates)
    
    return min_x, min_y, max_x, max_y

def path_to_rect(match):
    """Convert a path element to a rect element"""
    full_match = match.group(0)
    path_id = match.group(1) if match.group(1) else ""
    style = match.group(2)
    d = match.group(3)
    
    # Parse the path data
    coordinates = parse_path_data(d)
    
    if not coordinates:
        return full_match  # Return original if we can't parse
    
    # Calculate bounding box
    bbox = calculate_bounding_box(coordinates)
    if not bbox:
        return full_match
    
    min_x, min_y, max_x, max_y = bbox
    width = max_x - min_x
    height = max_y - min_y
    
    # Add some padding to make the square more visible
    padding = max(width, height) * 0.1
    width += padding * 2
    height += padding * 2
    min_x -= padding
    min_y -= padding
    
    # Create rect element
    rect_element = f'<rect\n           id="{path_id}"\n           style="{style}"\n           x="{min_x}"\n           y="{min_y}"\n           width="{width}"\n           height="{height}" />'
    
    return rect_element

def process_svg_colors(input_svg, output_svg):
    """
    Process SVG colors by replacing most hex colors with #202124,
    while keeping #ff00cd unchanged and converting strokes to fills.
    """
    try:
        # Read the SVG file
        with open(input_svg, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Create first output: only pink elements (#ff00cd)
        def keep_only_pink(match):
            color = match.group(1).lower()
            if color == 'ff00cd':
                return match.group(0)  # Keep pink
            else:
                return '#202124'  # Replace others with dark gray
        
        # Replace colors for pink-only version (intermediate step)
        pink_only_content = re.sub(r'#([0-9a-fA-F]{6})', keep_only_pink, content)
        
        # Create second output: filled shapes version
        # Find all hex color codes (#xxxxxx)
        hex_pattern = r'#([0-9a-fA-F]{6})'
        
        def replace_color(match):
            color = match.group(1).lower()
            # Keep #ff00cd unchanged, replace all others with #202124
            if color == 'ff00cd':
                return match.group(0)  # Return original match unchanged
            else:
                return '#202124'
        
        # Replace colors using the function
        processed_content = re.sub(hex_pattern, replace_color, content)
        
        # Now convert #ff00cd stroke elements to filled shapes
        # Pattern to match style attributes with #ff00cd stroke and fill:none
        stroke_to_fill_pattern = r'style="([^"]*fill:none[^"]*stroke:#ff00cd[^"]*)"'
        
        def convert_stroke_to_fill(match):
            style_attr = match.group(1)
            # Replace fill:none with fill:#ff00cd and remove stroke-related attributes
            new_style = style_attr.replace('fill:none', 'fill:#ff00cd')
            # Remove stroke-related attributes
            new_style = re.sub(r'stroke:#ff00cd[^;]*;?', '', new_style)
            new_style = re.sub(r'stroke-width:[^;]*;?', '', new_style)
            new_style = re.sub(r'stroke-linecap:[^;]*;?', '', new_style)
            new_style = re.sub(r'stroke-linejoin:[^;]*;?', '', new_style)
            new_style = re.sub(r'stroke-miterlimit:[^;]*;?', '', new_style)
            new_style = re.sub(r'stroke-dasharray:[^;]*;?', '', new_style)
            new_style = re.sub(r'stroke-opacity:[^;]*;?', '', new_style)
            # Clean up any double semicolons or trailing semicolons
            new_style = re.sub(r';;+', ';', new_style)
            new_style = new_style.strip(';')
            return f'style="{new_style}"'
        
        # Apply the stroke-to-fill conversion
        processed_content = re.sub(stroke_to_fill_pattern, convert_stroke_to_fill, processed_content)
        
        # Convert Z-shaped paths to rectangles
        # Pattern to match path elements with #ff00cd fill
        path_pattern = r'<path\s+([^>]*id="([^"]*)"[^>]*)?\s+style="([^"]*fill:#ff00cd[^"]*)"[^>]*d="([^"]*)"[^>]*/>'
        
        # Apply the path-to-rect conversion
        processed_content = re.sub(path_pattern, path_to_rect, processed_content)
        
        # Write the processed content to the output file
        with open(output_svg, 'w', encoding='utf-8') as file:
            file.write(processed_content)
        
        
        print("SVG processing completed!")
        print("Original colors replaced with #202124 (except #ff00cd)")
        print(f"Output saved to: {output_svg}")
        
    except FileNotFoundError:
        
        print(f"Error: Could not find input file {input_svg}", "error")
    except Exception as e:
        
        print(f"Error processing SVG: {e}", "error")

def run_step7():
    """
    Run Step7 processing - detect pink shapes
    """
    try:
        # Get the current working directory to determine the correct paths
        current_dir = os.getcwd()
        
        # If we're in the processors directory, use relative paths
        if current_dir.endswith('processors'):
            input_svg = "../files/Step4.svg"
            output_svg = "../files/Step7.svg"
            output_results = "../files/Step7-results.png"
            json_output = "../pinkFrames.json"
        else:
            # If we're in the server directory (when called from pipeline), use direct paths
            input_svg = "files/Step4.svg"
            output_svg = "files/Step7.svg"
            output_results = "files/Step7-results.png"
            json_output = "pinkFrames.json"
        
        # First process SVG colors
        process_svg_colors(input_svg, output_svg)
        
        # Then detect pink shapes on the processed SVG
        
        print(f"Detecting pink shapes in: {output_svg}")
        count, pink_frames_data = detect_pink_shapes(output_svg, output_results, save_json=False)
        
        # Save pink frames data to the specified JSON file
        save_pink_frames_to_json(pink_frames_data, json_output)
        
        print(f"\nFinal count: {count} pink shapes")
        print(f"Pink frames data saved to: {json_output}")
        
        return True
        
    except Exception as e:
        
        print(f"Error in processing: {e}", "error")
        return False

def main():
    parser = argparse.ArgumentParser(description='Contour-based Pink Shape Detection')
    parser.add_argument('--source', type=str, default='test/test1.png',
                       help='Path to image')
    parser.add_argument('--output', type=str, default='pink_results.png',
                       help='Output image path')
    parser.add_argument('--json-output', type=str, default='pinkFrames.json',
                       help='Output JSON file path')
    
    args = parser.parse_args()
    
    # Check if source exists
    source_path = Path(args.source)
    if not source_path.exists():
        print(f"Error: Source not found at {source_path}", "error")
        return
    
    # Detect pink shapes
    count, pink_frames_data = detect_pink_shapes(source_path, args.output, save_json=False)
    
    # Save pink frames data to JSON
    save_pink_frames_to_json(pink_frames_data, args.json_output)
    
    print(f"\nFinal count: {count} pink shapes")
    print(f"Pink frames data saved to: {args.json_output}")

if __name__ == "__main__":
    try:
        # Get the current working directory to determine the correct paths
        current_dir = os.getcwd()
        
        # If we're in the processors directory, use relative paths
        if current_dir.endswith('processors'):
            input_svg = "../files/Step4.svg"
            output_svg = "../files/Step7.svg"
            output_results = "../files/Step7-results.png"
            json_output = "../pinkFrames.json"
        else:
            # If we're in the server directory (when called from pipeline), use direct paths
            input_svg = "files/Step4.svg"
            output_svg = "files/Step7.svg"
            output_results = "files/Step7-results.png"
            json_output = "pinkFrames.json"
        
        # First process SVG colors
        process_svg_colors(input_svg, output_svg)
        
        # Then detect pink shapes on the processed SVG
        
        print(f"Detecting pink shapes in: {output_svg}")
        count, pink_frames_data = detect_pink_shapes(output_svg, output_results, save_json=False)
        
        # Save pink frames data to the specified JSON file
        save_pink_frames_to_json(pink_frames_data, json_output)
        
        print(f"\nFinal count: {count} pink shapes")
        print(f"Pink frames data saved to: {json_output}")
        
    except Exception as e:
        
        print(f"Error in processing: {e}", "error")