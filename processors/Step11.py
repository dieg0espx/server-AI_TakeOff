#!/usr/bin/env python3
"""
Step 10: Draw containers from greenFrames.json, pinkFrames.json, x-shores.json, and square-shores.json onto Step2.svg
Adds red border rectangles (green frames), pink border rectangles (pink frames), blue border rectangles (X shapes), and red border rectangles (red squares) with numeration to the SVG
"""

import json
import os
import sys
import re
from pathlib import Path
import cairosvg

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

def load_yellow_frames(json_path):
    """Load yellow frames data from JSON file"""
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

def print_drawn_objects(green_rectangles, pink_rectangles, x_shapes, red_squares, orange_rectangles, yellow_rectangles):
    """Print summary information about all drawn objects in table format"""
    total_objects = len(green_rectangles) + len(pink_rectangles) + len(x_shapes) + len(red_squares) + len(orange_rectangles) + len(yellow_rectangles)

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
    print(f"{'Yellow Frames':<20} {len(yellow_rectangles):<10}")
    print("-" * 40)
    print(f"{'TOTAL':<20} {total_objects:<10}")
    print("="*40)

def add_containers_to_svg(svg_content, green_rectangles, pink_rectangles, x_shapes, red_squares, orange_rectangles, yellow_rectangles):
    """Add container rectangles to SVG content"""
    # Find the opening <svg> tag to get viewBox dimensions
    svg_start_pos = svg_content.find('<svg')
    if svg_start_pos == -1:
        print("Error: Could not find opening <svg> tag")
        return None
    
    # Extract viewBox from SVG tag
    svg_tag_end = svg_content.find('>', svg_start_pos)
    svg_tag = svg_content[svg_start_pos:svg_tag_end + 1]
    
    # Try to extract viewBox dimensions
    import re
    viewbox_match = re.search(r'viewBox="([^"]*)"', svg_tag)
    if viewbox_match:
        viewbox = viewbox_match.group(1).split()
        if len(viewbox) >= 4:
            width = float(viewbox[2])
            height = float(viewbox[3])
        else:
            # Fallback dimensions if viewBox is not found
            width = 3000
            height = 2000
    else:
        # Fallback dimensions if viewBox is not found
        width = 3000
        height = 2000
    
    # Create dark gray background rectangle
    background_element = f'''
    <rect
       id="background"
       x="0"
       y="0"
       width="{width}"
       height="{height}"
       style="fill:#1c1c1c;stroke:none" />
    '''
    
    # Insert background right after the opening <svg> tag
    svg_tag_end_pos = svg_content.find('>', svg_start_pos) + 1
    svg_with_background = svg_content[:svg_tag_end_pos] + '\n' + background_element + svg_content[svg_tag_end_pos:]
    
    # Find the closing </svg> tag
    svg_end_pos = svg_with_background.rfind('</svg>')
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

    # Create container elements for yellow frames (yellow borders)
    for rect in yellow_rectangles:
        container_elements.append(create_rectangle_element(rect, color='#ffff00', prefix='yellow_container'))

    # Insert container elements before closing </svg> tag
    containers_svg = '\n'.join(container_elements)
    modified_svg = svg_with_background[:svg_end_pos] + '\n' + containers_svg + '\n' + svg_with_background[svg_end_pos:]
    
    return modified_svg

def save_svg_file(svg_content, output_path):
    """Save SVG content to file"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        return True
    except Exception as e:
        return False

def convert_svg_to_png(svg_path, png_path):
    """Convert SVG to PNG"""
    try:
        print(f"🔄 Attempting to convert {svg_path} to {png_path}")
        cairosvg.svg2png(url=str(svg_path), write_to=str(png_path))
        print(f"✅ Successfully converted SVG to PNG: {png_path}")
        return True
    except Exception as e:
        print(f"❌ Error converting SVG to PNG: {e}")
        print(f"❌ Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

_DIM_H_ABS = re.compile(r'\bM\s*(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)\s*H\s*(-?\d+(?:\.\d+)?)\b')
_DIM_V_ABS = re.compile(r'\bM\s*(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)\s*V\s*(-?\d+(?:\.\d+)?)\b')
_DIM_H_REL = re.compile(r'\bm\s*(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)\s*h\s*(-?\d+(?:\.\d+)?)\b')
_DIM_V_REL = re.compile(r'\bm\s*(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)\s*v\s*(-?\d+(?:\.\d+)?)\b')


def _candidate_segment(path_d, target_dimension, tolerance):
    """If path_d has an H/V run matching target_dimension (±tolerance), return
    (orient, x1, y1, x2, y2) in the path's *local* coordinate frame, else None.
    Only the first matching run is returned."""
    def matches(v):
        return abs(v - target_dimension) <= tolerance

    m = _DIM_H_ABS.search(path_d)
    if m:
        x1, y1, x2 = float(m.group(1)), float(m.group(2)), float(m.group(3))
        if matches(abs(x2 - x1)):
            return ('h', min(x1, x2), y1, max(x1, x2), y1)
    m = _DIM_V_ABS.search(path_d)
    if m:
        x1, y1, y2 = float(m.group(1)), float(m.group(2)), float(m.group(3))
        if matches(abs(y2 - y1)):
            return ('v', x1, min(y1, y2), x1, max(y1, y2))
    m = _DIM_H_REL.search(path_d)
    if m:
        sx, sy, dx = float(m.group(1)), float(m.group(2)), float(m.group(3))
        if matches(abs(dx)):
            return ('h', min(sx, sx + dx), sy, max(sx, sx + dx), sy)
    m = _DIM_V_REL.search(path_d)
    if m:
        sx, sy, dy = float(m.group(1)), float(m.group(2)), float(m.group(3))
        if matches(abs(dy)):
            return ('v', sx, min(sy, sy + dy), sx, max(sy, sy + dy))
    return None


_MATRIX_RE = re.compile(
    r"matrix\(\s*([-\d.]+)[,\s]+([-\d.]+)[,\s]+([-\d.]+)[,\s]+([-\d.]+)[,\s]+([-\d.]+)[,\s]+([-\d.]+)\s*\)"
)


def _build_parent_and_transform_maps(svg_content):
    """Parse the SVG once via ElementTree; return (parent_of, accumulated_transform).
    `accumulated_transform[el]` is the composed matrix from root → el's *parent*
    (so applying it to a child's local coords yields world coords)."""
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(svg_content)
    except ET.ParseError:
        return None, None

    parent_of = {child: parent for parent in root.iter() for child in parent}

    def parse_matrix(el):
        m = _MATRIX_RE.search(el.get('transform', '') or '')
        if not m:
            return None
        return tuple(float(m.group(i)) for i in range(1, 7))

    def compose(A, B):
        # A then B → (a,b,c,d,e,f) result
        a1, b1, c1, d1, e1, f1 = A
        a2, b2, c2, d2, e2, f2 = B
        return (
            a1*a2 + c1*b2,
            b1*a2 + d1*b2,
            a1*c2 + c1*d2,
            b1*c2 + d1*d2,
            a1*e2 + c1*f2 + e1,
            b1*e2 + d1*f2 + f1,
        )

    IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    accumulated = {root: IDENTITY}
    # BFS to compose transforms down the tree
    queue = [root]
    while queue:
        node = queue.pop()
        parent_xform = accumulated[node]
        for child in list(node):
            own = parse_matrix(child)
            xform = compose(parent_xform, own) if own else parent_xform
            accumulated[child] = xform
            queue.append(child)

    # Map by id for fast lookup from raw-regex matches
    by_id = {}
    for el in root.iter():
        eid = el.get('id', '')
        if eid:
            # parent's accumulated transform is what applies to el's local coords
            par = parent_of.get(el)
            if par is not None and par in accumulated:
                by_id[eid] = accumulated[par]
            else:
                by_id[eid] = IDENTITY
    return parent_of, by_id


def _apply_matrix(mx, x, y):
    a, b, c, d, tx, ty = mx
    return a * x + c * y + tx, b * x + d * y + ty


def mark_alum_beams_by_dimension(svg_content, target_dimension, stroke_color, tolerance=0):
    """Turn the stroke color of any <path> whose H/V run matches target_dimension
    AND has at least one parallel same-dimension partner rail nearby. Returns
    (updated_svg_content, changed_count).

    Real aluminum beams are always drawn as TWO parallel rails. A lone matching
    line is almost always a dimension/construction line that just happens to
    share a beam's nominal length — recoloring it gives a misleading SVG.
    """
    path_pattern = re.compile(r'<path\b[^>]*>')
    style_pattern = re.compile(r'\bstyle="([^"]*)"')
    d_pattern = re.compile(r'\bd="([^"]*)"')
    id_pattern = re.compile(r'\bid="([^"]+)"')

    # Build ancestor-transform map so we can convert local path coords → world.
    _parent_of, xform_by_id = _build_parent_and_transform_maps(svg_content)

    # Pass 1: collect candidate rails (geometry + fill/z guards).
    candidates = []  # list of (path_id, orient, x1, y1, x2, y2)
    for m in path_pattern.finditer(svg_content):
        tag = m.group(0)
        d_m = d_pattern.search(tag)
        st_m = style_pattern.search(tag)
        id_m = id_pattern.search(tag)
        if not (d_m and st_m and id_m):
            continue

        path_d = d_m.group(1)
        seg = _candidate_segment(path_d, target_dimension, tolerance)
        if seg is None:
            continue

        style_value = st_m.group(1)
        fill_m = re.search(r'fill\s*:\s*([^;"]+)', style_value, re.IGNORECASE)
        fill_val = fill_m.group(1).strip().lower() if fill_m else ''
        if fill_val and fill_val != 'none':
            continue
        if re.search(r'\bz\b', path_d, re.IGNORECASE):
            continue

        path_id = id_m.group(1)
        orient, lx1, ly1, lx2, ly2 = seg
        # Map to world coords via ancestor transform.
        mx = xform_by_id.get(path_id) if xform_by_id else None
        if mx is not None:
            wx1, wy1 = _apply_matrix(mx, lx1, ly1)
            wx2, wy2 = _apply_matrix(mx, lx2, ly2)
        else:
            wx1, wy1, wx2, wy2 = lx1, ly1, lx2, ly2
        candidates.append((
            path_id, orient,
            min(wx1, wx2), min(wy1, wy2),
            max(wx1, wx2), max(wy1, wy2),
        ))

    # Pass 2: keep only candidates that have a same-orientation parallel
    # partner (different perpendicular coord, overlapping parallel extent).
    EXTENT_TOL = 2.0
    OFFSET_TOL = 1.0  # essentially-same line → not a partner

    def has_partner(c):
        _id_c, o_c, cx1, cy1, cx2, cy2 = c
        for d in candidates:
            if d is c:
                continue
            _id_d, o_d, dx1, dy1, dx2, dy2 = d
            if o_d != o_c:
                continue
            if o_c == 'h':
                if abs(cy1 - dy1) < OFFSET_TOL:
                    continue
                if min(cx2, dx2) - max(cx1, dx1) > EXTENT_TOL:
                    return True
            else:
                if abs(cx1 - dx1) < OFFSET_TOL:
                    continue
                if min(cy2, dy2) - max(cy1, dy1) > EXTENT_TOL:
                    return True
        return False

    keepers = {c[0] for c in candidates if has_partner(c)}

    changed_count = 0

    def replace_path(match):
        nonlocal changed_count
        tag = match.group(0)
        id_m = id_pattern.search(tag)
        st_m = style_pattern.search(tag)
        if not (id_m and st_m):
            return tag
        if id_m.group(1) not in keepers:
            return tag

        style_value = st_m.group(1)
        if f'stroke:{stroke_color}'.lower() in style_value.lower():
            return tag

        if re.search(r'stroke\s*:\s*#[0-9a-fA-F]{3,6}', style_value):
            updated_style = re.sub(r'stroke\s*:\s*#[0-9a-fA-F]{3,6}', f'stroke:{stroke_color}', style_value)
        elif 'stroke:' in style_value:
            updated_style = re.sub(r'stroke\s*:\s*[^;"]+', f'stroke:{stroke_color}', style_value)
        else:
            updated_style = style_value + f';stroke:{stroke_color}'

        changed_count += 1
        return tag.replace(st_m.group(0), f'style="{updated_style}"', 1)

    updated_svg = path_pattern.sub(replace_path, svg_content)
    return updated_svg, changed_count

def update_data_json_with_counts(green_count, pink_count, x_count, red_count, orange_count, yellow_count, beam_counts):
    """Update data.json with current step results"""
    try:
        base_dir = Path(__file__).parent.parent
        data_file = base_dir / "data.json"

        # Load existing data.json
        if data_file.exists():
            with open(data_file, 'r') as f:
                data = json.load(f)
        else:
            data = {}

        # Update step_results
        data["step_results"] = {
            "step5_blue_X_shapes": x_count,
            "step6_red_squares": red_count,
            "step7_pink_shapes": pink_count,
            "step8_green_rectangles": green_count,
            "step9_orange_rectangles": orange_count,
            "step11_yellow_shapes": yellow_count
        }
        data["step_results"].update(beam_counts)

        # Write back to data.json
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=4)

        return True
    except Exception as e:
        print(f"⚠️  Error updating data.json: {e}")
        return False

def save_beam_counts_json(beam_counts):
    """Save each beam count into tempData for main pipeline aggregation."""
    try:
        base_dir = Path(__file__).parent.parent
        temp_data_dir = base_dir / "files" / "tempData"
        for key, count in beam_counts.items():
            output_file = temp_data_dir / f"{key}.json"
            with open(output_file, 'w') as f:
                json.dump({key: count}, f, indent=4)
        return True
    except Exception as e:
        print(f"⚠️  Error saving beam count JSON files: {e}")
        return False

def run_step11():
    """Main function to process Step 10"""
    # Define file paths
    base_dir = Path(__file__).parent.parent
    green_frames_path = base_dir / "files" / "tempData" / "greenFrames.json"
    pink_frames_path = base_dir / "files" / "tempData" / "pinkFrames.json"
    x_shapes_path = base_dir / "files" / "tempData" / "x-shores.json"
    red_squares_path = base_dir / "files" / "tempData" / "square-shores.json"
    orange_frames_path = base_dir / "files" / "tempData" / "orangeFrames.json"
    yellow_frames_path = base_dir / "files" / "tempData" / "yellowFrames.json"
    step2_svg_path = base_dir / "files" / "Step2.svg"
    output_path = base_dir / "files" / "Step11.svg"

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

    yellow_frames_data = load_yellow_frames(yellow_frames_path)
    if not yellow_frames_data:
        # Yellow frames are optional - continue with empty list
        yellow_rectangles = []
    else:
        yellow_rectangles = yellow_frames_data.get('shapes', [])

    # Filter out X-shapes that overlap with red squares (silently)
    filtered_x_shapes = filter_overlapping_x_shapes(x_shapes, red_squares)

    # Print only the table
    print_drawn_objects(green_rectangles, pink_rectangles, filtered_x_shapes, red_squares, orange_rectangles, yellow_rectangles)

    # Process SVG silently
    svg_content = read_svg_file(step2_svg_path)
    if not svg_content:
        return False

    modified_svg = add_containers_to_svg(svg_content, green_rectangles, pink_rectangles, filtered_x_shapes, red_squares, orange_rectangles, yellow_rectangles)
    if not modified_svg:
        return False

    # Beam categories and styling rules
    beam_specs = [
        ("alumBeam20", 1500, 1, "#A020F0"),
        ("alumBeam18", 1350, 1, "#FFD400"),
        ("alumBeam16", 1201, 1, "#ffffff"),
        ("alumBeam14", 1050, 1, "#1D915C"),
        ("alumBeam13", 975, 1, "#9CFF9C"),
        ("alumBeam12", 900, 1, "#F54927"),
        ("alumBeam11", 825, 1, "#FF6EC7"),
        ("alumBeam10_6", 787, 1, "#FFA805"),
        ("alumBeam10", 750, 1, "#00C8FF"),
        ("alumBeam9", 675, 1, "#B52FC4"),
        ("alumBeam8", 600, 1, "#00FFFF"),
        ("alumBeam7", 525, 1, "#FFBC85"),
        ("alumBeam6", 451, 1, "#E6E600"),
        ("alumBeam5", 376, 1, "#4084FF"),
    ]

    beam_counts = {}
    for beam_key, beam_dimension, beam_tolerance, beam_color in beam_specs:
        modified_svg, beam_count = mark_alum_beams_by_dimension(
            modified_svg,
            beam_dimension,
            beam_color,
            beam_tolerance,
        )
        beam_counts[beam_key] = beam_count

    # Update data.json with counts
    update_data_json_with_counts(
        len(green_rectangles),
        len(pink_rectangles),
        len(filtered_x_shapes),
        len(red_squares),
        len(orange_rectangles),
        len(yellow_rectangles),
        beam_counts
    )
    save_beam_counts_json(beam_counts)

    # Save SVG
    success = save_svg_file(modified_svg, output_path)
    if not success:
        return False

    # Convert to PNG
    png_output_path = base_dir / "files" / "Step11-results.png"
    png_success = convert_svg_to_png(output_path, png_output_path)

    return success and png_success

def main():
    """Main function to process Step 10"""
    return run_step11()

if __name__ == "__main__":
    main()
