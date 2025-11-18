import re
import os
import json
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from colorama import init, Fore, Style
from PatternComponents import shores_box, frames_6x4, frames_5x4, frames_inBox, shores, yellow_traffic_light
import cairosvg
import io
from PIL import Image

def print_table(box_count, shores_count, frames6x4_count, frames5x4_count, framesinbox_count):
    # Initialize colorama
    init()
    
    # Define colors for each category
    colors = {
        'Shores Box': Fore.RED,
        'Shores': Fore.BLUE,
        'Frames 6x4': Fore.GREEN,
        'Frames 5x4': Fore.MAGENTA,
        'Frames In Box': Fore.YELLOW
    }
    
    # Table dimensions
    width = 45
    
    print(f"\n{Fore.CYAN}{'='*width}")
    print(f"{' DETECTED ELEMENTS ':=^{width}}")
    print(f"{'='*width}{Style.RESET_ALL}")
    
    # Column headers
    print(f"{'Category':<30} {'':^8} {'Count':>6}")
    print(f"{'-'*width}")
    
    # Table rows with colored bullets
    elements = [
        ('Shores Box', box_count),
        ('Shores', shores_count),
        ('Frames 6x4', frames6x4_count),
        ('Frames 5x4', frames5x4_count),
        ('Frames In Box', framesinbox_count)
    ]
    
    for category, count in elements:
        color = colors[category]
        print(
            f"{category:<30} "
            f"{color}●{Style.RESET_ALL} "
            f"{count:>6}"
        )
    
    print(f"{'-'*width}")
    total = sum([box_count, shores_count, frames6x4_count, frames5x4_count, framesinbox_count])
    print(f"{'Total elements':<30} {'':^8} {total:>6}\n")

def append_counts_to_json(box_count, shores_count, frames6x4_count, frames5x4_count, framesinbox_count):
    # This function is no longer needed as we don't store objects in data.json
    # Keeping the function signature for compatibility but removing the JSON writing
    pass

def apply_color_to_specific_paths(input_file, output_file, red="#fb0505", blue="#0000ff", green="#70ff00", pink="#ff00cd", orange="#fb7905", yellow="#ffff00"):
    """
    Reads an SVG file and changes colors of specific paths:
    - shores_box paths to red
    - shores paths to blue
    - frames_6x4 paths to green
    - frames_5x4 paths to pink
    - frames_inBox paths to orange
    - yellow_traffic_light paths to yellow
    """
    try:
        if not os.path.exists(input_file):
            
            print(f"{input_file} not found.", "error")
            return

        with open(input_file, "r", encoding="utf-8") as file:
            svg_text = file.read()

        # Create regex patterns
        pattern_red = "|".join(re.escape(variation) for variation in shores_box)
        shores_box_pattern = re.compile(rf'<path[^>]+d="[^"]*({pattern_red})[^"]*"[^>]*>')
        
        frames6x4_pattern = re.compile(rf'<path[^>]+d="[^"]*({"|".join(re.escape(variation) for variation in frames_6x4)})[^"]*"[^>]*>')
        
        # Modified frames5x4 pattern including detection of diagonal segments
        frames5x4_base_pattern = "|".join(re.escape(variation) for variation in frames_5x4)
        # Generic diagonal pattern allowing leg lengths from 294-301px (covers 294-299/300/301)
        frames5x4_generic = r'h\s+(?:29[4-9]|30[0-1])\s+l\s+-?(?:29[4-9]|30[0-1]),-?(?:29[4-9]|30[0-1])'
        frames5x4_pattern = re.compile(
            rf'<path[^>]+d="[^"]*(?:({frames5x4_base_pattern})|({frames5x4_generic}))[^"]*"[^>]*>',
            re.IGNORECASE)
        
        framesinBox_pattern = re.compile(rf'<path[^>]+d="[^"]*({"|".join(re.escape(variation) for variation in frames_inBox)})[^"]*"[^>]*>')

        yellow_pattern = re.compile(rf'<path[^>]+d="[^"]*({"|".join(re.escape(variation) for variation in yellow_traffic_light)})[^"]*"[^>]*>')

        shores_pattern = re.compile(rf'<path[^>]+d="[^"]*({"|".join(re.escape(variation) for variation in shores)})[^"]*"[^>]*>')

        # Count matching paths
        match_count_box = len(shores_box_pattern.findall(svg_text))
        match_count_33_34 = len(shores_pattern.findall(svg_text))
        match_count_frames6x4 = len(frames6x4_pattern.findall(svg_text))
        match_count_frames5x4 = len(frames5x4_pattern.findall(svg_text))
        match_count_framesinBox = len(framesinBox_pattern.findall(svg_text))

        # Print table with counts
        print_table(
            match_count_box,
            match_count_33_34,
            match_count_frames6x4,
            match_count_frames5x4,
            match_count_framesinBox
        )

        # Append counts to JSON file
        append_counts_to_json(
            match_count_box,
            match_count_33_34,
            match_count_frames6x4,
            match_count_frames5x4,
            match_count_framesinBox
        )

        # Color change functions
        def change_to_red(match):
            path_tag = match.group(0)
            if "stroke" in path_tag:
                path_tag = re.sub(r'stroke:[#0-9a-fA-F]+', f'stroke:{red}', path_tag)
            else:
                path_tag = path_tag.replace("<path", f"<path stroke='{red}'", 1)
            if "fill" in path_tag:
                path_tag = re.sub(r'fill:[#0-9a-fA-F]+', f'fill:{red}', path_tag)
            else:
                path_tag = path_tag.replace("<path", f"<path fill='{red}'", 1)
            # Change colors inside style attributes
            path_tag = re.sub(r'style="[^"]*"', lambda m: re.sub(r'#[0-9a-fA-F]{6}', red, m.group(0)), path_tag)
            return path_tag

        def change_to_blue(match):
            path_tag = match.group(0)
            if "stroke" in path_tag:
                path_tag = re.sub(r'stroke:[#0-9a-fA-F]+', f'stroke:{blue}', path_tag)
            else:
                path_tag = path_tag.replace("<path", f"<path stroke='{blue}'", 1)
            if "fill" in path_tag:
                path_tag = re.sub(r'fill:[#0-9a-fA-F]+', f'fill:{blue}', path_tag)
            else:
                path_tag = path_tag.replace("<path", f"<path fill='{blue}'", 1)
            return path_tag

        def change_to_green(match):
            path_tag = match.group(0)
            if "stroke" in path_tag:
                path_tag = re.sub(r'stroke:[#0-9a-fA-F]+', f'stroke:{green}', path_tag)
            else:
                path_tag = path_tag.replace("<path", f"<path stroke='{green}'", 1)
            if "fill" in path_tag:
                path_tag = re.sub(r'fill:[#0-9a-fA-F]+', f'fill:{green}', path_tag)
            else:
                path_tag = path_tag.replace("<path", f"<path fill='{green}'", 1)
            return path_tag

        def change_to_pink(match):
            path_tag = match.group(0)
            if "stroke" in path_tag:
                path_tag = re.sub(r'stroke:[#0-9a-fA-F]+', f'stroke:{pink}', path_tag)
            else:
                path_tag = path_tag.replace("<path", f"<path stroke='{pink}'", 1)
            if "fill" in path_tag:
                path_tag = re.sub(r'fill:[#0-9a-fA-F]+', f'fill:{pink}', path_tag)
            else:
                path_tag = path_tag.replace("<path", f"<path fill='{pink}'", 1)
            return path_tag

        def change_to_orange(match):
            path_tag = match.group(0)
            if "stroke" in path_tag:
                path_tag = re.sub(r'stroke:[#0-9a-fA-F]+', f'stroke:{orange}', path_tag)
            else:
                path_tag = path_tag.replace("<path", f"<path stroke='{orange}'", 1)
            if "fill" in path_tag:
                path_tag = re.sub(r'fill:[#0-9a-fA-F]+', f'fill:{orange}', path_tag)
            else:
                path_tag = path_tag.replace("<path", f"<path fill='{orange}'", 1)
            return path_tag

        def change_to_yellow(match):
            path_tag = match.group(0)
            if "stroke" in path_tag:
                path_tag = re.sub(r'stroke:[#0-9a-fA-F]+', f'stroke:{yellow}', path_tag)
            else:
                path_tag = path_tag.replace("<path", f"<path stroke='{yellow}'", 1)
            if "fill" in path_tag:
                path_tag = re.sub(r'fill:[#0-9a-fA-F]+', f'fill:{yellow}', path_tag)
            else:
                path_tag = path_tag.replace("<path", f"<path fill='{yellow}'", 1)
            return path_tag

        def change_adjacent_paths_to_pink(svg_text):
            """
            Find and color adjacent paths that have lengths 294-300 pixels in their d parameter.
            Adjacent means the path ID is within 8 positions (greater or lesser) of a pink diagonal path ID.
            """
            
            def extract_path_id_number(path_id):
                """Extract numeric part from path ID (e.g., 'path13380' -> 13380)"""
                match = re.search(r'(\d+)', path_id)
                return int(match.group(1)) if match else None
            
            def color_path_pink(path_tag):
                """Apply pink color to a path tag."""
                new_tag = path_tag
                
                # Handle stroke
                if "stroke" in new_tag:
                    new_tag = re.sub(r'stroke:[#0-9a-fA-F]+', f'stroke:{pink}', new_tag)
                else:
                    new_tag = new_tag.replace("<path", f"<path stroke='{pink}'", 1)
                
                # Handle fill
                if "fill" in new_tag:
                    new_tag = re.sub(r'fill:[#0-9a-fA-F]+', f'fill:{pink}', new_tag)
                else:
                    new_tag = new_tag.replace("<path", f"<path fill='{pink}'", 1)
                
                return new_tag
            
            # Step 1: Find all diagonal paths (frames5x4) that will be colored pink
            diagonal_path_ids = set()
            for match in frames5x4_pattern.finditer(svg_text):
                path_tag = match.group(0)
                id_match = re.search(r'id="([^"]+)"', path_tag)
                if id_match:
                    path_id = id_match.group(1)
                    path_id_num = extract_path_id_number(path_id)
                    if path_id_num is not None:
                        diagonal_path_ids.add(path_id_num)
                        
                        print(f"[DIAG] Found diagonal path: {path_id} (ID number: {path_id_num})")
            
            
            print(f"Found {len(diagonal_path_ids)} diagonal paths with numeric IDs")
            
            # Step 2: Find all paths that contain lengths 294-300 or "V 9114" in their d parameter
            pattern = re.compile(r'<path[^>]+d="[^"]*(?:\b(29[4-9]|300)\b|V\s+9114)[^"]*"[^>]*>', re.IGNORECASE)
            
            modifications = []
            adjacent_count = 0
            
            for match in pattern.finditer(svg_text):
                path_tag = match.group(0)
                
                # Get path ID
                id_match = re.search(r'id="([^"]+)"', path_tag)
                if not id_match:
                    continue
                
                path_id = id_match.group(1)
                path_id_num = extract_path_id_number(path_id)
                
                if path_id_num is None:
                    continue
                
                # Get the matched length
                length = match.group(1)
                
                # Check if this path is adjacent to any diagonal path (within 8 positions)
                is_adjacent = False
                closest_diagonal = None
                min_distance = float('inf')
                
                for diagonal_id in diagonal_path_ids:
                    distance = abs(path_id_num - diagonal_id)
                    if distance <= 8 and distance < min_distance:
                        is_adjacent = True
                        closest_diagonal = diagonal_id
                        min_distance = distance
                
                if is_adjacent:
                    # Get the d parameter for logging
                    d_match = re.search(r'd="([^"]+)"', path_tag)
                    d_str = d_match.group(1) if d_match else "unknown"
                    
                    
                    print(f"[FOUND] Path {path_id} (ID: {path_id_num}) contains length {length} in d='{d_str}'")
                    print(f"[ADJACENT] Distance {min_distance} from diagonal path ID {closest_diagonal}")
                    
                    # Color this path pink
                    pink_tag = color_path_pink(path_tag)
                    modifications.append((path_tag, pink_tag))
                    adjacent_count += 1
                    
                    print(f"[NEIGH] id={path_id} → PINK (adjacent to diagonal ID {closest_diagonal}, distance: {min_distance})")
            
            print(f"Total adjacent paths with lengths 294-300: {adjacent_count}")
            print(f"Total modifications to apply: {len(modifications)}")
            
            # Apply all modifications
            modified_text = svg_text
            for original_tag, pink_tag in modifications:
                modified_text = modified_text.replace(original_tag, pink_tag)
            
            return modified_text

        # Apply colors
        modified_svg_text = shores_box_pattern.sub(change_to_red, svg_text)
        modified_svg_text = shores_pattern.sub(change_to_blue, modified_svg_text)
        
        # First apply adjacent path coloring, then the diagonal paths
        modified_svg_text = change_adjacent_paths_to_pink(modified_svg_text)
        modified_svg_text = frames5x4_pattern.sub(change_to_pink, modified_svg_text)
        modified_svg_text = framesinBox_pattern.sub(change_to_orange, modified_svg_text)
        modified_svg_text = yellow_pattern.sub(change_to_yellow, modified_svg_text)
        modified_svg_text = frames6x4_pattern.sub(change_to_green, modified_svg_text)

        # Write modified content
        with open(output_file, "w", encoding="utf-8") as file:
            file.write(modified_svg_text)

        
        print("SVG file updated successfully.")

    except Exception as e:
        
        print(f"Error applying colors: {e}", "error")

def svg_to_png(svg_path, png_path):
    """Convert SVG to PNG format"""
    try:
        # Convert SVG to PNG bytes
        png_data = cairosvg.svg2png(url=svg_path)
        
        # Convert to PIL Image
        image = Image.open(io.BytesIO(png_data))
        
        # Save as PNG
        image.save(png_path, 'PNG')
        
        print(f"✅ SVG converted to PNG: {png_path}")
        return True
        
    except Exception as e:
        
        print(f"❌ Error converting SVG to PNG: {e}", "error")
        return False

def run_step4():
    """
    Main function to run Step4 processing
    """
    try:
        # Get the current working directory to determine the correct paths
        current_dir = os.getcwd()
        
        # If we're in the processors directory, use relative paths
        if current_dir.endswith('processors'):
            input_svg = "../files/Step3.svg"
            output_svg = "../files/Step4.svg"
        else:
            # If we're in the server directory (when called from pipeline), use direct paths
            input_svg = "files/Step3.svg"
            output_svg = "files/Step4.svg"
        
        # Check if input file exists
        if not os.path.exists(input_svg):
            
            print(f"Error: Input file '{input_svg}' not found!", "error")
            print(f"Current working directory: {os.getcwd()}", "error")
            print(f"Tried path: {input_svg}", "error")
            return False
        
        apply_color_to_specific_paths(input_svg, output_svg)
        
        # Convert SVG to PNG
        output_png = output_svg.replace('.svg', '-results.png')
        if svg_to_png(output_svg, output_png):
            
            print(f"   - Generated PNG: {output_png}")
        else:
            print(f"   - Warning: PNG conversion failed", "warning")
        
        
        print(f"✅ Step4 completed successfully:")
        print(f"   - Input SVG: {input_svg}")
        print(f"   - Processed SVG: {output_svg}")
        print(f"   - Generated PNG: {output_png}")
        return True
            
    except Exception as e:
        
        print(f"An error occurred: {str(e)}", "error")
        return False

# Main execution
if __name__ == "__main__":
    run_step4()