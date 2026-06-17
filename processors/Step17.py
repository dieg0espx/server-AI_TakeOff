#!/usr/bin/env python3
"""
Step17: Find beam call-out bundles in files/groups/G1.svg.

A bundle = a beam-line <text> (e.g. "10'- 4 X 6", "6'- 4X6", "2X2X6")
paired with the spacing-line <text> right below it (e.g. '@ 16" 0/C').

Pairing is done by coordinate proximity (anchor extracted from each <text>'s
`transform="matrix(...)"`).
"""

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
GROUPS_DIR = BASE_DIR / "files" / "groups"
TEMP_DATA = BASE_DIR / "files" / "tempData"
GROUPS_JSON = TEMP_DATA / "step16_groups.json"
TARGET_SVG = GROUPS_DIR / "G1.svg"


def _load_group_bounds():
    """Map G{id}.svg filename → (x_min, y_min, x_max, y_max) of the group's
    frame bounding box (without Step16's viewBox padding). Returns {} if the
    JSON is missing — callers should fall back to viewBox-based filtering."""
    if not GROUPS_JSON.exists():
        return {}
    try:
        with open(GROUPS_JSON, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    out = {}
    for g in data.get("groups", []):
        gid = g.get("group_id")
        b = g.get("bounds") or {}
        if gid is None or not b:
            continue
        out[f"G{gid}.svg"] = (
            b["x"], b["y"], b["x"] + b["width"], b["y"] + b["height"],
        )
    return out

BEAM_RE = re.compile(r"^\s*\d+\s*'?\s*-?\s*\d+\s*[xX]\s*\d+\s*$")
SPACING_RE = re.compile(r'^\s*@\s*\d+(?:\.\d+)?"\s*[0oO]\s*/\s*[Cc]\s*$')
MATRIX_RE = re.compile(
    r"matrix\(\s*([-\d.]+)[,\s]+([-\d.]+)[,\s]+([-\d.]+)[,\s]+([-\d.]+)[,\s]+([-\d.]+)[,\s]+([-\d.]+)\s*\)"
)
FILL_RE = re.compile(r"fill\s*:\s*([^;]+)", re.IGNORECASE)
STROKE_RE = re.compile(r"stroke\s*:\s*([^;]+)", re.IGNORECASE)
BEAM_FILL = "#4e4e4e"  # only count text drawn in this color

# Aluminum beam size palette — stroke color → (size_name, nominal_length, tolerance).
# Mirrors Step11.mark_alum_beams_by_dimension's palette (Step11.py:464-476).
ALUM_BEAM_COLORS = {
    "#a020f0": ("alumBeam20",   1500, 1),
    "#ffd400": ("alumBeam18",   1350, 1),
    "#ffffff": ("alumBeam16",   1201, 1),
    "#1d915c": ("alumBeam14",   1050, 1),
    "#9cff9c": ("alumBeam13",    975, 1),
    "#f54927": ("alumBeam12",    900, 1),
    "#ff6ec7": ("alumBeam11",    825, 1),
    "#ffa805": ("alumBeam10_6",  787, 1),
    "#00c8ff": ("alumBeam10",    750, 1),
    "#b52fc4": ("alumBeam9",     675, 1),
    "#00ffff": ("alumBeam8",     600, 1),
    "#ffbc85": ("alumBeam7",     525, 1),
    "#e6e600": ("alumBeam6",     451, 1),
    "#4084ff": ("alumBeam5",     376, 1),
}

# Empirical thresholds in the beam's *local* text coordinates. Observed
# offset from beam anchor to spacing anchor (in local space) is ~(-38, +70)
# for every orientation, so we accept anything in this small window.
LOCAL_DX_MAX = 80.0   # |local dx| must be within this
LOCAL_DY_MIN = 20.0   # local dy must lie in [LOCAL_DY_MIN, LOCAL_DY_MAX]
LOCAL_DY_MAX = 200.0  # (canonical ~+70)


def _local(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def _matrix(el):
    """Return (a, b, c, d, tx, ty) from transform="matrix(...)" or None."""
    m = MATRIX_RE.search(el.get("transform", ""))
    if not m:
        return None
    return tuple(float(m.group(i)) for i in range(1, 7))


def _anchor(el):
    """Return (tx, ty) world anchor for a <text> element."""
    mx = _matrix(el)
    if mx is not None:
        return mx[4], mx[5]
    try:
        return float(el.get("x", "")), float(el.get("y", ""))
    except ValueError:
        return None


def _fill(el) -> str:
    """Return the element's fill color as a lowercase hex string, or ''."""
    m = FILL_RE.search(el.get("style", ""))
    if m:
        return m.group(1).strip().lower()
    return (el.get("fill") or "").strip().lower()


def _stroke(el) -> str:
    """Return the element's stroke color as a lowercase hex string, or ''."""
    m = STROKE_RE.search(el.get("style", ""))
    if m:
        return m.group(1).strip().lower()
    return (el.get("stroke") or "").strip().lower()


_PATH_START_RE = re.compile(r"\s*[Mm]\s*(-?\d+(?:\.\d+)?)[,\s]+(-?\d+(?:\.\d+)?)")

# Dimension extractors — mirror Step11.has_target_dimension.
_H_ABS_RE = re.compile(r"\bM\s*(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)\s*H\s*(-?\d+(?:\.\d+)?)\b")
_V_ABS_RE = re.compile(r"\bM\s*(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)\s*V\s*(-?\d+(?:\.\d+)?)\b")
_H_REL_RE = re.compile(r"\bm\s*-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?\s*h\s*(-?\d+(?:\.\d+)?)\b")
_V_REL_RE = re.compile(r"\bm\s*-?\d+(?:\.\d+)?,-?\d+(?:\.\d+)?\s*v\s*(-?\d+(?:\.\d+)?)\b")


def _path_start(el):
    """Return the first (x, y) point from a <path>'s `d` attribute."""
    d = el.get("d", "")
    m = _PATH_START_RE.match(d)
    if not m:
        return None
    return float(m.group(1)), float(m.group(2))


def _path_has_dimension(path_d: str, target: float, tolerance: float = 0.0) -> bool:
    """True iff `path_d` contains a horizontal or vertical run whose absolute
    length equals `target` (within `tolerance`). Same rule as Step11."""
    def matches(v):
        return abs(v - target) <= tolerance

    m = _H_ABS_RE.search(path_d)
    if m and matches(abs(float(m.group(3)) - float(m.group(1)))):
        return True
    m = _V_ABS_RE.search(path_d)
    if m and matches(abs(float(m.group(3)) - float(m.group(2)))):
        return True
    m = _H_REL_RE.search(path_d)
    if m and matches(abs(float(m.group(1)))):
        return True
    m = _V_REL_RE.search(path_d)
    if m and matches(abs(float(m.group(1)))):
        return True
    return False


def _world_to_local(mx, wx, wy):
    """Invert the affine matrix(a,b,c,d,tx,ty) and apply to (wx, wy).

    Returns the offset in the beam's local text coordinate frame relative to
    the beam's anchor (since we pass world delta in, tx/ty cancel out — but
    we do the full invert here to keep the function general).
    """
    a, b, c, d, tx, ty = mx
    det = a * d - b * c
    if det == 0:
        return None
    inv_a, inv_b, inv_c, inv_d = d / det, -b / det, -c / det, a / det
    dx_w = wx - tx
    dy_w = wy - ty
    return (inv_a * dx_w + inv_c * dy_w, inv_b * dx_w + inv_d * dy_w)


def _viewbox(root):
    vb = root.get("viewBox", "")
    try:
        x, y, w, h = (float(v) for v in vb.replace(",", " ").split())
        return x, y, w, h
    except ValueError:
        return None


def _apply_matrix(mx, x, y):
    a, b, c, d, tx, ty = mx
    return a * x + c * y + tx, b * x + d * y + ty


def _parent_map(root):
    """Map each element to its parent."""
    return {child: parent for parent in root.iter() for child in parent}


def _to_world(x, y, start_node, parent_of):
    """Walk up `start_node`'s ancestor chain, composing each matrix(...) we
    encounter, to map (x, y) from `start_node`'s local frame into world
    coordinates."""
    node = parent_of.get(start_node)
    while node is not None:
        mx = _matrix(node)
        if mx is not None:
            x, y = _apply_matrix(mx, x, y)
        node = parent_of.get(node)
    return x, y


def _world_anchor(el, parent_of):
    """World-space anchor for a <text> element."""
    anchor = _anchor(el)
    if anchor is None:
        return None
    return _to_world(anchor[0], anchor[1], el, parent_of)


def find_beam_bundles(svg_path: Path):
    tree = ET.parse(svg_path)
    root = tree.getroot()
    vb = _viewbox(root)
    parent_of = _parent_map(root)

    beams, spacings = [], []
    for el in root.iter():
        if _local(el.tag) != "text":
            continue
        if _fill(el) != BEAM_FILL:
            continue  # only count beam call-outs drawn in #4E4E4E
        content = "".join(el.itertext()).strip()
        mx = _matrix(el)
        anchor = _anchor(el)
        if anchor is None:
            continue
        wx, wy = _world_anchor(el, parent_of) or (None, None)
        if vb is not None and wx is not None:
            vx, vy, vw, vh = vb
            if not (vx <= wx <= vx + vw and vy <= wy <= vy + vh):
                continue  # outside the group's cropped viewBox
        rec = {
            "id": el.get("id", ""),
            "text": content,
            "x": anchor[0],
            "y": anchor[1],
            "wx": wx,
            "wy": wy,
            "matrix": mx,
        }
        if BEAM_RE.match(content):
            beams.append(rec)
        elif SPACING_RE.match(content):
            spacings.append(rec)

    # For each beam, find the spacing whose world anchor lies in the beam's
    # local "spacing window". This handles any text rotation uniformly.
    bundles = []
    used = set()
    for beam in beams:
        if beam["matrix"] is None:
            continue
        best, best_score = None, None
        for i, sp in enumerate(spacings):
            if i in used:
                continue
            local = _world_to_local(beam["matrix"], sp["x"], sp["y"])
            if local is None:
                continue
            lx, ly = local
            if abs(lx) > LOCAL_DX_MAX:
                continue
            if not (LOCAL_DY_MIN <= ly <= LOCAL_DY_MAX):
                continue
            score = abs(lx) + abs(ly - 70)  # prefer the canonical offset
            if best is None or score < best_score:
                best, best_score = i, score
        if best is not None:
            used.add(best)
            bundles.append({"beam": beam, "spacing": spacings[best]})

    # Drop duplicate bundles — same beam text + spacing text at the same
    # rounded world anchors (drawings often stamp identical call-outs).
    seen = set()
    deduped = []
    for bn in bundles:
        key = (
            bn["beam"]["text"],
            bn["spacing"]["text"],
            round(bn["beam"]["x"]), round(bn["beam"]["y"]),
            round(bn["spacing"]["x"]), round(bn["spacing"]["y"]),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(bn)
    bundles = deduped

    matched_beam_ids = {bn["beam"]["id"] for bn in bundles}
    unmatched_beams = [b for b in beams if b["id"] not in matched_beam_ids]
    unmatched_spacings = [s for i, s in enumerate(spacings) if i not in used]
    return bundles, unmatched_beams, unmatched_spacings


def _beam_segment(path_d: str, target: float, tol: float):
    """Return ('h'|'v', start_x, start_y, end_x, end_y) for the first
    horizontal/vertical run of length `target` (±tol) in `path_d`, or None.

    Coords are in the path's own local frame."""
    def near(v):
        return abs(v - target) <= tol

    m = _H_ABS_RE.search(path_d)
    if m:
        x1, y1, x2 = float(m.group(1)), float(m.group(2)), float(m.group(3))
        if near(abs(x2 - x1)):
            return ("h", min(x1, x2), y1, max(x1, x2), y1)
    m = _V_ABS_RE.search(path_d)
    if m:
        x1, y1, y2 = float(m.group(1)), float(m.group(2)), float(m.group(3))
        if near(abs(y2 - y1)):
            return ("v", x1, min(y1, y2), x1, max(y1, y2))
    m = _H_REL_RE.search(path_d)
    if m:
        ms = _PATH_START_RE.match(path_d)
        if ms:
            x1, y1 = float(ms.group(1)), float(ms.group(2))
            dx = float(m.group(1))
            if near(abs(dx)):
                return ("h", min(x1, x1 + dx), y1, max(x1, x1 + dx), y1)
    m = _V_REL_RE.search(path_d)
    if m:
        ms = _PATH_START_RE.match(path_d)
        if ms:
            x1, y1 = float(ms.group(1)), float(ms.group(2))
            dy = float(m.group(1))
            if near(abs(dy)):
                return ("v", x1, min(y1, y1 + dy), x1, max(y1, y1 + dy))
    return None


def find_alum_beams(svg_path: Path, group_bbox=None):
    """Find every aluminum-beam <path> in `svg_path` whose stroke matches one
    of the alumBeam palette colors, whose dimension matches the size, whose
    midpoint lies inside the group's frame bbox (or the SVG viewBox as a
    fallback), AND that lines up with at least one other same-size same-
    orientation beam sharing its perpendicular extent (real beams come in
    parallel rails, never alone).

    `group_bbox`: (x_min, y_min, x_max, y_max) of the group's frame bounding
    box (no padding). When given, this is used instead of the viewBox to
    decide which rails are "in the group" — the per-group SVG body still
    contains every path from the source, so the padded viewBox can include
    rails belonging to neighbouring groups.
    """
    tree = ET.parse(svg_path)
    root = tree.getroot()
    vb = _viewbox(root)
    parent_of = _parent_map(root)

    # Membership region: the frame bbox, padded outward so rails sitting just
    # outside the frame edges (a beam's top/bottom rail typically lies right at
    # or just past the frame bounds) still count as part of the group. The pad
    # is much smaller than Step16's viewBox crop padding so we don't accept
    # rails from neighbouring groups.
    GROUP_BBOX_PAD = 40.0
    if group_bbox is not None:
        mx_lo = group_bbox[0] - GROUP_BBOX_PAD
        my_lo = group_bbox[1] - GROUP_BBOX_PAD
        mx_hi = group_bbox[2] + GROUP_BBOX_PAD
        my_hi = group_bbox[3] + GROUP_BBOX_PAD
    elif vb is not None:
        mx_lo, my_lo = vb[0], vb[1]
        mx_hi, my_hi = vb[0] + vb[2], vb[1] + vb[3]
    else:
        mx_lo = my_lo = float("-inf")
        mx_hi = my_hi = float("inf")

    # First pass — color + dimension + WORLD coords. Keep only rails whose
    # midpoint lies inside the membership region (group's frame bbox).
    candidates = []
    for el in root.iter():
        if _local(el.tag) != "path":
            continue
        stroke = _stroke(el)
        if stroke not in ALUM_BEAM_COLORS:
            continue
        size_name, nominal, tol = ALUM_BEAM_COLORS[stroke]
        seg = _beam_segment(el.get("d", ""), nominal, tol)
        if seg is None:
            continue
        orient, lx1, ly1, lx2, ly2 = seg
        wx1, wy1 = _to_world(lx1, ly1, el, parent_of)
        wx2, wy2 = _to_world(lx2, ly2, el, parent_of)
        mx, my = (wx1 + wx2) / 2, (wy1 + wy2) / 2
        if not (mx_lo <= mx <= mx_hi and my_lo <= my <= my_hi):
            continue
        candidates.append({
            "id": el.get("id", ""),
            "size": size_name,
            "nominal": nominal,
            "stroke": stroke,
            "orient": orient,
            "x1": min(wx1, wx2), "y1": min(wy1, wy2),
            "x2": max(wx1, wx2), "y2": max(wy1, wy2),
            "wx": mx, "wy": my,
        })

    # Second pass — merge collinear segments before pairing, then keep only
    # rails that line up with another rail (parallel partner).
    EXTENT_TOL = 2.0
    OFFSET_TOL = 1.0  # ignore essentially-identical duplicate beams as "self"
    MERGE_GAP = 5.0   # collinear segments within this gap are one logical rail

    # Merge collinear same-stroke same-orientation candidates that sit at
    # nearly the same perpendicular coordinate and abut/overlap along the
    # parallel axis. Plans often draw a single rail as several abutting
    # feet-long path segments — without merging, the lineup check sees only
    # short stubs that can't find a partner. We bucket by (orient, stroke)
    # only, then group same-perp segments greedily inside each bucket so a
    # rail and its partner (different perpendicular y/x) stay separate.
    MERGE_PERP_TOL = 1.0  # tighter than EXTENT_TOL so partner rails stay distinct

    def _merge(cands):
        merged = []
        groups = {}
        for c in cands:
            groups.setdefault((c["orient"], c["stroke"]), []).append(c)
        for (orient, _stroke_key), items in groups.items():
            perp_key  = "y1" if orient == "h" else "x1"
            par_start = "x1" if orient == "h" else "y1"
            par_end   = "x2" if orient == "h" else "y2"

            remaining = sorted(items, key=lambda c: (c[perp_key], c[par_start]))
            while remaining:
                seed = remaining.pop(0)
                run = [seed]
                p0 = seed[perp_key]
                # gather collinear segments at perp ~= p0
                keep = []
                for c in remaining:
                    if abs(c[perp_key] - p0) <= MERGE_PERP_TOL:
                        run.append(c)
                    else:
                        keep.append(c)
                remaining = keep
                # sort along parallel axis and merge abutting/overlapping
                run.sort(key=lambda c: c[par_start])
                cur = dict(run[0])
                for c in run[1:]:
                    if c[par_start] <= cur[par_end] + MERGE_GAP:
                        cur[par_end] = max(cur[par_end], c[par_end])
                    else:
                        merged.append(cur)
                        cur = dict(c)
                merged.append(cur)
        return merged

    candidates = _merge(candidates)

    def _overlap(a1, a2, b1, b2):
        """True if [a1,a2] and [b1,b2] overlap by more than EXTENT_TOL."""
        return min(a2, b2) - max(a1, b1) > EXTENT_TOL

    def lines_up(a, b):
        # Same size + orientation + perpendicular-axis offset + overlapping
        # parallel extent. Same-size requirement prevents e.g. a 12' rail from
        # pairing with a stray 13' rail just because their x-extents overlap.
        if a is b:
            return False
        if a["size"] != b["size"]:
            return False
        if a["orient"] != b["orient"]:
            return False
        if a["orient"] == "h":
            if abs(a["y1"] - b["y1"]) < OFFSET_TOL: return False  # same line
            return _overlap(a["x1"], a["x2"], b["x1"], b["x2"])
        else:
            if abs(a["x1"] - b["x1"]) < OFFSET_TOL: return False
            return _overlap(a["y1"], a["y2"], b["y1"], b["y2"])

    # A rail is kept iff some other in-group rail lines up with it. Both rails
    # of a real beam pair belong to the same group's frames — if one is outside
    # the group's bbox, the wood beams stamped between them would land outside
    # the group too. So we require both partners to be in-group; no rescue
    # across the membership boundary.
    hits = []
    for c in candidates:
        if any(lines_up(c, o) for o in candidates):
            hits.append(c)
    return hits


def pair_rails(beams):
    """Pair the lined-up rails into beam *segments*. Two rails are partners
    if they share orientation, are offset on the perpendicular axis, and
    their parallel extents overlap. The paired beam spans only the *shared*
    overlap (so wood beams aren't stamped where one rail doesn't exist)."""
    OVERLAP_TOL = 2.0
    pairs = []
    used = set()
    for i, a in enumerate(beams):
        if i in used:
            continue
        partner = None
        for j, b in enumerate(beams):
            if j == i or j in used:
                continue
            if a["orient"] != b["orient"]:
                continue
            if a["size"] != b["size"]:
                continue  # only pair same-size rails
            if a["orient"] == "v":
                if abs(a["x1"] - b["x1"]) <= 1.0:  # same x → same rail, not partner
                    continue
                if min(a["y2"], b["y2"]) - max(a["y1"], b["y1"]) > OVERLAP_TOL:
                    partner = j; break
            else:
                if abs(a["y1"] - b["y1"]) <= 1.0:
                    continue
                if min(a["x2"], b["x2"]) - max(a["x1"], b["x1"]) > OVERLAP_TOL:
                    partner = j; break
        if partner is None:
            continue
        b = beams[partner]
        used.add(i); used.add(partner)
        if a["orient"] == "v":
            # clip beam to the y-range where BOTH rails exist
            y1 = max(a["y1"], b["y1"])
            y2 = min(a["y2"], b["y2"])
            xL, xR = sorted((a["x1"], b["x1"]))
            pairs.append({
                "orient": "v", "rail_left_x": xL, "rail_right_x": xR,
                "y1": y1, "y2": y2, "length": abs(y2 - y1),
                "size": a["size"], "stroke": a["stroke"],
            })
        else:
            x1 = max(a["x1"], b["x1"])
            x2 = min(a["x2"], b["x2"])
            yT, yB = sorted((a["y1"], b["y1"]))
            pairs.append({
                "orient": "h", "rail_top_y": yT, "rail_bot_y": yB,
                "x1": x1, "x2": x2, "length": abs(x2 - x1),
                "size": a["size"], "stroke": a["stroke"],
            })
    return pairs


def _size_factor_local(size_name: str) -> float:
    # "alumBeam16" → 16.0, "alumBeam10_6" → 10.6
    m = re.search(r"alumBeam([\d_]+)", size_name)
    return float(m.group(1).replace("_", ".")) if m else 0.0


def build_wood_beams(beams, spacing_inches: float, units_per_foot: float | None = None):
    """Generate one line segment per wood beam, perpendicular to each pair of
    aluminum rails, stamped every `spacing_inches` along the run. If
    `units_per_foot` isn't given, derive it from the first paired segment's
    world length / its nominal foot length. Returns world-coord lines."""
    segments = pair_rails(beams)
    if units_per_foot is None:
        units_per_foot = 12.0
        for seg in segments:
            ft = _size_factor_local(seg["size"])
            if ft > 0 and seg["length"] > 0:
                units_per_foot = seg["length"] / ft
                break
    step = (spacing_inches / 12.0) * units_per_foot
    lines = []
    for seg in segments:
        if seg["orient"] == "v":
            xL, xR = seg["rail_left_x"], seg["rail_right_x"]
            y = seg["y1"]
            stop = seg["y2"]
            # Stamp from y to stop in `step` increments (inclusive of start,
            # exclude the very end so we don't double-stamp shared edges).
            while y < stop - 1e-6:
                lines.append((xL, y, xR, y))
                y += step
        else:
            yT, yB = seg["rail_top_y"], seg["rail_bot_y"]
            x = seg["x1"]
            stop = seg["x2"]
            while x < stop - 1e-6:
                lines.append((x, yT, x, yB))
                x += step
    return lines


def draw_wood_beams_on_svg(svg_path: Path, wood_lines, stroke="#FFFF00",
                          stroke_width=4.0, out_path: Path | None = None):
    """Append <line> elements (one per wood beam) to `svg_path` and write to
    `out_path` (defaults to overwriting svg_path)."""
    with open(svg_path, "r", encoding="utf-8") as f:
        text = f.read()
    elems = []
    for (x1, y1, x2, y2) in wood_lines:
        elems.append(
            f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" '
            f'stroke="{stroke}" stroke-width="{stroke_width}" '
            f'stroke-linecap="round" />'
        )
    block = "\n  <!-- Step17 wood beams -->\n  " + "\n  ".join(elems) + "\n"
    new_text = re.sub(r"</svg\s*>\s*$", block + "</svg>\n", text, count=1)
    target = out_path or svg_path
    with open(target, "w", encoding="utf-8") as f:
        f.write(new_text)
    return target


_SPACING_INCHES_RE = re.compile(r'@\s*(\d+(?:\.\d+)?)\s*"')


def _size_factor(size_name: str) -> float:
    # "alumBeam16" → 16.0, "alumBeam10_6" → 10.6
    m = re.search(r"alumBeam([\d_]+)", size_name)
    return float(m.group(1).replace("_", ".")) if m else 0.0


def process_group(svg_path: Path, group_bbox=None):
    """Run the full Step17 pipeline on one G*.svg file.

    `group_bbox`: optional (x_min, y_min, x_max, y_max) of the group's frame
    bounding box (no padding). Used to restrict wood-beam placement to rails
    that actually belong to this group rather than every rail visible in the
    padded viewBox.

    Returns a dict with: bundles, alum_beams, beam_length_ft, spacing_inches,
    wood_count, wood_svg_path."""
    try:
        bundles, _ub, _us = find_beam_bundles(svg_path)
    except ET.ParseError as e:
        print(f"  ⚠️  {svg_path.name}: parse failed — {e}")
        return None

    alum = find_alum_beams(svg_path, group_bbox=group_bbox)
    # Convert each rail's world-coord extent into feet using units-per-foot
    # derived from the rail itself (extent / nominal_ft). Halve the sum to
    # count beam-feet (two parallel rails per physical beam). This is robust
    # to merging short collinear segments.
    total_ft = 0.0
    for h in alum:
        extent = (h["x2"] - h["x1"]) if h["orient"] == "h" else (h["y2"] - h["y1"])
        nom_ft = _size_factor(h["size"])
        if nom_ft <= 0:
            continue
        # Each rail's painted extent is some multiple of its nominal-foot
        # length (the merged rail can be N feet long). Divide by the size's
        # own per-foot factor (extent_of_one_foot ≈ extent / nom_ft for the
        # canonical stub, but here we just trust the world extent directly
        # with the canonical upf=12 derived from this pipeline's transforms).
        total_ft += extent / 12.0
    beam_length_ft = total_ft / 2

    spacing_counts = {}
    for bn in bundles:
        m = _SPACING_INCHES_RE.search(bn["spacing"]["text"])
        if not m:
            continue
        inches = float(m.group(1))
        spacing_counts[inches] = spacing_counts.get(inches, 0) + 1

    dominant_inches = None
    wood_lines = []
    wood_svg_path = None
    if spacing_counts and beam_length_ft > 0:
        dominant_inches = max(spacing_counts, key=spacing_counts.get)
        wood_lines = build_wood_beams(alum, dominant_inches)
        wood_svg_path = svg_path.parent / (svg_path.stem + "_wood.svg")
        draw_wood_beams_on_svg(svg_path, wood_lines,
                               stroke="#FFFF00", stroke_width=4.0,
                               out_path=wood_svg_path)

    return {
        "file": svg_path.name,
        "bundles": bundles,
        "alum_beams": alum,
        "beam_length_ft": beam_length_ft,
        "spacing_counts": spacing_counts,
        "spacing_inches": dominant_inches,
        "wood_count": len(wood_lines),
        "wood_svg_path": wood_svg_path,
    }


def run_step17():
    svg_files = sorted(GROUPS_DIR.glob("G*.svg"))
    # Skip already-generated _wood.svg outputs from prior runs
    svg_files = [p for p in svg_files if not p.stem.endswith("_wood")]

    if not svg_files:
        print(f"❌ No G*.svg files found in {GROUPS_DIR}")
        return False

    group_bounds = _load_group_bounds()
    if not group_bounds:
        print("⚠️  step16_groups.json not found — falling back to viewBox membership")

    print(f"🔎 Step17: processing {len(svg_files)} group SVG(s) in {GROUPS_DIR.relative_to(BASE_DIR)}")
    print(f"{'file':<10} {'bundles':>8} {'alum_rails':>11} {'alum_ft':>9} {'spacing':>9} {'wood':>6}  output")
    print("-" * 78)

    totals = {"bundles": 0, "rails": 0, "ft": 0.0, "wood": 0}
    for svg_path in svg_files:
        r = process_group(svg_path, group_bbox=group_bounds.get(svg_path.name))
        if r is None:
            continue
        spacing_str = f'{r["spacing_inches"]:g}"' if r["spacing_inches"] else "-"
        out_str = r["wood_svg_path"].relative_to(BASE_DIR) if r["wood_svg_path"] else "-"
        print(
            f"{r['file']:<10} {len(r['bundles']):>8} {len(r['alum_beams']):>11} "
            f"{r['beam_length_ft']:>9.2f} {spacing_str:>9} {r['wood_count']:>6}  {out_str}"
        )
        totals["bundles"] += len(r["bundles"])
        totals["rails"] += len(r["alum_beams"])
        totals["ft"] += r["beam_length_ft"]
        totals["wood"] += r["wood_count"]

    print("-" * 78)
    print(
        f"{'TOTAL':<10} {totals['bundles']:>8} {totals['rails']:>11} "
        f"{totals['ft']:>9.2f} {'':>9} {totals['wood']:>6}"
    )
    return True


if __name__ == "__main__":
    run_step17()
