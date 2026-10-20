#!/usr/bin/env python3
"""
Step 18: Per-category highlight SVGs.

Produces one SVG per element category where the ENTIRE drawing stays gray
(#4e4e4e) and only that category's elements are shown in color, so a user
can eyeball exactly what the pipeline detected for each category.

Outputs (into files/):
  - shores.svg     -> blue X shores (#0000ff) + red square shores (#fb0505)
  - alumBeams.svg  -> all aluminum beams (#0000ff)
  - frames.svg     -> all frames (#70ff00)
  - wood.svg       -> synthesized wood beams (#ffff00)
  - hardware.svg   -> U/heads + base plates (nested corner circles on each bay)

How it works:
  Base is Step2.svg, the clean gray drawing. Every path in it is already
  #4e4e4e. Elements are identified by path id via identified_elements.json
  (pathNNNN -> class). To highlight a category we recolor just those path
  ids to the category color and leave everything else gray.

  Two categories can't be recolored by path id:
    - Frames & shores: their path ids in identified_elements.json belong to
      a LATER (post-Step5) SVG, not the clean Step2.svg. But each has an
      x/y/w/h box in its detection JSON (greenFrames/orangeFrames/x-shores/
      square-shores), so we overlay colored rectangles at those boxes.
    - Wood beams: Step17 synthesizes them as <line> elements inside the
      per-group files/groups/*_wood.svg, already in full-drawing
      coordinates, so wood.svg overlays those lines directly.
  Only aluminum beams keep their path ids in Step2.svg, so those ARE
  recolored in place.
"""

import os
import re
import glob


GRAY = "#4e4e4e"

# Category -> (set of identified_elements classes, highlight color).
# Class names come from processors that write identified_elements.json:
#   shore_x, shore_square, greenFrame, orangeFrame, alumBeamNN, ...
SHORE_COLOR_X = "#0000ff"      # blue X shores (Shore #2)
SHORE_COLOR_SQUARE = "#fb0505"  # red square shores (Post Shore #4)
FRAME_COLOR = "#70ff00"         # frames (all unified green)
# Orange wrap around piggyback pairs (visualization only — counts unchanged).
PIGGYBACK_COLOR = "#ff8c00"
WOOD_COLOR = "#ffff00"          # synthesized wood beams
# Nested corner circles on each frame bay (outer = base plate, inner = U/head).
BASE_PLATE_COLOR = "#0088cc"
UHEAD_COLOR = "#ff5500"
# Circle geometry relative to each bay corner (drawing units).
_HW_CORNER_INSET = 7.0
_HW_R_OUTER = 5.5          # base plate (outer ring)
_HW_R_INNER = 2.75         # U/head (inner ring)
_HW_STROKE = 1.4

# Aluminum beams are colored PER SIZE so each beam length is visually
# distinct in alumBeams.svg. Any size not listed falls back to FALLBACK.
ALUM_BEAM_COLORS = {
    "alumBeam24":   "#e6beff",  # lavender
    "alumBeam5":    "#e6194b",  # red
    "alumBeam6":    "#f58231",  # orange
    "alumBeam7":    "#ffe119",  # yellow
    "alumBeam8":    "#bfef45",  # lime
    "alumBeam9":    "#3cb44b",  # green
    "alumBeam10":   "#42d4f4",  # cyan
    "alumBeam10_6": "#4363d8",  # blue
    "alumBeam11":   "#911eb4",  # purple
    "alumBeam12":   "#f032e6",  # magenta
    "alumBeam13":   "#a9a9a9",  # gray-blue
    "alumBeam14":   "#9a6324",  # brown
    "alumBeam16":   "#469990",  # teal
    "alumBeam18":   "#000075",  # navy
    "alumBeam20":   "#808000",  # olive
}
ALUM_BEAM_FALLBACK = "#0000ff"


def _load_identified(path):
    """Return {pathId: className} or {} if unavailable."""
    import json
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Step18: could not read {path}: {e}")
        return {}


def _recolor_paths(svg_text, id_to_color, min_stroke_width=None):
    """For each path id in id_to_color, rewrite the stroke/fill in that
    path's style to the target color. Paths not listed keep their gray.

    Matches a path element by its id then rewrites colors ONLY inside that
    element's style attribute, so unrelated paths are never touched. If
    min_stroke_width is given, a highlighted path's stroke-width is bumped
    to at least that value so the category stands out.
    """
    def repl(m):
        head = m.group(0)
        pid = m.group("pid")
        color = id_to_color.get(pid)
        if not color:
            return head
        # Recolor stroke and fill (whichever the path uses) within this tag.
        head = re.sub(r"stroke:#[0-9a-fA-F]{6}", f"stroke:{color}", head)
        head = re.sub(r"fill:#[0-9a-fA-F]{6}", f"fill:{color}", head)
        if min_stroke_width is not None:
            def bump(sw):
                try:
                    return sw if float(sw.group(1)) >= min_stroke_width \
                        else f"stroke-width:{min_stroke_width}"
                except ValueError:
                    return f"stroke-width:{min_stroke_width}"
            head = re.sub(r"stroke-width:([0-9.]+)", bump, head)
        return head

    # A path element from id up to (and including) its style attribute.
    # SVGs here render each path as: <path ... id="pathNNNN" ... style="..." .../>
    pat = re.compile(
        r'<path\b[^>]*?\bid="(?P<pid>path\d+)"[^>]*?style="[^"]*"',
        re.DOTALL,
    )
    return pat.sub(repl, svg_text)


def _write_highlight(base_svg, out_path, id_to_color, label,
                     min_stroke_width=None):
    svg = _recolor_paths(base_svg, id_to_color, min_stroke_width)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    n = len(id_to_color)
    print(f"✅ Step18 wrote {out_path} ({label}: {n} element(s) highlighted)")
    return n


def _load_boxes(path, list_key):
    """Return the list of {x,y,width,height} boxes from a detection JSON,
    or [] if unavailable."""
    import json
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d.get(list_key) or []
    except Exception:
        return []


def _load_layer_boxes(path):
    """Return the per-container layer boxes [{x,y,w,h,layers}] Step13 wrote to
    frame_layers.json, or [] if unavailable."""
    import json
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or []
    except Exception:
        return []


def _match_layer_box(x, y, w, h, layer_boxes):
    """Find the layer box for a frame by matching its bbox against the
    per-container layer boxes Step13 recorded. Returns the matched box dict, or
    None if no box centers within a small tolerance."""
    cx, cy = x + w / 2.0, y + h / 2.0
    best = None
    best_d = None
    for lb in layer_boxes:
        try:
            lcx = float(lb["x"]) + float(lb["w"]) / 2.0
            lcy = float(lb["y"]) + float(lb["h"]) / 2.0
        except (KeyError, TypeError, ValueError):
            continue
        d = (lcx - cx) ** 2 + (lcy - cy) ** 2
        if best_d is None or d < best_d:
            best_d = d
            best = lb
    # Tolerance: centers within ~10px (squared -> 100) count as the same box.
    if best is not None and best_d is not None and best_d <= 100:
        return best
    return None


def _layer_label(box):
    """Build the corner label lines for a matched layer box: one "<height>H x
    4W" line per stacked frame layer, STACKED vertically. A 5'+5' stack (or a
    5'+5' drawing default) -> ["5H x 4W", "5H x 4W"]; a single 6' default ->
    ["6H x 4W"]."""
    heights = box.get("heights") or []
    tokens = [f"{int(h)}H x 4W" for h in heights]
    if not tokens:
        # No heights recorded; fall back to the layer count.
        tokens = ["?H x 4W"] * max(1, int(box.get("layers", 1)))
    return tokens


def _find_piggybacks(boxes, edge_tol=15.0, align_tol=8.0):
    """Detect piggyback pairs among frame boxes. A piggyback is two bays that
    meet edge-to-edge and SHARE the physical frame on that side.

    Facing edges may slightly OVERLAP or leave a small GAP (both within
    edge_tol, ~one frame thickness) — detection JSONs often leave an ~8px
    seam between stacked bays, which must still count as piggyback. The
    perpendicular span must stay aligned (within align_tol). Returns a list
    of (i, j) index pairs into `boxes`.

    `boxes` is a list of (x, y, w, h) tuples."""
    pairs = []
    n = len(boxes)
    for i in range(n):
        ax, ay, aw, ah = boxes[i]
        for j in range(i + 1, n):
            bx, by, bw, bh = boxes[j]
            # Positive = overlap; negative = gap between boxes.
            ix = min(ax + aw, bx + bw) - max(ax, bx)
            iy = min(ay + ah, by + bh) - max(ay, by)
            # Shared VERTICAL edge (side-by-side): thin x touch, tall y overlap.
            share_v = (-edge_tol <= ix <= edge_tol and iy > edge_tol
                       and abs((ay + ah / 2) - (by + bh / 2)) <= align_tol)
            # Shared HORIZONTAL edge (stacked): thin y touch, wide x overlap.
            share_h = (-edge_tol <= iy <= edge_tol and ix > edge_tol
                       and abs((ax + aw / 2) - (bx + bw / 2)) <= align_tol)
            if share_v or share_h:
                pairs.append((i, j))
    return pairs


def _corner_text(el_id, tx, cy, color, lines):
    """A left-aligned <text> whose stacked lines are CENTERED VERTICALLY on
    `cy` (the box's vertical midpoint). One <tspan> per line, stacked downward
    by the 10px font line height; the block's first line starts high enough
    that the whole stack straddles `cy`."""
    LINE_H = 10.0
    y0 = cy - (len(lines) - 1) * LINE_H / 2.0
    spans = "".join(
        f'<tspan x="{tx}" dy="{0 if k == 0 else LINE_H}">{ln}</tspan>'
        for k, ln in enumerate(lines)
    )
    return (f'    <text id="{el_id}" x="{tx}" y="{y0}" '
            f'style="font-family:Arial;font-size:10px;fill:{color};'
            f'text-anchor:start;dominant-baseline:central;'
            f'font-weight:bold">{spans}</text>')


def _piggyback_label(el_id, ux, uy, uw, uh, color, stack_lines, positions):
    """Merged-piggyback label: draw `positions` groups spread across the
    outline, EACH group showing the full per-side stack (`stack_lines`). A
    TALL outline places the groups top -> bottom; a WIDE outline places them
    left -> right. So a 6+5 pair (stack ["5X4","6X4"], 3 positions) reads as
    three "5X4 / 6X4" blocks along the bay."""
    if not stack_lines or positions <= 0:
        return ""
    LINE_H = 10.0
    inset = 12.0
    sideways = uw > uh
    # Evenly space `positions` anchor points between the two insets.
    def lerp(a, b, t):
        return a + (b - a) * t
    anchors = []
    for p in range(positions):
        t = 0.5 if positions == 1 else p / (positions - 1)
        if sideways:
            anchors.append((lerp(ux + inset, ux + uw - inset, t), uy + uh / 2.0))
        else:
            anchors.append((ux + uw / 2.0, lerp(uy + inset, uy + uh - inset, t)))
    texts = []
    for gi, (ax, ay) in enumerate(anchors):
        # Anchor so the stack's rows are vertically centered on (ax, ay).
        y0 = ay - (len(stack_lines) - 1) * LINE_H / 2.0
        spans = "".join(
            f'<tspan x="{ax}" dy="{0 if k == 0 else LINE_H}">{ln}</tspan>'
            for k, ln in enumerate(stack_lines)
        )
        texts.append(
            f'    <text id="{el_id}_g{gi + 1}" x="{ax}" y="{y0}" '
            f'style="font-family:Arial;font-size:10px;fill:{color};'
            f'text-anchor:middle;dominant-baseline:central;'
            f'font-weight:bold">{spans}</text>'
        )
    return "\n".join(texts)


def _merged_piggyback_stack(box_a, box_b):
    """For a merged piggyback pair, return (stack_lines, positions):
      - stack_lines: the DISTINCT per-side stack as "<h>H x 4W" rows, e.g. a
        6+5 bay -> ["5H x 4W", "6H x 4W"].
      - positions: total merged frames / stack size. Each bay's `heights` is
        the per-side stack with every height DOUBLED and grouped (a 5'+6' bay
        -> [5,5,6,6]); the two bays SHARE one physical side, so total frames =
        A + B - min(stack_A, stack_B). Using min (not a fixed bay) keeps the
        taller bay's outer stack and counts the shared wall once even when
        stack heights differ. Divided by the distinct per-side stack size,
        that's how many times the stack repeats along the merged bay
        (a 6+5 pair -> 6 frames / stack [5,6] -> 3 positions)."""
    def undouble(hs):
        # [5,5,6,6] (each height duplicated, grouped) -> distinct stack [5,6].
        return [hs[k] for k in range(0, len(hs), 2)]

    ha = list((box_a or {}).get("heights") or [])
    hb = list((box_b or {}).get("heights") or [])
    sa, sb = undouble(ha), undouble(hb)
    if not sa and not sb:
        return [], 0
    # Physical frames = both sides of the taller bay + outer side of the
    # shorter bay (shared wall counted once). Equals A+B-min(stack_A,stack_B).
    if len(sa) >= len(sb):
        stack, phys = sa, list(ha) + list(sb)
    else:
        stack, phys = sb, list(hb) + list(sa)
    total_frames = len(phys)
    # Equal stacks: repeat the per-side stack along the bay. Unequal: one
    # centered block listing every physical frame (avoids truncating via //).
    if sa and sb and len(sa) == len(sb) and sa == sb:
        stack_lines = [f"{int(h)}H x 4W" for h in stack]
        positions = max(1, total_frames // max(1, len(stack)))
    else:
        stack_lines = [f"{int(h)}H x 4W" for h in phys]
        positions = 1
    return stack_lines, positions


def _write_frame_count(base_dir, height_counts):
    """Write the physical frame count derived from the frames.svg annotations
    to data.json as `frame_count`: a total plus a per-height breakdown.
    Also refreshes `frame_totals` so it matches the piggyback-aware physical
    count (Step13's frame_totals double-count shared sides).
    data.json lives one level above base_dir (files/ -> ./data.json)."""
    import json
    data_path = os.path.join(os.path.dirname(base_dir.rstrip("/")) or ".",
                             "data.json")
    by_height = {str(h): height_counts[h] for h in sorted(height_counts)}
    frame_count = {"total": sum(height_counts.values()), "by_height": by_height}
    # Mirror into frame_totals keys the UI/DB still read (frame_5 / frame_6 / …).
    frame_totals = {f"frame_{h}": height_counts[h] for h in sorted(height_counts)}
    frame_totals["total"] = frame_count["total"]
    try:
        data = {}
        if os.path.exists(data_path):
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        data["frame_count"] = frame_count
        data["frame_totals"] = frame_totals
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"✅ Step18 wrote frame_count to {data_path}: {frame_count}")
        print(f"   frame_totals (piggyback-aware): {frame_totals}")
    except Exception as e:
        print(f"⚠️  Step18: could not write frame_count to {data_path}: {e}")


def _overlay_rects(base_svg, out_path, box_layers, label, layer_boxes=None):
    """Overlay colored bounding rectangles onto the gray base. box_layers is
    a list of (boxes, color, prefix). One <rect> per box, drawn before
    </svg> so it sits on top. When `layer_boxes` is given, also draw the stack
    LAYER count in each box's top-left corner."""
    els = []
    total = 0
    height_counts = {}   # physical frame count per height (ft) across the sheet
    layer_boxes = layer_boxes or []

    def _tally(lines, times=1):
        # Each "<h>H x 4W" line is one physical frame; add `times` of each.
        for ln in lines:
            m = re.match(r"\s*(\d+)H", ln)
            if m:
                h = int(m.group(1))
                height_counts[h] = height_counts.get(h, 0) + times

    # prefix used in the rendered rect id -> the id NAMESPACE that
    # identified_elements uses for that element, so the correction endpoint can
    # find a frame/shore by its real element id (the rect's own hl_ index is
    # just a positional counter and does NOT match identified_elements).
    ID_NAMESPACE = {
        "greenFrames": "green_container",
        "orangeFrames": "orange_container",
        "pinkFrames": "pink_container",
        "yellowFrames": "yellow_container",
        "shore_x": "x_shape",
        "shore_square": "red_square",
    }

    # Flatten every color group into one indexed list so piggybacks can be
    # detected across colors (green frame stacked on an orange one, etc.).
    flat = []  # (x, y, w, h, color, prefix, i, el_id)
    for boxes, color, prefix in box_layers:
        for i, b in enumerate(boxes, 1):
            try:
                x = float(b["x"]); y = float(b["y"])
                w = float(b["width"]); h = float(b["height"])
            except (KeyError, TypeError, ValueError):
                continue
            # Real identified_elements id: "<namespace>_<box id>" (box id is the
            # detection JSON's own id). Falls back to the positional counter.
            ns = ID_NAMESPACE.get(prefix)
            box_id = b.get("id", i)
            el_id = f"{ns}_{box_id}" if ns else f"{prefix}_{box_id}"
            flat.append((x, y, w, h, color, prefix, i, el_id))

    coords = [(f[0], f[1], f[2], f[3]) for f in flat]
    pig_pairs = _find_piggybacks(coords)
    # Boxes that belong to a piggyback are drawn as ONE merged unit instead of
    # two separate colored squares, so suppress them from the normal pass.
    # Only change vs before: the merged outline is orange (viz).
    suppressed = {idx for pair in pig_pairs for idx in pair}

    for k, (x, y, w, h, color, prefix, i, el_id) in enumerate(flat):
        if k in suppressed:
            continue
        # data-el-id carries the REAL identified_elements id so the correction
        # endpoint can locate this exact frame/shore (the hl_ id is positional).
        els.append(
            f'    <rect id="hl_{prefix}_{i}" data-el-id="{el_id}" x="{x}" y="{y}" '
            f'width="{w}" height="{h}" '
            f'style="fill:none;stroke:{color};stroke-width:3;stroke-opacity:1" />'
        )
        match = _match_layer_box(x, y, w, h, layer_boxes)
        if match is not None:
            lines = _layer_label(match)
            _tally(lines)
            els.append(_corner_text(f"layers_{prefix}_{i}", x + 3, y + h / 2.0,
                                    color, lines))
        total += 1

    # Piggybacks: same merged outline + tally as before, stroke is orange only.
    for pk, (i, j) in enumerate(pig_pairs, 1):
        ax, ay, aw, ah, _, _, _, a_id = flat[i]
        bx, by, bw, bh, _, _, _, b_id = flat[j]
        ux, uy = min(ax, bx), min(ay, by)
        uw = max(ax + aw, bx + bw) - ux
        uh = max(ay + ah, by + bh) - uy
        pad = 2.0  # nudge the outline just outside both boxes
        els.append(
            f'    <rect id="piggyback_{pk}" data-el-id="{a_id}" data-el-id-2="{b_id}" '
            f'x="{ux - pad}" y="{uy - pad}" '
            f'width="{uw + 2 * pad}" height="{uh + 2 * pad}" '
            f'style="fill:none;stroke:{PIGGYBACK_COLOR};stroke-width:3;stroke-opacity:1" />'
        )
        stack_lines, positions = _merged_piggyback_stack(
            _match_layer_box(ax, ay, aw, ah, layer_boxes),
            _match_layer_box(bx, by, bw, bh, layer_boxes))
        if stack_lines:
            _tally(stack_lines, times=positions)
            els.append(_piggyback_label(
                f"piggyback_layers_{pk}", ux, uy, uw, uh, PIGGYBACK_COLOR,
                stack_lines, positions))
        total += 1
    if pig_pairs:
        print(f"   frames: {len(pig_pairs)} piggyback pair(s) wrapped in orange")

    if els:
        block = "\n" + "\n".join(els) + "\n"
        svg = base_svg.replace("</svg>", block + "</svg>", 1)
    else:
        svg = base_svg
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"✅ Step18 wrote {out_path} ({label}: {total} element(s) highlighted)")
    return total, height_counts


def _hardware_nested_pair(el_id, tag, cx, cy):
    """One nested base-plate (outer) + U/head (inner) at (cx, cy)."""
    safe = re.sub(r"[^A-Za-z0-9_\-]", "_", str(el_id))
    return [
        f'    <circle id="hardware_baseplate_{safe}_{tag}" '
        f'data-el-id="{el_id}" data-hw="baseplate" data-corner="{tag}" '
        f'cx="{cx:.2f}" cy="{cy:.2f}" r="{_HW_R_OUTER}" '
        f'style="fill:none;stroke:{BASE_PLATE_COLOR};stroke-width:{_HW_STROKE};'
        f'stroke-opacity:1" />',
        f'    <circle id="hardware_uhead_{safe}_{tag}" '
        f'data-el-id="{el_id}" data-hw="uhead" data-corner="{tag}" '
        f'cx="{cx:.2f}" cy="{cy:.2f}" r="{_HW_R_INNER}" '
        f'style="fill:none;stroke:{UHEAD_COLOR};stroke-width:{_HW_STROKE};'
        f'stroke-opacity:1" />',
    ]


def _hardware_corner_circles(el_id, x, y, w, h, extra_points=None):
    """Nested circles on the four corners of a frame bay (+ optional extras).

    Each point gets an OUTER base-plate ring and an INNER U/head ring.
    Piggyback shared-wall endpoints are passed via `extra_points`
    ([(tag, cx, cy), ...]) — typically 2 more of each on the center seam.
    Returns (svg_elements, n_uhead, n_baseplate).
    """
    inset = _HW_CORNER_INSET
    points = [
        ("tl", x + inset, y + inset),
        ("tr", x + w - inset, y + inset),
        ("br", x + w - inset, y + h - inset),
        ("bl", x + inset, y + h - inset),
    ]
    if extra_points:
        points.extend(extra_points)
    els = []
    for tag, cx, cy in points:
        els.extend(_hardware_nested_pair(el_id, tag, cx, cy))
    n = len(points)
    return els, n, n


def _shared_seam_points(ax, ay, aw, ah, bx, by, bw, bh,
                        edge_tol=15.0, align_tol=8.0):
    """Two endpoints of the shared wall between a piggyback pair.

    Side-by-side (shared vertical edge) → top + bottom of the seam.
    Stacked (shared horizontal edge) → left + right of the seam.
    Returns [(tag, cx, cy), ...] (empty if not a piggyback touch).
    """
    ix = min(ax + aw, bx + bw) - max(ax, bx)
    iy = min(ay + ah, by + bh) - max(ay, by)
    share_v = (-edge_tol <= ix <= edge_tol and iy > edge_tol
               and abs((ay + ah / 2) - (by + bh / 2)) <= align_tol)
    share_h = (-edge_tol <= iy <= edge_tol and ix > edge_tol
               and abs((ax + aw / 2) - (bx + bw / 2)) <= align_tol)
    inset = _HW_CORNER_INSET
    if share_v:
        seam_x = (max(ax, bx) + min(ax + aw, bx + bw)) / 2.0
        y0 = max(ay, by) + inset
        y1 = min(ay + ah, by + bh) - inset
        return [("seam_t", seam_x, y0), ("seam_b", seam_x, y1)]
    if share_h:
        seam_y = (max(ay, by) + min(ay + ah, by + bh)) / 2.0
        x0 = max(ax, bx) + inset
        x1 = min(ax + aw, bx + bw) - inset
        return [("seam_l", x0, seam_y), ("seam_r", x1, seam_y)]
    return []


def _collect_frame_towers(td):
    """Return list of (el_id, x, y, w, h, extra_points) per independent tower.

    Piggyback pairs merge into one outline (same rules as frames.svg). The
    shared center wall contributes two extra nested-circle points so the
    tower gets 4 corners + 2 seam = 6 of each hardware type.
    """
    ID_NAMESPACE = {
        "greenFrames": "green_container",
        "orangeFrames": "orange_container",
        "pinkFrames": "pink_container",
        "yellowFrames": "yellow_container",
    }
    flat = []
    for fname, lk in (("greenFrames.json", "rectangles"),
                      ("orangeFrames.json", "rectangles"),
                      ("pinkFrames.json", "pink_shapes"),
                      ("yellowFrames.json", "rectangles")):
        boxes = _load_boxes(os.path.join(td, fname), lk)
        prefix = fname[:-5]
        ns = ID_NAMESPACE.get(prefix)
        for i, b in enumerate(boxes, 1):
            try:
                x = float(b["x"]); y = float(b["y"])
                w = float(b["width"]); h = float(b["height"])
            except (KeyError, TypeError, ValueError):
                continue
            box_id = b.get("id", i)
            el_id = f"{ns}_{box_id}" if ns else f"{prefix}_{box_id}"
            flat.append((el_id, x, y, w, h))

    if not flat:
        return []

    coords = [(x, y, w, h) for _, x, y, w, h in flat]
    pig_pairs = _find_piggybacks(coords)
    suppressed = {idx for pair in pig_pairs for idx in pair}
    towers = []
    for k, (el_id, x, y, w, h) in enumerate(flat):
        if k in suppressed:
            continue
        towers.append((el_id, x, y, w, h, None))
    for i, j in pig_pairs:
        a_id, ax, ay, aw, ah = flat[i]
        _b_id, bx, by, bw, bh = flat[j]
        ux, uy = min(ax, bx), min(ay, by)
        uw = max(ax + aw, bx + bw) - ux
        uh = max(ay + ah, by + bh) - uy
        pad = 2.0
        seam = _shared_seam_points(ax, ay, aw, ah, bx, by, bw, bh)
        towers.append((a_id, ux - pad, uy - pad, uw + 2 * pad, uh + 2 * pad, seam))
    return towers


def _build_hardware_svg(base_svg, td, out_path, base_dir):
    """Draw nested U/head + base-plate circles on every frame bay corner.

    Called right after wood.svg. Each tower gets 4 corner pairs; piggybacks
    get 2 more pairs on the shared center seam (+2 of each). Also writes
    hardware_totals onto data.json.
    """
    towers = _collect_frame_towers(td)
    els = []
    n_uhead = 0
    n_base = 0
    for el_id, x, y, w, h, extra in towers:
        circles, nu, nb = _hardware_corner_circles(el_id, x, y, w, h, extra)
        els.extend(circles)
        n_uhead += nu
        n_base += nb

    if els:
        block = "\n" + "\n".join(els) + "\n"
        svg = base_svg.replace("</svg>", block + "</svg>", 1)
    else:
        svg = base_svg
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"✅ Step18 wrote {out_path} "
          f"(towers={len(towers)}, uhead={n_uhead}, baseplate={n_base})")

    import json
    # data.json sits next to files/ in both microservice and monolith layouts.
    if os.path.basename(os.path.abspath(base_dir).rstrip(os.sep)) == "files":
        candidates = [
            os.path.join(os.path.dirname(os.path.abspath(base_dir)), "data.json"),
            os.path.join(base_dir, "data.json"),
            "data.json",
        ]
    else:
        candidates = [os.path.join(base_dir, "data.json"), "data.json"]
    for data_path in candidates:
        if not os.path.exists(data_path):
            continue
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["hardware_totals"] = {
                "uhead": n_uhead,
                "baseplate": n_base,
                "towers": len(towers),
            }
            with open(data_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            print(f"✅ Step18 wrote hardware_totals to {data_path}: "
                  f"uhead={n_uhead}, baseplate={n_base}")
        except Exception as e:
            print(f"⚠️  Step18: could not write hardware_totals: {e}")
        break
    return n_uhead, n_base


def _build_wood_svg(base_svg, groups_dir, out_path):
    """Overlay every wood <line> from files/groups/*_wood.svg onto the gray
    base. The lines are already in full-drawing coordinates, so they drop in
    directly before </svg>."""
    line_re = re.compile(r"<line\b[^>]*/>", re.DOTALL)
    wood_lines = []
    for gf in sorted(glob.glob(os.path.join(groups_dir, "*_wood.svg"))):
        try:
            with open(gf, "r", encoding="utf-8") as f:
                gtext = f.read()
        except Exception:
            continue
        # Only the synthesized beam lines carry an explicit stroke="#..."
        # (the base drawing paths use style="..."). Recolor them to WOOD_COLOR
        # so mixed per-size colors read as one wood category.
        for ln in line_re.findall(gtext):
            ln = re.sub(r'stroke="#[0-9a-fA-F]{6}"', f'stroke="{WOOD_COLOR}"', ln)
            wood_lines.append("    " + ln)

    if wood_lines:
        block = "\n" + "\n".join(wood_lines) + "\n"
        svg = base_svg.replace("</svg>", block + "</svg>", 1)
    else:
        svg = base_svg
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"✅ Step18 wrote {out_path} (wood: {len(wood_lines)} line(s) overlaid)")
    return len(wood_lines)


def _build_crossbars_svg(base_svg, step13_path, out_path):
    """Overlay the crossbar color lines onto the gray base. Step13 already
    drew them as <line id="crossbar_line_*"> on Step13.svg in full-drawing
    coordinates, each keeping its own per-color style, so we lift those lines
    out and drop them onto the clean gray base."""
    if not os.path.exists(step13_path):
        print(f"⚠️  Step18: {step13_path} not found, skipping crossbars.svg")
        return 0
    try:
        with open(step13_path, "r", encoding="utf-8") as f:
            s13 = f.read()
    except Exception as e:
        print(f"⚠️  Step18: could not read {step13_path}: {e}")
        return 0
    line_re = re.compile(r'<line\b[^>]*\bid="crossbar_line_[^"]*"[^>]*/>', re.DOTALL)
    lines = ["    " + ln for ln in line_re.findall(s13)]
    if lines:
        block = "\n" + "\n".join(lines) + "\n"
        svg = base_svg.replace("</svg>", block + "</svg>", 1)
    else:
        svg = base_svg
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"✅ Step18 wrote {out_path} (crossbars: {len(lines)} line(s) overlaid)")
    return len(lines)


def _merge_piggybacks_on_main_svg(svg_path):
    """Rewrite Step11.svg (Main layer) so piggyback pairs are easy to see:
    both green squares keep their own numbers, linked via data-el-id-2, wrapped
    by one orange outline. Counts/logic elsewhere are unchanged — this is viz.
    """
    if not os.path.exists(svg_path):
        print(f"⚠️  Step18: {svg_path} not found, skipping main piggyback merge")
        return 0
    try:
        with open(svg_path, "r", encoding="utf-8") as f:
            svg = f.read()
    except Exception as e:
        print(f"⚠️  Step18: could not read {svg_path}: {e}")
        return 0

    rect_re = re.compile(
        r'<rect\s*\n\s*id="((?:green|orange|pink|yellow)_container_(\d+))"\s*\n'
        r'\s*x="([^"]+)"\s*\n\s*y="([^"]+)"\s*\n'
        r'\s*width="([^"]+)"\s*\n\s*height="([^"]+)"\s*\n'
        r'\s*style="([^"]*)"\s*/>',
        re.MULTILINE,
    )
    rects = []
    for m in rect_re.finditer(svg):
        el_id, num, x, y, w, h, style = m.groups()
        stroke = FRAME_COLOR
        sm = re.search(r"stroke:(#[0-9a-fA-F]{3,8})", style or "")
        if sm:
            stroke = sm.group(1)
        rects.append({
            "el_id": el_id, "num": int(num), "text": m.group(0),
            "x": float(x), "y": float(y), "w": float(w), "h": float(h),
            "stroke": stroke,
        })
    if len(rects) < 2:
        return 0

    boxes = [(r["x"], r["y"], r["w"], r["h"]) for r in rects]
    pairs = _find_piggybacks(boxes)
    if not pairs:
        print("   main: no piggyback pairs to merge")
        return 0

    # Keep each green's own number label (same as solo greens). Only add the
    # orange wrap + link the pair for single-element selection.
    for i, j in pairs:
        for primary, partner in ((rects[i], rects[j]), (rects[j], rects[i])):
            old = primary["text"]
            if old not in svg or "data-el-id-2=" in old:
                continue
            new = re.sub(
                rf'(id="{re.escape(primary["el_id"])}")',
                rf'\1 data-el-id="{primary["el_id"]}" '
                rf'data-el-id-2="{partner["el_id"]}"',
                old,
                count=1,
            )
            svg = svg.replace(old, new, 1)
            primary["text"] = new

    els = []
    for pk, (i, j) in enumerate(pairs, 1):
        a, b = rects[i], rects[j]
        if a["num"] > b["num"]:
            a, b = b, a
        ux = min(a["x"], b["x"])
        uy = min(a["y"], b["y"])
        uw = max(a["x"] + a["w"], b["x"] + b["w"]) - ux
        uh = max(a["y"] + a["h"], b["y"] + b["h"]) - uy
        pad = 2.0
        els.append(
            f'    <rect id="piggyback_{pk}" data-el-id="{a["el_id"]}" '
            f'data-el-id-2="{b["el_id"]}" '
            f'x="{ux - pad}" y="{uy - pad}" '
            f'width="{uw + 2 * pad}" height="{uh + 2 * pad}" '
            f'style="fill:none;stroke:{PIGGYBACK_COLOR};stroke-width:2;'
            f'stroke-opacity:1" />'
        )

    if "</svg>" not in svg:
        print(f"⚠️  Step18: no </svg> in {svg_path}")
        return 0
    new_svg = re.sub(r"\n{3,}", "\n\n",
                     svg.replace("</svg>", "\n" + "\n".join(els) + "\n</svg>", 1))
    try:
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(new_svg)
    except Exception as e:
        print(f"⚠️  Step18: could not write {svg_path}: {e}")
        return 0
    print(f"   main: {len(pairs)} piggyback pair(s) wrapped in orange on {svg_path}")
    return len(pairs)


def run_step18():
    """Generate the per-category highlight SVGs. Returns True on success."""
    try:
        if os.path.exists("files/Step2.svg"):
            base_dir = "files"
        elif os.path.exists("../files/Step2.svg"):
            base_dir = "../files"
        else:
            print("⚠️  Step18: files/Step2.svg not found, skipping")
            return False

        base_path = os.path.join(base_dir, "Step2.svg")
        with open(base_path, "r", encoding="utf-8") as f:
            base_svg = f.read()

        identified = _load_identified(
            os.path.join(base_dir, "tempData", "identified_elements.json"))
        td = os.path.join(base_dir, "tempData")

        # Aluminum beams: recolor their paths in place (their ids survive
        # into Step2.svg), one distinct color PER SIZE.
        beams = {pid: ALUM_BEAM_COLORS.get(str(cls), ALUM_BEAM_FALLBACK)
                 for pid, cls in identified.items()
                 if str(cls).startswith("alumBeam")}
        _write_highlight(base_svg, os.path.join(base_dir, "alumBeams.svg"),
                         beams, "alumBeams", min_stroke_width=18)

        # Shores: overlay boxes from the detection JSONs (blue X + red square).
        x_shores = _load_boxes(os.path.join(td, "x-shores.json"), "x_shapes")
        sq_shores = _load_boxes(os.path.join(td, "square-shores.json"),
                                "red_squares")
        _overlay_rects(base_svg, os.path.join(base_dir, "shores.svg"), [
            (x_shores, SHORE_COLOR_X, "shore_x"),
            (sq_shores, SHORE_COLOR_SQUARE, "shore_square"),
        ], "shores")

        # Frames: overlay boxes (green + orange + any pink/yellow), all green.
        frame_layers = []
        # NOTE: each detection file stores its box list under its OWN key.
        # pinkFrames.json uses "pink_shapes" (OpenCV contour detection), not
        # "rectangles" — reading the wrong key silently dropped all pink frames
        # from the drawn/labeled/counted output.
        for fname, lk in (("greenFrames.json", "rectangles"),
                          ("orangeFrames.json", "rectangles"),
                          ("pinkFrames.json", "pink_shapes"),
                          ("yellowFrames.json", "rectangles")):
            boxes = _load_boxes(os.path.join(td, fname), lk)
            if boxes:
                frame_layers.append((boxes, FRAME_COLOR, fname[:-5]))
        layer_boxes = _load_layer_boxes(os.path.join(td, "frame_layers.json"))
        _, frame_height_counts = _overlay_rects(
            base_svg, os.path.join(base_dir, "frames.svg"),
            frame_layers, "frames", layer_boxes=layer_boxes)
        # Persist the true PHYSICAL frame count (from the frames.svg labels:
        # each layer x2, piggybacks share a side) + a per-height breakdown.
        _write_frame_count(base_dir, frame_height_counts)

        # Main drawing (Step11.svg): merge piggyback container pairs the same
        # way frames.svg does, so the Main layer shows one linked outline
        # (e.g. "44+46") instead of two separate green boxes.
        _merge_piggybacks_on_main_svg(os.path.join(base_dir, "Step11.svg"))

        # Wood beams: overlay synthesized lines from the per-group SVGs.
        _build_wood_svg(base_svg, os.path.join(base_dir, "groups"),
                        os.path.join(base_dir, "wood.svg"))

        # U/heads + base plates: nested corner circles on each frame bay
        # (right after wood, before crossbars).
        _build_hardware_svg(base_svg, td,
                            os.path.join(base_dir, "hardware.svg"), base_dir)

        # Crossbars: overlay the color lines Step13 drew on Step13.svg.
        _build_crossbars_svg(base_svg, os.path.join(base_dir, "Step13.svg"),
                             os.path.join(base_dir, "crossbars.svg"))

        print("✓ Step18 completed")
        return True
    except Exception as e:
        print(f"✗ Error in Step18: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    run_step18()
