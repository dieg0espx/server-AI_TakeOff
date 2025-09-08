import re
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


# ====== SETTING ELEMENTS COLOR LIGHTGRAY AND BLACK SLABBANDS ====== #

# This step is to modify the stroke and fill colors of the SVG file
def modify_svg_stroke_and_fill(svg_text, black_stroke="#000000", white_stroke="#4e4e4e", new_stroke="#4e4e4e", fill_color="#4e4e4e"):
    try:
        # Find and print IDs of elements with #ffdf7f
        yellow_elements = re.finditer(r'<[^>]*?id="([^"]*)"[^>]*(?:stroke|fill):#ffdf7f[^>]*>', svg_text)
        skipped_ids = set()
        for match in yellow_elements:
            if match.group(1):  # if ID exists
                skipped_ids.add(match.group(1))
        
        # if skipped_ids:
            # print("Skipped elements with #ffdf7f (by ID):", ", ".join(skipped_ids))

        # Modify stroke colors, but skip elements with #ffdf7f and #fb3205
        modified_svg_text = re.sub(
            r'(?:<[^>]*(?:stroke|fill):#(?:ffdf7f|fb3205)[^>]*>)|(?:stroke:(#[0-9a-fA-F]{6}))',
            lambda m: m.group(0) if any(color in m.group(0) for color in ['ffdf7f', 'fb3205']) else (
                f"stroke:{new_stroke}" if m.group(1) == black_stroke else f"stroke:{white_stroke}"
            ),
            svg_text
        )

        # Modify fill colors, but skip elements with #ffdf7f and #fb3205
        modified_svg_text = re.sub(
            r'(?:<[^>]*(?:stroke|fill):#(?:ffdf7f|fb3205)[^>]*>)|(?:fill:(#[0-9a-fA-F]{6}))',
            lambda m: m.group(0) if any(color in m.group(0) for color in ['ffdf7f', 'fb3205']) else f"fill:{fill_color}",
            modified_svg_text
        )

        # Continue with text modifications
        modified_svg_text = re.sub(r'(<text[^>]*style="[^"]*)fill:[#0-9a-fA-F]+', rf'\1fill:{new_stroke}', modified_svg_text)
        modified_svg_text = re.sub(r'(<text[^>]*style="[^"]*)stroke:[#0-9a-fA-F]+', rf'\1stroke:{new_stroke}', modified_svg_text)
        modified_svg_text = re.sub(r'(<text(?![^>]*style=)[^>]*)>', rf'\1 style="fill:{new_stroke}; stroke:{new_stroke}">', modified_svg_text)

        # Change all #ffdf7f elements to #000000
        modified_svg_text = re.sub(
            r'(stroke|fill):#ffdf7f',
            r'\1:#000000',
            modified_svg_text
        )

        return modified_svg_text

    except Exception as e:
        
        print(f"Error modifying SVG colors: {e}")
        return svg_text

def run_step2():
    """
    Main function to run Step2 processing
    """
    try:
        # Get the current working directory to determine the correct paths
        current_dir = os.getcwd()
        
        # If we're in the processors directory, use relative paths
        if current_dir.endswith('processors'):
            input_svg = "../files/Step1.svg"
            output_svg = "../files/Step2.svg"
        else:
            # If we're in the server directory (when called from pipeline), use direct paths
            input_svg = "files/Step1.svg"
            output_svg = "files/Step2.svg"
        
        # Check if input file exists
        if not os.path.exists(input_svg):
            print(f"Error: Input file '{input_svg}' not found!")
            print(f"Current working directory: {os.getcwd()}")
            print(f"Tried path: {input_svg}")
            return False
        
        # Read the input file
        with open(input_svg, "r", encoding="utf-8") as file:
            svg_text = file.read()
        
        # Modify the colors
        
        print("Modifying colors...")
        final_svg = modify_svg_stroke_and_fill(svg_text)
        
        # Write the final result
        with open(output_svg, "w", encoding="utf-8") as file:
            file.write(final_svg)
        
        
        print(f"✅ Step2 completed successfully:")
        print(f"   - Input SVG: {input_svg}")
        print(f"   - Processed SVG: {output_svg}")
        return True
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return False

# Main execution
if __name__ == "__main__":
    run_step2()
