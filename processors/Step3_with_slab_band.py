#!/usr/bin/env python3
"""
Step3 with Slab Band: Apply black element overlay technique
Takes Step3.svg and makes black elements render ON TOP of all other elements
by cloning them and appending at the end of the SVG document.
"""

import os
import sys
import re
import copy
import xml.etree.ElementTree as ET

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


def register_namespaces():
    """Register SVG namespaces to preserve them in output"""
    namespaces = {
        '': 'http://www.w3.org/2000/svg',
        'xlink': 'http://www.w3.org/1999/xlink',
        'sodipodi': 'http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd',
        'inkscape': 'http://www.inkscape.org/namespaces/inkscape',
    }
    for prefix, uri in namespaces.items():
        ET.register_namespace(prefix, uri)


def build_parent_map(root):
    """Create a dictionary mapping each element to its parent"""
    parent_map = {}
    for parent in root.iter():
        for child in parent:
            parent_map[child] = parent
    return parent_map


def is_black_color(color_value):
    """Check if a color value is black"""
    if not color_value:
        return False
    color = color_value.strip().lower()

    # Check keyword
    if color == 'black':
        return True

    # Check hex formats: #000, #000000, #00000000 (with alpha)
    if re.match(r'^#0{3}(?:0{3})?(?:[0-9a-f]{2})?$', color):
        return True

    # Check rgb/rgba formats
    if re.match(r'^rgba?\s*\(\s*0\s*,\s*0\s*,\s*0\s*(?:,\s*[\d.]+\s*)?\)$', color):
        return True

    return False


def parse_style_attribute(style):
    """Parse CSS style attribute into dictionary"""
    styles = {}
    if not style:
        return styles
    for item in style.split(';'):
        if ':' in item:
            key, value = item.split(':', 1)
            styles[key.strip()] = value.strip()
    return styles


def is_black_element(element):
    """Check if an element has black fill or stroke"""
    # Check direct attributes
    fill = element.get('fill')
    stroke = element.get('stroke')

    if is_black_color(fill) or is_black_color(stroke):
        return True

    # Check style attribute
    style = element.get('style')
    if style:
        styles = parse_style_attribute(style)
        if is_black_color(styles.get('fill')) or is_black_color(styles.get('stroke')):
            return True

    return False


def get_transform_chain(element, root, parent_map):
    """
    Walk up the tree and collect all transforms from ancestors.
    Returns the full transform chain as a single string.
    """
    transforms = []
    current = element

    while current is not None and current != root:
        transform = current.get('transform')
        if transform:
            transforms.insert(0, transform)  # Insert at beginning to maintain order
        current = parent_map.get(current)

    return ' '.join(transforms) if transforms else None


def apply_black_overlay(input_svg, output_svg):
    """
    Make black elements overlap all other elements in SVG.

    Algorithm:
    1. Find all black elements
    2. Get their full transform chain
    3. Clone them with transform wrapper
    4. Append clones at the END of the SVG document
    """
    try:
        print(f"  Reading SVG: {input_svg}")

        # Register namespaces before parsing
        register_namespaces()

        # Parse the SVG
        tree = ET.parse(input_svg)
        root = tree.getroot()

        # Build parent map for transform chain traversal
        parent_map = build_parent_map(root)

        # Find all black elements and their transform chains
        black_elements = []

        for element in root.iter():
            if is_black_element(element):
                transform_chain = get_transform_chain(element, root, parent_map)
                black_elements.append((element, transform_chain))

        print(f"  Found {len(black_elements)} black elements")

        if not black_elements:
            print("  No black elements found. Copying file as-is.")
            # Still write the file
            tree.write(output_svg, encoding='unicode', xml_declaration=True)
            return True

        # Create overlay group for cloned black elements
        overlay_group = ET.Element('g')
        overlay_group.set('id', 'black-overlay-slab-band')

        # Clone black elements with their transform chains
        for element, transform_chain in black_elements:
            # Deep copy the element
            cloned = copy.deepcopy(element)

            if transform_chain:
                # Create wrapper group with the full transform chain
                wrapper = ET.Element('g')
                wrapper.set('transform', transform_chain)
                wrapper.append(cloned)
                overlay_group.append(wrapper)
            else:
                # No transforms needed, just append the clone
                overlay_group.append(cloned)

        # Append overlay group at the END of the root element
        # This makes black elements render ON TOP of everything
        root.append(overlay_group)

        print(f"  Added overlay group with {len(black_elements)} cloned black elements")

        # Write the modified SVG
        tree.write(output_svg, encoding='unicode', xml_declaration=True)

        print(f"  Written to: {output_svg}")
        return True

    except ET.ParseError as e:
        print(f"  Error parsing SVG: {e}")
        return False
    except Exception as e:
        print(f"  Error applying black overlay: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_step3_with_slab_band():
    """
    Main function to run Step3 with slab band processing
    """
    try:
        print("=" * 60)
        print("Step3 with Slab Band: Making black elements overlap")
        print("=" * 60)

        # Get the current working directory to determine the correct paths
        current_dir = os.getcwd()

        # If we're in the processors directory, use relative paths
        if current_dir.endswith('processors'):
            input_svg = "../files/Step3.svg"
            output_svg = "../files/Step3_with_slab_band.svg"
        else:
            # If we're in the server directory (when called from pipeline), use direct paths
            input_svg = "files/Step3.svg"
            output_svg = "files/Step3_with_slab_band.svg"

        # Check if input file exists
        if not os.path.exists(input_svg):
            print(f"Error: Input file '{input_svg}' not found!")
            print(f"Current working directory: {os.getcwd()}")
            return False

        # Apply the black overlay technique
        success = apply_black_overlay(input_svg, output_svg)

        if success:
            print(f"\n✅ Step3 with Slab Band completed successfully:")
            print(f"   - Input SVG: {input_svg}")
            print(f"   - Output SVG: {output_svg}")
            print(f"   - Black elements now render ON TOP of all other elements")
        else:
            print(f"\n❌ Step3 with Slab Band failed")

        return success

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


# Usage
if __name__ == "__main__":
    run_step3_with_slab_band()
