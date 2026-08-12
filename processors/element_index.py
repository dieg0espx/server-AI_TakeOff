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


# crossbar line stroke color -> type label. Step13 draws Green/Red/Yellow lines;
# create.php maps Green->crossbar_5, Red->crossbar_6, Yellow->crossbar_7.
_CROSSBAR_COLOR_TYPES = {
    "#00ff00": "crossbar_Green",
    "#ff0000": "crossbar_Red",
    "#ffff00": "crossbar_Yellow",
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
    """Return {line_id: {"category": "crossbars", "type": "crossbar_<Color>"}}."""
    out = {}
    text = None
    try:
        with open(svg_path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return out
    for m in _CROSSBAR_LINE_RE.finditer(text):
        tag = m.group(0)
        lid = m.group("id")
        sm = _STROKE_RE.search(tag)
        color = ("#" + sm.group(1).lower()) if sm else None
        ctype = _CROSSBAR_COLOR_TYPES.get(color, "crossbar")
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
