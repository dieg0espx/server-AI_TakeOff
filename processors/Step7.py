#!/usr/bin/env python3
"""
Step7: Keep only pink (#ff00cd) shapes, remove all other colors
Uses OpenCV contour detection to count individual pink shapes
"""

import re
import math
import os
import sys
import cv2
import numpy as np
import cairosvg
import io
from PIL import Image
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
        print(f"Error converting SVG to image: {e}")
        return None


def detect_pink_shapes(image_path, output_path='results.png'):
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
        print(f"Error: Could not read image {image_path}")
        return 0, []

    # Convert to HSV for better color detection
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Define pink color range in HSV for #ff00cd (RGB: 255, 0, 205 = HSV: 310°, 100%, 100%)
    # In OpenCV HSV: H ranges 0-180, S and V range 0-255
    # 310° / 2 = 155 in OpenCV
    # We need to use two ranges because pink wraps around the hue circle
    lower_pink1 = np.array([140, 50, 50])   # Lower magenta/pink (wider range)
    upper_pink1 = np.array([170, 255, 255])   # Upper magenta/pink

    lower_pink2 = np.array([0, 50, 50])     # Lower red/pink (wrapping, wider range)
    upper_pink2 = np.array([15, 255, 255])    # Upper red/pink (wrapping)

    # Create mask for pink objects (combine both ranges)
    pink_mask1 = cv2.inRange(hsv, lower_pink1, upper_pink1)
    pink_mask2 = cv2.inRange(hsv, lower_pink2, upper_pink2)
    pink_mask = cv2.bitwise_or(pink_mask1, pink_mask2)

    # Apply morphological operations to clean up the mask
    kernel = np.ones((3,3), np.uint8)
    pink_mask = cv2.morphologyEx(pink_mask, cv2.MORPH_CLOSE, kernel)
    pink_mask = cv2.morphologyEx(pink_mask, cv2.MORPH_OPEN, kernel)

    # Find contours
    contours, _ = cv2.findContours(pink_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter contours based on area and shape
    valid_contours = []
    for contour in contours:
        area = cv2.contourArea(contour)

        # Filter by area (adjust these values based on your shapes)
        if 10 < area < 50000:  # Very broad range to catch all potential shapes
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)

            # Check aspect ratio (diagonal lines can have various aspect ratios)
            aspect_ratio = w / h if h > 0 else 0
            # Allow for various shapes
            if 0.2 < aspect_ratio < 5.0:
                # Additional check: ensure reasonable size
                if w >= 10 and h >= 10:  # Minimum size requirement
                    valid_contours.append((contour, x, y, w, h, area))

    print(f"Found {len(valid_contours)} initial contours")

    # Group nearby contours to identify individual shapes
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
                if distance < 25:  # Adjust based on your shape spacing
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
                if 0.2 < group_aspect_ratio < 5.0:
                    grouped_contours.append((nearby_contours, min_x, min_y, group_w, group_h))
                else:
                    # If grouped bounding box doesn't meet aspect ratio, treat each contour individually
                    for contour, x, y, w, h, area in nearby_contours:
                        grouped_contours.append(([(contour, x, y, w, h, area)], x, y, w, h))

        valid_contours = grouped_contours
        print(f"Grouped into {len(valid_contours)} pink shapes")

    # Create result image by copying the original image
    result_img = img.copy()

    # List to store shape data
    shapes_data = []

    # Draw results
    for i, (contours_group, x, y, w, h) in enumerate(valid_contours):
        # Draw all contours in the group in green (#00ff00)
        for contour, _, _, _, _, _ in contours_group:
            cv2.drawContours(result_img, [contour], -1, (0, 255, 0), 2)  # Green color (BGR)

        # Draw bounding box around the group in green (#00ff00)
        cv2.rectangle(result_img, (int(x), int(y)), (int(x + w), int(y + h)), (0, 255, 0), 2)

        # Add label in white
        label = f"{i+1}"
        cv2.putText(result_img, label, (int(x), int(y)-10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Store shape data
        shape_info = {
            "id": i + 1,
            "x": float(x),
            "y": float(y),
            "width": float(w),
            "height": float(h),
            "contours_count": len(contours_group),
            "center_x": float(x + w/2),
            "center_y": float(y + h/2)
        }
        shapes_data.append(shape_info)

        print(f"{i+1}: Size={w:.1f}x{h:.1f}, Contours={len(contours_group)}")

    # Save result
    if output_path.lower().endswith('.svg'):
        png_path = output_path.replace('.svg', '.png')
        cv2.imwrite(png_path, result_img)
        print(f"Result saved as: {png_path} (PNG format)")
    else:
        cv2.imwrite(output_path, result_img)
        print(f"Result saved as: {output_path}")

    print(f"Total pink shapes detected: {len(valid_contours)}")

    return len(valid_contours), shapes_data


def save_shapes_to_json(shapes_data, output_file='pinkFrames.json'):
    """Save shape data to JSON file"""
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
            "total_pink_shapes": len(shapes_data),
            "pink_shapes": shapes_data,
            "detection_method": "OpenCV contour detection",
            "note": "Count obtained by detecting pink (#ff00cd) contours in SVG"
        }

        # Save to JSON file
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"Shape data saved to: {json_path}")
        return True

    except Exception as e:
        print(f"Error saving to JSON: {e}")
        return False


def process_svg_colors(input_svg, output_svg):
    """
    Process SVG colors following Step8 strategy:
    1. Replace all colors with #202124 except pink (#ff00cd)
    2. Convert pink stroke elements to filled shapes with green border
    3. Convert paths to rectangles with padding
    """
    try:
        # Read the SVG file
        with open(input_svg, 'r', encoding='utf-8') as file:
            content = file.read()

        # Replace all hex colors except pink with dark gray
        hex_pattern = r'#([0-9a-fA-F]{6})'

        def replace_color(match):
            color = match.group(1).lower()
            if color == 'ff00cd':
                return match.group(0)  # Keep pink unchanged
            else:
                return '#202124'  # Replace with dark gray

        processed_content = re.sub(hex_pattern, replace_color, content)

        # Convert pink stroke elements to filled shapes
        # Pattern to match style attributes with #ff00cd stroke and fill:none
        stroke_to_fill_pattern = r'style="([^"]*fill:none[^"]*stroke:#ff00cd[^"]*)"'
        
        def convert_stroke_to_fill(match):
            style_attr = match.group(1)
            
            # Replace fill:none with pink fill
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
            
            # Add thin green border
            new_style += ';stroke:#00ff00;stroke-width:3'
            
            return f'style="{new_style}"'
        
        # Apply the stroke-to-fill conversion
        processed_content = re.sub(stroke_to_fill_pattern, convert_stroke_to_fill, processed_content, flags=re.IGNORECASE)

        # Convert paths to rectangles
        # Pattern to match path elements with #ff00cd fill
        path_pattern = r'<path\s+[^>]*?style="([^"]*fill:#ff00cd[^"]*)"[^>]*?d="([^"]*)"[^>]*?/?>'
        
        def path_to_rect(match):
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
            
            # Add some padding to make the rectangle more visible
            padding = max(width, height) * 0.1
            width += padding * 2
            height += padding * 2
            min_x -= padding
            min_y -= padding
            
            # Ensure thin green border is in the style
            if 'stroke:' not in style:
                style += ';stroke:#00ff00;stroke-width:3'
            else:
                # Replace existing stroke with green border
                style = re.sub(r'stroke:[^;]*', 'stroke:#00ff00', style)
                if 'stroke-width:' not in style:
                    style += ';stroke-width:3'
                else:
                    style = re.sub(r'stroke-width:[^;]*', 'stroke-width:3', style)
            
            # Create rect element
            rect_element = f'<rect\n           style="{style}"\n           x="{min_x}"\n           y="{min_y}"\n           width="{width}"\n           height="{height}" />'
            
            return rect_element
        
        # Apply the path-to-rect conversion
        processed_content = re.sub(path_pattern, path_to_rect, processed_content, flags=re.DOTALL)

        # Write the processed content
        with open(output_svg, 'w', encoding='utf-8') as file:
            file.write(processed_content)

        print("✓ SVG processing completed")
        print(f"  - All colors replaced with #202124 (except #ff00cd pink)")
        print(f"  - Pink stroke elements converted to filled shapes")
        print(f"  - Paths converted to rectangles with green borders")
        print(f"  - Output saved to: {output_svg}")

    except FileNotFoundError:
        print(f"✗ Error: Could not find input file {input_svg}")
    except Exception as e:
        print(f"✗ Error processing SVG: {e}")


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


def count_pink_shapes_from_svg(svg_path):
    """Count pink shapes directly from SVG by counting stroke:#ff00cd occurrences"""
    try:
        with open(svg_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # Count occurrences of pink stroke (original diagonal lines)
        count = len(re.findall(r'stroke:#ff00cd', content, re.IGNORECASE))
        return count
    except Exception as e:
        print(f"Error counting pink shapes: {e}")
        return 0


def count_pink_rectangles_from_svg(svg_path):
    """Count pink rectangles from SVG by counting rect elements with fill:#ff00cd"""
    try:
        with open(svg_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # Count occurrences of rectangles with pink fill
        count = len(re.findall(r'<rect[^>]*fill:#ff00cd[^>]*>', content, re.IGNORECASE))
        return count
    except Exception as e:
        print(f"Error counting pink rectangles: {e}")
        return 0


def filter_shapes_by_size(shapes_data, tolerance=10):
    """
    Filter shapes to only include those within acceptable size ranges.
    Uses fixed reference ranges (46.5-72.0 width, 56.0-59.0 height) with tolerance.

    Args:
        shapes_data: List of shape dictionaries with 'width' and 'height'
        tolerance: Number of pixels tolerance from reference ranges (default: 10)

    Returns:
        Filtered list of shapes
    """
    if not shapes_data:
        return []

    # Fixed reference ranges from typical pink frame sizes
    ref_min_width = 46.5
    ref_max_width = 72.0
    ref_min_height = 56.0
    ref_max_height = 59.0

    # Apply tolerance to reference ranges
    min_width = ref_min_width - tolerance
    max_width = ref_max_width + tolerance
    min_height = ref_min_height - tolerance
    max_height = ref_max_height + tolerance

    print(f"\n  Size filtering (tolerance: ±{tolerance}px from reference):")
    print(f"  Reference width range: {ref_min_width:.1f} - {ref_max_width:.1f}")
    print(f"  Reference height range: {ref_min_height:.1f} - {ref_max_height:.1f}")
    print(f"  Acceptable width range: {min_width:.1f} - {max_width:.1f}")
    print(f"  Acceptable height range: {min_height:.1f} - {max_height:.1f}")

    # Filter shapes
    filtered_shapes = []
    rejected_count = 0

    for shape in shapes_data:
        width = shape['width']
        height = shape['height']

        # Check if within acceptable ranges
        if (min_width <= width <= max_width and
            min_height <= height <= max_height):
            filtered_shapes.append(shape)
        else:
            rejected_count += 1
            print(f"  Rejected shape {shape['id']}: {width:.1f}x{height:.1f} (outside range)")

    print(f"  Kept {len(filtered_shapes)} shapes, rejected {rejected_count} shapes")

    # Re-number the filtered shapes
    for i, shape in enumerate(filtered_shapes):
        shape['id'] = i + 1

    return filtered_shapes


def split_elongated_rectangles(shapes_data, aspect_ratio_threshold=2.0):
    """Split rectangles that are too elongated into 2 separate shapes"""
    new_shapes = []
    split_count = 0
    
    for shape in shapes_data:
        width = shape['width']
        height = shape['height']
        aspect_ratio = max(width, height) / min(width, height) if min(width, height) > 0 else 1
        
        # If aspect ratio is too high, split the rectangle
        if aspect_ratio >= aspect_ratio_threshold:
            split_count += 1
            x = shape['x']
            y = shape['y']
            
            # Determine if it's horizontal or vertical
            if width > height:
                # Split horizontally into 2 rectangles
                new_width = width / 2
                
                # First half
                shape1 = {
                    'x': x,
                    'y': y,
                    'width': new_width,
                    'height': height,
                    'center_x': x + new_width / 2,
                    'center_y': y + height / 2,
                    'split_from': shape['id']
                }
                
                # Second half
                shape2 = {
                    'x': x + new_width,
                    'y': y,
                    'width': new_width,
                    'height': height,
                    'center_x': x + new_width + new_width / 2,
                    'center_y': y + height / 2,
                    'split_from': shape['id']
                }
                
                new_shapes.extend([shape1, shape2])
                print(f"  Split shape {shape['id']} (horizontal {width:.1f}x{height:.1f}) into 2 shapes")
            else:
                # Split vertically into 2 rectangles
                new_height = height / 2
                
                # First half (top)
                shape1 = {
                    'x': x,
                    'y': y,
                    'width': width,
                    'height': new_height,
                    'center_x': x + width / 2,
                    'center_y': y + new_height / 2,
                    'split_from': shape['id']
                }
                
                # Second half (bottom)
                shape2 = {
                    'x': x,
                    'y': y + new_height,
                    'width': width,
                    'height': new_height,
                    'center_x': x + width / 2,
                    'center_y': y + new_height + new_height / 2,
                    'split_from': shape['id']
                }
                
                new_shapes.extend([shape1, shape2])
                print(f"  Split shape {shape['id']} (vertical {width:.1f}x{height:.1f}) into 2 shapes")
        else:
            # Keep the original shape
            new_shapes.append(shape)
    
    # Re-number all shapes
    for i, shape in enumerate(new_shapes):
        shape['id'] = i + 1
    
    if split_count > 0:
        print(f"\n✓ Split {split_count} elongated rectangles")
        print(f"  Total shapes after splitting: {len(new_shapes)}")
    
    return new_shapes


def add_numbered_labels_to_svg(svg_path, shapes_data):
    """Add numbered labels on top of each pink rectangle"""
    try:
        with open(svg_path, 'r', encoding='utf-8') as file:
            content = file.read()

        # Create markers for each shape
        markers = []
        for shape in shapes_data:
            shape_id = shape['id']
            center_x = shape['center_x']
            center_y = shape['center_y']

            # Add small green text label
            font_size = 16

            text = f'  <text x="{center_x}" y="{center_y + 6}" style="fill:#00ff00;font-size:{font_size}px;font-weight:bold;text-anchor:middle;font-family:Arial">{shape_id}</text>\n'

            markers.append(text)

        # Find the closing </svg> tag and insert markers before it
        svg_end = content.rfind('</svg>')
        if svg_end == -1:
            print("Warning: Could not find </svg> tag")
            return False

        # Insert all markers before </svg>
        markers_svg = '  <!-- Pink rectangle numbered labels -->\n' + ''.join(markers)
        new_content = content[:svg_end] + markers_svg + content[svg_end:]

        # Write the modified content
        with open(svg_path, 'w', encoding='utf-8') as file:
            file.write(new_content)

        print(f"✓ Added {len(markers)} numbered labels to SVG")
        return True

    except Exception as e:
        print(f"Error adding numbered labels: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_step7():
    """
    Run Step7 processing - keep only pink shapes and count them
    """
    try:
        # Determine paths based on current directory
        current_dir = os.getcwd()

        if current_dir.endswith('processors'):
            input_svg = "../files/Step4.svg"
            output_svg = "../files/Step7.svg"
            output_results = "../files/Step7-results.png"
        else:
            input_svg = "files/Step4.svg"
            output_svg = "files/Step7.svg"
            output_results = "files/Step7-results.png"

        # Process SVG colors and convert paths to rectangles
        process_svg_colors(input_svg, output_svg)

        # Detect pink rectangles using OpenCV
        print(f"\nDetecting pink rectangles in: {output_svg}")
        count, shapes_data = detect_pink_shapes(output_svg, output_results)
        print(f"\nInitial count: {count} pink shapes")

        # Split elongated rectangles into 2 separate shapes
        if shapes_data:
            print(f"\nChecking for elongated rectangles to split...")
            shapes_data = split_elongated_rectangles(shapes_data, aspect_ratio_threshold=1.6)
            count = len(shapes_data)
            print(f"\nCount after splitting: {count} pink shapes")

        # Filter shapes by size (±10 pixels from average)
        if shapes_data:
            print(f"\nApplying size filtering...")
            shapes_data = filter_shapes_by_size(shapes_data, tolerance=10)
            count = len(shapes_data)
            print(f"\nFinal count after filtering: {count} pink shapes")

        # Save shape data to JSON (always save, even if empty)
        save_shapes_to_json(shapes_data if shapes_data else [], 'pinkFrames.json')

        # Add numbered labels to the SVG
        if shapes_data:
            print(f"\nAdding numbered labels to SVG...")
            add_numbered_labels_to_svg(output_svg, shapes_data)

        print(f"\n✓ Step7 completed successfully")
        print(f"  - Pink shapes preserved in: {output_svg}")

        return True

    except Exception as e:
        print(f"✗ Error in Step7 processing: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        # Determine paths
        current_dir = os.getcwd()

        if current_dir.endswith('processors'):
            input_svg = "../files/Step4.svg"
            output_svg = "../files/Step7.svg"
            output_results = "../files/Step7-results.png"
        else:
            input_svg = "files/Step4.svg"
            output_svg = "files/Step7.svg"
            output_results = "files/Step7-results.png"

        # Process SVG colors and convert paths to rectangles
        process_svg_colors(input_svg, output_svg)

        # Detect pink rectangles using OpenCV
        print(f"\nDetecting pink rectangles in: {output_svg}")
        count, shapes_data = detect_pink_shapes(output_svg, output_results)
        print(f"\nInitial count: {count} pink shapes")

        # Split elongated rectangles into 2 separate shapes
        if shapes_data:
            print(f"\nChecking for elongated rectangles to split...")
            shapes_data = split_elongated_rectangles(shapes_data, aspect_ratio_threshold=1.6)
            count = len(shapes_data)
            print(f"\nCount after splitting: {count} pink shapes")

        # Filter shapes by size (±10 pixels from average)
        if shapes_data:
            print(f"\nApplying size filtering...")
            shapes_data = filter_shapes_by_size(shapes_data, tolerance=10)
            count = len(shapes_data)
            print(f"\nFinal count after filtering: {count} pink shapes")

        # Save shape data to JSON (always save, even if empty)
        save_shapes_to_json(shapes_data if shapes_data else [], 'pinkFrames.json')

        # Add numbered labels to the SVG
        if shapes_data:
            print(f"\nAdding numbered labels to SVG...")
            add_numbered_labels_to_svg(output_svg, shapes_data)

        print(f"\n✓ Done! Pink shapes are now isolated in {output_svg}")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
