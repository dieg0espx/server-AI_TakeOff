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
WOOD_COLOR = "#ffff00"          # synthesized wood beams

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


def _overlay_rects(base_svg, out_path, box_layers, label):
    """Overlay colored bounding rectangles onto the gray base. box_layers is
    a list of (boxes, color, prefix). One <rect> per box, drawn before
    </svg> so it sits on top."""
    els = []
    total = 0
    for boxes, color, prefix in box_layers:
        for i, b in enumerate(boxes, 1):
            try:
                x = float(b["x"]); y = float(b["y"])
                w = float(b["width"]); h = float(b["height"])
            except (KeyError, TypeError, ValueError):
                continue
            els.append(
                f'    <rect id="hl_{prefix}_{i}" x="{x}" y="{y}" '
                f'width="{w}" height="{h}" '
                f'style="fill:none;stroke:{color};stroke-width:3;stroke-opacity:1" />'
            )
            total += 1
    if els:
        block = "\n" + "\n".join(els) + "\n"
        svg = base_svg.replace("</svg>", block + "</svg>", 1)
    else:
        svg = base_svg
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"✅ Step18 wrote {out_path} ({label}: {total} element(s) highlighted)")
    return total


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
        for fname, lk in (("greenFrames.json", "rectangles"),
                          ("orangeFrames.json", "rectangles"),
                          ("pinkFrames.json", "rectangles"),
                          ("yellowFrames.json", "rectangles")):
            boxes = _load_boxes(os.path.join(td, fname), lk)
            if boxes:
                frame_layers.append((boxes, FRAME_COLOR, fname[:-5]))
        _overlay_rects(base_svg, os.path.join(base_dir, "frames.svg"),
                       frame_layers, "frames")

        # Wood beams: overlay synthesized lines from the per-group SVGs.
        _build_wood_svg(base_svg, os.path.join(base_dir, "groups"),
                        os.path.join(base_dir, "wood.svg"))

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
