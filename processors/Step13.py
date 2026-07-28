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

# ── Cross bar lookup tables ──
# Frame size + span between frames -> cross bar size + color.
# Group 1 covers 6' & 5' frames; group 2 covers 4' & 3' frames.
CROSS_BAR_TABLES = [
    {
        "frame_sizes": ["6'", "5'"],
        "rows": [
            {"span": "10'", "cross_bar_size": "10x4", "color": "Purple"},
            {"span": "7'",  "cross_bar_size": "7x4",  "color": "Yellow"},
            {"span": "5'",  "cross_bar_size": "5x4",  "color": "Green"},
            {"span": "4'",  "cross_bar_size": "4x4",  "color": "Blue"},
        ],
    },
    {
        "frame_sizes": ["4'", "3'"],
        "rows": [
            {"span": "10'", "cross_bar_size": "10x2", "color": "Pink"},
            {"span": "7'",  "cross_bar_size": "7x2",  "color": "Red"},
            {"span": "5'",  "cross_bar_size": "5x2",  "color": "Orange"},
            {"span": "4'",  "cross_bar_size": "4x2",  "color": "White"},
        ],
    },
]

# ── Glyph signatures ──
# Each digit has a distinctive relative path pattern (after the initial "m x,y").
# These patterns appear in two orientations depending on container layout.
GLYPH_SIGNATURES = {
    "5": [
        # Horizontal containers (vertical text): starts with "-21,1 -2,-19" or "-20,1 -3,-19" etc.
        re.compile(r'^-?\d{1,2},\s*1\s+-\d,-1[89]'),
        # Also "h -20 l -3,-18" variant
        re.compile(r'^h\s+-?\d{1,2}\s+l?\s*-?\d,-1[89]'),
        # Slight-slant variant: "-21,-1 -2,-18" (slight downslope on top stroke)
        re.compile(r'^-?\d{1,2},-?[01]\s+-?\d,-1[89]'),
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
        # Horizontal variant: "h -44 l 29,-21 v 31"  (also accept "-20" vertical leg)
        re.compile(r'^h\s+-4[34]\s+l?\s*[23]\d,-2[012]'),
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
        # Horizontal text: "-4,-3 -2,-6 v -4 l 2,-6 6,-4 11,-2 h 10 l 8,2 ..."
        # Bottom edge accepts either flat "h 10 l" or slight-slant "10,1" / "10,0".
        re.compile(r'^-[345],-[23]\s+-\d,-[67]\s+v\s+-\d\s+l\s+\d,-\d\s+\d,-\d\s+\d{1,2},-\d\s+(?:h\s+\d{1,2}\s+l|\d{1,2},[01])\s+\d,\d'),
        # Vertical text, longer top arc (segmented top stroke before bottom curve):
        # "-3,4 -6,3 -4,-1 -6,-2 -4,-6 -2,-10 v -11 l 2,-8 ..."
        re.compile(r'^-\d,[45]\s+-\d,\d\s+-\d,-\d\s+-\d,-\d\s+-\d,-\d\s+-\d,-1[01]\s+v\s+-1[01]\s+l\s+\d,-\d'),
    ],
    "7": [
        # Horizontal text: long down-right diagonal + small terminal tick.
        # e.g. "-43,23 -1,-29" / "-43,22 -1,-29" / "-44,23 -1,-29"
        re.compile(r'^-4[2345],2[234]\s+-?[01],-2[89]$'),
        # Mirrored horizontal: "43,-23 1,29" etc.
        re.compile(r'^4[2345],-2[234]\s+-?[01],2[89]$'),
        # Vertical text orientation: "23,43 -29,1" / "22,43 -29,0"
        re.compile(r'^2[234],4[2345]\s+-2[89],-?[01]$'),
        re.compile(r'^-2[234],-4[2345]\s+2[89],-?[01]$'),
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
    "apostrophe": [
        # Foot/prime mark: two z-closed subpaths with a ~±20,±30 diagonal,
        # e.g. "-5,5 -20,-30 z m -5,5 -20,-30 -5,5 z" (and mirrored). This is a
        # DIMENSION tick, NOT a cross-bar 'x' — it flags the numbers as a
        # measurement (e.g. 5'6"), not a cross-bar size.
        re.compile(r'^-?[45],-?[45]\s+-?2[01],-?[23]\d\s+z\s+m\s+-?[45],-?[45]\s+-?2[01],-?[23]\d'),
        # Small comma-shaped prime tick, e.g.
        # "2,-2 -2,-2 -2,2 2,2 h 4 l 4,-2 2,-2". All coordinates jitter between
        # 2 and 3 (either sign) across drawings, so match the STRUCTURE: four
        # small coord pairs, "h N l", then two small coord pairs. Same meaning:
        # a dimension foot/inch mark.
        re.compile(r'^-?[23],-?[23]\s+-?[23],-?[23]\s+-?[23],-?[23]\s+-?[23],-?[23]'
                   r'\s+h\s+[45]\s+l\s+-?[2345],-?[23]\s+-?[23],-?[23]$'),
        # Vertical-orientation prime tick (tall/narrow), e.g.
        # "-2,-3 -2,3 2,2 2,-2 v -5 l -2,-4 -2,-2". Coordinates jitter between
        # 2 and 3 (either sign) across drawings, so match the STRUCTURE: four
        # small coord pairs, "v -N l", then two small coord pairs.
        re.compile(r'^-?[23],-?[23]\s+-?[23],-?[23]\s+-?[23],-?[23]\s+-?[23],-?[23]'
                   r'\s+v\s+-[45]\s+l\s+-?[23],-?[2345]\s+-?[23],-?[23]$'),
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
    "7": "#ffffff",
    "cross_v": "#ffffff",
    "cross_h": "#ffffff",
    "apostrophe": "#ffffff",
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


def box_contained(container, path_box, tol=1.0):
    """Check if path_box is fully contained within container, with sub-pixel tolerance
    to absorb stroke linecap overhang and floating-point drift on edges."""
    return (path_box[0] >= container[0] - tol and
            path_box[1] >= container[1] - tol and
            path_box[2] <= container[2] + tol and
            path_box[3] <= container[3] + tol)


def box_overlap_fraction(container, path_box):
    """Return the fraction of path_box's area that lies inside container.
    Used to classify glyphs whose stroke overhangs the container edge."""
    iw = max(0.0, min(path_box[2], container[2]) - max(path_box[0], container[0]))
    ih = max(0.0, min(path_box[3], container[3]) - max(path_box[1], container[1]))
    inter = iw * ih
    pw = max(0.0, path_box[2] - path_box[0])
    ph = max(0.0, path_box[3] - path_box[1])
    parea = pw * ph
    if parea <= 0:
        return 0.0
    return inter / parea


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


def find_contained_paths(containers, paths, min_overlap=0.5):
    """For each container, find all paths that belong to it. A path counts when:
      - majority (>= min_overlap) of its bbox area lies inside the container, OR
      - it has a zero-area bbox (a single straight stroke) and is contained
        within the container's edges (with sub-pixel tolerance).
    This catches both stroke-overhang glyphs and degenerate strokes that the
    pure-overlap rule would otherwise reject."""
    results = {}
    for num in sorted(containers.keys()):
        cbox = containers[num]['screen_bbox']
        matched = []
        for p in paths:
            pb = p['screen_bbox']
            parea = max(0.0, pb[2]-pb[0]) * max(0.0, pb[3]-pb[1])
            if parea == 0.0:
                if box_contained(cbox, pb):
                    matched.append(p)
            else:
                if box_overlap_fraction(cbox, pb) >= min_overlap:
                    matched.append(p)
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

    # ── Print summary ──
    total_structural = sum(len(analyzed[n]['structural']) for n in analyzed)
    total_glyphs = sum(len(analyzed[n]['glyphs']) for n in analyzed)
    print(f"  {len(analyzed)} containers, {total_structural} structural paths, {total_glyphs} glyphs")

    # ── Apply color changes ──
    changed_count = 0
    for num in sorted(analyzed.keys()):
        glyphs = analyzed[num]['glyphs']
        # If a container has at least one recognized label glyph, tiny
        # unidentified fragments in it (digit=None) are stray strokes/ticks
        # that belong to the same white label — recolor those white too.
        # Only genuinely tiny fragments qualify; larger unrecognized shapes
        # are real glyphs we simply failed to classify and are left alone.
        TICK_MAX = 3.0
        has_known = any(g['digit'] in GLYPH_COLOR_CHANGES for g in glyphs)
        for g in glyphs:
            if g['digit'] in GLYPH_COLOR_CHANGES:
                new_color = GLYPH_COLOR_CHANGES[g['digit']]
                svg_content = change_path_color(svg_content, g['id'], new_color)
                changed_count += 1
            elif (g['digit'] is None and has_known
                  and g['width'] < TICK_MAX and g['height'] < TICK_MAX):
                svg_content = change_path_color(svg_content, g['id'], "#ffffff")
                changed_count += 1

    # ── Move labels to bottom-right ──
    svg_content, moved_count = move_labels_to_bottom_right(svg_content, containers, prefix)
    print(f"  Moved {moved_count} labels")

    # ── Collect glyph counts per container ──
    container_summary = {}
    for num in sorted(analyzed.keys()):
        glyphs = analyzed[num]['glyphs']
        def ids_for(digit):
            return [g['id'] for g in glyphs if g['digit'] == digit]

        n4 = ids_for('4')
        n5 = ids_for('5')
        n6 = ids_for('6')

        # Detect crossbar: num4 paired with numX (path IDs differ by 2)
        crossbar = None
        paired_num = None
        if n4:
            id4 = int(n4[0].replace('path', ''))
            if n5:
                if abs(id4 - int(n5[0].replace('path', ''))) == 2:
                    crossbar = 5
                    paired_num = 'num5'
            if crossbar is None and n6:
                if abs(id4 - int(n6[0].replace('path', ''))) == 2:
                    crossbar = 6
                    paired_num = 'num6'

        # Frame: a lone num not paired with num4
        frame = None
        if n5 and paired_num != 'num5':
            frame = 5
        if n6 and paired_num != 'num6':
            frame = 6
        if not n4:
            if n5:
                frame = 5
            elif n6:
                frame = 6

        container_summary[containers[num]['id']] = {
            "crossbar": crossbar if crossbar is not None else 7,
            "frame": frame,
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


# Hex colors for cross bar colors named in CROSS_BAR_TABLES.
CROSS_BAR_COLOR_HEX = {
    "Purple": "#a000c0",
    "Yellow": "#ffff00",
    "Green":  "#00c000",
    "Blue":   "#0000ff",
    "Pink":   "#ff69b4",
    "Red":    "#ff0000",
    "Orange": "#ff8c00",
    "White":  "#ffffff",
}


def read_container_span(container, paths, default_span):
    """
    Read the span digit from a green container's glyphs.

    An annotation like "5x4" means span=5, frame height=4. The first digit
    (topmost for vertical layouts, leftmost for horizontal) is the span, which
    overrides the drawing default bracing. Containers with no digit spec fall
    back to `default_span`.

    Returns the span as a string like "5'", or default if none found.
    """
    contained = find_contained_paths({0: container}, paths)
    analyzed = find_glyph_paths(contained)
    glyphs = analyzed.get(0, {}).get('glyphs', [])

    # An apostrophe/foot mark means the numbers are a DIMENSION (e.g. 5'6"),
    # not a cross-bar size — so this annotation uses the drawing default.
    if any(g.get('digit') == 'apostrophe' for g in glyphs):
        return default_span

    digit_glyphs = [g for g in glyphs if g.get('digit') in ('4', '5', '6', '7')]
    if not digit_glyphs:
        return default_span

    x0, y0, x1, y1 = container['screen_bbox']
    is_vertical = (y1 - y0) >= (x1 - x0)
    # First digit = topmost (vertical) or leftmost (horizontal).
    key = (lambda g: g['screen_bbox'][1]) if is_vertical else (lambda g: g['screen_bbox'][0])
    first = sorted(digit_glyphs, key=key)[0]
    return f"{first['digit']}'"


def warn_unmatched_apostrophes(containers, paths):
    """
    Safeguard: an apostrophe/foot mark is a small glyph that sits right next to
    a digit. If detection ever fails to classify one (digit=None), the frame
    count silently drops. Scan for small unidentified glyphs adjacent to a
    digit and warn loudly so a new coordinate variant can't regress unnoticed.

    Returns the list of suspects [(container_id, rel_d), ...].
    """
    an = find_glyph_paths(find_contained_paths(containers, paths))
    suspects = []
    for num, d in an.items():
        digits = [g for g in d['glyphs'] if g['digit'] in ('3', '4', '5', '6', '7')]
        for g in d['glyphs']:
            if g['digit'] is None and g['width'] < 3.5 and g['height'] < 3.5:
                gx = (g['screen_bbox'][0] + g['screen_bbox'][2]) / 2
                gy = (g['screen_bbox'][1] + g['screen_bbox'][3]) / 2
                near = any(
                    abs((dd['screen_bbox'][0] + dd['screen_bbox'][2]) / 2 - gx) < 6 and
                    abs((dd['screen_bbox'][1] + dd['screen_bbox'][3]) / 2 - gy) < 6
                    for dd in digits
                )
                if near:
                    suspects.append((containers[num]['id'], g['rel_d']))
    if suspects:
        print(f"⚠️  Step13: {len(suspects)} small unidentified glyph(s) sit next "
              f"to a digit — likely MISSED apostrophe/dimension marks. Frame "
              f"counts may be wrong. Add these rel_d shapes to the 'apostrophe' "
              f"signature:")
        for cid, rel in suspects:
            print(f"     {cid}: {rel[:60]}")
    return suspects


def read_container_frames(container, paths, default_height):
    """
    Read the FRAMES for a green container from its apostrophe/dimension
    numbers.

    Every annotation spans 2 SIDES, and frames come one-per-side. The
    apostrophe numbers describe the STACK on a single side:
      - No apostrophe -> stack of 1 per side (the default height).
      - "5'+5'" (two apostrophe numbers) -> stack of 2 per side, heights
        [5, 5].
    The full annotation is that stack duplicated across both sides, so the
    returned list has length = stack_size * 2 (e.g. default -> 2 frames;
    "5'+5'" -> 4 frames).

    Returns a list of frame heights (ints), e.g. [6, 6] or [5, 5, 5, 5].
    """
    contained = find_contained_paths({0: container}, paths)
    analyzed = find_glyph_paths(contained)
    glyphs = analyzed.get(0, {}).get('glyphs', [])

    apostrophes = [g for g in glyphs if g.get('digit') == 'apostrophe']
    digits = [g for g in glyphs if g.get('digit') in ('3', '4', '5', '6', '7')]

    if not apostrophes or not digits:
        # Default stack of 1 per side -> 2 frames total.
        return [int(default_height)] * 2

    def center(g):
        x0, y0, x1, y1 = g['screen_bbox']
        return ((x0 + x1) / 2.0, (y0 + y1) / 2.0)

    # Pair each apostrophe with its nearest digit (each digit used once) to
    # build the per-side stack.
    used = set()
    stack = []
    for ap in apostrophes:
        ax, ay = center(ap)
        best = None
        best_d = None
        for i, dg in enumerate(digits):
            if i in used:
                continue
            dx, dy = center(dg)
            dist = (dx - ax) ** 2 + (dy - ay) ** 2
            if best_d is None or dist < best_d:
                best_d = dist
                best = i
        if best is not None:
            used.add(best)
            stack.append(int(digits[best]['digit']))

    if not stack:
        return [int(default_height)] * 2

    # The stack is duplicated across both sides of the annotation.
    return stack * 2


def _table_for_height(height):
    """Pick the cross bar table whose frame_sizes include this height (ft)."""
    key = f"{int(height)}'"
    for table in CROSS_BAR_TABLES:
        if key in table["frame_sizes"]:
            return table
    return None


def color_for_frame(height, span):
    """
    Look up the cross bar color for one frame: the frame HEIGHT picks the
    table (6'&5' vs 4'&3'), the SPAN picks the row. Returns (hex, name);
    falls back to Yellow if no match.
    """
    table = _table_for_height(height)
    if table is not None:
        for row in table["rows"]:
            if row["span"] == span:
                return CROSS_BAR_COLOR_HEX.get(row["color"], "#ffff00"), row["color"]
    return "#ffff00", "Yellow"


def color_for_span(span):
    """
    Backwards-compatible helper: color for a default-height (6') frame at the
    given span.
    """
    return color_for_frame(6, span)


def _tri_color_diagonal(id_base, p0, p1, color_hex, stroke_width=2.0,
                        end_frac=0.18):
    """
    Build a crossbar brace as a diagonal that runs corner-to-corner from p0 to
    p1, colored like the reference: the two END sections carry the frame's
    cross-bar `color_hex`, and the long MIDDLE section is white.

    `end_frac` is the fraction of the line length each colored end occupies
    (so ~18% color, ~64% white, ~18% color). Returns a list of 3 <line>
    element strings.
    """
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0

    def pt(t):
        return (x0 + dx * t, y0 + dy * t)

    a = pt(end_frac)          # end of first colored tip
    b = pt(1.0 - end_frac)    # start of second colored tip
    style_c = f"stroke:{color_hex};stroke-width:{stroke_width};stroke-opacity:1"
    style_w = f"stroke:#ffffff;stroke-width:{stroke_width};stroke-opacity:1"
    seg = []
    for i, ((sx, sy), (ex, ey), st) in enumerate((
            (p0, a, style_c),      # colored tip near p0
            (a, b, style_w),       # white middle
            (b, p1, style_c),      # colored tip near p1
    )):
        seg.append(
            f'    <line id="{id_base}_{i + 1}" '
            f'x1="{sx:.2f}" y1="{sy:.2f}" x2="{ex:.2f}" y2="{ey:.2f}" '
            f'style="{st}" />'
        )
    return seg


def add_crossbar_lines(svg_content, paths, default_span, default_height,
                       prefixes=('green_container', 'orange_container')):
    """
    For every container of the given prefixes:
      - read its span (cross-bar size) -> picks the table row
      - read its frames from apostrophe dimension numbers (each apostrophe
        number is one frame's height; default is `default_height`)
    Each frame's own HEIGHT picks the table (6'&5' vs 4'&3') and the span
    picks the row, so a mixed stack like "5'+4'" gets DIFFERENT colors per
    frame.

    Drawing: one crossbar X per container, spanning corner-to-corner like a
    real brace. The X is two diagonals (\\ and /); each diagonal is tri-colored
    with the frame's cross-bar color at the ends and white in the middle. When
    a container's frames resolve to two DIFFERENT colors, the two diagonals take
    those two colors (e.g. red \\ + yellow /); otherwise both diagonals share
    the single color. Color/frame counts are still tallied PER FRAME so the
    downstream crossbar_totals stay accurate.

    Returns (svg_content, count, color_breakdown, frame_breakdown).
    """
    line_els = []
    color_counts = {}
    frame_counts = {}
    count = 0
    INSET = 3.0        # keep the X just inside the container edges
    STROKE = 2.0
    HALF_GAP = 2.0     # gap between the left-half and right-half X's
    GAP = 3.0          # offset between overlapping per-color (stacked) X's
    for prefix in prefixes:
        # Match each <prefix>_N rect (id + x/y/width/height attributes).
        rect_re = re.compile(
            r'<rect\s+id="' + re.escape(prefix) + r'_(\d+)"\s+x="([\d.]+)"\s+y="([\d.]+)"'
            r'\s+width="([\d.]+)"\s+height="([\d.]+)"',
            re.DOTALL,
        )
        for m in rect_re.finditer(svg_content):
            num, x, y, w, h = m.groups()
            x = float(x); y = float(y); w = float(w); h = float(h)

            container = {'id': f'{prefix}_{num}',
                         'screen_bbox': (x, y, x + w, y + h)}
            span = read_container_span(container, paths, default_span)
            frames = read_container_frames(container, paths, default_height)
            n_frames = len(frames)
            frame_counts[n_frames] = frame_counts.get(n_frames, 0) + 1

            # Tally the color for EVERY frame (downstream totals depend on this).
            frame_colors = []
            for frame_height in frames:
                color_hex, color_name = color_for_frame(frame_height, span)
                color_counts[color_name] = color_counts.get(color_name, 0) + 1
                frame_colors.append(color_hex)

            # `frames` is the per-side stack duplicated across 2 sides. Layout:
            #   - The box is split into a LEFT half and a RIGHT half, so a
            #     single frame shows a DOUBLE X (one X per half, side by side).
            #   - Within EACH half, every distinct stack color draws its own
            #     FULL-HEIGHT X, overlapping and offset by GAP px so the colors
            #     read separately — e.g. a "5'+4'" stack shows a red X and a
            #     yellow X overlapping in each half.
            n_rows = max(1, n_frames // 2)
            # One color per stack level, first-seen order preserved.
            colors = list(dict.fromkeys(frame_colors[:n_rows])) or ["#ffff00"]

            base = f"crossbar_line_{prefix}_{num}"
            yt, yb = y + INSET, y + h - INSET
            mid = x + w / 2.0
            # Left half + right half, split horizontally with a small gap.
            cells = [(x + INSET, mid - HALF_GAP / 2.0),
                     (mid + HALF_GAP / 2.0, x + w - INSET)]
            for si, (cx0, cx1) in enumerate(cells):
                for ci, color_hex in enumerate(colors):
                    off = ci * GAP  # offset each overlapping color X
                    b = f"{base}_s{si + 1}_c{ci + 1}"
                    # "\" top-left -> bottom-right, then "/" top-right -> bottom-left
                    line_els += _tri_color_diagonal(
                        f"{b}_d1", (cx0 + off, yt), (cx1 + off, yb), color_hex, STROKE)
                    line_els += _tri_color_diagonal(
                        f"{b}_d2", (cx1 + off, yt), (cx0 + off, yb), color_hex, STROKE)
            count += 1

    if line_els:
        block = "\n" + "\n".join(line_els) + "\n"
        svg_content = svg_content.replace("</svg>", block + "</svg>", 1)
    return svg_content, count, color_counts, frame_counts


def extract_default_frame_spec(extracted_text):
    """
    Use Gemini to pull the drawing's default frame spec from OCR text, e.g.
    "ALL FRAMES TO BE 6' HIGH X 4' WIDE HEAVY DUTY(10K/LEG) WITH 7' BRACING TYP".

    Returns a dict like {"height_ft": 6, "bracing_ft": 7} (values null if absent),
    or None if extraction could not run.
    """
    if not extracted_text or not extracted_text.strip():
        print("⚠️  No extracted_text available — skipping default frame spec extraction")
        return None

    # Honor SKIP_GEMINI=1 for local/dev runs that shouldn't burn API quota.
    if os.getenv('SKIP_GEMINI'):
        print("⏭️  SKIP_GEMINI set — skipping default frame spec extraction")
        return None

    try:
        import json
        from google import genai
        from google.genai import types

        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("⚠️  GEMINI_API_KEY not found — skipping default frame spec extraction")
            return None

        prompt = f"""You are reading OCR text from a scaffolding/shoring construction drawing.

Find the DEFAULT FRAME specification note. It usually reads like:
"ALL FRAMES TO BE 6' HIGH X 4' WIDE HEAVY DUTY(10K/LEG) WITH 7' BRACING TYP"

Extract ONLY these two values:
- height_ft: the frame HIGH/HEIGHT value in feet (integer or decimal)
- bracing_ft: the BRACING value in feet (integer or decimal)

Return STRICT JSON with exactly these keys and nothing else:
{{"height_ft": <number or null>, "bracing_ft": <number or null>}}

Use null for any value not present. Do not include units, comments, or extra text.

OCR TEXT:
{extracted_text}"""

        print("\n🤖 Extracting default frame spec with Gemini...")
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=200,
            )
        )

        raw = (response.text or "").strip()
        # Strip markdown code fences if present.
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.lstrip().lower().startswith("json"):
                raw = raw.lstrip()[4:]
        # Grab the first {...} block to be safe.
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if not m:
            print(f"⚠️  Could not parse frame spec from Gemini response: {raw!r}")
            return None

        spec = json.loads(m.group(0))
        result = {
            "height_ft": spec.get("height_ft"),
            "bracing_ft": spec.get("bracing_ft"),
        }
        print(f"✅ Default frame spec: {result}")
        return result

    except ImportError:
        print("⚠️  google-genai not installed — skipping default frame spec extraction")
        return None
    except Exception as e:
        print(f"⚠️  Error extracting default frame spec: {e}")
        return None


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

        svg_path = f"{base}/files/Step11.svg"
        out_path = f"{base}/files/Step13.svg"
        if os.path.exists(svg_path):
            print(f"\n{'=' * 60}")
            print(f"Processing Step11.svg")
            print(f"{'=' * 60}")
            result, summary = process_svg(svg_path, out_path)
            if not result:
                success = False
            else:
                all_summary = summary
        else:
            print(f"⚠️  {svg_path} not found, skipping")

        # Save the drawing's default frame spec to data.json.
        data_path = f"{base}/data.json"
        data = {}
        if os.path.exists(data_path):
            try:
                with open(data_path, 'r') as f:
                    data = json.load(f)
            except (json.JSONDecodeError, Exception):
                data = {}

        # Pull default frame spec (height_ft, bracing_ft) from the drawing's
        # OCR text via Gemini.
        frame_spec = extract_default_frame_spec(data.get('extracted_text', ''))
        if frame_spec is not None:
            data['default_frame_spec'] = frame_spec

        # Store the cross bar lookup tables (frame size + span -> size + color).
        data['cross_bar_tables'] = CROSS_BAR_TABLES

        with open(data_path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"\n✅ Saved default frame spec to data.json")

        # ── Draw crossbar color lines on Step13.svg ──
        # Each green container's span is read from its glyphs (e.g. "5x4" ->
        # span 5). Containers with no digits fall back to the drawing default
        # bracing. Span maps to a cross bar color via the 6' & 5' table.
        default_bracing = None
        default_height = None
        if frame_spec:
            default_bracing = frame_spec.get('bracing_ft')
            default_height = frame_spec.get('height_ft')
        if default_bracing is None:
            default_bracing = 7  # drawing default when spec unavailable
        if default_height is None:
            default_height = 6  # drawing default when spec unavailable
        default_span = f"{int(default_bracing)}'"

        if os.path.exists(out_path):
            import xml.etree.ElementTree as _ET
            _root = _ET.parse(out_path).getroot()
            green_paths = get_g10_paths(_root)

            # Safeguard: warn if any apostrophe/dimension mark was missed, so a
            # new coordinate variant can't silently corrupt the frame counts.
            for _pre in ('green_container', 'orange_container'):
                warn_unmatched_apostrophes(get_containers(_root, _pre), green_paths)

            with open(out_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            svg_content, n_lines, color_counts, frame_counts = add_crossbar_lines(
                svg_content, green_paths, default_span, default_height)
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(svg_content)
            print(f"✅ Added crossbar lines to {n_lines} annotation(s) in Step13.svg")
            print(f"   Color breakdown: {color_counts}")
            print(f"   Frames-per-annotation breakdown: {frame_counts}")

            # Crossbar counts ARE the annotation lines: one colored line was
            # drawn per frame, so each color's line count is that crossbar
            # color's total. Persist these to data.json for Step13b/downstream.
            crossbar_totals = {f"crossbar_{name}": n
                               for name, n in sorted(color_counts.items())}
            crossbar_totals['total'] = sum(color_counts.values())
            frame_totals = {f"frame_{k}": v
                            for k, v in sorted(frame_counts.items())}
            frame_totals['total'] = sum(frame_counts.values())
            data['crossbar_totals'] = crossbar_totals
            data['frame_totals'] = frame_totals
            with open(data_path, 'w') as f:
                json.dump(data, f, indent=4)
            print(f"✅ Saved crossbar_totals/frame_totals to data.json")

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
