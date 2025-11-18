#!/usr/bin/env python3
"""
Contour-based Object Detection for Red Squares (#fb0505)
Uses OpenCV contour detection to find individual red squares with color #fb0505 on black background
"""

import re
import os
import cv2
import numpy as np
from pathlib import Path
import argparse
import cairosvg
import io
import json
from PIL import Image
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


# Shores pattern for detecting specific path elements
shores = re.compile(
    r'<path[^>]+d="[^"]*m\s*(-?\d+),(-?\d+)\s+('
    r'-?(33|34),-?(33|34)|'
    r'-?(33|34),(33|34)|'
    r'(33|34),-?(33|34)|'
    r'(33|34),(33|34))[^"]*"[^>]*>'
)

def save_red_squares_to_json(red_squares_data, output_path):
    """Save red squares data to JSON file"""
    try:
        # Create the JSON structure
        json_data = {
            "total_red_squares": len(red_squares_data),
            "red_squares": red_squares_data
        }
        
        # Write to JSON file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        print(f"Red squares data saved to: {output_path}")
        return True
    except Exception as e:
        print(f"Error saving red squares data to JSON: {e}")
        return False

def split_elongated_squares(squares_data, aspect_ratio_threshold=2.0):
    """Split squares that are too elongated (likely 2 or more stacked) into separate squares"""
    new_squares = []
    split_count = 0

    for square in squares_data:
        width = square['width']
        height = square['height']
        aspect_ratio = max(width, height) / min(width, height) if min(width, height) > 0 else 1

        # If aspect ratio is too high, split the rectangle
        if aspect_ratio >= aspect_ratio_threshold:
            split_count += 1
            x = square['x']
            y = square['y']

            # Determine how many squares to split into
            num_splits = round(aspect_ratio)

            # Determine if it's horizontal or vertical
            if width > height:
                # Split horizontally into multiple squares
                new_width = width / num_splits

                for i in range(num_splits):
                    square_split = {
                        'x': x + (i * new_width),
                        'y': y,
                        'width': new_width,
                        'height': height,
                        'center_x': x + (i * new_width) + new_width / 2,
                        'center_y': y + height / 2,
                        'area': new_width * height,
                        'split_from': square['id']
                    }
                    new_squares.append(square_split)

                print(f"  Split square {square['id']} (horizontal {width:.1f}x{height:.1f}) into {num_splits} squares")
            else:
                # Split vertically into multiple squares
                new_height = height / num_splits

                for i in range(num_splits):
                    square_split = {
                        'x': x,
                        'y': y + (i * new_height),
                        'width': width,
                        'height': new_height,
                        'center_x': x + width / 2,
                        'center_y': y + (i * new_height) + new_height / 2,
                        'area': width * new_height,
                        'split_from': square['id']
                    }
                    new_squares.append(square_split)

                print(f"  Split square {square['id']} (vertical {width:.1f}x{height:.1f}) into {num_splits} squares")
        else:
            # Keep the original square
            new_squares.append(square)

    # Re-number all squares
    for i, square in enumerate(new_squares):
        square['id'] = i + 1
        # Remove split_from if it exists and update contours_count if not present
        if 'split_from' in square:
            square.pop('split_from', None)
        if 'contours_count' not in square:
            square['contours_count'] = 1

    if split_count > 0:
        print(f"\n✓ Split {split_count} elongated squares into {len(new_squares) - len(squares_data) + split_count} new squares")
        print(f"  Total squares after splitting: {len(new_squares)}")

    return new_squares

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

def detect_red_squares(image_path, output_path='results.png', json_output_path=None):
    """Detect individual red squares with color #fb0505 using contour detection"""
    
    print(f"Processing image: {image_path}")
    
    # Check if input is SVG and convert if needed
    if str(image_path).lower().endswith('.svg'):
        
        print("Converting SVG to image for processing...")
        pil_image = svg_to_image(str(image_path))
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
    
    print(f"Image loaded successfully: {img.shape}")
    
    # Convert to HSV for better color detection
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Define specific red color #fb0505 in HSV
    # Convert #fb0505 from RGB to HSV
    # #fb0505 in RGB is (251, 5, 5)
    # OpenCV uses BGR, so it's (5, 5, 251)
    target_color_bgr = np.array([5, 5, 251], dtype=np.uint8)
    target_color_hsv = cv2.cvtColor(target_color_bgr.reshape(1, 1, 3), cv2.COLOR_BGR2HSV)
    target_h, target_s, target_v = target_color_hsv[0, 0]
    
    print(f"Target HSV values: H={target_h}, S={target_s}, V={target_v}")
    
    # Create a wider range around the target color for better detection
    # Allow more tolerance for slight variations and lighting differences
    tolerance_h = 30  # Increased hue tolerance
    tolerance_s = 150  # Increased saturation tolerance  
    tolerance_v = 150  # Increased value tolerance
    
    # Fix overflow issues by using proper data types
    lower_red = np.array([
        max(0, int(target_h) - tolerance_h), 
        max(0, int(target_s) - tolerance_s), 
        max(0, int(target_v) - tolerance_v)
    ], dtype=np.uint8)
    
    upper_red = np.array([
        min(180, int(target_h) + tolerance_h), 
        min(255, int(target_s) + tolerance_s), 
        min(255, int(target_v) + tolerance_v)
    ], dtype=np.uint8)
    
    print(f"HSV range: Lower={lower_red}, Upper={upper_red}")
    
    # Create mask for the specific red color
    red_mask = cv2.inRange(hsv, lower_red, upper_red)
    
    # Count non-zero pixels in mask
    mask_pixels = cv2.countNonZero(red_mask)
    print(f"HSV mask pixels: {mask_pixels}")
    
    # If HSV detection fails, try RGB-based detection as fallback
    if mask_pixels < 50:  # Reduced threshold
        # Convert to RGB for alternative detection
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Define target color in RGB
        target_rgb = np.array([251, 5, 5])  # #fb0505 in RGB
        
        # Create tolerance for RGB detection
        tolerance_rgb = 50  # Increased tolerance
        
        # Create RGB mask
        lower_rgb = np.maximum(0, target_rgb - tolerance_rgb)
        upper_rgb = np.minimum(255, target_rgb + tolerance_rgb)
        
        print(f"RGB range: Lower={lower_rgb}, Upper={upper_rgb}")
        
        # Create mask for red objects in RGB
        red_mask_rgb = cv2.inRange(rgb, lower_rgb, upper_rgb)
        
        rgb_mask_pixels = cv2.countNonZero(red_mask_rgb)
        print(f"RGB mask pixels: {rgb_mask_pixels}")
        
        # Use the better mask
        if rgb_mask_pixels > mask_pixels:
            red_mask = red_mask_rgb
            mask_pixels = rgb_mask_pixels
            print("Using RGB mask")
        else:
            print("Using HSV mask")
    
    # Save debug mask
    debug_mask_path = output_path.replace('.png', '_mask.png')
    cv2.imwrite(debug_mask_path, red_mask)
    print(f"Debug mask saved to: {debug_mask_path}")
    
    # Apply morphological operations to clean up the mask
    kernel = np.ones((3,3), np.uint8)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
    red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    print(f"Total contours found: {len(contours)}")
    
    # Filter contours based on area and shape
    valid_contours = []
    for i, contour in enumerate(contours):
        area = cv2.contourArea(contour)
        
        # Print all contours for debugging
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / h if h > 0 else 0
        
        # Filter by area (adjust these values based on your square sizes)
        if 5 < area < 10000:  # Even broader range to catch all potential squares
            # Check aspect ratio (squares should be roughly square)
            # Ensure width/height ratio is within 3.0 tolerance (very lenient)
            if 0.3 < aspect_ratio < 3.0:  # Very lenient aspect ratio
                # Additional check: ensure reasonable size
                if w >= 2 and h >= 2:  # Very reduced minimum size requirement
                    valid_contours.append((contour, x, y, w, h, area))
                    print(f"Contour {i}: Area={area:.1f}, Size={w}x{h}, Aspect={aspect_ratio:.2f} - ACCEPTED")
                else:
                    print(f"Contour {i}: Area={area:.1f}, Size={w}x{h}, Aspect={aspect_ratio:.2f} - REJECTED (size)")
            else:
                print(f"Contour {i}: Area={area:.1f}, Size={w}x{h}, Aspect={aspect_ratio:.2f} - REJECTED (aspect)")
        else:
            print(f"Contour {i}: Area={area:.1f}, Size={w}x{h}, Aspect={aspect_ratio:.2f} - REJECTED (area filter)")
    
    print(f"Found {len(valid_contours)} initial contours")
    
    # Group nearby contours to identify individual squares
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
                
                # If contours are very close, group them (much stricter for squares)
                if distance < 20:  # Increased from 15 to 20 for more grouping
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
                if 0.3 < group_aspect_ratio < 3.0:  # Very lenient aspect ratio
                    grouped_contours.append((nearby_contours, min_x, min_y, group_w, group_h))
                else:
                    # If grouped bounding box doesn't meet aspect ratio, treat each contour individually
                    for contour, x, y, w, h, area in nearby_contours:
                        grouped_contours.append(([(contour, x, y, w, h, area)], x, y, w, h))
        
        valid_contours = grouped_contours
        print(f"Grouped into {len(valid_contours)} squares")
    
    # Collect red squares data for JSON output
    red_squares_data = []
    
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
        label = f"{i+1}"
        cv2.putText(result_img, label, (int(x), int(y)-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Collect data for JSON
        red_square_data = {
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
        red_squares_data.append(red_square_data)
        
        print(f"Square{i+1}: Size={w:.1f}x{h:.1f}, Contours={len(contours_group)}")
    
    # Save result image
    cv2.imwrite(output_path, result_img)
    print(f"Result saved as: {output_path}")

    print(f"Total squares detected: {len(valid_contours)}")

    # Split elongated squares before saving
    if red_squares_data:
        print(f"\nChecking for elongated squares to split...")
        red_squares_data = split_elongated_squares(red_squares_data, aspect_ratio_threshold=2.0)

    # Save red squares data to JSON if path provided
    if json_output_path:
        save_red_squares_to_json(red_squares_data, json_output_path)

    # Delete the debug mask file after processing
    debug_mask_path = output_path.replace('.png', '_mask.png')
    if os.path.exists(debug_mask_path):
        os.remove(debug_mask_path)
        print(f"Debug mask deleted: {debug_mask_path}")

    return len(red_squares_data), red_squares_data

def process_svg_colors():
    # Get the current working directory to determine the correct paths
    current_dir = os.getcwd()
    
    # If we're in the processors directory, use relative paths
    if current_dir.endswith('processors'):
        input_svg = "../files/Step4.svg"
        output_svg = "../files/Step6.svg"
        output_results = "../files/Step6-results.png"
    else:
        # If we're in the server directory (when called from pipeline), use direct paths
        input_svg = "files/Step4.svg"
        output_svg = "files/Step6.svg"
        output_results = "files/Step6-results.png"
    
    # PHASE 1: Color processing from Step4.svg to Step6.svg
    
    print("PHASE 1: Processing colors from Step4.svg to Step6.svg")
    
    # Read the SVG file
    with open(input_svg, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Find all hex color codes (#xxxxxx)
    hex_pattern = r'#([0-9a-fA-F]{6})'
    
    def replace_color(match):
        color = match.group(1).lower()
        # Change #0000ff to #fb0505, keep #fb0505 unchanged, replace all others with #202124
        if color == '0000ff':
            return '#fb0505'
        elif color == 'fb0505':
            return match.group(0)  # Return original match unchanged
        else:
            return '#202124'
    
    # Replace colors using the function
    processed_content = re.sub(hex_pattern, replace_color, content)
    
    # Write the processed content to Step6.svg
    with open(output_svg, 'w', encoding='utf-8') as file:
        file.write(processed_content)
    
    print("Phase 1 completed: Colors processed and saved to Step6.svg")
    
    # PHASE 2: Shores processing on Step6.svg
    print("\nPHASE 2: Processing shores on Step6.svg")
    
    # Read the Step6.svg file for shores processing
    with open(output_svg, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Pattern to find elements with stroke:#fb0505 and fill:none
    # This will match the style attribute and replace fill:none with fill:#fb0505
    pattern = r'(style="[^"]*fill:none[^"]*stroke:#fb0505[^"]*")'
    
    def replace_fill(match):
        style_attr = match.group(1)
        # Replace fill:none with fill:#fb0505
        new_style = style_attr.replace('fill:none', 'fill:#fb0505')
        return new_style
    
    # Apply the replacement for fill
    modified_content = re.sub(pattern, replace_fill, content)
    
    # Function to change shores color to #202124
    def change_shores_color(match):
        path_element = match.group(0)
        
        # Check if the path has a style attribute
        if 'style=' in path_element:
            # Replace any existing stroke color with #202124
            if 'stroke:' in path_element:
                # Replace existing stroke color
                path_element = re.sub(r'stroke:#[0-9a-fA-F]{6}', 'stroke:#202124', path_element)
                path_element = re.sub(r'stroke:#[0-9a-fA-F]{3}', 'stroke:#202124', path_element)
            else:
                # Add stroke color if it doesn't exist
                path_element = re.sub(r'(style="[^"]*)"', r'\1;stroke:#202124"', path_element)
        else:
            # Add style attribute with stroke color
            path_element = re.sub(r'(<path[^>]*>)', r'\1 style="stroke:#202124"', path_element)
        
        return path_element
    
    # Apply the shores color change
    modified_content = shores.sub(change_shores_color, modified_content)
    
    # Final color transformations: #202124 to black, red to red
    # Change all #202124 to black (for squares)
    modified_content = modified_content.replace('#202124', '#000000')
    
    # Change all #fb0505 (red) to red (for background)
    modified_content = modified_content.replace('#fb0505', '#ff0000')
    
    # Write the final processed content back to Step6.svg
    with open(output_svg, 'w', encoding='utf-8') as file:
        file.write(modified_content)
    
    print("SVG processing completed!")
    print("Phase 1: Original colors replaced with #202124 (except #fb0505)")
    print("Phase 1: #0000ff changed to #fb0505")
    print("Phase 2: All elements with stroke:#fb0505 now have fill:#fb0505")
    print("Phase 2: All shores matching the pattern now have stroke color #202124")
    print("Phase 2: All #202124 colors changed to black (squares)")
    print("Phase 2: All red (#fb0505) colors changed to red (background)")
    print(f"Final output saved to: {output_svg}")
    
    # PHASE 3: Fill squares before conversion
    print("\nPHASE 3: Filling squares in Step6.svg")
    
    # Read the Step6.svg file for square filling
    with open(output_svg, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # More selective approach: only fill elements that have red stroke
    # Pattern to find elements with stroke:#ff0000 and fill:none
    fill_pattern = r'(style="[^"]*fill:none[^"]*stroke:#ff0000[^"]*")'
    
    def fill_red_squares(match):
        style_attr = match.group(1)
        # Replace fill:none with fill:#ff0000 to fill the squares
        new_style = style_attr.replace('fill:none', 'fill:#ff0000')
        return new_style
    
    # Apply the replacement to fill only red squares
    filled_content = re.sub(fill_pattern, fill_red_squares, content)
    
    # Write the filled content back to Step6.svg
    with open(output_svg, 'w', encoding='utf-8') as file:
        file.write(filled_content)
    
    print("Phase 3 completed: Squares filled with red color")
    print(f"Filled SVG saved to: {output_svg}")
    
    # PHASE 4: Contour-based object detection
    print("\nPHASE 4: Contour-based object detection on Step6.svg")
    
    # Define JSON output path
    json_output = "files/tempData/square-shores.json"
    if current_dir.endswith('processors'):
        json_output = "../files/tempData/square-shores.json"
    
    try:
        # Detect red squares in the processed SVG
        count, red_squares_data = detect_red_squares(output_svg, output_results, json_output)
        print(f"Phase 4 completed: Detected {count} red squares")
        print(f"Results saved to: {output_results}")
        print(f"JSON data saved to: {json_output}")
    except Exception as e:
        print(f"Phase 4 error: {e}", "error")
        print("Note: Make sure cairosvg is installed: pip install cairosvg", "warning")

def run_step6():
    """
    Run Step6 processing - detect red squares
    """
    try:
        # Get the current working directory to determine the correct paths
        current_dir = os.getcwd()
        
        # If we're in the processors directory, use relative paths
        if current_dir.endswith('processors'):
            input_svg = "../files/Step4.svg"
            output_svg = "../files/Step6.svg"
            output_results = "../files/Step6-results.png"
        else:
            # If we're in the server directory (when called from pipeline), use direct paths
            input_svg = "files/Step4.svg"
            output_svg = "files/Step6.svg"
            output_results = "files/Step6-results.png"
        
        # Run full SVG processing pipeline
        process_svg_colors()
        
        return True
        
    except Exception as e:
        
        print(f"Error in processing: {e}", "error")
        return False

def main():
    parser = argparse.ArgumentParser(description='Contour-based Red Square Detection (#fb0505)')
    parser.add_argument('--source', type=str, default='Step6.svg',
                       help='Path to SVG image (default: Step6.svg)')
    parser.add_argument('--output', type=str, default='Step6-results.png',
                       help='Output image path (default: Step6-results.png)')
    parser.add_argument('--process-only', action='store_true',
                       help='Only run contour detection, skip SVG processing')
    
    args = parser.parse_args()
    
    if args.process_only:
        # Only run contour detection
        source_path = Path(args.source)
        if not source_path.exists():
            
            print(f"Error: Source not found at {source_path}", "error")
            return
        
        count, red_squares_data = detect_red_squares(source_path, args.output)
        print(f"\nFinal count: {count} red squares (#fb0505)")
    else:
        # Run full SVG processing pipeline
        process_svg_colors()

if __name__ == "__main__":
    main()