#!/usr/bin/env python3
"""
Step 10: Draw containers from greenFrames.json, pinkFrames.json, x-shores.json, and square-shores.json onto Step2.svg
Adds red border rectangles (green frames), pink border rectangles (pink frames), blue border rectangles (X shapes), and red border rectangles (red squares) with numeration to the SVG
"""

import json
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def load_green_frames(json_path):
    """Load green frames data from JSON file"""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        return None

def load_pink_frames(json_path):
    """Load pink frames data from JSON file"""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        return None

def load_x_shapes(json_path):
    """Load X shapes data from JSON file"""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        return None

def load_red_squares(json_path):
    """Load red squares data from JSON file"""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        return None

def load_orange_frames(json_path):
    """Load orange frames data from JSON file"""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        return None

def read_svg_file(svg_path):
    """Read SVG file content"""
    try:
        with open(svg_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return None

def rectangles_overlap(rect1, rect2):
    """Check if two rectangles overlap or share coordinates"""
    # Get coordinates for rectangle 1
    x1, y1 = rect1['x'], rect1['y']
    w1, h1 = rect1['width'], rect1['height']
    
    # Get coordinates for rectangle 2
    x2, y2 = rect2['x'], rect2['y']
    w2, h2 = rect2['width'], rect2['height']
    
    # Check for overlap
    # Two rectangles overlap if:
    # - One is not completely to the left of the other
    # - One is not completely to the right of the other
    # - One is not completely above the other
    # - One is not completely below the other
    return not (x1 + w1 <= x2 or x2 + w2 <= x1 or y1 + h1 <= y2 or y2 + h2 <= y1)

def filter_overlapping_x_shapes(x_shapes, red_squares):
    """Filter out X-shapes that overlap with red squares"""
    filtered_x_shapes = []
    
    for x_shape in x_shapes:
        overlaps_with_red_square = False
        
        for red_square in red_squares:
            if rectangles_overlap(x_shape, red_square):
                overlaps_with_red_square = True
                break
        
        if not overlaps_with_red_square:
            filtered_x_shapes.append(x_shape)
    
    return filtered_x_shapes

def create_rectangle_element(rect_data, color='red', prefix='container'):
    """Create SVG rectangle element with colored border and numeration"""
    x = rect_data['x']
    y = rect_data['y']
    width = rect_data['width']
    height = rect_data['height']
    rect_id = rect_data['id']
    
    # Create rectangle with colored border (1px width)
    rect_element = f'''
    <rect
       id="{prefix}_{rect_id}"
       x="{x}"
       y="{y}"
       width="{width}"
       height="{height}"
       style="fill:none;stroke:{color};stroke-width:1;stroke-opacity:1" />
    '''
    
    # Position text based on prefix (X shapes on right side, red squares on left side, others centered)
    if prefix == 'x_shape':
        # For X shapes, position text on the right side of the rectangle
        text_x = x + width + 5  # 5px offset to the right
        text_y = y + height / 2  # Vertically centered
        text_anchor = "start"
    elif prefix == 'red_square':
        # For red squares, position text on the left side of the rectangle
        text_x = x - 5  # 5px offset to the left
        text_y = y + height / 2  # Vertically centered
        text_anchor = "end"
    else:
        # For other shapes, center the text
        text_x = x + width / 2
        text_y = y + height / 2
        text_anchor = "middle"
    
    text_element = f'''
    <text
       id="text_{prefix}_{rect_id}"
       x="{text_x}"
       y="{text_y}"
       style="font-family:Arial;font-size:12px;fill:{color};text-anchor:{text_anchor};dominant-baseline:central;font-weight:bold">{rect_id}</text>
    '''
    
    return rect_element + text_element

def print_drawn_objects(green_rectangles, pink_rectangles, x_shapes, red_squares, orange_rectangles):
    """Print summary information about all drawn objects in table format"""
    total_objects = len(green_rectangles) + len(pink_rectangles) + len(x_shapes) + len(red_squares) + len(orange_rectangles)
    
    print("\n" + "="*40)
    print("DRAWN OBJECTS SUMMARY")
    print("="*40)
    print(f"{'Object Type':<20} {'Count':<10}")
    print("-" * 40)
    print(f"{'Green Frames':<20} {len(green_rectangles):<10}")
    print(f"{'Pink Frames':<20} {len(pink_rectangles):<10}")
    print(f"{'X Shapes':<20} {len(x_shapes):<10}")
    print(f"{'Red Squares':<20} {len(red_squares):<10}")
    print(f"{'Orange Frames':<20} {len(orange_rectangles):<10}")
    print("-" * 40)
    print(f"{'TOTAL':<20} {total_objects:<10}")
    print("="*40)

def add_containers_to_svg(svg_content, green_rectangles, pink_rectangles, x_shapes, red_squares, orange_rectangles):
    """Add container rectangles to SVG content"""
    # Find the closing </svg> tag
    svg_end_pos = svg_content.rfind('</svg>')
    if svg_end_pos == -1:
        print("Error: Could not find closing </svg> tag")
        return None
    
    # Create container elements for green frames (green borders)
    container_elements = []
    for rect in green_rectangles:
        container_elements.append(create_rectangle_element(rect, color='#70ff00', prefix='green_container'))
    
    # Create container elements for pink frames (pink borders)
    for rect in pink_rectangles:
        container_elements.append(create_rectangle_element(rect, color='#ff69b4', prefix='pink_container'))
    
    # Create container elements for X shapes (blue borders)
    for rect in x_shapes:
        container_elements.append(create_rectangle_element(rect, color='#0000ff', prefix='x_shape'))
    
    # Create container elements for red squares (red borders)
    for rect in red_squares:
        container_elements.append(create_rectangle_element(rect, color='#ff0000', prefix='red_square'))
    
    # Create container elements for orange frames (orange borders)
    for rect in orange_rectangles:
        container_elements.append(create_rectangle_element(rect, color='#fb7905', prefix='orange_container'))
    
    # Insert container elements before closing </svg> tag
    containers_svg = '\n'.join(container_elements)
    modified_svg = svg_content[:svg_end_pos] + '\n' + containers_svg + '\n' + svg_content[svg_end_pos:]
    
    return modified_svg

def save_svg_file(svg_content, output_path):
    """Save SVG content to file"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        return True
    except Exception as e:
        return False

def run_step10():
    """Main function to process Step 10"""
    # Define file paths
    base_dir = Path(__file__).parent.parent
    green_frames_path = base_dir / "greenFrames.json"
    pink_frames_path = base_dir / "pinkFrames.json"
    x_shapes_path = base_dir / "x-shores.json"
    red_squares_path = base_dir / "square-shores.json"
    orange_frames_path = base_dir / "orangeFrames.json"
    step2_svg_path = base_dir / "files" / "Step2.svg"
    output_path = base_dir / "files" / "step10.svg"
    
    # Load data silently
    green_frames_data = load_green_frames(green_frames_path)
    if not green_frames_data:
        return False
    
    green_rectangles = green_frames_data.get('rectangles', [])
    
    pink_frames_data = load_pink_frames(pink_frames_path)
    if not pink_frames_data:
        return False
    
    pink_rectangles = pink_frames_data.get('pink_shapes', [])
    
    x_shapes_data = load_x_shapes(x_shapes_path)
    if not x_shapes_data:
        return False
    
    x_shapes = x_shapes_data.get('x_shapes', [])
    
    red_squares_data = load_red_squares(red_squares_path)
    if not red_squares_data:
        return False
    
    red_squares = red_squares_data.get('red_squares', [])
    
    orange_frames_data = load_orange_frames(orange_frames_path)
    if not orange_frames_data:
        return False
    
    orange_rectangles = orange_frames_data.get('rectangles', [])
    
    # Filter out X-shapes that overlap with red squares (silently)
    filtered_x_shapes = filter_overlapping_x_shapes(x_shapes, red_squares)
    
    # Print only the table
    print_drawn_objects(green_rectangles, pink_rectangles, filtered_x_shapes, red_squares, orange_rectangles)
    
    # Process SVG silently
    svg_content = read_svg_file(step2_svg_path)
    if not svg_content:
        return False
    
    modified_svg = add_containers_to_svg(svg_content, green_rectangles, pink_rectangles, filtered_x_shapes, red_squares, orange_rectangles)
    if not modified_svg:
        return False
    
    # Save silently
    success = save_svg_file(modified_svg, output_path)
    
    return success

def main():
    """Main function to process Step 10"""
    return run_step10()

if __name__ == "__main__":
    main()
