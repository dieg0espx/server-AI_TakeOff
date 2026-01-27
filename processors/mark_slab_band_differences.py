#!/usr/bin/env python3
"""
Mark Slab Band Differences: Add * markers to annotations that are hidden by slab band.

This script compares detection results from no_slab_band and with_slab_band runs,
and adds a "*" marker to elements in the final SVG that are NOT detected when
slab band is applied.
"""

import os
import json
import re
from pathlib import Path


def load_json_file(filepath):
    """Load JSON file and return data"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"  Error loading {filepath}: {e}")
        return None


def get_element_key(element, element_type):
    """
    Generate a unique key for an element based on its position.
    Uses center coordinates rounded to nearest 5 pixels for fuzzy matching.
    """
    if element_type == 'x_shape':
        x = element.get('center_x', element.get('x', 0))
        y = element.get('center_y', element.get('y', 0))
    else:
        # For rectangles, use center of bounding box
        x = element.get('x', 0) + element.get('width', 0) / 2
        y = element.get('y', 0) + element.get('height', 0) / 2

    # Round to nearest 10 pixels for fuzzy matching
    return (round(x / 10) * 10, round(y / 10) * 10)


def find_missing_elements(no_slab_data, with_slab_data, element_type):
    """
    Find elements that exist in no_slab_data but not in with_slab_data.
    Returns list of indices (1-based) of missing elements.
    """
    if not no_slab_data or not with_slab_data:
        return []

    # Get the list key based on element type
    key_map = {
        'x_shapes': 'x_shapes',
        'green_rectangles': 'rectangles',
        'pink_shapes': 'pink_shapes',
        'orange_rectangles': 'rectangles',
        'red_squares': 'red_squares'
    }

    list_key = key_map.get(element_type, 'shapes')

    no_slab_elements = no_slab_data.get(list_key, [])
    with_slab_elements = with_slab_data.get(list_key, [])

    # Create set of position keys for with_slab elements
    with_slab_keys = set()
    for elem in with_slab_elements:
        key = get_element_key(elem, element_type)
        with_slab_keys.add(key)

    # Find missing elements (in no_slab but not in with_slab)
    missing_indices = []
    for idx, elem in enumerate(no_slab_elements):
        key = get_element_key(elem, element_type)
        if key not in with_slab_keys:
            missing_indices.append(idx + 1)  # 1-based index

    return missing_indices


def add_asterisk_to_svg_labels(svg_path, missing_elements_by_type, output_path=None):
    """
    Add * to labels in SVG for elements that are missing in slab band detection.

    missing_elements_by_type: dict with keys like 'green', 'pink', 'blue', 'orange', 'red'
                              and values as lists of missing indices
    """
    try:
        with open(svg_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()

        modified = False

        # Color mapping for label identification
        color_patterns = {
            'green': r'fill="(?:#70ff00|#00ff00|green)"',
            'pink': r'fill="(?:#ff00cd|#ff00ff|pink|magenta)"',
            'blue': r'fill="(?:#0000ff|blue)"',
            'orange': r'fill="(?:#fb7905|#ff7f00|orange)"',
            'red': r'fill="(?:#fb0505|#ff0000|red)"'
        }

        for color, missing_indices in missing_elements_by_type.items():
            if not missing_indices:
                continue

            print(f"  Marking {len(missing_indices)} {color} elements: {missing_indices}")

            for idx in missing_indices:
                # Pattern to find text elements with the number
                # Look for <text ...>NUMBER</text> patterns
                patterns = [
                    # Pattern 1: Simple text with number
                    rf'(<text[^>]*>)({idx})(</text>)',
                    # Pattern 2: Text with tspan
                    rf'(<tspan[^>]*>)({idx})(</tspan>)',
                ]

                for pattern in patterns:
                    # Find and replace, adding * after the number
                    new_content = re.sub(
                        pattern,
                        rf'\g<1>\g<2>*\g<3>',
                        svg_content,
                        count=1  # Only replace first occurrence
                    )
                    if new_content != svg_content:
                        svg_content = new_content
                        modified = True
                        break

        if output_path is None:
            output_path = svg_path

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)

        if modified:
            print(f"  ✅ Added * markers to {output_path}")
        else:
            print(f"  ⚠️  No labels were modified in {output_path}")

        return modified

    except Exception as e:
        print(f"  ❌ Error modifying SVG: {e}")
        return False


def mark_differences(base_dir=None):
    """
    Main function to mark slab band differences in the final SVG.
    """
    print("=" * 60)
    print("Marking Slab Band Differences")
    print("=" * 60)

    if base_dir is None:
        base_dir = Path(__file__).parent.parent
    else:
        base_dir = Path(base_dir)

    temp_data = base_dir / "files" / "tempData"

    # We need to compare results from both runs
    # The JSON files in tempData are from the LAST run (with_slab_band)
    # We need to save no_slab_band results separately

    # Check if we have saved no_slab_band results
    no_slab_dir = temp_data / "no_slab_band"
    with_slab_dir = temp_data  # Current files are from with_slab_band run

    if not no_slab_dir.exists():
        print("  ⚠️  No slab band results directory not found")
        print("  Run the pipeline first to generate both result sets")
        return False

    # Load and compare each element type
    missing_elements = {
        'blue': [],
        'green': [],
        'pink': [],
        'orange': [],
        'red': []
    }

    # Compare X shapes (blue)
    no_slab = load_json_file(no_slab_dir / "x-shores.json")
    with_slab = load_json_file(with_slab_dir / "x-shores.json")
    if no_slab and with_slab:
        missing_elements['blue'] = find_missing_elements(no_slab, with_slab, 'x_shapes')
        print(f"  Blue X shapes: {len(missing_elements['blue'])} hidden by slab band")

    # Compare Green rectangles
    no_slab = load_json_file(no_slab_dir / "greenFrames.json")
    with_slab = load_json_file(with_slab_dir / "greenFrames.json")
    if no_slab and with_slab:
        missing_elements['green'] = find_missing_elements(no_slab, with_slab, 'green_rectangles')
        print(f"  Green rectangles: {len(missing_elements['green'])} hidden by slab band")

    # Compare Pink shapes
    no_slab = load_json_file(no_slab_dir / "pinkFrames.json")
    with_slab = load_json_file(with_slab_dir / "pinkFrames.json")
    if no_slab and with_slab:
        missing_elements['pink'] = find_missing_elements(no_slab, with_slab, 'pink_shapes')
        print(f"  Pink shapes: {len(missing_elements['pink'])} hidden by slab band")

    # Compare Orange rectangles
    no_slab = load_json_file(no_slab_dir / "orangeFrames.json")
    with_slab = load_json_file(with_slab_dir / "orangeFrames.json")
    if no_slab and with_slab:
        missing_elements['orange'] = find_missing_elements(no_slab, with_slab, 'orange_rectangles')
        print(f"  Orange rectangles: {len(missing_elements['orange'])} hidden by slab band")

    # Compare Red squares
    no_slab = load_json_file(no_slab_dir / "square-shores.json")
    with_slab = load_json_file(with_slab_dir / "square-shores.json")
    if no_slab and with_slab:
        missing_elements['red'] = find_missing_elements(no_slab, with_slab, 'red_squares')
        print(f"  Red squares: {len(missing_elements['red'])} hidden by slab band")

    # Add * markers to the no_slab_band SVG (which is the one that gets uploaded)
    svg_path = base_dir / "files" / "Step10_no_slab_band.svg"

    if svg_path.exists():
        total_missing = sum(len(v) for v in missing_elements.values())
        print(f"\n  Total elements hidden by slab band: {total_missing}")

        if total_missing > 0:
            add_asterisk_to_svg_labels(svg_path, missing_elements)
        else:
            print("  No differences found - no markers to add")
    else:
        print(f"  ⚠️  SVG file not found: {svg_path}")
        return False

    print("=" * 60)
    return True


def run_mark_slab_band_differences():
    """Entry point for the marking script"""
    return mark_differences()


if __name__ == "__main__":
    mark_differences()
