#!/usr/bin/env python3
"""
Step16: Group same-color frames that share an X or Y axis (center within 5px)
and draw a white bounding rectangle around each valid group.

Rules:
- Frames only: green, orange, pink, yellow. Shores (red squares, blue X) are excluded.
- Axis = center_x or center_y, 5px tolerance.
- Min group size: 2.
- All members must share the same color.
- A frame qualifying for both an X-group and a Y-group joins the larger group;
  ties broken by smaller bounding-box area.
- Other-color frames inside the bounding box are allowed; only a non-member
  same-color frame inside the box disqualifies the group.
- Group bounding boxes must not overlap each other; overlaps are resolved by
  keeping the larger group (ties → smaller area).
"""

import json
import os
import re
from pathlib import Path

AXIS_TOLERANCE = 5.0
MIN_GROUP_SIZE = 2

BASE_DIR = Path(__file__).resolve().parent.parent
TEMP_DATA = BASE_DIR / "files" / "tempData"

FRAME_SOURCES = [
    ("green",  TEMP_DATA / "greenFrames.json",  "rectangles"),
    ("orange", TEMP_DATA / "orangeFrames.json", "rectangles"),
    ("pink",   TEMP_DATA / "pinkFrames.json",   "pink_shapes"),
    ("yellow", TEMP_DATA / "yellowFrames.json", "shapes"),
]

INPUT_SVG = BASE_DIR / "files" / "Step11.svg"
OUTPUT_SVG = BASE_DIR / "files" / "Step16.svg"
GROUPS_DIR = BASE_DIR / "files" / "groups"

# Padding around each group bbox when cropping (in SVG user units).
# Sized so paired aluminum-beam rails sitting just outside the frame bbox
# (e.g. the second rail of an alumBeam pair) stay inside the viewBox so
# Step17 can pair them and stamp wood beams across the full region.
GROUP_CROP_PADDING = 10.0


def load_frames():
    """Return list of (color, frame_dict) for every frame across all colors."""
    frames = []
    for color, path, key in FRAME_SOURCES:
        if not path.exists():
            continue
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except Exception as e:
            print(f"  ⚠️  Failed to read {path}: {e}")
            continue
        # Some files use alternate keys — try a couple of fallbacks
        items = data.get(key) or data.get("rectangles") or data.get("shapes") or []
        for item in items:
            if "center_x" not in item or "center_y" not in item:
                continue
            frames.append((color, item))
    return frames


ORIENTATION_TOLERANCE = 5.0


def frame_orientation(frame):
    """'tall' if height - width > tol, 'wide' if width - height > tol,
    otherwise 'square' (near-square shapes group together)."""
    w, h = frame["width"], frame["height"]
    if h - w > ORIENTATION_TOLERANCE:
        return "tall"
    if w - h > ORIENTATION_TOLERANCE:
        return "wide"
    return "square"


def cluster_by_axis(frames_of_color, axis):
    """Cluster frames (same color, same orientation) by center coordinate on the given axis.

    Returns a list of groups; each group is a list of frame dicts whose
    centers are within AXIS_TOLERANCE of each other on `axis` (transitively
    via single-link clustering, sorted by coordinate) and that all share
    the same orientation (all tall, all wide, or all square).
    """
    key = "center_x" if axis == "x" else "center_y"
    by_orient = {}
    for f in frames_of_color:
        by_orient.setdefault(frame_orientation(f), []).append(f)

    all_groups = []
    for orient_frames in by_orient.values():
        sorted_frames = sorted(orient_frames, key=lambda f: f[key])
        current = []
        last = None
        for frame in sorted_frames:
            v = frame[key]
            if last is None or abs(v - last) <= AXIS_TOLERANCE:
                current.append(frame)
            else:
                if len(current) >= MIN_GROUP_SIZE:
                    all_groups.append(current)
                current = [frame]
            last = v
        if len(current) >= MIN_GROUP_SIZE:
            all_groups.append(current)
    return all_groups


def group_bounds(group):
    """Axis-aligned bounding box of a list of frames (using x/y/width/height)."""
    xs1 = [f["x"] for f in group]
    ys1 = [f["y"] for f in group]
    xs2 = [f["x"] + f["width"] for f in group]
    ys2 = [f["y"] + f["height"] for f in group]
    x_min, y_min = min(xs1), min(ys1)
    x_max, y_max = max(xs2), max(ys2)
    return x_min, y_min, x_max, y_max


def frame_center_in_box(frame, box):
    x_min, y_min, x_max, y_max = box
    cx, cy = frame["center_x"], frame["center_y"]
    return x_min <= cx <= x_max and y_min <= cy <= y_max


def box_area(box):
    x_min, y_min, x_max, y_max = box
    return max(0.0, x_max - x_min) * max(0.0, y_max - y_min)


def frame_key(color, frame):
    return (color, frame.get("id"))


def build_candidate_groups(frames):
    """Per color, build X and Y groups. Returns list of dicts with members,
    color, axis, bounds, area, and a set of member keys."""
    candidates = []
    by_color = {}
    for color, frame in frames:
        by_color.setdefault(color, []).append(frame)

    for color, color_frames in by_color.items():
        for axis in ("x", "y"):
            for group in cluster_by_axis(color_frames, axis):
                bounds = group_bounds(group)
                candidates.append({
                    "color": color,
                    "axis": axis,
                    "members": group,
                    "member_keys": {frame_key(color, f) for f in group},
                    "bounds": bounds,
                    "area": box_area(bounds),
                })
    return candidates


def select_groups_for_frames(frames, candidates):
    """For each frame, pick at most one group: prefer largest, ties → smaller area.
    A group is kept only if every member chose it.
    """
    # Map: frame_key -> chosen candidate index
    best_for_frame = {}
    for idx, cand in enumerate(candidates):
        size = len(cand["members"])
        area = cand["area"]
        for k in cand["member_keys"]:
            cur = best_for_frame.get(k)
            if cur is None:
                best_for_frame[k] = idx
                continue
            cur_cand = candidates[cur]
            cur_size = len(cur_cand["members"])
            cur_area = cur_cand["area"]
            # Larger size wins; tie → smaller area
            if size > cur_size or (size == cur_size and area < cur_area):
                best_for_frame[k] = idx

    # Keep a candidate only if every member's best == this candidate
    selected = []
    for idx, cand in enumerate(candidates):
        if all(best_for_frame.get(k) == idx for k in cand["member_keys"]):
            selected.append(cand)
    return selected


def _is_contaminated(bounds, member_keys, cand_color, cand_orient, frames):
    """True if any non-member, disallowed frame sits inside bounds."""
    for color, frame in frames:
        if frame_key(color, frame) in member_keys:
            continue
        # Same color, different orientation → allowed
        if color == cand_color and frame_orientation(frame) != cand_orient:
            continue
        if frame_center_in_box(frame, bounds):
            return True
    return False


def filter_groups_by_containment(selected, frames):
    """Drop any group whose bounding box contains a non-member frame:
    - Other-color frames inside the bbox are disallowed.
    - Same-color non-member frames are disallowed only if they share the
      group's orientation (different-orientation same-color frames are OK).

    When a group is contaminated, split it into the longest contiguous
    sub-runs (along the perpendicular axis) that remain contamination-free
    and have at least MIN_GROUP_SIZE members.
    """
    kept = []
    for cand in selected:
        cand_color = cand["color"]
        cand_orient = frame_orientation(cand["members"][0])
        members = cand["members"]
        member_keys = {frame_key(cand_color, f) for f in members}

        if not _is_contaminated(cand["bounds"], member_keys, cand_color, cand_orient, frames):
            kept.append(cand)
            continue

        # Sort members along the perpendicular axis (x-axis groups → sort by y;
        # y-axis groups → sort by x), then try every contiguous sub-run of
        # length >= MIN_GROUP_SIZE and keep the longest non-contaminated runs.
        sort_key = "center_y" if cand["axis"] == "x" else "center_x"
        ordered = sorted(members, key=lambda f: f[sort_key])

        n = len(ordered)
        used = [False] * n
        # Greedy: try the largest possible runs first
        for size in range(n, MIN_GROUP_SIZE - 1, -1):
            for start in range(0, n - size + 1):
                if any(used[start:start + size]):
                    continue
                sub = ordered[start:start + size]
                sub_keys = {frame_key(cand_color, f) for f in sub}
                sub_bounds = group_bounds(sub)
                if _is_contaminated(sub_bounds, sub_keys, cand_color, cand_orient, frames):
                    continue
                kept.append({
                    "color": cand_color,
                    "axis": cand["axis"],
                    "members": sub,
                    "member_keys": sub_keys,
                    "bounds": sub_bounds,
                    "area": box_area(sub_bounds),
                })
                for i in range(start, start + size):
                    used[i] = True
    return kept


def boxes_overlap(b1, b2):
    """True if two axis-aligned bounding boxes overlap (touching edges don't count)."""
    x1a, y1a, x2a, y2a = b1
    x1b, y1b, x2b, y2b = b2
    return not (x2a <= x1b or x2b <= x1a or y2a <= y1b or y2b <= y1a)


def filter_overlapping_groups(groups):
    """Remove overlapping groups, but only block overlaps between groups on
    different axes (horizontal vs vertical). Same-axis overlaps are allowed.
    Priority: more members first, then smaller area."""
    ordered = sorted(groups, key=lambda c: (-len(c["members"]), c["area"]))
    kept = []
    for cand in ordered:
        conflicts = any(
            k["axis"] != cand["axis"] and boxes_overlap(cand["bounds"], k["bounds"])
            for k in kept
        )
        if conflicts:
            continue
        kept.append(cand)
    return kept


def make_group_rect_svg(cand, group_id):
    x_min, y_min, x_max, y_max = cand["bounds"]
    w = x_max - x_min
    h = y_max - y_min
    color = "#ffffff"
    return (
        f'    <rect id="step16_group_{group_id}" '
        f'x="{x_min}" y="{y_min}" width="{w}" height="{h}" '
        f'style="fill:{color};stroke:{color};stroke-width:5;stroke-opacity:1;fill-opacity:0.5" />\n'
        f'    <text x="{x_min + 2}" y="{y_min - 4}" '
        f'style="font-family:Arial;font-size:10px;fill:{color};font-weight:bold">'
        f'G{group_id} ({cand["color"]},{cand["axis"]},n={len(cand["members"])})</text>\n'
    )


def inject_into_svg(svg_text, group_svg):
    """Insert group rects just before the closing </svg> tag."""
    closing = "</svg>"
    idx = svg_text.rfind(closing)
    if idx == -1:
        return svg_text + group_svg
    return svg_text[:idx] + group_svg + svg_text[idx:]


SVG_NS = "http://www.w3.org/2000/svg"

# Map Step16 color names → Step11 SVG id prefixes for frame rects.
FRAME_PREFIX = {
    "green":  "green_container",
    "orange": "orange_container",
    "pink":   "pink_container",
    "yellow": "yellow_container",
}

# Aluminum beam stroke colors (from Step11.py mapping) + gray annotation color.
KEEP_STROKES = {
    "#4e4e4e",
    "#A020F0", "#FFD400", "#ffffff", "#1D915C", "#9CFF9C", "#F54927", "#FF6EC7",
    "#FFA805", "#00C8FF", "#B52FC4", "#00FFFF", "#FFBC85", "#E6E600",
    "#4084FF",
}
KEEP_STROKES_LOWER = {c.lower() for c in KEEP_STROKES}


def _local(tag):
    return tag.split("}", 1)[1] if "}" in tag else tag


_STROKE_RE = re.compile(r"stroke:\s*([^;]+)")


def _element_stroke(el):
    """Return the lowercased stroke color of an element (from style= or stroke=),
    or empty string if none."""
    style = el.get("style", "") or ""
    m = _STROKE_RE.search(style)
    if m:
        return m.group(1).strip().lower()
    s = el.get("stroke", "") or ""
    return s.strip().lower()


# Aluminum-rail stroke colors only — recoloring these is the goal. We don't
# touch shores or container frames.
ALUM_STROKES_LOWER = {
    "#a020f0", "#ffd400", "#ffffff", "#1d915c", "#9cff9c", "#f54927",
    "#ff6ec7", "#ffa805", "#00c8ff", "#b52fc4", "#00ffff", "#ffbc85",
    "#e6e600", "#4084ff",
}

# How far outside the group's frame bbox an alum-rail's midpoint may sit and
# still count as "this group's rail". Matches Step17's GROUP_BBOX_PAD so both
# steps agree on group membership.
ALUM_GROUP_TOL = 15.0

_MATRIX_RE = re.compile(
    r"matrix\(\s*([-\d.]+)[,\s]+([-\d.]+)[,\s]+([-\d.]+)[,\s]+([-\d.]+)[,\s]+([-\d.]+)[,\s]+([-\d.]+)\s*\)"
)
_H_ABS_RE = re.compile(r'\bM\s*(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)\s*H\s*(-?\d+(?:\.\d+)?)\b')
_V_ABS_RE = re.compile(r'\bM\s*(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)\s*V\s*(-?\d+(?:\.\d+)?)\b')
_H_REL_RE = re.compile(r'\bm\s*(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)\s*h\s*(-?\d+(?:\.\d+)?)\b')
_V_REL_RE = re.compile(r'\bm\s*(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)\s*v\s*(-?\d+(?:\.\d+)?)\b')


_PATH_M_RE = re.compile(r"[Mm]\s*(-?\d+(?:\.\d+)?)[,\s]+(-?\d+(?:\.\d+)?)")


def _path_midpoint_local(path_d):
    """Best-effort midpoint of a path in its local frame: average of the
    first H/V run's endpoints if there is one, otherwise the first `M`/`m`
    coordinate (close enough for membership tests)."""
    m = _H_ABS_RE.search(path_d)
    if m:
        x1, y1, x2 = float(m.group(1)), float(m.group(2)), float(m.group(3))
        return (x1 + x2) / 2, y1
    m = _V_ABS_RE.search(path_d)
    if m:
        x1, y1, y2 = float(m.group(1)), float(m.group(2)), float(m.group(3))
        return x1, (y1 + y2) / 2
    m = _H_REL_RE.search(path_d)
    if m:
        sx, sy, dx = float(m.group(1)), float(m.group(2)), float(m.group(3))
        return sx + dx / 2, sy
    m = _V_REL_RE.search(path_d)
    if m:
        sx, sy, dy = float(m.group(1)), float(m.group(2)), float(m.group(3))
        return sx, sy + dy / 2
    # Fall back to the first move-to coordinate.
    m = _PATH_M_RE.search(path_d)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None


def _apply_matrix(mx, x, y):
    a, b, c, d, tx, ty = mx
    return a * x + c * y + tx, b * x + d * y + ty


def _recolor_out_of_group_rails(root, bounds, pad=0.0):
    """Walk the tree; for every <path> with an alum-beam stroke, compute its
    world-coord midpoint and, if it falls outside (bounds ± pad), REMOVE the
    path from the tree. Those rails belong to a neighbouring group, so they
    shouldn't appear in this group's cropped SVG at all.

    (Kept the original name for callers; behavior changed from recolor →
    remove since the recolored gray rails were still visually cluttering
    the per-group views.)
    """
    x_min, y_min, x_max, y_max = bounds
    x_min -= pad; y_min -= pad
    x_max += pad; y_max += pad

    # Build parent-map and accumulated-transform map (root → parent of node).
    parent_of = {c: p for p in root.iter() for c in p}
    accum = {root: (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)}
    stack = [root]
    while stack:
        node = stack.pop()
        par_xform = accum[node]
        for child in list(node):
            m = _MATRIX_RE.search(child.get("transform", "") or "")
            if m:
                own = tuple(float(m.group(i)) for i in range(1, 7))
                a1,b1,c1,d1,e1,f1 = par_xform
                a2,b2,c2,d2,e2,f2 = own
                xform = (a1*a2+c1*b2, b1*a2+d1*b2,
                         a1*c2+c1*d2, b1*c2+d1*d2,
                         a1*e2+c1*f2+e1, b1*e2+d1*f2+f1)
            else:
                xform = par_xform
            accum[child] = xform
            stack.append(child)

    # Collect out-of-group alum paths to remove. We can't mutate during iter,
    # so gather first then drop via the parent map.
    to_remove = []
    for el in root.iter():
        if _local(el.tag) != "path":
            continue
        stroke = _element_stroke(el)
        if stroke not in ALUM_STROKES_LOWER:
            continue
        mid = _path_midpoint_local(el.get("d", ""))
        if mid is None:
            continue
        par = parent_of.get(el)
        xform = accum.get(par, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0))
        wx, wy = _apply_matrix(xform, mid[0], mid[1])
        if x_min <= wx <= x_max and y_min <= wy <= y_max:
            continue  # in-group — keep
        to_remove.append(el)

    removed = 0
    for el in to_remove:
        par = parent_of.get(el)
        if par is not None:
            try:
                par.remove(el)
                removed += 1
            except ValueError:
                pass
    return removed


def _filter_floorplan_group(g_el):
    """Recursively walk a transformed floor-plan <g>, removing any leaf
    element (path/text) whose stroke is not in the keep list. Keeps nested
    <g> wrappers as long as they still contain something."""
    to_remove = []
    for child in list(g_el):
        tag = _local(child.tag)
        if tag == "g":
            _filter_floorplan_group(child)
            if len(list(child)) == 0:
                to_remove.append(child)
        elif tag in ("path", "text"):
            stroke = _element_stroke(child)
            if stroke and stroke not in KEEP_STROKES_LOWER:
                to_remove.append(child)
            elif not stroke:
                # No stroke specified — drop to be safe (avoids leaking shores etc.)
                to_remove.append(child)
    for el in to_remove:
        g_el.remove(el)


def crop_svg_to_bounds(svg_text, bounds, cand, padding=GROUP_CROP_PADDING):
    """Return an SVG cropped to the given bounds. Removes only the same-color
    frame rects/text labels that aren't members of `cand`. Everything else
    (other-color frames, shores, floor-plan, background) stays."""
    import xml.etree.ElementTree as ET

    x_min, y_min, x_max, y_max = bounds
    px = x_min - padding
    py = y_min - padding
    pw = (x_max - x_min) + 2 * padding
    ph = (y_max - y_min) + 2 * padding

    ET.register_namespace("", SVG_NS)
    ET.register_namespace("dc", "http://purl.org/dc/elements/1.1/")
    ET.register_namespace("cc", "http://creativecommons.org/ns#")
    ET.register_namespace("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")
    ET.register_namespace("svg", SVG_NS)

    try:
        root = ET.fromstring(svg_text)
    except ET.ParseError as e:
        print(f"  ⚠️  SVG parse failed, falling back to raw text: {e}")
        return svg_text

    root.set("viewBox", f"{px} {py} {pw} {ph}")
    root.set("width", str(pw))
    root.set("height", str(ph))

    color = cand["color"]
    frame_prefix = FRAME_PREFIX.get(color, "")
    text_prefix = f"text_{frame_prefix}"
    member_ids = {str(f["id"]) for f in cand["members"]}

    # Prefixes for all known frame/shore container elements added by Step11.
    ALL_FRAME_PREFIXES = set(FRAME_PREFIX.values()) | {"red_square", "x_shape"}

    def classify_rect(el):
        eid = el.get("id", "") or ""
        # background → keep
        if eid == "background":
            return "keep"
        for pref in ALL_FRAME_PREFIXES:
            if eid.startswith(pref + "_"):
                suffix = eid[len(pref) + 1:]
                if pref == frame_prefix and suffix in member_ids:
                    return "keep"
                return "drop"
        return "keep"  # unknown rect — keep

    def classify_text(el):
        eid = el.get("id", "") or ""
        for pref in ALL_FRAME_PREFIXES:
            tp = f"text_{pref}"
            if eid.startswith(tp + "_"):
                suffix = eid[len(tp) + 1:]
                if pref == frame_prefix and suffix in member_ids:
                    return "keep"
                return "drop"
        return "keep"

    to_remove = []
    for child in list(root):
        tag = _local(child.tag)
        if tag == "rect" and classify_rect(child) == "drop":
            to_remove.append(child)
        elif tag == "text" and classify_text(child) == "drop":
            to_remove.append(child)
    for el in to_remove:
        root.remove(el)

    # Recolor alum-beam rails outside this group's bbox back to #4e4e4e —
    # they belong to a different group, so they shouldn't read as "alum" in
    # this group's view. Membership uses the unpadded frame bbox + a small
    # tolerance so rails sitting right at the frame edge still count.
    _recolor_out_of_group_rails(root, bounds, pad=ALUM_GROUP_TOL)

    return ET.tostring(root, encoding="unicode")


_XML_DECL = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
_SVG_PREFIX_TAG_RE = re.compile(r"(</?)svg:([A-Za-z][\w-]*)")
_BG_RECT_RE = re.compile(r'\s*<rect\s+id="background"[^/>]*/>\s*', re.IGNORECASE)


def _make_figma_compatible(svg_text: str) -> str:
    """Post-process a cropped SVG so Figma can open it: drop the `svg:` element
    prefix, swap `xmlns:svg` for the default `xmlns`, remove the oversized
    background rect, and prepend an XML declaration if missing."""
    svg_text = _SVG_PREFIX_TAG_RE.sub(r"\1\2", svg_text)
    svg_text = svg_text.replace(
        'xmlns:svg="http://www.w3.org/2000/svg"',
        'xmlns="http://www.w3.org/2000/svg"',
        1,
    )
    svg_text = _BG_RECT_RE.sub("\n", svg_text, count=1)
    if not svg_text.lstrip().startswith("<?xml"):
        svg_text = _XML_DECL + svg_text
    return svg_text



def write_group_svgs(svg_text, kept_groups, groups_dir):
    """Write one cropped SVG per group: groups_dir/G{n}.svg."""
    groups_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for i, cand in enumerate(kept_groups, start=1):
        cropped = crop_svg_to_bounds(svg_text, cand["bounds"], cand)
        cropped = _make_figma_compatible(cropped)
        out_path = groups_dir / f"G{i}.svg"
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(cropped)
            written += 1
        except Exception as e:
            print(f"  ⚠️  Failed to write {out_path}: {e}")
    return written


def run_step16():
    print(f"📦 Step16: grouping same-color frames by shared axis (tol={AXIS_TOLERANCE}px)")

    if not INPUT_SVG.exists():
        print(f"❌ Input SVG not found: {INPUT_SVG}")
        return False

    frames = load_frames()
    if not frames:
        print("⚠️  No frames found — nothing to group")
        return False

    color_counts = {}
    for color, _ in frames:
        color_counts[color] = color_counts.get(color, 0) + 1
    print(f"  Loaded frames: {dict(color_counts)} (total {len(frames)})")

    candidates = build_candidate_groups(frames)
    print(f"  Candidate axis-clusters: {len(candidates)}")

    kept = filter_groups_by_containment(candidates, frames)
    print(f"  After containment filter: {len(kept)} groups")

    kept = filter_overlapping_groups(kept)
    print(f"  After overlap filter: {len(kept)} valid groups")

    # Read input SVG
    try:
        with open(INPUT_SVG, "r", encoding="utf-8") as f:
            svg_text = f.read()
    except Exception as e:
        print(f"❌ Failed to read {INPUT_SVG}: {e}")
        return False

    # Build group rects, sorted for deterministic IDs
    kept_sorted = sorted(
        kept,
        key=lambda c: (c["color"], c["axis"], c["bounds"][1], c["bounds"][0]),
    )
    rect_svgs = []
    group_summary = []
    for i, cand in enumerate(kept_sorted, start=1):
        rect_svgs.append(make_group_rect_svg(cand, i))
        member_ids = sorted(f.get("id") for f in cand["members"])
        group_summary.append({
            "group_id": i,
            "color": cand["color"],
            "axis": cand["axis"],
            "members": member_ids,
            "bounds": {
                "x": cand["bounds"][0],
                "y": cand["bounds"][1],
                "width": cand["bounds"][2] - cand["bounds"][0],
                "height": cand["bounds"][3] - cand["bounds"][1],
            },
        })

    modified = inject_into_svg(svg_text, "\n".join(rect_svgs) + "\n")

    try:
        with open(OUTPUT_SVG, "w", encoding="utf-8") as f:
            f.write(modified)
    except Exception as e:
        print(f"❌ Failed to write {OUTPUT_SVG}: {e}")
        return False

    # Save group data for debugging / downstream use
    out_json = TEMP_DATA / "step16_groups.json"
    try:
        with open(out_json, "w") as f:
            json.dump({"total_groups": len(group_summary), "groups": group_summary}, f, indent=2)
    except Exception as e:
        print(f"  ⚠️  Could not write {out_json}: {e}")

    print(f"✅ Step16 wrote {OUTPUT_SVG.name} with {len(kept_sorted)} white bounding rectangles")

    # Per-group cropped SVGs from the original (uncluttered) source SVG
    written = write_group_svgs(svg_text, kept_sorted, GROUPS_DIR)
    print(f"📁 Wrote {written} cropped group SVGs to {GROUPS_DIR.relative_to(BASE_DIR)}/")
    return True


if __name__ == "__main__":
    run_step16()
