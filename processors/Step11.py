#!/usr/bin/env python3
"""
Step 10: Draw containers from greenFrames.json, pinkFrames.json, x-shores.json, and square-shores.json onto Step2.svg
Adds red border rectangles (green frames), pink border rectangles (pink frames), blue border rectangles (X shapes), and red border rectangles (red squares) with numeration to the SVG
"""

import json
import os
import sys
import re
import math
from pathlib import Path
import cairosvg

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Matches the injected #4e4e4e full-canvas background rect (the recolored copy
# of the original #1c1c1c backdrop). Used to strip the duplicate before saving.
_BG_4E_RECT_RE = re.compile(
    r'\s*<rect\s+id="background"[^>]*?fill:#4e4e4e[^>]*?/>\s*',
    re.IGNORECASE,
)

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

# --- Angled post-shore annotation rotation ---------------------------------
# Post shores in the drawing's diagonal band are drawn as small rotated-square
# markers (legs at ~27°/32°, not 45°). The raster detector groups the several
# markers of one post-shore symbol into a single axis-aligned annotation box.
# We recover each marker's angle from its SVG path, then rotate an annotation
# by the median angle of the markers clustered within it.
_SHORE_LEG_MIN, _SHORE_LEG_MAX = 55.0, 70.0
_SHORE_SIDE_RATIO_MAX = 1.12
_SHORE_CLUSTER_RADIUS = 120.0  # world units; markers within this belong to one annotation


def _shore_marker_angle(path_d):
    """If path_d is a rotated-square post-shore marker, return
    (angle_deg, local_cx, local_cy); else None. angle folded to (-45, 45]."""
    segs = list(_iter_line_segments(path_d))
    if len(segs) not in (4, 5):
        return None
    legs = segs[:4]
    lens = [math.hypot(x2 - x1, y2 - y1) for x1, y1, x2, y2 in legs]
    if any(not (_SHORE_LEG_MIN <= L <= _SHORE_LEG_MAX) for L in lens):
        return None
    if max(lens) / min(lens) > _SHORE_SIDE_RATIO_MAX:
        return None
    angs = [_seg_angle_deg(*leg) for leg in legs]
    if any(min(abs(a), abs(a - 90), abs(a - 180)) < 8 for a in angs):
        return None  # axis-aligned squares are boxes/frames, not angled shores

    def pdiff(a, b):
        d = abs(a - b) % 180.0
        return min(d, 180.0 - d)
    if pdiff(angs[0], angs[2]) > 12 or pdiff(angs[1], angs[3]) > 12:
        return None
    if abs(pdiff(angs[0], angs[1]) - 90.0) > 15:
        return None
    xs = [p for s in legs for p in (s[0], s[2])]
    ys = [p for s in legs for p in (s[1], s[3])]
    a = angs[0] % 90.0
    if a > 45.0:
        a -= 90.0
    return (a, sum(xs) / len(xs), sum(ys) / len(ys))


def build_shore_markers(svg_content):
    """Return [(world_cx, world_cy, angle_deg), ...] for every rotated-square
    post-shore marker in svg_content, in world (viewBox) coords."""
    _parent_of, xform_by_id = _build_parent_and_transform_maps(svg_content)
    path_pattern = re.compile(r'<path\b[^>]*>')
    d_pattern = re.compile(r'\bd="([^"]*)"')
    id_pattern = re.compile(r'\bid="([^"]+)"')
    markers = []
    for m in path_pattern.finditer(svg_content):
        tag = m.group(0)
        d_m = d_pattern.search(tag)
        id_m = id_pattern.search(tag)
        if not (d_m and id_m):
            continue
        info = _shore_marker_angle(d_m.group(1))
        if info is None:
            continue
        angle, lcx, lcy = info
        mx = xform_by_id.get(id_m.group(1)) if xform_by_id else None
        if mx is not None:
            wcx, wcy = _apply_matrix(mx, lcx, lcy)
            if mx[3] < 0:  # y-flip negates the drawn angle in world space
                angle = -angle
        else:
            wcx, wcy = lcx, lcy
        markers.append((wcx, wcy, angle))
    return markers


def _cluster_shore_angle(cx, cy, markers):
    """Median angle of shore markers within _SHORE_CLUSTER_RADIUS of (cx, cy),
    or None if this annotation has no angled markers (it's axis-aligned)."""
    near = [a for mx, my, a in markers
            if math.hypot(mx - cx, my - cy) < _SHORE_CLUSTER_RADIUS]
    if not near:
        return None
    near.sort()
    return near[len(near) // 2]


_SHORE_LINK_RADIUS = 90.0     # markers within this are one post-shore symbol
_SHORE_NEW_BOX = 18.0         # side length for a synthesised annotation box
# A cluster counts as "already annotated" only if an existing box sits this
# close to its center. Kept tight (existing matches are ≤81px) so a box that
# belongs to a NEIGHBOURING shore (~92px away) doesn't suppress a new one.
_SHORE_HAS_ANN_RADIUS = 85.0


def cluster_shore_markers(markers):
    """Single-link cluster markers into distinct post shores. Returns
    [(cx, cy, median_angle, n_markers), ...] in world coords."""
    used = [False] * len(markers)
    clusters = []
    for i, (x, y, _a) in enumerate(markers):
        if used[i]:
            continue
        grp = [markers[i]]
        used[i] = True
        changed = True
        while changed:
            changed = False
            for j, (x2, y2, _a2) in enumerate(markers):
                if used[j]:
                    continue
                if any(math.hypot(x2 - gx, y2 - gy) < _SHORE_LINK_RADIUS
                       for gx, gy, _ in grp):
                    grp.append(markers[j])
                    used[j] = True
                    changed = True
        cx = sum(g[0] for g in grp) / len(grp)
        cy = sum(g[1] for g in grp) / len(grp)
        angs = sorted(g[2] for g in grp)
        clusters.append((cx, cy, angs[len(angs) // 2], len(grp)))
    return clusters


def synth_missing_shore_squares(markers, existing_rects, start_id):
    """For each post-shore cluster with no existing annotation nearby, build a
    synthetic red_square dict (with angle). `existing_rects` is the combined
    list of already-detected annotation dicts (need center_x/center_y).
    Returns (new_rects, next_id)."""
    ann_centers = [
        (r.get('center_x', r['x'] + r['width'] / 2),
         r.get('center_y', r['y'] + r['height'] / 2))
        for r in existing_rects
    ]
    new_rects = []
    rid = start_id
    for cx, cy, angle, _n in cluster_shore_markers(markers):
        nearest = min((math.hypot(ax - cx, ay - cy) for ax, ay in ann_centers),
                      default=1e9)
        if nearest < _SHORE_HAS_ANN_RADIUS:
            continue  # already annotated
        half = _SHORE_NEW_BOX / 2.0
        new_rects.append({
            'id': rid,
            'x': cx - half,
            'y': cy - half,
            'width': _SHORE_NEW_BOX,
            'height': _SHORE_NEW_BOX,
            'center_x': cx,
            'center_y': cy,
            '_shore_angle': angle,   # pre-computed; skips cluster lookup
        })
        rid += 1
    return new_rects, rid


def create_rectangle_element(rect_data, color='red', prefix='container', angle=None):
    """Create SVG rectangle element with colored border and numeration.
    When `angle` is given (degrees), the box + label are rotated about the
    rectangle center to align with an angled post shore."""
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

    combined = rect_element + text_element
    if angle:
        # Rotate the box + label about the rectangle center so the annotation
        # aligns with an angled post shore.
        rot_cx = x + width / 2
        rot_cy = y + height / 2
        combined = (
            f'<g transform="rotate({angle:.2f} {rot_cx:.2f} {rot_cy:.2f})">'
            f'{combined}</g>'
        )
    return combined

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
    # Find the opening <svg> tag.
    svg_start_pos = svg_content.find('<svg')
    if svg_start_pos == -1:
        print("Error: Could not find opening <svg> tag")
        return None

    # No background rect is injected: Step11.svg must render with a transparent
    # canvas so it can overlay cleanly. The #4e4e4e backdrop inherited from
    # Step2 is stripped later (see _BG_4E_RECT_RE), leaving no full-canvas fill.
    svg_with_background = svg_content

    # Find the closing </svg> tag
    svg_end_pos = svg_with_background.rfind('</svg>')
    if svg_end_pos == -1:
        print("Error: Could not find closing </svg> tag")
        return None
    
    # Angled post-shore markers, so X-shape and red-square annotations sitting
    # on the diagonal band can be rotated to match (others get angle=None).
    shore_markers = build_shore_markers(svg_content)

    def _shore_angle_for(rect):
        if rect.get('_shore_angle') is not None:
            return rect['_shore_angle']  # synthesised shore box: angle known
        cx = rect.get('center_x', rect['x'] + rect['width'] / 2)
        cy = rect.get('center_y', rect['y'] + rect['height'] / 2)
        return _cluster_shore_angle(cx, cy, shore_markers)

    # All frame types are drawn GREEN. Detection still runs per color
    # (green/pink/orange/yellow) and each keeps its own container prefix so
    # downstream steps (Step13/16/17) can still identify them, but visually
    # every frame is a single unified green frame type. Shores (blue X shapes
    # and red squares) are NOT frames and keep their own colors.
    FRAME_COLOR = '#70ff00'
    container_elements = []
    for rect in green_rectangles:
        container_elements.append(create_rectangle_element(rect, color=FRAME_COLOR, prefix='green_container'))

    # Pink frames -> drawn green
    for rect in pink_rectangles:
        container_elements.append(create_rectangle_element(rect, color=FRAME_COLOR, prefix='pink_container'))

    # Create container elements for X shapes (blue borders)
    for rect in x_shapes:
        container_elements.append(create_rectangle_element(
            rect, color='#0000ff', prefix='x_shape', angle=_shore_angle_for(rect)))

    # Create container elements for red squares (red borders)
    for rect in red_squares:
        container_elements.append(create_rectangle_element(
            rect, color='#ff0000', prefix='red_square', angle=_shore_angle_for(rect)))

    # Orange frames -> drawn green
    for rect in orange_rectangles:
        container_elements.append(create_rectangle_element(rect, color=FRAME_COLOR, prefix='orange_container'))

    # Yellow frames -> drawn green
    for rect in yellow_rectangles:
        container_elements.append(create_rectangle_element(rect, color=FRAME_COLOR, prefix='yellow_container'))

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

_PATH_TOKEN_RE = re.compile(r'([MmLlHhVvCcSsQqTtAaZz])([^MmLlHhVvCcSsQqTtAaZz]*)')
_PATH_NUM_RE = re.compile(r'-?\d+(?:\.\d+)?')


def _iter_line_segments(path_d):
    """Walk an SVG path's `d` data and yield every straight LINE sub-segment as
    (x1, y1, x2, y2) in local coords. Handles M/m (incl. implicit trailing
    linetos), L/l, H/h, V/v, and Z/z (close). Curve commands (C/S/Q/T/A) advance
    the current point past their endpoint but are not treated as straight rails.
    Yields ALL segments in the path, not just the first."""
    cx = cy = 0.0      # current point
    sx = sy = 0.0      # subpath start (for Z)
    for cmd, args in _PATH_TOKEN_RE.findall(path_d):
        nums = [float(n) for n in _PATH_NUM_RE.findall(args)]
        if cmd in 'Mm':
            i = 0
            first = True
            while i + 1 < len(nums):
                x, y = nums[i], nums[i + 1]
                nx, ny = (cx + x, cy + y) if cmd == 'm' else (x, y)
                if first:
                    cx, cy = nx, ny
                    sx, sy = nx, ny
                    first = False
                else:
                    # implicit lineto after the initial moveto pair
                    yield (cx, cy, nx, ny)
                    cx, cy = nx, ny
                i += 2
        elif cmd in 'Ll':
            i = 0
            while i + 1 < len(nums):
                x, y = nums[i], nums[i + 1]
                nx, ny = (cx + x, cy + y) if cmd == 'l' else (x, y)
                yield (cx, cy, nx, ny)
                cx, cy = nx, ny
                i += 2
        elif cmd in 'Hh':
            for x in nums:
                nx = cx + x if cmd == 'h' else x
                yield (cx, cy, nx, cy)
                cx = nx
        elif cmd in 'Vv':
            for y in nums:
                ny = cy + y if cmd == 'v' else y
                yield (cx, cy, cx, ny)
                cy = ny
        elif cmd in 'Zz':
            yield (cx, cy, sx, sy)
            cx, cy = sx, sy
        else:
            # Curve/arc: consume to endpoint so the current point stays correct.
            # Endpoint is the last coordinate pair of the argument list.
            if len(nums) >= 2:
                if cmd.islower():
                    cx += nums[-2]
                    cy += nums[-1]
                else:
                    cx, cy = nums[-2], nums[-1]


def _candidate_segments(path_d, target_dimension, tolerance):
    """Return a list of ALL straight line sub-segments in path_d whose length
    matches target_dimension (±tolerance), each as (x1, y1, x2, y2) in local
    coords. Beams may be drawn at any angle and a single path may contain
    several matching rails, so every match is returned."""
    out = []
    for x1, y1, x2, y2 in _iter_line_segments(path_d):
        length = math.hypot(x2 - x1, y2 - y1)
        if abs(length - target_dimension) <= tolerance:
            out.append((x1, y1, x2, y2))
    return out


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


# Two rails belong to the same beam when they are PARALLEL (angle within
# _ANGLE_TOL) and OFFSET from each other (perpendicular gap > _OFFSET_TOL) with
# overlapping extent along their shared direction. Beams are detected at ANY
# angle — no 90°/180° restriction.
_ANGLE_TOL_DEG = 4.0    # max angle difference for two rails to count as parallel
_OFFSET_TOL = 1.0       # min perpendicular gap; below this they're the same line
_EXTENT_TOL = 2.0       # min overlap along the shared direction
# The opposite rail of a beam sits a fixed, tight distance away (measured ~6
# world units across all detected beams). A parallel neighbor within this gap
# confirms a beam even when that neighbor is a SHORT segment (an opposite rail
# broken into pieces, or a cross-tie) rather than a full beam-length rail.
_RAIL_SPACING_MAX = 10.0  # world units
# Upper bound on the perpendicular gap to a FULL beam-length partner rail. The
# second acceptance clause (partner is itself a beam-length candidate) used to
# accept a partner at ANY distance, which let two far-apart parallel dimension/
# leader lines that merely share a beam's nominal length validate each other as
# a "beam". This clause is already strict — it requires the partner to itself be
# a full same-nominal-length, overlapping, parallel rail (two dimension lines
# rarely both hit an exact beam nominal AND fully overlap). Wider beams do exist:
# e.g. an alumBeam14 pair (path14512/path14514, 1050-long rails) sits ~48 units
# apart. The measured gap distribution for beam-length twins is a continuum up to
# ~48, with dimension-line noise beginning ~53+, so this bound is set just past
# the real 48-unit beams and below the noise band.
_BEAMLEN_PARTNER_MAX = 50.0  # world units
# The far-right strip of the sheet is the TITLE BLOCK / legend — a stack of
# uniformly-spaced horizontal rules, some of which happen to hit a beam nominal
# length and validate each other as a "pair". Real beams live in the plan area
# and never reach into this strip (measured rightmost real beam ~2950 world;
# the title-block rules sit at ~3245+ on a 3456-wide sheet). Candidates whose
# rails lie entirely to the right of this fraction of sheet width are dropped.
_TITLE_BLOCK_X_FRAC = 0.90  # 0.90 * 3456 ≈ 3110, between the two clusters
# A real drawing-geometry path is named "path" + digits (e.g. path14514).
# Anything else is a Vector / synthesized element and is never an aluminum beam.
_PATH_ID_RE = re.compile(r'^path\d+$')
# Min world length for a segment to serve as a partner rail. The opposite rail
# is often split into short pieces (~48 world units here), so this must stay
# well below that; it only filters out tiny arrowhead/tick stubs.
_PARTNER_MIN_LEN = 25.0   # world units
# A single aluminum-beam rail is drawn as ONE standalone straight line whose
# nominal length is the beam size. Two shapes masquerade as rails because they
# contain a matching-length run but are NOT beams:
#   - Small closed RECTANGLES (a box drawn as long,short,long,short = 4 segs,
#     e.g. a 375x50 marker) — one long side coincidentally hits a beam length.
#   - Long multi-segment POLYLINES (dimension/construction runs) that happen to
#     include one beam-length straight run among many segments.
# A real rail path has few segments (the rail, sometimes split, plus stubs) and
# is never a closed box. Paths with more segments than this are polylines.
_MAX_RAIL_SEGMENTS = 6


def _is_beam_rail_shape(path_d, target_dimension, tolerance):
    """True if path_d looks like a real beam rail rather than a box outline or a
    long dimension polyline. Rejects: (a) closed rectangles that merely have one
    side at the beam length, and (b) paths with many straight sub-segments (a
    polyline whose beam-length run is incidental). See _MAX_RAIL_SEGMENTS."""
    segs = list(_iter_line_segments(path_d))
    n = len(segs)
    if n == 0:
        return False
    lengths = [math.hypot(x2 - x1, y2 - y1) for x1, y1, x2, y2 in segs]
    # A 4-segment closed rectangle: two sides near the beam length and two much
    # shorter sides. That is a marker/box, not a rail — reject it.
    if n == 4:
        longs = sum(1 for L in lengths
                    if abs(L - target_dimension) <= tolerance)
        shorts = sum(1 for L in lengths if L < target_dimension / 2.0)
        if longs >= 2 and shorts >= 2:
            return False
    # A many-segment polyline is a dimension/construction run, not a rail.
    if n > _MAX_RAIL_SEGMENTS:
        return False
    return True


def _seg_angle_deg(x1, y1, x2, y2):
    """Undirected line angle in [0, 180) degrees. A segment and its reverse
    share the same angle, so orientation of the drawn direction doesn't matter."""
    ang = math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180.0
    return ang


def _angle_close(a, b, tol=_ANGLE_TOL_DEG):
    """True if two undirected angles (each in [0,180)) are within tol degrees,
    accounting for the 0/180 wrap."""
    diff = abs(a - b) % 180.0
    return diff <= tol or diff >= 180.0 - tol


def _build_parallel_pool(svg_content, xform_by_id):
    """Return every straight line segment in the SVG (>= _PARTNER_MIN_LEN in
    WORLD coords) as (path_id, angle_deg, x1, y1, x2, y2). Used as the pool of
    potential partner rails — a beam's opposite rail may be short or split into
    pieces, so we can't restrict partners to beam-length segments."""
    path_pattern = re.compile(r'<path\b[^>]*>')
    d_pattern = re.compile(r'\bd="([^"]*)"')
    id_pattern = re.compile(r'\bid="([^"]+)"')
    pool = []
    for m in path_pattern.finditer(svg_content):
        tag = m.group(0)
        d_m = d_pattern.search(tag)
        id_m = id_pattern.search(tag)
        if not (d_m and id_m):
            continue
        path_id = id_m.group(1)
        # Only real drawing geometry ("path####") can be a beam rail. Vector /
        # synthesized elements never partner-validate a beam.
        if not _PATH_ID_RE.match(path_id):
            continue
        mx = xform_by_id.get(path_id) if xform_by_id else None
        for lx1, ly1, lx2, ly2 in _iter_line_segments(d_m.group(1)):
            if mx is not None:
                wx1, wy1 = _apply_matrix(mx, lx1, ly1)
                wx2, wy2 = _apply_matrix(mx, lx2, ly2)
            else:
                wx1, wy1, wx2, wy2 = lx1, ly1, lx2, ly2
            if math.hypot(wx2 - wx1, wy2 - wy1) < _PARTNER_MIN_LEN:
                continue
            pool.append((path_id, _seg_angle_deg(wx1, wy1, wx2, wy2),
                         wx1, wy1, wx2, wy2))
    return pool


def _sheet_width(svg_content):
    """Sheet width in world units from the viewBox (defaults to 3456)."""
    m = re.search(r'viewBox="[^"]*?\s([\d.]+)\s+[\d.]+"', svg_content)
    try:
        return float(m.group(1)) if m else 3456.0
    except (ValueError, AttributeError):
        return 3456.0


def _in_title_block(candidate, sheet_w):
    """True if this rail lies entirely in the far-right title-block strip, so
    it should never be treated as an aluminum beam. `candidate` is
    (id, angle, x1, y1, x2, y2) in world coords."""
    if not sheet_w:
        return False
    limit = _TITLE_BLOCK_X_FRAC * sheet_w
    _id, _a, x1, _y1, x2, _y2 = candidate
    return min(x1, x2) >= limit


def mark_alum_beams_by_dimension(svg_content, target_dimension, stroke_color, tolerance=0):
    """Turn the stroke color of any <path> whose straight run matches
    target_dimension AND has at least one parallel same-dimension partner rail
    nearby. Returns (updated_svg_content, changed_count).

    Beams may be drawn at ANY angle (not just 90°/180°). A rail is kept only if
    it has a parallel partner: real aluminum beams are always two parallel
    rails, whereas a lone matching line is usually a dimension/construction line
    that merely shares a beam's nominal length. Rails inside the title-block
    strip are excluded (see _in_title_block).
    """
    path_pattern = re.compile(r'<path\b[^>]*>')
    style_pattern = re.compile(r'\bstyle="([^"]*)"')
    d_pattern = re.compile(r'\bd="([^"]*)"')
    id_pattern = re.compile(r'\bid="([^"]+)"')

    # Build ancestor-transform map so we can convert local path coords → world.
    _parent_of, xform_by_id = _build_parent_and_transform_maps(svg_content)
    sheet_w = _sheet_width(svg_content)

    # Pass 1: collect candidate rails (geometry + fill guard). A single path may
    # contain several matching segments, so every one is registered. Each is
    # stored as (path_id, angle_deg, x1, y1, x2, y2) in WORLD coords, angle in
    # [0,180). path_id repeats across a path's segments — recoloring keys on it.
    candidates = []
    for m in path_pattern.finditer(svg_content):
        tag = m.group(0)
        d_m = d_pattern.search(tag)
        st_m = style_pattern.search(tag)
        id_m = id_pattern.search(tag)
        if not (d_m and st_m and id_m):
            continue

        path_d = d_m.group(1)
        segs = _candidate_segments(path_d, target_dimension, tolerance)
        if not segs:
            continue

        style_value = st_m.group(1)
        fill_m = re.search(r'fill\s*:\s*([^;"]+)', style_value, re.IGNORECASE)
        fill_val = fill_m.group(1).strip().lower() if fill_m else ''
        if fill_val and fill_val != 'none':
            continue

        # Shape guard: skip box outlines and long polylines that only contain a
        # beam-length run (see _is_beam_rail_shape). A real rail is a standalone
        # straight line, so these are false positives (e.g. small rectangle
        # markers or dimension polylines sharing a beam's nominal length).
        if not _is_beam_rail_shape(path_d, target_dimension, tolerance):
            continue

        path_id = id_m.group(1)
        # Real drawing geometry is named "path####". Anything else is a Vector /
        # synthesized element (containers, annotations, id-less graphics), never
        # an aluminum beam — skip it.
        if not _PATH_ID_RE.match(path_id):
            continue
        mx = xform_by_id.get(path_id) if xform_by_id else None
        for lx1, ly1, lx2, ly2 in segs:
            # Map to world coords via ancestor transform.
            if mx is not None:
                wx1, wy1 = _apply_matrix(mx, lx1, ly1)
                wx2, wy2 = _apply_matrix(mx, lx2, ly2)
            else:
                wx1, wy1, wx2, wy2 = lx1, ly1, lx2, ly2
            # Length was already matched in local space (target_dimension is in
            # the path's local units). World coords are used only for angle +
            # partner geometry, which stay consistent under the transform scale.
            angle = _seg_angle_deg(wx1, wy1, wx2, wy2)
            candidates.append((path_id, angle, wx1, wy1, wx2, wy2))

    # Pool of ALL long parallel-partner-eligible segments (any length), so a
    # beam's opposite rail counts even when it's short or split into pieces.
    partner_pool = _build_parallel_pool(svg_content, xform_by_id)

    # Pass 2: keep a candidate rail if it has a parallel partner. A partner is
    # any DIFFERENT-path segment that is parallel (angle within tol), offset from
    # it, and overlapping along the shared direction — AND EITHER sits within the
    # tight beam rail spacing (_RAIL_SPACING_MAX, the opposite rail) OR is itself
    # a beam-length candidate (a second full rail, possibly farther out).
    def _project_extent(ux, uy, x1, y1, x2, y2):
        """Signed projections of both endpoints onto unit direction (ux,uy)."""
        p1 = x1 * ux + y1 * uy
        p2 = x2 * ux + y2 * uy
        return (min(p1, p2), max(p1, p2))

    beamlen_ids = {c[0] for c in candidates}

    def has_partner(c):
        _id_c, a_c, cx1, cy1, cx2, cy2 = c
        # Unit direction of this rail (its own axis).
        clen = math.hypot(cx2 - cx1, cy2 - cy1)
        if clen == 0:
            return False
        ux, uy = (cx2 - cx1) / clen, (cy2 - cy1) / clen
        nx, ny = -uy, ux  # perpendicular unit vector
        c_min, c_max = _project_extent(ux, uy, cx1, cy1, cx2, cy2)
        c_perp = cx1 * nx + cy1 * ny
        for _id_d, a_d, dx1, dy1, dx2, dy2 in partner_pool:
            # Partner must be a DIFFERENT path (two separate rails = a real beam).
            if _id_d == _id_c:
                continue
            if not _angle_close(a_c, a_d):
                continue
            # Perpendicular gap between the two parallel lines.
            offset = abs(c_perp - (dx1 * nx + dy1 * ny))
            if offset < _OFFSET_TOL:
                continue  # essentially the same line
            # Overlap along the shared direction.
            d_min, d_max = _project_extent(ux, uy, dx1, dy1, dx2, dy2)
            if min(c_max, d_max) - max(c_min, d_min) <= _EXTENT_TOL:
                continue
            # Accept if it's the tight opposite rail, or a full beam-length
            # rail — but a beam-length partner only counts within
            # _BEAMLEN_PARTNER_MAX, else far-apart dimension lines self-validate.
            if offset <= _RAIL_SPACING_MAX:
                return True
            if _id_d in beamlen_ids and offset <= _BEAMLEN_PARTNER_MAX:
                return True
        return False

    keepers = {c[0] for c in candidates
               if not _in_title_block(c, sheet_w) and has_partner(c)}

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
    # `keepers` is the set of ORIGINAL path ids recolored to this beam class —
    # returned so callers can map path id -> classification without re-scraping
    # colors from the SVG (white #ffffff is shared with non-beam paths).
    return updated_svg, changed_count, keepers

def update_data_json_with_counts(green_count, pink_count, x_count, red_count, orange_count, yellow_count, beam_counts, identified=None):
    """Update data.json with current step results.

    `identified` is the {element_id: classification} map for every non-gray
    element (beams keyed by path id, shores/frames by container id); it is stored
    under the top-level "identified_elements" key so the database gets it too."""
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

        # Store the full id -> classification map for the database.
        if identified is not None:
            data["identified_elements"] = identified

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

    # Read the source SVG so we can recover angled post-shore markers that the
    # raster detector missed entirely.
    svg_content = read_svg_file(step2_svg_path)
    if not svg_content:
        return False

    # NOTE: Auto-synthesis of post-shore boxes from rotated-square SVG markers is
    # disabled. Those markers land on meaningless diagonal-line details (not real
    # post shores), producing spurious annotations. Post shores come solely from
    # the raster detector (red squares / X-shapes).

    # Filter out X-shapes that overlap with red squares (silently)
    filtered_x_shapes = filter_overlapping_x_shapes(x_shapes, red_squares)

    # Print only the table
    print_drawn_objects(green_rectangles, pink_rectangles, filtered_x_shapes, red_squares, orange_rectangles, yellow_rectangles)

    modified_svg = add_containers_to_svg(svg_content, green_rectangles, pink_rectangles, filtered_x_shapes, red_squares, orange_rectangles, yellow_rectangles)
    if not modified_svg:
        return False

    # Beam categories and styling rules. Tolerance is 2 local units: diagonal
    # rails of the same beam can differ by ~1.5 units due to rounding, and the
    # smallest gap between adjacent beam dimensions is 37, so 2 stays unambiguous.
    beam_specs = [
        ("alumBeam24", 1800, 2, "#00A000"),
        ("alumBeam20", 1500, 2, "#A020F0"),
        ("alumBeam18", 1350, 2, "#FFD400"),
        ("alumBeam16", 1201, 2, "#ffffff"),
        ("alumBeam14", 1050, 2, "#1D915C"),
        ("alumBeam13", 975, 2, "#9CFF9C"),
        ("alumBeam12", 900, 2, "#F54927"),
        ("alumBeam11", 825, 2, "#FF6EC7"),
        ("alumBeam10_6", 787, 2, "#FFA805"),
        ("alumBeam10", 750, 2, "#00C8FF"),
        ("alumBeam9", 675, 2, "#B52FC4"),
        ("alumBeam8", 600, 2, "#00FFFF"),
        ("alumBeam7", 525, 2, "#FFBC85"),
        ("alumBeam6", 451, 2, "#E6E600"),
        ("alumBeam5", 376, 2, "#4084FF"),
    ]

    beam_counts = {}
    identified = {}   # element id -> classification label (path id for beams)
    for beam_key, beam_dimension, beam_tolerance, beam_color in beam_specs:
        modified_svg, beam_count, beam_ids = mark_alum_beams_by_dimension(
            modified_svg,
            beam_dimension,
            beam_color,
            beam_tolerance,
        )
        beam_counts[beam_key] = beam_count
        for pid in beam_ids:
            identified[pid] = beam_key

    # Add the annotation containers (shores + frames) to the identified map.
    # Their ids are the ones create_rectangle_element assigns: "<prefix>_<id>".
    for rect in green_rectangles:
        identified[f"green_container_{rect['id']}"] = "greenFrame"
    for rect in pink_rectangles:
        identified[f"pink_container_{rect['id']}"] = "pinkFrame"
    for rect in filtered_x_shapes:
        identified[f"x_shape_{rect['id']}"] = "shore_x"
    for rect in red_squares:
        identified[f"red_square_{rect['id']}"] = "shore_square"
    for rect in orange_rectangles:
        identified[f"orange_container_{rect['id']}"] = "orangeFrame"
    for rect in yellow_rectangles:
        identified[f"yellow_container_{rect['id']}"] = "yellowFrame"

    # Write the single path-id -> classification map for all non-gray elements.
    ident_path = base_dir / "files" / "tempData" / "identified_elements.json"
    try:
        with open(ident_path, "w", encoding="utf-8") as f:
            json.dump(identified, f, indent=2)
        print(f"  Wrote {len(identified)} identified elements to {ident_path}")
    except Exception as e:
        print(f"  Warning: could not write identified_elements.json: {e}")

    # Update data.json with counts
    update_data_json_with_counts(
        len(green_rectangles),
        len(pink_rectangles),
        len(filtered_x_shapes),
        len(red_squares),
        len(orange_rectangles),
        len(yellow_rectangles),
        beam_counts,
        identified
    )
    save_beam_counts_json(beam_counts)

    # Step2 recolors the original #1c1c1c background rect to #4e4e4e, and this
    # step adds a fresh #1c1c1c rect on top — leaving two stacked backgrounds.
    # Strip the #4e4e4e duplicate so only the original #1c1c1c background remains.
    modified_svg = _BG_4E_RECT_RE.sub("\n", modified_svg)

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
