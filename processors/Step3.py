import re
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


def add_background_to_svg(input_file, output_file, background_color):
    """
    Adds a background color to the SVG by inserting a <rect> element.
    """
    try:
        with open(input_file, "r", encoding="utf-8") as file:
            svg_text = file.read()

        # Insert a <rect> element after the opening <svg> tag
        svg_text = re.sub(
            r'(<svg[^>]*>)',
            rf'\1<rect width="100%" height="100%" fill="{background_color}" />',
            svg_text,
            count=1
        )

        with open(output_file, "w", encoding="utf-8") as file:
            file.write(svg_text)

    except Exception as e:
        
        print(f"Error adding background to SVG: {e}")

def run_step3():
    """
    Main function to run Step3 processing
    """
    try:
        # Get the current working directory to determine the correct paths
        current_dir = os.getcwd()
        
        # If we're in the processors directory, use relative paths
        if current_dir.endswith('processors'):
            input_svg = "../files/Step2.svg"
            output_svg = "../files/Step3.svg"
        else:
            # If we're in the server directory (when called from pipeline), use direct paths
            input_svg = "files/Step2.svg"
            output_svg = "files/Step3.svg"
        
        background_color = "#202124"  # Gray background
        
        # Check if input file exists
        if not os.path.exists(input_svg):
            
            print(f"Error: Input file '{input_svg}' not found!")
            print(f"Current working directory: {os.getcwd()}")
            print(f"Tried path: {input_svg}")
            return False
        
        add_background_to_svg(input_svg, output_svg, background_color)
        
        
        print(f"✅ Step3 completed successfully:")
        print(f"   - Input SVG: {input_svg}")
        print(f"   - Processed SVG: {output_svg}")
        return True
            
    except Exception as e:
        
        print(f"An error occurred: {str(e)}")
        return False

# Main execution
if __name__ == "__main__":
    run_step3()