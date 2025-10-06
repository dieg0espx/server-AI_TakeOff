#!/usr/bin/env python3
"""
Step 11: Take Step4.svg and make the black <g> elements (slab bands) overlap the rest of the elements
Black <g> elements with fill:#000000 in their style attribute are considered slab bands.
They will be moved to render after all <p> tags to ensure they appear on top of other elements.
"""

import re
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def read_svg_file(svg_path):
    """Read SVG file content"""
    try:
        with open(svg_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading SVG file: {e}")
        return None

def save_svg_file(svg_content, output_path):
    """Save SVG content to file"""
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        return True
    except Exception as e:
        print(f"Error saving SVG file: {e}")
        return False

def extract_black_path_elements(svg_content):
    """
    Extract all <path> elements with black fill (slab bands) from the SVG content.
    This approach preserves the XML structure by only moving the path elements themselves.
    """
    # Pattern to match <path> elements with black fill
    black_path_pattern = re.compile(
        r'<path[^>]*style="[^"]*fill:#000000[^"]*"[^>]*>',
        re.IGNORECASE | re.MULTILINE | re.DOTALL
    )
    
    black_path_elements = []
    modified_content = svg_content
    
    # Find all <path> elements with black fill
    for match in black_path_pattern.finditer(svg_content):
        black_path_elements.append(match.group(0))
        # Remove the black <path> element from its original position
        modified_content = modified_content.replace(match.group(0), '', 1)
    
    print(f"Found {len(black_path_elements)} <path> elements with black fill (slab bands)")
    return black_path_elements, modified_content

def add_black_path_elements_on_top(svg_content, black_path_elements):
    """
    Add the black <path> elements before the final closing tags to ensure they render on top of other elements.
    """
    if not black_path_elements:
        return svg_content
    
    # Find the pattern </g></g></g></svg> at the end
    final_pattern = '</g></g></g></svg>'
    pattern_pos = svg_content.rfind(final_pattern)
    
    if pattern_pos == -1:
        print("Warning: Could not find final closing pattern, adding black elements at the end")
        # Fallback to adding at the end
        svg_end_pos = svg_content.rfind('</svg>')
        if svg_end_pos == -1:
            print("Error: Could not find closing </svg> tag")
            return svg_content
        insert_pos = svg_end_pos
    else:
        # Insert before the final closing pattern
        insert_pos = pattern_pos
    
    # Create a comment to identify the black path elements section
    black_path_comment = '\n    <!-- Black <path> elements (slab bands) - rendered on top -->\n'
    
    # Add all black <path> elements before the final closing tags
    black_path_elements_svg = black_path_comment + '\n'.join(f'    {element}' for element in black_path_elements)
    
    modified_svg = svg_content[:insert_pos] + '\n' + black_path_elements_svg + '\n' + svg_content[insert_pos:]
    
    return modified_svg

def process_step11():
    """
    Main function to process Step 11:
    1. Read Step4.svg
    2. Extract black strips (slab bands)
    3. Remove them from their original positions
    4. Add them at the end to ensure they overlap other elements
    5. Save as step11.svg
    """
    try:
        # Define file paths
        base_dir = Path(__file__).parent.parent
        input_svg_path = base_dir / "files" / "Step4.svg"
        output_svg_path = base_dir / "files" / "step11.svg"
        
        # Check if input file exists
        if not input_svg_path.exists():
            print(f"Error: Input file '{input_svg_path}' not found!")
            return False
        
        print(f"Processing Step 11...")
        print(f"Input: {input_svg_path}")
        print(f"Output: {output_svg_path}")
        
        # Read SVG content
        svg_content = read_svg_file(input_svg_path)
        if not svg_content:
            return False
        
        # Extract black <path> elements and get modified content
        black_path_elements, content_without_black_paths = extract_black_path_elements(svg_content)
        
        if not black_path_elements:
            print("Warning: No black <path> elements found in the SVG")
            return False
        
        # Add black <path> elements on top
        final_svg_content = add_black_path_elements_on_top(content_without_black_paths, black_path_elements)
        
        # Save the result
        success = save_svg_file(final_svg_content, output_svg_path)
        
        if success:
            print(f"✅ Step 11 completed successfully!")
            print(f"   - Processed {len(black_path_elements)} black <path> elements")
            print(f"   - Output saved to: {output_svg_path}")
            return True
        else:
            print(f"❌ Failed to save output file")
            return False
            
    except Exception as e:
        print(f"❌ An error occurred in Step 11: {str(e)}")
        return False

def run_step11():
    """Wrapper function for compatibility"""
    return process_step11()

# Main execution
if __name__ == "__main__":
    process_step11()