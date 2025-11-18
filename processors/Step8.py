#!/usr/bin/env python3
"""
Contour-based Object Detection for Green Rectangles
Uses OpenCV contour detection to find individual green rectangles
"""

import re
import math
import os
import cv2
import numpy as np
from pathlib import Path
import argparse
import cairosvg
import io
from PIL import Image
import sys
import json
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


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

def detect_green_rectangles(image_path, output_path='results.png'):
    """Detect individual green rectangles using contour detection"""
    
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
    
    # Define green color range in HSV for #70ff00
    # Convert #70ff00 to HSV: H=120, S=255, V=255 (bright green)
    # Adjust range to catch variations in lighting and image quality
    lower_green = np.array([35, 50, 50])   # Darker green
    upper_green = np.array([85, 255, 255]) # Lighter green
    
    # Create mask for green objects
    green_mask = cv2.inRange(hsv, lower_green, upper_green)
    
    # Apply morphological operations to clean up the mask
    kernel = np.ones((3,3), np.uint8)
    green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_CLOSE, kernel)
    green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_OPEN, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours based on area and shape
    valid_contours = []
    for contour in contours:
        area = cv2.contourArea(contour)
        
        # Filter by area (adjust these values based on your rectangles)
        if 50 < area < 10000:  # Broader range to catch all potential rectangles
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            
            # Check aspect ratio (rectangles can have various aspect ratios)
            aspect_ratio = w / h if h > 0 else 0
            # Allow for rectangular shapes (not too extreme aspect ratios)
            if 0.2 < aspect_ratio < 5.0:  # Allow rectangles but not extremely thin lines
                # Additional check: ensure reasonable size
                if w >= 10 and h >= 10:  # Minimum size requirement
                    valid_contours.append((contour, x, y, w, h, area))
    
    print(f"Found {len(valid_contours)} initial contours")
    
    # Group nearby contours to identify individual rectangles
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
                if distance < 25:  # Adjust based on your rectangle spacing
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
                
                # Apply aspect ratio constraint to grouped bounding boxes
                group_aspect_ratio = group_w / group_h if group_h > 0 else 0
                if 0.2 < group_aspect_ratio < 5.0:  # Same tolerance as individual contours
                    grouped_contours.append((nearby_contours, min_x, min_y, group_w, group_h))
                else:
                    # If grouped bounding box doesn't meet aspect ratio, treat each contour individually
                    for contour, x, y, w, h, area in nearby_contours:
                        grouped_contours.append(([(contour, x, y, w, h, area)], x, y, w, h))
        
        valid_contours = grouped_contours
        print(f"Grouped into {len(valid_contours)} rectangles")
    
    # Create result image by copying the original image
    result_img = img.copy()
    
    # List to store rectangle data
    rectangles_data = []
    
    # Draw results
    # Draw contours and bounding boxes
    for i, (contours_group, x, y, w, h) in enumerate(valid_contours):
        # Draw all contours in the group in red (#ff0000)
        for contour, _, _, _, _, _ in contours_group:
            cv2.drawContours(result_img, [contour], -1, (0, 0, 255), 2)  # Red color (BGR)
        
        # Draw bounding box around the group in red (#ff0000)
        cv2.rectangle(result_img, (int(x), int(y)), (int(x + w), int(y + h)), (0, 0, 255), 2)
        
        # Add label in white
        label = f"{i+1}"
        cv2.putText(result_img, label, (int(x), int(y)-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Store rectangle data
        rectangle_info = {
            "id": i + 1,
            "x": float(x),
            "y": float(y),
            "width": float(w),
            "height": float(h),
            "contours_count": len(contours_group),
            "center_x": float(x + w/2),
            "center_y": float(y + h/2)
        }
        rectangles_data.append(rectangle_info)
        
        print(f"{i+1}: Size={w:.1f}x{h:.1f}, Contours={len(contours_group)}")
    
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
    print(f"Total rectangles detected: {len(valid_contours)}")
    
    return len(valid_contours), rectangles_data

def save_rectangles_to_json(rectangles_data, output_file='greenFrames.json'):
    """Save rectangle data to JSON file"""
    try:
        # Get the current working directory to determine the correct paths
        current_dir = os.getcwd()
        
        # If we're in the processors directory, use relative paths
        if current_dir.endswith('processors'):
            json_path = f"../files/tempData/{output_file}"
        else:
            # If we're in the server directory (when called from pipeline), use direct paths
            json_path = f"files/tempData/{output_file}"
        
        # Prepare the data structure
        output_data = {
            "total_rectangles": len(rectangles_data),
            "rectangles": rectangles_data,
            "metadata": {
                "description": "Green rectangle detection results",
                "format": "x, y coordinates (top-left corner), width, height, center coordinates"
            }
        }
        
        # Save to JSON file
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"Rectangle data saved to: {json_path}")
        return True
        
    except Exception as e:
        print(f"Error saving to JSON: {e}")
        return False

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

def process_svg_colors():
    # Get the current working directory to determine the correct paths
    current_dir = os.getcwd()
    
    # If we're in the processors directory, use relative paths
    if current_dir.endswith('processors'):
        input_svg = "../files/Step4.svg"
        output_svg = "../files/Step8.svg"
    else:
        # If we're in the server directory (when called from pipeline), use direct paths
        input_svg = "files/Step4.svg"
        output_svg = "files/Step8.svg"
    
    # Read the SVG file
    with open(input_svg, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Find all hex color codes (#xxxxxx)
    hex_pattern = r'#([0-9a-fA-F]{6})'
    
    def replace_color(match):
        color = match.group(1).lower()
        # Keep #0000ff and #fb0505 unchanged, replace all others with #202124
        if color == '70ff00':
            return match.group(0)  # Return original match unchanged
        else:
            return '#202124'
    
    # Replace colors using the function
    processed_content = re.sub(hex_pattern, replace_color, content)
    
    # Now convert #70ff00 (green) and #fb0505 (pink) stroke elements to filled shapes
    # Pattern to match style attributes with #70ff00 or #fb0505 stroke and fill:none
    stroke_to_fill_pattern = r'style="([^"]*fill:none[^"]*stroke:#(70ff00|fb0505)[^"]*)"'
    
    def convert_stroke_to_fill(match):
        style_attr = match.group(1)
        stroke_color = match.group(2)  # Get the matched color (70ff00 or fb0505)
        
        # Replace fill:none with the appropriate fill color
        if stroke_color == '70ff00':
            new_style = style_attr.replace('fill:none', 'fill:#70ff00')
        else:  # fb0505
            new_style = style_attr.replace('fill:none', 'fill:#fb0505')
        
        # Remove stroke-related attributes
        new_style = re.sub(r'stroke:#(70ff00|fb0505)[^;]*;?', '', new_style)
        new_style = re.sub(r'stroke-width:[^;]*;?', '', new_style)
        new_style = re.sub(r'stroke-linecap:[^;]*;?', '', new_style)
        new_style = re.sub(r'stroke-linejoin:[^;]*;?', '', new_style)
        new_style = re.sub(r'stroke-miterlimit:[^;]*;?', '', new_style)
        new_style = re.sub(r'stroke-dasharray:[^;]*;?', '', new_style)
        new_style = re.sub(r'stroke-opacity:[^;]*;?', '', new_style)
        # Clean up any double semicolons or trailing semicolons
        new_style = re.sub(r';;+', ';', new_style)
        new_style = new_style.strip(';')
        # Add thick red border
        new_style += ';stroke:#ff0000;stroke-width:50'
        return f'style="{new_style}"'
    
    # Apply the stroke-to-fill conversion
    processed_content = re.sub(stroke_to_fill_pattern, convert_stroke_to_fill, processed_content)
    
    # Convert Z-shaped paths to rectangles
    # Pattern to match path elements with #70ff00 fill - updated for multi-line structure
    path_pattern = r'<path\s+[^>]*?style="([^"]*fill:#70ff00[^"]*)"[^>]*?d="([^"]*)"[^>]*?/>'
    
    def path_to_rect_updated(match):
        style = match.group(1)
        d = match.group(2)
        
        # Parse the path data
        coordinates = parse_path_data(d)
        
        if not coordinates:
            return match.group(0)  # Return original if we can't parse
        
        # Calculate bounding box
        bbox = calculate_bounding_box(coordinates)
        if not bbox:
            return match.group(0)
        
        min_x, min_y, max_x, max_y = bbox
        width = max_x - min_x
        height = max_y - min_y
        
        # Add some padding to make the square more visible
        padding = max(width, height) * 0.1
        width += padding * 2
        height += padding * 2
        min_x -= padding
        min_y -= padding
        
        # Add thick red border to the style
        if 'stroke:' not in style:
            style += ';stroke:#ff0000;stroke-width:50'
        else:
            # Replace existing stroke with red border
            style = re.sub(r'stroke:[^;]*', 'stroke:#ff0000', style)
            style = re.sub(r'stroke-width:[^;]*', 'stroke-width:50', style)
            if 'stroke-width:8' not in style:
                style += ';stroke-width:50'
        
        # Create rect element
        rect_element = f'<rect\n           style="{style}"\n           x="{min_x}"\n           y="{min_y}"\n           width="{width}"\n           height="{height}" />'
        
        return rect_element
    
    # Apply the path-to-rect conversion
    processed_content = re.sub(path_pattern, path_to_rect_updated, processed_content, flags=re.DOTALL)
    
    # Write the processed content to a new file
    with open(output_svg, 'w', encoding='utf-8') as file:
        file.write(processed_content)
    
    
    print("SVG processing completed!")
    print("Original colors replaced with #202124 (except #70ff00)")
    print("#70ff00 stroke elements converted to filled shapes")
    print("Z-shaped paths converted to squares/rectangles")
    print(f"Output saved to: {output_svg}")

def run_step8():
    """
    Run Step8 processing - detect green rectangles
    """
    try:
        # Get the current working directory to determine the correct paths
        current_dir = os.getcwd()
        
        # If we're in the processors directory, use relative paths
        if current_dir.endswith('processors'):
            input_svg = "../files/Step4.svg"
            output_svg = "../files/Step8.svg"
            output_results = "../files/Step8-results.png"
        else:
            # If we're in the server directory (when called from pipeline), use direct paths
            input_svg = "files/Step4.svg"
            output_svg = "files/Step8.svg"
            output_results = "files/Step8-results.png"
        
        # First process SVG colors and convert paths to rectangles
        process_svg_colors()
        
        # Then detect green rectangles on the processed SVG
        
        print(f"Detecting green rectangles in: {output_svg}")
        count, rectangles_data = detect_green_rectangles(output_svg, output_results)
        print(f"\nFinal count: {count} green rectangles")
        
        # Save rectangle data to JSON (always save, even if empty)
        save_rectangles_to_json(rectangles_data if rectangles_data else [], 'greenFrames.json')
        
        return True
        
    except Exception as e:
        
        print(f"Error in processing: {e}", "error")
        return False

def main():
    parser = argparse.ArgumentParser(description='Contour-based Green Rectangle Detection')
    parser.add_argument('--source', type=str, default='test/test.png',
                       help='Path to image')
    parser.add_argument('--output', type=str, default='results.png',
                       help='Output image path')
    
    args = parser.parse_args()
    
    # Check if source exists
    source_path = Path(args.source)
    if not source_path.exists():
        print(f"Error: Source not found at {source_path}", "error")
        return
    
    # Detect rectangles
    count, rectangles_data = detect_green_rectangles(source_path, args.output)
    
    print(f"\nFinal count: {count} green rectangles")
    
    # Save rectangle data to JSON
    if rectangles_data:
        save_rectangles_to_json(rectangles_data, 'greenFrames.json')

if __name__ == "__main__":
    try:
        # Get the current working directory to determine the correct paths
        current_dir = os.getcwd()
        
        # If we're in the processors directory, use relative paths
        if current_dir.endswith('processors'):
            input_svg = "../files/Step8.svg"
            output_svg = "../files/Step8.svg"
            output_results = "../files/Step8-results.png"
        else:
            # If we're in the server directory (when called from pipeline), use direct paths
            input_svg = "files/Step8.svg"
            output_svg = "files/Step8.svg"
            output_results = "files/Step8-results.png"
        
        # First process SVG colors and convert paths to rectangles
        process_svg_colors()
        
        # Then detect green rectangles on the processed SVG
        
        print(f"Detecting green rectangles in: {output_svg}")
        count, rectangles_data = detect_green_rectangles(output_svg, output_results)
        print(f"\nFinal count: {count} green rectangles")
        
        # Save rectangle data to JSON (always save, even if empty)
        save_rectangles_to_json(rectangles_data if rectangles_data else [], 'greenFrames.json')
        
    except Exception as e:
        
        print(f"Error in processing: {e}", "error")