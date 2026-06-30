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
# Captures the leading foot value from a beam call-out like "12'- 4 X 6" or
# "5'- 4X6" → 12, 5. Used to determine the per-beam length (in feet) for
# the wood-beam size split.
_BEAM_SIZE_FT_RE = re.compile(r"^\s*(\d+)\s*'?\s*-?\s*\d+\s*[xX]\s*\d+\s*$")
SPACING_RE = re.compile(r'^\s*@\s*\d+(?:\.\d+)?"\s*[0oO]\s*/\s*[Cc]\s*$')
MATRIX_RE = re.compile(
    r"matrix\(\s*([-\d.]+)[,\s]+([-\d.]+)[,\s]+([-\d.]+)[,\s]+([-\d.]+)[,\s]+([-\d.]+)[,\s]+([-\d.]+)\s*\)"
)
FILL_RE = re.compile(r"fill\s*:\s*([^;]+)", re.IGNORECASE)
STROKE_RE = re.compile(r"stroke\s*:\s*([^;]+)", re.IGNORECASE)
BEAM_FILL = "#4e4e4e"  # original bundle-text color on first-run input
# Bundle text colors accepted by find_beam_bundles. After Step17 runs once,
# bundle text gets recolored to #ffffff by _recolor_text_white, so subsequent
# runs must also accept white as a valid bundle color.
BEAM_FILL_COLORS = {"#4e4e4e", "#ffffff"}

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


_GREEN_RECT_RE = re.compile(
    r'<(?:[\w-]+:)?rect\b[^>]*\bid\s*=\s*"green_container_[^"]*"[^>]*'
    r'x\s*=\s*"([-\d.]+)"[^>]*y\s*=\s*"([-\d.]+)"[^>]*'
    r'width\s*=\s*"([-\d.]+)"[^>]*height\s*=\s*"([-\d.]+)"',
    re.DOTALL,
)


def _find_green_containers(svg_path: Path):
    """Return a list of (x, y, w, h) for every Step15 frame-container rect
    (id="green_container_*", stroke:#70ff00) in the SVG. Used as a
    rail-less fallback in process_group — each container becomes its own
    little run that wood beams get stamped across."""
    try:
        with open(svg_path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return []
    return [
        (float(m.group(1)), float(m.group(2)),
         float(m.group(3)), float(m.group(4)))
        for m in _GREEN_RECT_RE.finditer(text)
    ]


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
        if _fill(el) not in BEAM_FILL_COLORS:
            continue  # only count beam call-outs (#4E4E4E on first run, #FFFFFF after recolor)
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

    # Membership region: the frame bbox + a small pad. The pad must be just
    # large enough to catch rails sitting right at a frame edge but small
    # enough to exclude rails belonging to the neighbouring group (e.g. for
    # frame groups packed close together with a ~35 px gap, pad ≤ 17).
    GROUP_BBOX_PAD = 15.0
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


def pair_rails(beams, canonical_perp=None):
    """Pair the lined-up rails into beam *segments*. Two rails are partners
    if they share orientation, are offset on the perpendicular axis, and
    their parallel extents overlap. The paired beam spans only the *shared*
    overlap (so wood beams aren't stamped where one rail doesn't exist).

    A rail CAN appear in more than one pair (as the shared middle rail of two
    stacked beams). What we forbid is reusing the same UNORDERED pair (i, j).

    `canonical_perp`: optional {(orient, size): expected_perp_distance} from
    the pipeline-wide first pass. If this group's own rail population
    suggests a different canonical (mode of adjacent perps among same-size
    rails), we use the local one instead — supports stacked beam patterns
    that don't match the drawing's dominant gap.
    """
    OVERLAP_TOL = 2.0
    PERP_REL_TOL = 0.20  # 20% over canonical is the most we accept

    def _ext(r):
        return (r["y2"] - r["y1"]) if r["orient"] == "v" else (r["x2"] - r["x1"])

    effective_canon = dict(canonical_perp or {})

    def _perp_coord(r):
        return r["x1"] if r["orient"] == "v" else r["y1"]

    # Per-group canonical *fallback*: if the global canonical disqualifies
    # every candidate pair for some (orient, size) present in this group,
    # try the largest distinct local gap as a fallback canonical. This
    # rescues groups whose physical rail spacing genuinely differs from the
    # drawing's mode (e.g. a 48"-spaced pair in a drawing where most pairs
    # are 84"). We pick the *largest* gap rather than the mode because
    # small gaps are usually intra-beam rail thickness, not pair spacing.
    rails_by_key = {}
    for r in beams:
        rails_by_key.setdefault((r["orient"], r["size"]), []).append(r)
    for key, rs in rails_by_key.items():
        global_canon = effective_canon.get(key)
        if global_canon is None:
            continue
        # Would any candidate pair pass the global canonical's ±band?
        coords = sorted({round(_perp_coord(r), 3) for r in rs})
        if len(coords) < 2:
            continue
        # All pairwise (not just adjacent) gaps — pair_rails enumerates all.
        pair_gaps = [round(coords[j] - coords[i])
                     for i in range(len(coords))
                     for j in range(i+1, len(coords))
                     if coords[j] - coords[i] > 1.0]
        if not pair_gaps:
            continue
        passes = [g for g in pair_gaps
                  if g <= global_canon * 1.20 and g >= global_canon * 0.75]
        if passes:
            continue  # global canonical works for this group
        # No pair passes the global. Use the largest local gap as a fallback
        # — that's the most likely real pair spacing here (small gaps are
        # usually the rail thickness within one beam, not a pair gap).
        effective_canon[key] = float(max(pair_gaps))

    # "Stubs" — rails much shorter than their peers — get filtered out before
    # pairing. They're usually fragments of a neighbour group bleeding into
    # our viewBox; pairing one with a long real rail produces a wrong-perp
    # pair (G24 case). Threshold: 40% of the longest same-(orient,size) rail.
    STUB_REL = 0.4
    max_ext_by_key = {}
    for r in beams:
        k = (r["orient"], r["size"])
        max_ext_by_key[k] = max(max_ext_by_key.get(k, 0.0), _ext(r))

    # Enumerate every valid (i, j) candidate with its score, then greedily
    # pick the best ones first, allowing each rail to participate in multiple
    # pairs but forbidding the same UNORDERED pair twice.
    candidates = []  # list of (score, i, j, perp)
    for i, a in enumerate(beams):
        for j in range(i + 1, len(beams)):
            b = beams[j]
            if a["orient"] != b["orient"]:
                continue
            if a["size"] != b["size"]:
                continue
            if a["orient"] == "v":
                perp = abs(a["x1"] - b["x1"])
                if perp <= 1.0:
                    continue
                if min(a["y2"], b["y2"]) - max(a["y1"], b["y1"]) <= OVERLAP_TOL:
                    continue
            else:
                perp = abs(a["y1"] - b["y1"])
                if perp <= 1.0:
                    continue
                if min(a["x2"], b["x2"]) - max(a["x1"], b["x1"]) <= OVERLAP_TOL:
                    continue
            canon = effective_canon.get((a["orient"], a["size"]))
            if canon is not None:
                # Reject perps significantly larger than the canonical — they
                # span across a real pair, not adjacent to it.
                if perp > canon * (1.0 + PERP_REL_TOL):
                    continue
                # Reject perps significantly smaller than the canonical — a
                # pair gap that's e.g. 36 or 48 when the canon is 84 is two
                # rails of one *side* of a wider stack, not a real rail pair.
                if perp < canon * 0.75:
                    continue
                score = (abs(perp - canon), abs(_ext(a) - _ext(b)))
            else:
                score = (abs(_ext(a) - _ext(b)), perp)

            # Skip stub-with-long mismatched pairs (G24-style).
            max_ext = max_ext_by_key[(a["orient"], a["size"])]
            if max_ext > 0:
                a_rel = _ext(a) / max_ext
                b_rel = _ext(b) / max_ext
                if min(a_rel, b_rel) < STUB_REL and max(a_rel, b_rel) > STUB_REL:
                    continue

            candidates.append((score, i, j, perp))

    # Sort by score (closest-to-canonical) so the best pairs claim rails
    # first. Each rail is used in at most one pair (MAX_USES=1), so the
    # remaining candidates with the same rail are dropped automatically.
    candidates.sort(key=lambda c: c[0])

    pairs = []
    seen = set()  # (i, j) already paired
    # A rail can be used in multiple pairs, but limit to 2 pair-partners to
    # avoid runaway when an alum-color smudge has many neighbors.
    use_count = {}
    # Each rail belongs to at most one pair. Stacked pairs sharing a middle
    # rail are intentionally not supported — the field's wood-beam pattern
    # doesn't physically share rails between two beams; that would require
    # the middle "rail" to be a real shared beam piece, which it never is.
    MAX_USES = 1

    # Track each rail's perpendicular coordinate so we can detect "spanning"
    # pairs that cross over an already-paired middle rail.
    def _perp_coord(r):
        return r["x1"] if r["orient"] == "v" else r["y1"]
    perp_coords = {idx: _perp_coord(beams[idx]) for idx in range(len(beams))}

    paired_with = {}  # idx → set of partner idxs

    for score, i, j, perp in candidates:
        key = (i, j)
        if key in seen:
            continue
        if use_count.get(i, 0) >= MAX_USES or use_count.get(j, 0) >= MAX_USES:
            continue
        # Reject pairs that span over an already-paired neighbor (the
        # "outer rail pair across a 3-rail stack" mistake). i.e. if there is
        # any rail k whose perp coord is strictly between i and j and whose
        # orientation/size match, and k is already in some pair, then (i, j)
        # would cross over a real beam — drop it.
        pi, pj = perp_coords[i], perp_coords[j]
        p_lo, p_hi = min(pi, pj), max(pi, pj)
        spans_existing = False
        for k, pk in perp_coords.items():
            if k == i or k == j:
                continue
            if p_lo + 1.0 < pk < p_hi - 1.0:
                if (beams[k]["orient"] == beams[i]["orient"]
                        and beams[k]["size"] == beams[i]["size"]
                        and paired_with.get(k)):
                    spans_existing = True
                    break
        if spans_existing:
            continue

        seen.add(key)
        use_count[i] = use_count.get(i, 0) + 1
        use_count[j] = use_count.get(j, 0) + 1
        paired_with.setdefault(i, set()).add(j)
        paired_with.setdefault(j, set()).add(i)
        a, b = beams[i], beams[j]
        if a["orient"] == "v":
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


def build_wood_beams(beams, spacing_inches: float, units_per_foot: float | None = None,
                     group_bbox=None, canonical_perp=None,
                     pre_segments=None):
    """Generate one line segment per 4x6 wood beam, perpendicular to each
    pair of aluminum rails. `spacing_inches` is the *clear gap* between
    adjacent beam faces (e.g. 16, 19.2); each beam is 4" thick. The number
    of beams that fit along a run of length W is:
        N = floor((W + gap) / (beamThickness + gap))
    so the first/last beam sit flush with the run start/end and only N-1
    gaps live between them. If `units_per_foot` isn't given, defaults to
    12 — the drawing-wide pipeline constant (1 SVG unit = 1 inch). Earlier
    versions derived upf from rail extent / nominal_ft, but that breaks
    when rails are merged across multiple physical beams (e.g. G23's
    "alumBeam14" rail is 42 ft long, painted as one merged extent).

    `group_bbox` (x_min, y_min, x_max, y_max): if given, extend each pair's
    parallel extent to the bbox so wood beams cover the entire group, not
    just the short stretch where both rails were physically drawn. Real
    drawings sometimes show alum rails only over part of a frame run; the
    wood-beam pattern in the field still spans every frame.

    `pre_segments`: optional list of synthetic segment dicts (same shape
    `pair_rails` returns) — used by groups that have bundle call-outs but
    no aluminum rails (e.g. G22), where we build a rail-less synthetic run
    upstream and want to skip pairing entirely.

    Returns world-coord lines."""
    if pre_segments is not None:
        segments = list(pre_segments)
    else:
        segments = pair_rails(beams, canonical_perp=canonical_perp)
    if units_per_foot is None:
        units_per_foot = 12.0
    # spacing_inches is the clear gap between adjacent 4x6 wood beams.
    # N beams of 4" thickness with N-1 gaps fit when:
    #   N = floor((totalWidth + gap) / (beamThickness + gap))
    beam_thickness_in = 4.0
    gap_in = spacing_inches
    beam_thickness = (beam_thickness_in / 12.0) * units_per_foot
    gap = (gap_in / 12.0) * units_per_foot
    pitch = beam_thickness + gap  # center-to-center stride

    def _stamp_run(run_start, run_stop, center_start=None, center_stop=None):
        """Return beam-center coords for a wood-beam pattern.

        `run_start`/`run_stop`: the physical rail extent — used to count
        how many beams fit via N = floor((W + gap) / (beam + gap)).

        `center_start`/`center_stop`: optional centering span — when given,
        the N-beam pattern is centered within [center_start, center_stop]
        instead of within [run_start, run_stop]. This is used to center
        the stack inside the group bbox even when the rails are offset
        within the bbox (e.g. G1 has rails biased to the bottom of its
        bbox; centering on the bbox makes the wood beams sit visually
        centered)."""
        total_width = run_stop - run_start
        if total_width < beam_thickness:
            return []
        n = int((total_width + gap) // pitch)
        if n <= 0:
            return []
        used = n * beam_thickness + (n - 1) * gap
        cs = center_start if center_start is not None else run_start
        ce = center_stop if center_stop is not None else run_stop
        center_width = ce - cs
        slack = center_width - used
        # If the centering span is narrower than the pattern, fall back to
        # rail-extent centering (don't squeeze the beams inside a too-small
        # bbox).
        if slack < 0:
            cs = run_start
            slack = max(0.0, total_width - used)
        offset = slack / 2.0
        centers = []
        c = cs + offset + beam_thickness / 2.0
        for _ in range(n):
            centers.append(c)
            c += pitch
        return centers

    # Merge pairs that lie on the same rail lines into a single "run". Two
    # pairs sharing rail lines come in two flavors:
    #   (a) Overlapping parallel extent (e.g. G1's top + bottom rail pairs
    #       at the same x's) — stamping each pair separately would emit
    #       duplicate wood beams. We keep just one, with the union extent.
    #   (b) Disjoint parallel extent of *different beam sizes* (e.g. G29's
    #       alumBeam14 + alumBeam8 end-to-end at the same y's) — same
    #       physical run, just two aluminum sizes concatenated. We merge
    #       into one segment whose extent is the union, so wood beams are
    #       computed once across the whole run (avoids both gaps where the
    #       sizes meet and duplicate stamps if treated as two runs).
    # Skip merging when caller supplied pre_segments — those are independent
    # synthetic runs (e.g. G22's green containers) that happen to share
    # rail-y coords but represent physically distinct frames.
    if group_bbox is not None and pre_segments is None:
        merged = []
        for seg in segments:
            if seg["orient"] == "v":
                rail_key = ("v",
                            round(seg["rail_left_x"], 1),
                            round(seg["rail_right_x"], 1))
                lo, hi = seg["y1"], seg["y2"]
            else:
                rail_key = ("h",
                            round(seg["rail_top_y"], 1),
                            round(seg["rail_bot_y"], 1))
                lo, hi = seg["x1"], seg["x2"]
            absorbed = False
            for prev in merged:
                if prev["orient"] == "v":
                    prev_rail = ("v",
                                 round(prev["rail_left_x"], 1),
                                 round(prev["rail_right_x"], 1))
                else:
                    prev_rail = ("h",
                                 round(prev["rail_top_y"], 1),
                                 round(prev["rail_bot_y"], 1))
                if prev_rail != rail_key:
                    continue
                # Same rail lines — merge into a single run with the union
                # of parallel extents.
                if seg["orient"] == "v":
                    prev["y1"] = min(prev["y1"], lo)
                    prev["y2"] = max(prev["y2"], hi)
                else:
                    prev["x1"] = min(prev["x1"], lo)
                    prev["x2"] = max(prev["x2"], hi)
                absorbed = True
                break
            if not absorbed:
                merged.append(dict(seg))
        segments = merged

    # When using pre_segments (rail-less synthesis from green containers),
    # each segment is its own self-contained run and should center *within*
    # itself rather than across the full bbox.
    use_bbox_centering = (group_bbox is not None and pre_segments is None)

    lines = []
    for seg in segments:
        # The rail-run length determines how MANY beams fit; the group bbox
        # (when given for real rail-based segments) determines WHERE the
        # pattern sits, so the wood-beam stack ends up visually centered in
        # the group even when the rails are biased toward one end of the
        # bbox (e.g. G1's rails span y=213..921 inside a bbox y=163..925 —
        # centering on the rails alone would leave a huge gap at the top
        # of the bbox).
        if seg["orient"] == "v":
            xL, xR = seg["rail_left_x"], seg["rail_right_x"]
            y_start = seg["y1"]
            y_stop = seg["y2"]
            center_start = group_bbox[1] if use_bbox_centering else None
            center_stop = group_bbox[3] if use_bbox_centering else None
            for y in _stamp_run(y_start, y_stop, center_start, center_stop):
                lines.append((xL, y, xR, y))
        else:
            yT, yB = seg["rail_top_y"], seg["rail_bot_y"]
            x_start = seg["x1"]
            x_stop = seg["x2"]
            center_start = group_bbox[0] if use_bbox_centering else None
            center_stop = group_bbox[2] if use_bbox_centering else None
            for x in _stamp_run(x_start, x_stop, center_start, center_stop):
                lines.append((x, yT, x, yB))
    return lines


_SVG_OPEN_RE = re.compile(r"<(?:([\w-]+):)?svg\b[^>]*>", re.DOTALL)
_SVG_CLOSE_RE = re.compile(r"</(?:([\w-]+):)?svg\s*>\s*$")
_VIEWBOX_ATTR_RE = re.compile(
    r'viewBox\s*=\s*"\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*"'
)


def draw_wood_beams_on_svg(svg_path: Path, wood_lines, stroke="#FFFF00",
                          stroke_width=4.0, out_path: Path | None = None,
                          sizes_split=None):
    """Append <line> elements (one per wood beam) plus a count badge to
    `svg_path` and write to `out_path` (defaults to overwriting svg_path).
    The emitted elements use the same namespace prefix as the source <svg>
    root, so viewers render them inside the SVG namespace.

    The badge is a yellow rect with black text placed in the bottom-right
    of the SVG's viewBox. When `sizes_split` is given as a list of
    (size_ft, count) pairs, the badge renders one line per size
    (e.g. "16x 10'-4x6\n15x 12'-4x6"); otherwise it falls back to
    "Nx 4x6"."""
    with open(svg_path, "r", encoding="utf-8") as f:
        text = f.read()

    open_m = _SVG_OPEN_RE.search(text)
    close_m = _SVG_CLOSE_RE.search(text)
    if close_m is None:
        raise ValueError(f"{svg_path.name}: closing </svg> tag not found")
    prefix = open_m.group(1) if open_m else None
    line_tag = f"{prefix}:line" if prefix else "line"
    rect_tag = f"{prefix}:rect" if prefix else "rect"
    text_tag = f"{prefix}:text" if prefix else "text"
    tspan_tag = f"{prefix}:tspan" if prefix else "tspan"

    elems = []
    for (x1, y1, x2, y2) in wood_lines:
        elems.append(
            f'<{line_tag} x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" '
            f'stroke="{stroke}" stroke-width="{stroke_width}" '
            f'stroke-linecap="round" />'
        )

    badge = ""
    vb_m = _VIEWBOX_ATTR_RE.search(open_m.group(0)) if open_m else None
    if vb_m:
        vx, vy, vw, vh = (float(vb_m.group(i)) for i in range(1, 5))

        # Build the badge label lines from sizes_split, or fall back to the
        # one-line "Nx 4x6" form.
        if sizes_split:
            lines_txt = [
                f"{cnt}x {ft}'-4x6" if ft is not None else f"{cnt}x 4x6"
                for (ft, cnt) in sizes_split
            ]
        else:
            lines_txt = [f"{len(wood_lines)}x 4x6"]
        longest = max((len(s) for s in lines_txt), default=0)
        n_lines = len(lines_txt)

        # Sizing: clamp font size so the badge fits within both viewBox
        # width AND height. Width: ~0.6em-per-char Arial + 1.2em padding
        # + 0.4em outer margin → font_size ≤ vw / (0.6*longest + 1.6).
        # Height: N lines + 0.6em padding + 0.4em margin → font_size ≤
        # vh / (1.2 * N_lines + 1.0).
        line_height_factor = 1.2  # em per line
        char_factor = 0.6 * longest + 1.6
        max_font_by_width = vw / char_factor if char_factor > 0 else 24.0
        max_font_by_height = vh / (line_height_factor * n_lines + 1.0)
        font_size = min(max_font_by_height, 24.0, max_font_by_width)
        font_size = max(4.0, font_size)  # don't shrink below readable floor
        pad_x = font_size * 0.6
        pad_y = font_size * 0.3
        text_w = font_size * 0.6 * longest
        text_h = font_size * line_height_factor * n_lines
        box_w = text_w + 2 * pad_x
        box_h = text_h + 2 * pad_y
        margin = font_size * 0.4
        # Right-align inside viewBox; if it would still overflow (very narrow
        # group), pin the badge to the right edge with zero margin.
        box_x = vx + vw - box_w - margin
        if box_x < vx:
            box_x = vx + max(0.0, vw - box_w)
        box_y = vy + vh - box_h - margin
        if box_y < vy:
            box_y = vy + max(0.0, vh - box_h)
        text_x = box_x + box_w / 2.0
        # First line baseline (central-aligned for each line individually):
        # vertical center of the first line is box_y + pad_y + 0.5*line_height.
        line_height = font_size * line_height_factor
        first_line_cy = box_y + pad_y + line_height / 2.0
        tspans = []
        for i, s in enumerate(lines_txt):
            cy = first_line_cy + i * line_height
            tspans.append(
                f'<{tspan_tag} x="{text_x:.2f}" y="{cy:.2f}">{s}</{tspan_tag}>'
            )
        badge = (
            f'\n  <{rect_tag} x="{box_x:.2f}" y="{box_y:.2f}" '
            f'width="{box_w:.2f}" height="{box_h:.2f}" '
            f'fill="#FFFF00" stroke="#000000" stroke-width="1" />'
            f'\n  <{text_tag} font-family="Arial" font-size="{font_size:.2f}" '
            f'font-weight="bold" fill="#000000" '
            f'text-anchor="middle" dominant-baseline="central">'
            + "".join(tspans) + f'</{text_tag}>'
        )

    block = ("\n  <!-- Step17 wood beams -->\n  "
             + "\n  ".join(elems)
             + badge
             + "\n")
    new_text = text[:close_m.start()] + block + close_m.group(0).lstrip() + "\n"
    target = out_path or svg_path
    with open(target, "w", encoding="utf-8") as f:
        f.write(new_text)
    return target


_SPACING_INCHES_RE = re.compile(r'@\s*(\d+(?:\.\d+)?)\s*"')


def _size_factor(size_name: str) -> float:
    # "alumBeam16" → 16.0, "alumBeam10_6" → 10.6
    m = re.search(r"alumBeam([\d_]+)", size_name)
    return float(m.group(1).replace("_", ".")) if m else 0.0


def process_group(svg_path: Path, group_bbox=None, canonical_perp=None,
                   default_spacing_inches=None, default_sizes_ft=None):
    """Run the full Step17 pipeline on one G*.svg file.

    `group_bbox`: optional (x_min, y_min, x_max, y_max) of the group's frame
    bounding box (no padding). Used to restrict wood-beam placement to rails
    that actually belong to this group rather than every rail visible in the
    padded viewBox.

    `default_spacing_inches`: optional fallback spacing (e.g. 19.2) used
    when this group's own viewBox contains no beam call-out bundles. Small
    detail groups often have rails but no local bundle text, since the
    call-outs sit elsewhere on the parent drawing.

    `default_sizes_ft`: optional fallback list of beam lengths in feet
    (e.g. [10]) used when the group has no local bundles to determine the
    physical 4x6 size. Same rationale as `default_spacing_inches`.

    Returns a dict with: bundles, alum_beams, beam_length_ft, spacing_inches,
    sizes_split, wood_count, wood_svg_path. `sizes_split` is a list of
    (size_ft, count) pairs summing to wood_count — when the group's
    bundles mention more than one beam size, the total wood-beam count is
    split as evenly as possible across them."""
    try:
        bundles, _ub, _us = find_beam_bundles(svg_path)
    except ET.ParseError as e:
        print(f"  ⚠️  {svg_path.name}: parse failed — {e}")
        return None

    alum = find_alum_beams(svg_path, group_bbox=group_bbox)

    # A real frame group has wood beams of a single orientation. The
    # dominant orientation+size is the one with the most painted extent,
    # but a single physical run may concatenate different aluminum sizes
    # end-to-end (e.g. G29: alumBeam14 + alumBeam8 sharing the same rail
    # lines). Keep all rails that lie on the dominant rail lines (same
    # perpendicular coord and same orientation), regardless of size, so
    # the run's true extent is recovered.
    def _dominant(rails):
        if not rails:
            return rails
        weight = {}
        for r in rails:
            extent = (r["x2"] - r["x1"]) if r["orient"] == "h" else (r["y2"] - r["y1"])
            key = (r["orient"], r["size"])
            weight[key] = weight.get(key, 0.0) + extent
        best_orient, _best_size = max(weight, key=weight.get)
        # Collect the perpendicular coords of every rail of the dominant
        # size — those are the "rail lines" of the physical pair.
        def _perp(r):
            return r["y1"] if r["orient"] == "h" else r["x1"]
        dom_lines = {round(_perp(r), 1)
                     for r in rails if (r["orient"], r["size"]) == (best_orient, _best_size)}
        # Include any rail sharing one of those perpendicular coords (±1 tol)
        # AND the same orientation, regardless of its own size.
        out = []
        for r in rails:
            if r["orient"] != best_orient:
                continue
            if any(abs(round(_perp(r), 1) - line) <= 1.0 for line in dom_lines):
                out.append(r)
        return out

    alum = _dominant(alum)

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
    # Pick the spacing: when the group's bundles call out a single spacing
    # we use it directly; when they call out multiple (e.g. G16 has both
    # 12" and 19.2"), we use the AVERAGE of the distinct values as a single
    # effective spacing so the wood-beam pattern blends both. Falls back to
    # the drawing-wide default for groups with no local bundles (G29 etc.).
    if spacing_counts:
        distinct_spacings = list(spacing_counts.keys())
        dominant_inches = sum(distinct_spacings) / len(distinct_spacings)
    elif default_spacing_inches is not None:
        dominant_inches = default_spacing_inches

    # Determine the 4x6 sizes mentioned by THIS group's bundles. Preserve
    # the first-seen order so the split is deterministic.
    local_sizes = []
    seen_sizes = set()
    for bn in bundles:
        m = _BEAM_SIZE_FT_RE.match(bn["beam"]["text"].strip())
        if not m:
            continue
        ft = int(m.group(1))
        if ft not in seen_sizes:
            seen_sizes.add(ft)
            local_sizes.append(ft)
    if not local_sizes and default_sizes_ft:
        local_sizes = list(default_sizes_ft)

    sizes_split = []
    # Fallback synthesis: groups whose bundles call out beams but Step11
    # painted no aluminum rails for them (e.g. G22). When the group SVG
    # contains green-stroked frame "container" rects (Step15's frame
    # markers, stroke:#70ff00), we treat each container as its own little
    # rail-bounded run and stamp wood beams across each. Otherwise fall
    # back to using the bundle beam-size sum + group bbox as a single run.
    synthetic_segments = None
    if (dominant_inches is not None
            and beam_length_ft <= 0
            and bundles
            and group_bbox is not None):
        containers = _find_green_containers(svg_path)
        if containers:
            # One segment per container. Orientation = container aspect
            # (wider → horizontal, else vertical). The container's
            # perpendicular edges play the role of rails; its parallel
            # edges define the run start/stop.
            synthetic_segments = []
            for cx, cy, cw, ch in containers:
                if cw >= ch:
                    synthetic_segments.append({
                        "orient": "h",
                        "rail_top_y": cy,
                        "rail_bot_y": cy + ch,
                        "x1": cx,
                        "x2": cx + cw,
                        "length": cw,
                        "size": "synthetic",
                        "stroke": "#000000",
                    })
                else:
                    synthetic_segments.append({
                        "orient": "v",
                        "rail_left_x": cx,
                        "rail_right_x": cx + cw,
                        "y1": cy,
                        "y2": cy + ch,
                        "length": ch,
                        "size": "synthetic",
                        "stroke": "#000000",
                    })
            beam_length_ft = sum(s["length"] for s in synthetic_segments) / 12.0
        else:
            # No containers — synthesize a single run from bundle-ft sum,
            # centered in the bbox along the longer axis.
            bundle_ft_sum = 0
            for bn in bundles:
                mft = _BEAM_SIZE_FT_RE.match(bn["beam"]["text"].strip())
                if mft:
                    bundle_ft_sum += int(mft.group(1))
            if bundle_ft_sum > 0:
                upf = 12.0
                run_units = bundle_ft_sum * upf
                bx0, by0, bx2, by2 = group_bbox
                bw = bx2 - bx0
                bh = by2 - by0
                if bw >= bh:
                    run_start = bx0 + max(0.0, (bw - run_units) / 2.0)
                    run_stop = run_start + min(run_units, bw)
                    synthetic_segments = [{
                        "orient": "h",
                        "rail_top_y": by0,
                        "rail_bot_y": by2,
                        "x1": run_start,
                        "x2": run_stop,
                        "length": run_stop - run_start,
                        "size": "synthetic",
                        "stroke": "#000000",
                    }]
                else:
                    run_start = by0 + max(0.0, (bh - run_units) / 2.0)
                    run_stop = run_start + min(run_units, bh)
                    synthetic_segments = [{
                        "orient": "v",
                        "rail_left_x": bx0,
                        "rail_right_x": bx2,
                        "y1": run_start,
                        "y2": run_stop,
                        "length": run_stop - run_start,
                        "size": "synthetic",
                        "stroke": "#000000",
                    }]
                beam_length_ft = bundle_ft_sum

    if dominant_inches is not None and beam_length_ft > 0:
        if synthetic_segments is not None:
            wood_lines = build_wood_beams([], dominant_inches,
                                           group_bbox=group_bbox,
                                           pre_segments=synthetic_segments)
        else:
            wood_lines = build_wood_beams(alum, dominant_inches, group_bbox=group_bbox,
                                          canonical_perp=canonical_perp)
        n = len(wood_lines)
        if n > 0 and local_sizes:
            k = len(local_sizes)
            base, extra = divmod(n, k)
            sizes_split = [(local_sizes[i], base + (1 if i < extra else 0))
                           for i in range(k)]
        elif n > 0:
            sizes_split = [(None, n)]  # no size info — show count only
        wood_svg_path = svg_path.parent / (svg_path.stem + "_wood.svg")
        draw_wood_beams_on_svg(svg_path, wood_lines,
                               stroke="#FFFF00", stroke_width=4.0,
                               out_path=wood_svg_path,
                               sizes_split=sizes_split)

    return {
        "file": svg_path.name,
        "bundles": bundles,
        "alum_beams": alum,
        "beam_length_ft": beam_length_ft,
        "spacing_counts": spacing_counts,
        "spacing_inches": dominant_inches,
        "sizes_split": sizes_split,
        "wood_count": len(wood_lines),
        "wood_svg_path": wood_svg_path,
    }


def _compute_canonical_perp(svg_files, group_bounds):
    """First-pass scan: collect every adjacent-perp distance among same-
    (orient, size) rails across all groups, then take the mode per key. The
    mode is the drawing's "canonical" rail-pair gap for that beam size.

    Looking at *adjacent* perps (not paired perps) avoids the chicken-and-
    egg problem where pair_rails needs the canonical to do its job.
    Rounded to the nearest pixel so 83.8 and 84.0 cluster together.
    """
    from collections import Counter

    def _perp_coord(r):
        return r["x1"] if r["orient"] == "v" else r["y1"]

    perp_samples = {}
    for svg_path in svg_files:
        try:
            rails = find_alum_beams(svg_path, group_bbox=group_bounds.get(svg_path.name))
        except (ET.ParseError, OSError):
            continue
        if not rails:
            continue
        # Group rails by (orient, size) and within each, collect adjacent
        # perp gaps from sorted coords. Adjacent (not spanning) gaps are
        # what a real beam pair uses.
        by_key = {}
        for r in rails:
            by_key.setdefault((r["orient"], r["size"]), []).append(r)
        for key, rs in by_key.items():
            coords = sorted({round(_perp_coord(r)) for r in rs})
            for i in range(len(coords) - 1):
                gap = coords[i+1] - coords[i]
                if gap > 1:
                    perp_samples.setdefault(key, []).append(gap)

    canonical = {}
    for key, samples in perp_samples.items():
        if len(samples) < 3:
            continue  # too few to trust a mode
        canonical[key] = float(Counter(samples).most_common(1)[0][0])
    return canonical


_TEXT_FILL_RE = re.compile(r"fill:\s*#[0-9A-Fa-f]{3,8}")


_TEXT_GRAY = "#4e4e4e"


def _recolor_text_white(svg_path: Path) -> None:
    """Recolor <text> elements: bundle text (beam call-out N'- A X B or
    spacing @ N\" 0/C) → white, everything else → #4e4e4e."""
    try:
        with open(svg_path, "r", encoding="utf-8") as f:
            text = f.read()
        root = ET.fromstring(text)
    except (OSError, ET.ParseError):
        return
    changed = False
    for el in root.iter():
        if _local(el.tag) != "text":
            continue
        content = "".join(el.itertext()).strip()
        is_bundle = bool(BEAM_RE.match(content) or SPACING_RE.match(content))
        target = "#ffffff" if is_bundle else _TEXT_GRAY
        style = el.get("style", "") or ""
        if _TEXT_FILL_RE.search(style):
            style = _TEXT_FILL_RE.sub(f"fill:{target}", style)
        else:
            style = (style + f";fill:{target}").lstrip(";")
        el.set("style", style)
        if el.get("fill"):
            el.set("fill", target)
        changed = True
    if not changed:
        return
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(ET.tostring(root, encoding="unicode"))


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

    # ── First pass — pair every group's rails *without* a canonical and
    # collect the mode of perpendicular distances per (orient, size). A real
    # rail-pair gap is consistent across the whole drawing (e.g. 84 px for
    # alumBeam16). Ambiguous groups (G24-style trios) will produce wrong
    # perps here, but they're outvoted by the majority. ──
    canonical_perp = _compute_canonical_perp(svg_files, group_bounds)
    if canonical_perp:
        print(f"  Canonical pair gaps (orient, size → perp): {len(canonical_perp)} entries")
        for k, v in sorted(canonical_perp.items()):
            print(f"    {k}: {v:.1f}")

    # Drawing-wide defaults — used for groups whose own viewBox holds no
    # beam call-out bundles (small detail crops). Pick the most common
    # bundle spacing AND beam size across all groups that DO have bundles.
    from collections import Counter as _Counter
    spacing_votes = _Counter()
    size_votes = _Counter()
    for p in svg_files:
        try:
            bundles, _, _ = find_beam_bundles(p)
        except ET.ParseError:
            continue
        for bn in bundles:
            m = _SPACING_INCHES_RE.search(bn["spacing"]["text"])
            if m:
                spacing_votes[float(m.group(1))] += 1
            ms = _BEAM_SIZE_FT_RE.match(bn["beam"]["text"].strip())
            if ms:
                size_votes[int(ms.group(1))] += 1
    default_spacing = (spacing_votes.most_common(1)[0][0]
                       if spacing_votes else None)
    default_sizes_ft = ([size_votes.most_common(1)[0][0]]
                        if size_votes else None)
    if default_spacing is not None:
        print(f"  Drawing-wide default spacing (fallback): {default_spacing}\"")
    if default_sizes_ft is not None:
        print(f"  Drawing-wide default size (fallback): {default_sizes_ft[0]}'")

    print(f"🔎 Step17: processing {len(svg_files)} group SVG(s) in {GROUPS_DIR.relative_to(BASE_DIR)}")
    print(f"{'file':<10} {'bundles':>8} {'alum_rails':>11} {'alum_ft':>9} {'spacing':>9} {'wood':>6}  output")
    print("-" * 78)

    totals = {"bundles": 0, "rails": 0, "ft": 0.0, "wood": 0}
    by_size_total = {}  # {ft: count} aggregated across all groups
    per_group = []  # one entry per processed group, for the sidecar JSON
    for svg_path in svg_files:
        r = process_group(svg_path, group_bbox=group_bounds.get(svg_path.name),
                          canonical_perp=canonical_perp,
                          default_spacing_inches=default_spacing,
                          default_sizes_ft=default_sizes_ft)
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
        for (ft, cnt) in (r.get("sizes_split") or []):
            if ft is None:
                continue
            by_size_total[ft] = by_size_total.get(ft, 0) + cnt
        per_group.append({
            "file": r["file"],
            "wood_count": r["wood_count"],
            "spacing_inches": r["spacing_inches"],
            "sizes_split": [
                {"size_ft": ft, "count": cnt}
                for (ft, cnt) in (r.get("sizes_split") or [])
                if ft is not None
            ],
        })

    print("-" * 78)
    print(
        f"{'TOTAL':<10} {totals['bundles']:>8} {totals['rails']:>11} "
        f"{totals['ft']:>9.2f} {'':>9} {totals['wood']:>6}"
    )

    # Write sidecar JSON with the wood-beam totals so downstream code
    # (main.py's data.json writer) can pick them up.
    out_json = TEMP_DATA / "step17_wood.json"
    try:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        with open(out_json, "w") as f:
            json.dump({
                "total_wood_beams": totals["wood"],
                "by_size_ft": {str(k): v for k, v in sorted(by_size_total.items())},
                "groups": per_group,
            }, f, indent=2)
        print(f"  Wrote {out_json.relative_to(BASE_DIR)} (total={totals['wood']})")
    except OSError as e:
        print(f"  ⚠️  Could not write {out_json}: {e}")

    # Recolor only the source group SVGs; _wood.svg outputs already have
    # their colors set correctly (yellow rails, black badge text).
    for p in sorted(GROUPS_DIR.glob("G*.svg")):
        if p.stem.endswith("_wood"):
            continue
        _recolor_text_white(p)

    return True


if __name__ == "__main__":
    run_step17()
