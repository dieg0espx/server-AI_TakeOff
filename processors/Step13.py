#!/usr/bin/env python3
"""
Find all SVG paths geometrically inside each pink_container rectangle,
identify glyph characters, and apply color changes.

The SVG has:
- Paths inside <g transform="matrix(0.16,0,0,-0.16,18.666666,2240)">
  so screen_x = 0.16 * path_x + 18.666666
     screen_y = -0.16 * path_y + 2240
- Pink container rects in screen coordinates (outside the transform group)

Output: files/test.svg with color modifications applied.
"""

import os
import re
import xml.etree.ElementTree as ET

SVG_FILE = "files/final_marked.svg"
OUTPUT_FILE = "files/test.svg"

# When called from pipeline, these get overridden
PIPELINE_MODE = False

# Default transform parameters (will be read dynamically from SVG)
TX_A = 0.16
TX_D = -0.16
TX_E = 18.666666
TX_F = 2240.0

# ── Glyph signatures ──
# Each digit has a distinctive relative path pattern (after the initial "m x,y").
# These patterns appear in two orientations depending on container layout.
GLYPH_SIGNATURES = {
    "5": [
        # Horizontal containers (vertical text): starts with "-21,1 -2,-19" or "-20,1 -3,-19" etc.
        re.compile(r'^-?\d{1,2},\s*1\s+-\d,-1[89]'),
        # Also "h -20 l -3,-18" variant
        re.compile(r'^h\s+-?\d{1,2}\s+l?\s*-?\d,-1[89]'),
        # Vertical containers (horizontal text): starts with "-1,-21 19,-2" or similar
        re.compile(r'^-?1,-2[01]\s+1[89],-\d'),
        # Also "v -21 l 18,-2" variant
        re.compile(r'^v\s+-2[01]\s+l?\s*1[89],-\d'),
    ],
    "4": [
        # Horizontal orientation: "-44,2 29,-22 1,31" or "-43,2 28,-22" etc.
        re.compile(r'^-4[34],[12]\s+2[89],-2[12]'),
        # Horizontal variant: "-44,-1 30,-20 v 31"
        re.compile(r'^-4[34],-?[01]\s+[23]\d,-2[01]'),
        # Horizontal variant: "h -44 l 29,-21 v 31"
        re.compile(r'^h\s+-4[34]\s+l?\s*[23]\d,-2[12]'),
        # Vertical orientation: "2,44 -22,-29 31,-1" or "2,43 -22,-28" etc.
        re.compile(r'^[12],4[34]\s+-2[12],-2[89]'),
        # Alternate vertical "4": "v 44 l -21,-30 h 32" or "v 44 l -21,-29 h 31" etc.
        re.compile(r'^v\s+4[34]\s+l\s+-2[01],-[23]\d\s+'),
        # Variant: "-1,44 -20,-29 h 31"
        re.compile(r'^-?1,4[34]\s+-2[01],-[23]\d'),
    ],
    "slash": [
        # Forward slash mark: "45,27" or "44,27" or "45,28" (and vertical: "27,-45" etc.)
        re.compile(r'^4[45],2[78]$'),
        re.compile(r'^2[78],-4[45]$'),
        re.compile(r'^2[78],-4[34]$'),
    ],
    "backslash": [
        # Backslash mark: "43,-31" or "42,-31" or "43,-30" (and vertical: "-31,-43" etc.)
        re.compile(r'^4[23],-3[01]$'),
        re.compile(r'^-3[01],-4[23]$'),
        re.compile(r'^-3[01],-4[24]$'),
    ],
    "6": [
        # Vertical text: "-2,4 -7,2 h -4 l -6,-2 -4,-6 -2,-11 v -10 l 2,-8 ..."
        re.compile(r'^-\d,[45]\s+-[67],\d\s+h\s+-\d\s+l\s+-\d,-\d\s+-\d,-\d\s+-\d,-\d{1,2}\s+v\s+-\d{1,2}\s+l\s+\d,-\d'),
        # Vertical text variant: uses "1,-11" instead of "v -11"
        re.compile(r'^-\d,[45]\s+-[67],[23]\s+h\s+-\d\s+l\s+-\d,-[23]\s+-\d,-\d\s+-\d,-\d{1,2}\s+[01],-\d{1,2}\s+\d,-\d'),
        # Horizontal text: "-4,-3 -2,-6 v -4 l 2,-6 6,-4 11,-2 h 10 ..."
        re.compile(r'^-[345],-[23]\s+-\d,-[67]\s+v\s+-\d\s+l\s+\d,-\d\s+\d,-\d\s+\d{1,2},-\d\s+h\s+\d{1,2}\s+l\s+\d,\d'),
    ],
    "cross_v": [
        # Vertical line of cross/plus: "v -37" or "v -38" etc.
        re.compile(r'^v\s+-?3[678]$'),
        # Slight-angle variant: "1,-37" or "-1,37" etc.
        re.compile(r'^-?1,-3[678]$'),
        re.compile(r'^-?1,3[678]$'),
    ],
    "cross_h": [
        # Horizontal line of cross/plus: "h 38" or "h 37" etc.
        re.compile(r'^h\s+-?3[678]$'),
        # Variant with slight angle: "38,1" or "37,1"
        re.compile(r'^-?3[78],[01]$'),
        re.compile(r'^-?[01],3[78]$'),
    ],
}

# ── Color changes to apply ──
# Map digit -> new stroke color
GLYPH_COLOR_CHANGES = {
    "5": "#ffffff",
    "4": "#ffffff",
    "slash": "#ffffff",
    "backslash": "#ffffff",
    "6": "#ffffff",
    "cross_v": "#ffffff",
    "cross_h": "#ffffff",
}


def transform_point(x, y):
    """Convert path coordinates to screen coordinates."""
    return TX_A * x + TX_E, TX_D * y + TX_F


def parse_path_bbox(d):
    """
    Parse SVG path d attribute and compute bounding box.
    Handles M, m, L, l, H, h, V, v, Z, z, C, c, S, s, Q, q, T, t, A, a commands.
    Returns (min_x, min_y, max_x, max_y) in path coordinates.
    """
    tokens = re.findall(
        r'[MmLlHhVvZzCcSsQqTtAa]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?', d
    )

    cx, cy = 0.0, 0.0
    xs, ys = [], []
    start_x, start_y = 0.0, 0.0

    i = 0
    while i < len(tokens):
        cmd = tokens[i]
        if not cmd.isalpha():
            i += 1
            continue
        i += 1

        if cmd == 'M':
            while i < len(tokens) and not tokens[i].isalpha():
                cx, cy = float(tokens[i]), float(tokens[i + 1]); i += 2
                xs.append(cx); ys.append(cy)
                start_x, start_y = cx, cy
        elif cmd == 'm':
            first = True
            while i < len(tokens) and not tokens[i].isalpha():
                dx, dy = float(tokens[i]), float(tokens[i + 1]); i += 2
                if first:
                    cx += dx; cy += dy
                    start_x, start_y = cx, cy
                    first = False
                else:
                    cx += dx; cy += dy
                xs.append(cx); ys.append(cy)
        elif cmd == 'L':
            while i < len(tokens) and not tokens[i].isalpha():
                cx, cy = float(tokens[i]), float(tokens[i + 1]); i += 2
                xs.append(cx); ys.append(cy)
        elif cmd == 'l':
            while i < len(tokens) and not tokens[i].isalpha():
                dx, dy = float(tokens[i]), float(tokens[i + 1]); i += 2
                cx += dx; cy += dy
                xs.append(cx); ys.append(cy)
        elif cmd == 'H':
            while i < len(tokens) and not tokens[i].isalpha():
                cx = float(tokens[i]); i += 1
                xs.append(cx); ys.append(cy)
        elif cmd == 'h':
            while i < len(tokens) and not tokens[i].isalpha():
                cx += float(tokens[i]); i += 1
                xs.append(cx); ys.append(cy)
        elif cmd == 'V':
            while i < len(tokens) and not tokens[i].isalpha():
                cy = float(tokens[i]); i += 1
                xs.append(cx); ys.append(cy)
        elif cmd == 'v':
            while i < len(tokens) and not tokens[i].isalpha():
                cy += float(tokens[i]); i += 1
                xs.append(cx); ys.append(cy)
        elif cmd == 'C':
            while i < len(tokens) and not tokens[i].isalpha():
                for _ in range(3):
                    px, py = float(tokens[i]), float(tokens[i + 1]); i += 2
                    xs.append(px); ys.append(py)
                cx, cy = px, py
        elif cmd == 'c':
            while i < len(tokens) and not tokens[i].isalpha():
                for j in range(3):
                    dx, dy = float(tokens[i]), float(tokens[i + 1]); i += 2
                    xs.append(cx + dx); ys.append(cy + dy)
                cx += dx; cy += dy
        elif cmd == 'S':
            while i < len(tokens) and not tokens[i].isalpha():
                for _ in range(2):
                    px, py = float(tokens[i]), float(tokens[i + 1]); i += 2
                    xs.append(px); ys.append(py)
                cx, cy = px, py
        elif cmd == 's':
            while i < len(tokens) and not tokens[i].isalpha():
                for j in range(2):
                    dx, dy = float(tokens[i]), float(tokens[i + 1]); i += 2
                    xs.append(cx + dx); ys.append(cy + dy)
                cx += dx; cy += dy
        elif cmd == 'Q':
            while i < len(tokens) and not tokens[i].isalpha():
                for _ in range(2):
                    px, py = float(tokens[i]), float(tokens[i + 1]); i += 2
                    xs.append(px); ys.append(py)
                cx, cy = px, py
        elif cmd == 'q':
            while i < len(tokens) and not tokens[i].isalpha():
                for j in range(2):
                    dx, dy = float(tokens[i]), float(tokens[i + 1]); i += 2
                    xs.append(cx + dx); ys.append(cy + dy)
                cx += dx; cy += dy
        elif cmd == 'T':
            while i < len(tokens) and not tokens[i].isalpha():
                cx, cy = float(tokens[i]), float(tokens[i + 1]); i += 2
                xs.append(cx); ys.append(cy)
        elif cmd == 't':
            while i < len(tokens) and not tokens[i].isalpha():
                dx, dy = float(tokens[i]), float(tokens[i + 1]); i += 2
                cx += dx; cy += dy
                xs.append(cx); ys.append(cy)
        elif cmd in ('A', 'a'):
            while i < len(tokens) and not tokens[i].isalpha():
                for _ in range(5):
                    i += 1
                if cmd == 'A':
                    cx, cy = float(tokens[i]), float(tokens[i + 1])
                else:
                    cx += float(tokens[i]); cy += float(tokens[i + 1])
                i += 2
                xs.append(cx); ys.append(cy)
        elif cmd in ('Z', 'z'):
            cx, cy = start_x, start_y

    if not xs or not ys:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def box_contained(container, path_box):
    """Check if path_box is fully contained within container. Each is (min_x, min_y, max_x, max_y)."""
    return (path_box[0] >= container[0] and
            path_box[1] >= container[1] and
            path_box[2] <= container[2] and
            path_box[3] <= container[3])


REFERENCE_SCALE = 0.16  # Scale factor the glyph patterns were developed against


def get_rel_d(d):
    """Extract the relative drawing commands (everything after 'm x,y ')."""
    m = re.match(r'm\s+[-\d.]+,[-\d.]+\s+(.*)', d)
    return m.group(1) if m else d


def normalize_rel_d(rel_d):
    """
    Normalize relative path commands to the reference scale (0.16).
    This makes glyph patterns work regardless of SVG resolution.
    """
    scale_ratio = abs(TX_A) / REFERENCE_SCALE
    if abs(scale_ratio - 1.0) < 0.01:
        return rel_d  # Already at reference scale

    def scale_number(match):
        num = float(match.group(0))
        scaled = round(num * scale_ratio)
        return str(int(scaled))

    # Scale all numbers in the path but preserve commands
    normalized = re.sub(r'-?\d+', scale_number, rel_d)
    return normalized


def identify_glyph(rel_d):
    """Identify which digit a glyph path represents based on its relative path commands."""
    # Normalize to reference scale before matching
    normalized = normalize_rel_d(rel_d)
    for digit, patterns in GLYPH_SIGNATURES.items():
        for pat in patterns:
            if pat.search(normalized):
                return digit
    return None


def get_containers(root, prefix):
    """Extract all container rects with given prefix (e.g. 'pink_container', 'green_container')."""
    containers = {}
    for rect in root.iter('{http://www.w3.org/2000/svg}rect'):
        rid = rect.get('id', '')
        if rid.startswith(f'{prefix}_') and 'text' not in rid:
            num = int(rid.split('_')[-1])
            x = float(rect.get('x'))
            y = float(rect.get('y'))
            w = float(rect.get('width'))
            h = float(rect.get('height'))
            containers[num] = {
                'id': rid,
                'x': x, 'y': y, 'w': w, 'h': h,
                'screen_bbox': (x, y, x + w, y + h)
            }
    return containers


def get_g10_paths(root):
    """Extract all paths from the g10 transform group with screen-space bounding boxes."""
    global TX_A, TX_D, TX_E, TX_F

    g10 = root.find('.//{http://www.w3.org/2000/svg}g[@id="g10"]')
    if g10 is None:
        print("ERROR: Could not find g10")
        return []

    # Read transform dynamically from g10
    transform = g10.get('transform', '')
    m = re.match(r'matrix\(([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+),([-\d.]+)\)', transform.replace(' ', ''))
    if m:
        TX_A = float(m.group(1))
        TX_D = float(m.group(4))
        TX_E = float(m.group(5))
        TX_F = float(m.group(6))
        print(f"  Transform: a={TX_A}, d={TX_D}, e={TX_E}, f={TX_F}")

    paths = []
    for path in g10.iter('{http://www.w3.org/2000/svg}path'):
        pid = path.get('id', '')
        d = path.get('d', '')
        if not d or not pid:
            continue

        bbox = parse_path_bbox(d)
        if bbox is None:
            continue

        sx1, sy1 = transform_point(bbox[0], bbox[1])
        sx2, sy2 = transform_point(bbox[2], bbox[3])
        screen_bbox = (min(sx1, sx2), min(sy1, sy2), max(sx1, sx2), max(sy1, sy2))

        paths.append({
            'id': pid,
            'd': d,
            'rel_d': get_rel_d(d),
            'screen_bbox': screen_bbox,
            'width': round(screen_bbox[2] - screen_bbox[0], 2),
            'height': round(screen_bbox[3] - screen_bbox[1], 2),
        })

    return paths


def find_contained_paths(containers, paths):
    """For each container, find all paths fully contained within it."""
    results = {}
    for num in sorted(containers.keys()):
        cbox = containers[num]['screen_bbox']
        matched = [p for p in paths if box_contained(cbox, p['screen_bbox'])]
        results[num] = matched
    return results


def find_glyph_paths(contained_paths):
    """
    For each container, separate paths into glyphs (small character shapes)
    and structural paths (lines, boxes, etc.).
    Then identify which glyph represents which digit.
    """
    results = {}
    for num, paths in contained_paths.items():
        glyphs = []
        structural = []
        for p in paths:
            if p['width'] < 10 and p['height'] < 10:
                digit = identify_glyph(p['rel_d'])
                glyphs.append({**p, 'digit': digit})
            else:
                structural.append(p)
        results[num] = {'glyphs': glyphs, 'structural': structural}
    return results


def boxes_overlap(box1, box2):
    """Check if two bounding boxes overlap at all. Each is (min_x, min_y, max_x, max_y)."""
    return not (box1[2] < box2[0] or box2[2] < box1[0] or
                box1[3] < box2[1] or box2[3] < box1[1])


def find_overflow_paths(containers, paths):
    """
    Find paths that overlap a container but are NOT fully contained.
    These are the paths that 'go beyond' the container area.
    Returns a set of path IDs to remove.
    """
    contained_ids = set()
    overflow_ids = set()

    for num in sorted(containers.keys()):
        cbox = containers[num]['screen_bbox']
        for p in paths:
            if boxes_overlap(cbox, p['screen_bbox']):
                if box_contained(cbox, p['screen_bbox']):
                    contained_ids.add(p['id'])
                else:
                    overflow_ids.add(p['id'])

    # Only remove paths that overflow AND are not fully contained in some other container
    return overflow_ids - contained_ids


def remove_paths_from_svg(svg_content, path_ids):
    """Remove path elements by their IDs from the SVG content."""
    removed = 0
    for pid in path_ids:
        # Match the full <path ... /> element containing this ID
        pattern = rf'<path\s[^>]*?id="{pid}"[^>]*/>'
        match = re.search(pattern, svg_content)
        if match:
            svg_content = svg_content.replace(match.group(0), '')
            removed += 1
    return svg_content, removed


def change_path_color(svg_content, path_id, new_color):
    """Change the stroke color of a path by its ID."""
    pattern = rf'(id="{path_id}"\s+style="[^"]*?)stroke:#[0-9a-fA-F]{{6}}'
    match = re.search(pattern, svg_content)
    if match:
        old = match.group(0)
        new = re.sub(r'stroke:#[0-9a-fA-F]{6}', f'stroke:{new_color}', old)
        return svg_content.replace(old, new)
    return svg_content


def move_labels_to_bottom_right(svg_content, containers, prefix):
    """Move text labels from center to bottom-right of each container."""
    moved = 0
    padding = 3  # pixels from the edge

    for num in sorted(containers.keys()):
        c = containers[num]
        text_id = f"text_{prefix}_{num}"

        # New position: bottom-right corner with small padding
        new_x = c['x'] + c['w'] - padding
        new_y = c['y'] + c['h'] - padding

        # Find and replace the x and y attributes for this text element
        pattern = rf'(id="{text_id}"\s+)x="[^"]*"\s+y="[^"]*"(\s+style="[^"]*?)font-size:12px;([^"]*?)text-anchor:middle;dominant-baseline:central'
        match = re.search(pattern, svg_content)
        if match:
            old = match.group(0)
            new = (f'{match.group(1)}x="{new_x}" y="{new_y}"{match.group(2)}'
                   f'font-size:8px;{match.group(3)}'
                   f'text-anchor:end;dominant-baseline:auto')
            svg_content = svg_content.replace(old, new)
            moved += 1

    return svg_content, moved


def process_container_group(prefix, containers, paths, svg_content):
    """Process a group of containers: find glyphs, recolor, move labels."""

    # ── Find contained paths ──
    contained = find_contained_paths(containers, paths)

    # ── Identify glyphs ──
    analyzed = find_glyph_paths(contained)

    # ── Print report ──
    for num in sorted(analyzed.keys()):
        c = containers[num]
        data = analyzed[num]
        print(f"=== {c['id']} === (x={c['x']}, y={c['y']}, {c['w']}x{c['h']})")
        print(f"  Structural paths: {len(data['structural'])}")
        for p in data['structural']:
            print(f"    - {p['id']:20s}  w={p['width']:8.2f}  h={p['height']:8.2f}")
        print(f"  Glyphs: {len(data['glyphs'])}")
        for g in data['glyphs']:
            digit_label = f" [digit {g['digit']}]" if g['digit'] else ""
            print(f"    - {g['id']:20s}  w={g['width']:5.2f}  h={g['height']:5.2f}{digit_label}")
        print()

    # ── Apply color changes ──
    changed_count = 0
    for num in sorted(analyzed.keys()):
        for g in analyzed[num]['glyphs']:
            if g['digit'] in GLYPH_COLOR_CHANGES:
                new_color = GLYPH_COLOR_CHANGES[g['digit']]
                svg_content = change_path_color(svg_content, g['id'], new_color)
                changed_count += 1
                print(f"  Changed {g['id']} (in {containers[num]['id']}, digit {g['digit']}) -> {new_color}")

    # ── Move labels to bottom-right ──
    svg_content, moved_count = move_labels_to_bottom_right(svg_content, containers, prefix)
    print(f"  Moved {moved_count} labels")

    # ── Collect glyph counts per container ──
    container_summary = {}
    for num in sorted(analyzed.keys()):
        glyphs = analyzed[num]['glyphs']
        count_4 = sum(1 for g in glyphs if g['digit'] == '4')
        count_5 = sum(1 for g in glyphs if g['digit'] == '5')
        count_6 = sum(1 for g in glyphs if g['digit'] == '6')
        container_summary[containers[num]['id']] = {
            "num4": count_4,
            "num5": count_5,
            "num6": count_6,
        }

    return svg_content, changed_count, moved_count, container_summary


def collect_all_contained_path_ids(all_containers, paths):
    """Collect IDs of all paths that are fully contained in ANY container."""
    contained_ids = set()
    for containers in all_containers.values():
        for num in containers:
            cbox = containers[num]['screen_bbox']
            for p in paths:
                if box_contained(cbox, p['screen_bbox']):
                    contained_ids.add(p['id'])
    return contained_ids


def remove_non_frame_elements(svg_content, contained_ids, color='4e4e4e'):
    """
    Remove all elements with the given stroke/fill color that are not inside any container.
    Uses string replacement on individual elements to avoid breaking chained tags.
    """
    removed = 0

    # Collect path IDs with #4e4e4e that are NOT in any container
    # Find all path IDs that have this color
    path_id_pattern = re.compile(
        rf'<path\s[^>]*?id="(path\d+)"[^>]*?#{color}[^>]*/>', re.IGNORECASE
    )

    ids_to_remove = set()
    for m in path_id_pattern.finditer(svg_content):
        pid = m.group(1)
        if pid not in contained_ids:
            ids_to_remove.add(pid)

    # Remove each path by its unique ID - replace entire <path.../> element with empty string
    for pid in ids_to_remove:
        # Use a precise pattern that matches this specific path element
        # The path ends at the first /> after its id
        pattern = rf'<path\s[^>]*?id="{pid}"[^>]*/>'
        match = re.search(pattern, svg_content)
        if match:
            svg_content = svg_content[:match.start()] + svg_content[match.end():]
            removed += 1

    # Remove text elements with that color (dimension labels outside containers)
    # Text elements: <text ...>...</text> with possible <tspan> inside
    text_pattern = re.compile(
        rf'<text\s[^>]*?#{color}[^>]*>.*?</text>', re.IGNORECASE | re.DOTALL
    )
    # Collect all, then remove in reverse order to preserve positions
    text_matches = list(text_pattern.finditer(svg_content))
    for match in reversed(text_matches):
        svg_content = svg_content[:match.start()] + svg_content[match.end():]
        removed += 1

    return svg_content, removed


def process_svg(input_file, output_file):
    """
    Process an SVG file: recolor glyphs in containers and move labels.
    Can be called standalone or from the pipeline.
    """
    # ── Parse SVG ──
    tree = ET.parse(input_file)
    root = tree.getroot()

    paths = get_g10_paths(root)
    print(f"Found {len(paths)} paths in g10 group\n")

    # ── Load SVG content ──
    with open(input_file, 'r', encoding='utf-8') as f:
        svg_content = f.read()

    total_changed = 0
    total_moved = 0
    all_summary = {}

    # ── Collect all containers ──
    all_containers = {}
    for prefix in ['pink_container', 'green_container', 'orange_container']:
        all_containers[prefix] = get_containers(root, prefix)

    # ── Process each container type ──
    for prefix in ['pink_container', 'green_container', 'orange_container']:
        containers = all_containers[prefix]
        print(f"\n{'=' * 60}")
        print(f"Processing {prefix} ({len(containers)} containers)")
        print(f"{'=' * 60}\n")

        svg_content, changed, moved, summary = process_container_group(
            prefix, containers, paths, svg_content
        )
        total_changed += changed
        total_moved += moved
        all_summary.update(summary)

    # ── Save output ──
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(svg_content)

    print(f"\nTotal paths recolored: {total_changed}")
    print(f"Total labels moved: {total_moved}")
    print(f"Output saved to: {output_file}")

    return True, all_summary


def run_step13():
    """
    Pipeline entry point. Processes both Step11 SVG variants in-place.
    Called from main.py after Step11, before SVG upload.
    """
    try:
        import json

        current_dir = os.getcwd()

        if current_dir.endswith('processors'):
            base = ".."
        else:
            base = "."

        success = True
        all_summary = {}

        # Process each Step11 SVG variant (overwrite in-place)
        for variant in ['no_slab_band', 'with_slab_band']:
            svg_path = f"{base}/files/Step11_{variant}.svg"
            if os.path.exists(svg_path):
                print(f"\n{'=' * 60}")
                print(f"Processing Step11_{variant}.svg")
                print(f"{'=' * 60}")
                result, summary = process_svg(svg_path, svg_path)
                if not result:
                    success = False
                else:
                    all_summary = summary  # Use the latest (both should be same)
            else:
                print(f"⚠️  {svg_path} not found, skipping")

        # Save glyph totals per container type to data.json
        if all_summary:
            data_path = f"{base}/data.json"
            data = {}
            if os.path.exists(data_path):
                try:
                    with open(data_path, 'r') as f:
                        data = json.load(f)
                except (json.JSONDecodeError, Exception):
                    data = {}

            # Aggregate by container type
            totals = {}
            for container_id, counts in all_summary.items():
                ctype = container_id.rsplit('_', 1)[0]  # e.g. "pink_container"
                if ctype not in totals:
                    totals[ctype] = {"count": 0, "num4": 0, "num5": 0, "num6": 0}
                totals[ctype]["count"] += 1
                totals[ctype]["num4"] += counts["num4"]
                totals[ctype]["num5"] += counts["num5"]
                totals[ctype]["num6"] += counts["num6"]

            data['container_glyphs'] = totals
            with open(data_path, 'w') as f:
                json.dump(data, f, indent=4)
            print(f"\n✅ Saved glyph totals to data.json")

        print(f"\n✓ Step13 completed")
        return success

    except Exception as e:
        print(f"✗ Error in Step13: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Standalone mode: process final_marked.svg -> test.svg"""
    result, summary = process_svg(SVG_FILE, OUTPUT_FILE)
    if summary:
        import json
        print(f"\nGlyph summary ({len(summary)} containers):")
        print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
