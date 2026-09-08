"""Build the canonical per-element path-id index for a processed drawing.

The frontend selects an element on one of the takeoff SVGs and needs to know
its path id so front/back can communicate about specific elements by id. This
module turns the pipeline's per-category identity data into ONE map:

    { "<path_id>": {"category": "<category>", "type": "<type>"}, ... }

Sources (all in files/ after Step18 runs, before cleanup):
  - tempData/identified_elements.json : {path_id -> class} for aluminum beams,
    frames and shores. Beam classes are alumBeam<size>; frame classes are
    <color>Frame; shore classes are shore_x / shore_square. These path ids are
    stable and appear in the rendered step11 / alumBeams / shores SVGs.
  - crossbars.svg (or Step13.svg) : <line id="crossbar_line_..."> elements,
    each carrying its own stroke color. Crossbars are NOT in
    identified_elements.json, so we lift their ids straight from the SVG and
    type them by color (Green/Red/Yellow).

Wood beams are synthesized <line> elements with NO ids, so they cannot be
addressed by path id and are intentionally absent from the index.
"""

import json
import os
import re


# class name (from identified_elements.json) -> category bucket
def _category_for_class(cls: str) -> str:
    c = str(cls)
    if c.startswith("alumBeam"):
        return "alumBeams"
    if c.endswith("Frame"):
        return "frames"
    if c.startswith("shore_"):
        return "shores"
    return "other"


# crossbar line stroke color -> type label. These hexes MUST match the palette
# Step13 actually draws (Step13.CROSS_BAR_COLOR_HEX). Each crossbar diagonal is
# tri-colored — colored tips + a white middle — so a single crossbar's lines
# carry BOTH the color hex and #ffffff; white is intentionally NOT in this map
# so the white middle segments don't get typed as their own crossbar.
_CROSSBAR_COLOR_TYPES = {
    "#a000c0": "crossbar_Purple",
    "#ffff00": "crossbar_Yellow",
    "#00c000": "crossbar_Green",
    "#0000ff": "crossbar_Blue",
    "#ff69b4": "crossbar_Pink",
    "#ff0000": "crossbar_Red",
    "#ff8c00": "crossbar_Orange",
}

# A <line ... id="crossbar_line_..." ... /> element with its style/stroke.
_CROSSBAR_LINE_RE = re.compile(
    r'<line\b[^>]*\bid="(?P<id>crossbar_line_[^"]+)"[^>]*?/>',
    re.DOTALL,
)
_STROKE_RE = re.compile(r'stroke[:=]"?#([0-9a-fA-F]{6})', re.IGNORECASE)


def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _crossbars_from_svg(svg_path):
    """Return {line_id: {"category": "crossbars", "type": "crossbar_<Color>"}}.

    Each crossbar diagonal is drawn as 3 segments — "<base>_1" (colored tip),
    "<base>_2" (WHITE middle), "<base>_3" (colored tip). The white middle isn't
    its own crossbar color; it inherits the diagonal's color from its siblings.
    So we resolve every segment's type to the colored tip's type, keyed by the
    shared "<base>" prefix, and never emit the generic "crossbar" for a white
    middle whose colored siblings are known.
    """
    out = {}
    text = None
    try:
        with open(svg_path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return out

    # First pass: collect each segment's raw stroke and the color type of every
    # diagonal base (from its colored, non-white tips).
    segs = []          # (line_id, base, raw_color)
    base_type = {}     # "<base>" -> "crossbar_<Color>"
    for m in _CROSSBAR_LINE_RE.finditer(text):
        tag = m.group(0)
        lid = m.group("id")
        sm = _STROKE_RE.search(tag)
        color = ("#" + sm.group(1).lower()) if sm else None
        # "<base>_<segidx>" -> strip the trailing "_<n>" to group the 3 segments.
        base = lid.rsplit("_", 1)[0]
        segs.append((lid, base, color))
        ctype = _CROSSBAR_COLOR_TYPES.get(color)
        if ctype is not None:
            base_type[base] = ctype

    # Second pass: type every segment by its diagonal's resolved color (so the
    # white middle inherits its tips' type). Fall back to a per-color match,
    # then the generic label only if truly unknown.
    for lid, base, color in segs:
        ctype = (base_type.get(base)
                 or _CROSSBAR_COLOR_TYPES.get(color)
                 or "crossbar")
        out[lid] = {"category": "crossbars", "type": ctype}
    return out


def build_element_index(base_dir="files"):
    """Assemble the {path_id: {category, type}} index from files in base_dir.

    Returns the dict (empty if nothing could be read). Safe to call even when
    some sources are missing — each source is optional.
    """
    index = {}

    # Beams / frames / shores from identified_elements.json (path_id -> class).
    identified = _load_json(
        os.path.join(base_dir, "tempData", "identified_elements.json"))
    if isinstance(identified, dict):
        for pid, cls in identified.items():
            index[str(pid)] = {
                "category": _category_for_class(cls),
                "type": str(cls),
            }

    # Crossbars from the rendered crossbars.svg (fallback: Step13.svg).
    for svg_name in ("crossbars.svg", "Step13.svg"):
        svg_path = os.path.join(base_dir, svg_name)
        if os.path.exists(svg_path):
            cb = _crossbars_from_svg(svg_path)
            if cb:
                index.update(cb)
                break

    return index
