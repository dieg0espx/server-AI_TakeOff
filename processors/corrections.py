#!/usr/bin/env python3
"""
Apply user element corrections to an already-processed takeoff record.

A "correction" is one of:
  - remove:     a false-positive detection. The element is deleted from its
                layer SVG (so the drawing no longer shows it) and dropped from
                identified_elements; counts are recomputed by correct.php.
  - reclassify: the element's type changes (e.g. alumBeam14 -> alumBeam12, or
                greenFrame -> pinkFrame). The layer SVG element is recolored to
                the new type's color and its identified_elements type/category
                is updated.

This is the LIGHTWEIGHT path: instead of re-running the whole detection
pipeline, we fetch the current layer SVG(s) from their public URLs, edit only
the affected elements, re-upload the edited SVG(s), and persist both the new
URLs and the mutated identified_elements to the DB via correct.php.

Element id -> layer SVG mapping:
  alumBeams : alumBeams.svg — <path id="pathNNNN">              (recolor / gray-out)
  crossbars : crossbars.svg — <line id="crossbar_line_...">     (delete / recolor)
  frames    : frames.svg    — <rect id="hl_*Frames_N"> + label  (delete / recolor)
  shores    : shores.svg    — <rect id="hl_*_N">                (delete / recolor)
"""

import os
import re
import sys
import requests

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'api'))

# Reuse the pipeline's palettes so recolors match the original render exactly.
try:
    from processors.Step18 import (ALUM_BEAM_COLORS, ALUM_BEAM_FALLBACK, GRAY,
                                    FRAME_COLOR, SHORE_COLOR_X, SHORE_COLOR_SQUARE)
except Exception:  # pragma: no cover - fallback when imported flat
    from Step18 import (ALUM_BEAM_COLORS, ALUM_BEAM_FALLBACK, GRAY,
                        FRAME_COLOR, SHORE_COLOR_X, SHORE_COLOR_SQUARE)

try:
    from processors.Step13 import CROSS_BAR_COLOR_HEX
except Exception:  # pragma: no cover
    from Step13 import CROSS_BAR_COLOR_HEX

# The MAIN drawing (step11) colors beams with a DIFFERENT palette than the
# alumBeams.svg layer: Step17's color->size map (which mirrors Step11's beam
# palette) is what actually appears on the drawing. Invert it to size->color so
# an assigned/reclassified beam in step11 matches the auto-detected beams.
try:
    from processors.Step17 import ALUM_BEAM_COLORS as _S17_COLOR_TO_SIZE
except Exception:  # pragma: no cover
    from Step17 import ALUM_BEAM_COLORS as _S17_COLOR_TO_SIZE
STEP11_BEAM_COLORS = {size: hexcol for hexcol, (size, *_ ) in _S17_COLOR_TO_SIZE.items()}

# Reuse the exact frame-box/label/crossbar-X drawing helpers so a MANUALLY added
# frame renders identically to an auto-detected one.
try:
    from processors.Step13 import _tri_color_diagonal, color_for_frame
    from processors.Step18 import _corner_text
except Exception:  # pragma: no cover
    from Step13 import _tri_color_diagonal, color_for_frame
    from Step18 import _corner_text

CORRECT_PHP_URL = os.environ.get(
    'CORRECT_API_URL',
    'https://ttfconstruction.com/ai-takeoff-results/correct.php')
READ_PHP_URL = os.environ.get(
    'READ_API_URL',
    'https://ttfconstruction.com/ai-takeoff-results/read.php')
CORRECT_API_KEY = os.environ.get('AITAKEOFF_CORRECT_KEY', 'ttf-correct-2026')


# ── crossbar type ("crossbar_Green") -> hex, for recolor on reclassify ──
def _crossbar_hex(ctype):
    name = ctype.replace('crossbar_', '') if ctype else ''
    return CROSS_BAR_COLOR_HEX.get(name, "#ffff00")


def _category_of(el_id, entry):
    """Category for an element, trusting the stored entry then falling back to
    the id shape (so a correction still routes even with a thin entry)."""
    if isinstance(entry, dict) and entry.get('category'):
        return entry['category']
    if el_id.startswith('crossbar_line_'):
        return 'crossbars'
    if '_container_' in el_id:
        return 'frames'
    if el_id.startswith('x_shape_') or el_id.startswith('red_square_'):
        return 'shores'
    if el_id.startswith('path'):
        return 'alumBeams'
    return 'other'


def _layer_for_category(category):
    return {
        'alumBeams': 'alumBeams',
        'crossbars': 'crossbars',
        'frames': 'frames',
        'shores': 'shores',
    }.get(category)


def _category_for_type(new_type):
    """Category inferred from a type code (for ADDs, where the element isn't yet
    in identified_elements). Mirrors the frontend/PHP inference."""
    t = new_type or ''
    if t.startswith('alumBeam'):
        return 'alumBeams'
    if t.endswith('Frame'):
        return 'frames'
    if t.startswith('shore_'):
        return 'shores'
    if t.startswith('crossbar'):
        return 'crossbars'
    return 'other'


def _fetch_svg(url):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    return r.text


# ─────────────────────────── per-category SVG edits ───────────────────────────

def _edit_alumbeam(svg, el_id, action, new_type):
    """alumBeams.svg: <path id="pathNNNN" ... style="...stroke:#hex...">.
    remove -> recolor to GRAY (blends into the drawing); reclassify -> recolor
    to the new size's color."""
    if action == 'remove':
        target = GRAY
    else:
        key = 'alumBeam106' if new_type == 'alumBeam10_6' else new_type
        target = ALUM_BEAM_COLORS.get(new_type, ALUM_BEAM_COLORS.get(key, ALUM_BEAM_FALLBACK))
    # Recolor every stroke/fill hex inside just this path element's style.
    pat = re.compile(rf'(<path\b[^>]*\bid="{re.escape(el_id)}"[^>]*?/>)', re.DOTALL)
    m = pat.search(svg)
    if not m:
        return svg, False
    tag = m.group(1)
    new_tag = re.sub(r'(stroke|fill):#[0-9a-fA-F]{6}',
                     lambda mm: f'{mm.group(1)}:{target}', tag)
    return svg[:m.start()] + new_tag + svg[m.end():], (new_tag != tag)


def _edit_crossbar(svg, el_id, action, new_type):
    """crossbars.svg: a crossbar is 6 <line> segments sharing a base id
    'crossbar_line_<container>_sX_cY_dZ' (each diagonal = _1 tip, _2 white
    middle, _3 tip). The clicked id may be one segment; operate on ALL segments
    of its whole crossbar (strip the trailing _dN_M to get the container+side
    base, then match every id under it)."""
    # Base up to and including the container/side/color group, before _dN_M.
    mbase = re.match(r'(crossbar_line_.+?_s\d+_c\d+)', el_id)
    base = mbase.group(1) if mbase else el_id
    seg_re = re.compile(rf'\s*<line\b[^>]*\bid="{re.escape(base)}[^"]*"[^>]*?/>',
                        re.DOTALL)
    matches = list(seg_re.finditer(svg))
    if not matches:
        return svg, False
    if action == 'remove':
        # Delete every segment of this crossbar.
        out = svg
        for m in reversed(matches):
            out = out[:m.start()] + out[m.end():]
        return out, True
    # reclassify -> recolor the COLORED tip segments (leave white middles white).
    target = _crossbar_hex(new_type)
    out = svg
    changed = False
    for m in reversed(matches):
        tag = m.group(0)
        # Only touch segments that currently carry a non-white stroke.
        def _recolor(mm):
            return f'stroke:{target}'
        new_tag = re.sub(r'stroke:#(?!ffffff)[0-9a-fA-F]{6}', _recolor, tag)
        if new_tag != tag:
            out = out[:m.start()] + new_tag + out[m.end():]
            changed = True
    return out, changed


def _find_by_el_id(svg, el_id):
    """Find an overlaid rect (frame/shore) by its data-el-id attribute — the
    REAL identified_elements id Step18 now stamps on each rect (the rect's own
    hl_ id is a positional counter that does NOT match identified_elements).
    Returns the match object for the whole <rect .../> element, or None.
    A piggyback rect carries data-el-id AND data-el-id-2, so match either."""
    for attr in ('data-el-id', 'data-el-id-2'):
        m = re.search(rf'<rect\b[^>]*\b{attr}="{re.escape(el_id)}"[^>]*?/>', svg, re.DOTALL)
        if m:
            return m
    return None


def _edit_frame(svg, el_id, action, new_type):
    """frames.svg: each frame is a <rect id="hl_*Frames_i" data-el-id="<container
    id>"> plus a label <text id="layers_*Frames_i">. We locate the rect by its
    data-el-id (== el_id), then also remove its sibling label (same hl_ index).
    remove -> delete rect + label; reclassify -> recolor the rect stroke."""
    m = _find_by_el_id(svg, el_id)
    if not m:
        return svg, False
    tag = m.group(0)
    if action == 'remove':
        out = svg[:m.start()] + svg[m.end():]
        # Remove the sibling label sharing this rect's hl_ index.
        idm = re.search(r'id="hl_([A-Za-z]+_\d+)"', tag)
        if idm:
            lbl = f'layers_{idm.group(1)}'
            lre = re.compile(rf'\s*<text\b[^>]*\bid="{re.escape(lbl)}"[^>]*?>.*?</text>', re.DOTALL)
            out = lre.sub('', out, count=1)
        return out, True
    # reclassify: frames all render the same green in the SVG, so there's no
    # visible recolor; the type change is persisted in identified_elements.
    return svg, True


def _edit_shore(svg, el_id, action, new_type):
    """shores.svg: <rect id="hl_shore_x_i" data-el-id="x_shape_N"> (blue) or
    id="hl_shore_square_i" data-el-id="red_square_N" (red). Match by data-el-id.
    remove -> delete; reclassify -> swap X<->square color."""
    m = _find_by_el_id(svg, el_id)
    if not m:
        return svg, False
    tag = m.group(0)
    if action == 'remove':
        return svg[:m.start()] + svg[m.end():], True
    target = SHORE_COLOR_X if new_type == 'shore_x' else SHORE_COLOR_SQUARE
    new_tag = re.sub(r'stroke:#[0-9a-fA-F]{6}', f'stroke:{target}', tag)
    return svg[:m.start()] + new_tag + svg[m.end():], (new_tag != tag)


_EDITORS = {
    'alumBeams': _edit_alumbeam,
    'crossbars': _edit_crossbar,
    'frames': _edit_frame,
    'shores': _edit_shore,
}

# Gray tone the pipeline uses for "not this element" — matches Step2/Step11.
_STEP11_GRAY = "#4e4e4e"


def _edit_step11(svg, el_id, action, new_type, category):
    """Edit the element in the MAIN drawing (step11.svg). Unlike the per-category
    layers, step11 draws each element as a single tag with its NATIVE id
    (x_shape_N, red_square_N, <color>_container_N, pathNNNN) and a stroke hex —
    so we recolor by id here. Crossbars aren't drawn in step11, so they no-op.

      remove     -> recolor stroke (and any non-none fill) to the drawing gray
      reclassify -> recolor to the new type's color (beams per size; shores
                    x/square; frames stay green)
    """
    # crossbars are drawn as <line> structures only on crossbars.svg — a lone
    # step11 path can't become a real crossbar, but for an ADD we still recolor
    # the clicked path to the crossbar color so the user sees their assignment.
    if category == 'crossbars' and action != 'add':
        return svg, False
    pat = re.compile(rf'(<(?:rect|path)\b[^>]*\bid="{re.escape(el_id)}"[^>]*?/>)', re.DOTALL)
    m = pat.search(svg)
    if not m:
        return svg, False
    tag = m.group(1)

    if action == 'remove':
        target = _STEP11_GRAY
    else:
        # reclassify / add -> the new type's color, using the STEP11 (drawing)
        # palette so it matches the auto-detected beams on the Main view.
        if category == 'alumBeams':
            key = 'alumBeam10_6' if new_type == 'alumBeam106' else new_type
            target = STEP11_BEAM_COLORS.get(key, STEP11_BEAM_COLORS.get(new_type, ALUM_BEAM_FALLBACK))
        elif category == 'shores':
            target = SHORE_COLOR_X if new_type == 'shore_x' else SHORE_COLOR_SQUARE
        elif category == 'crossbars':
            target = _crossbar_hex(new_type)
        elif category == 'frames':
            target = FRAME_COLOR if action == 'add' else None  # frames render green
        else:
            target = None
    if target is None:
        return svg, True    # counted as handled (no visual change needed)

    new_tag = re.sub(r'stroke:#[0-9a-fA-F]{6}',
                     lambda _mm: f'stroke:{target}', tag)
    # Also gray a painted fill on removal so a filled shape doesn't stay colored.
    if action == 'remove':
        new_tag = re.sub(r'fill:#(?!ffffff)(?!none)[0-9a-fA-F]{6}',
                         f'fill:{_STEP11_GRAY}', new_tag)
    return svg[:m.start()] + new_tag + svg[m.end():], (new_tag != tag)


# Frame width label by type: green=4x5, orange=4x6, pink=4x4. Used in the
# per-height stack labels ("<h>H x <W>W").
_FRAME_WIDTH_BY_TYPE = {
    'greenFrame': 4, 'orangeFrame': 4, 'pinkFrame': 4, 'yellowFrame': 4,
}
# Crossbar type name (as sent from the form) -> the span string color_for_frame
# expects. The form sends crossbar_Green/Red/Yellow/Blue; map back to a span so
# color_for_frame() picks the same hex the pipeline would.
_CROSSBAR_TYPE_TO_SPAN = {
    'crossbar_Green': "5'", 'crossbar_Red': "6'",
    'crossbar_Yellow': "7'", 'crossbar_Blue': "4'",
}


def _synthesize_frame_elements(el_id, bbox, per_side, sides, crossbar_type):
    """Build the SVG element strings for a MANUALLY added frame at `bbox`,
    matching how Step13/Step18 render an auto-detected frame:
      - a green highlight rect carrying data-el-id=<el_id> (so it's selectable),
      - one "<h>H x 4W" corner label per physical frame (heights duplicated
        across `sides`), and
      - one tri-colored crossbar X per stack LAYER, per half (left/right).

    Returns (elements: list[str], frame_count, heights, crossbar_count,
    crossbar_color_name). `per_side` is the per-side height stack (e.g. [5, 5]);
    the full frame lists each height `sides` times.
    """
    x, y, w, h = bbox
    INSET, STROKE, HALF_GAP, GAP = 3.0, 2.0, 2.0, 3.0

    heights = [ht for ht in per_side for _ in range(sides)]
    frame_count = len(heights)

    # Crossbar color: derived from the form's crossbar_type (its span) against
    # each layer's frame height. All layers here share the chosen crossbar type,
    # so use it directly for the color + count.
    span = _CROSSBAR_TYPE_TO_SPAN.get(crossbar_type, "7'")
    # Color per layer by the layer's height + span (matches color_for_frame).
    layer_colors = [color_for_frame(ht, span)[0] for ht in per_side] or ["#ffff00"]
    color_name = crossbar_type.replace('crossbar_', '') if crossbar_type else 'Yellow'

    els = []
    # 1) The frame box (green), selectable via data-el-id.
    els.append(
        f'    <rect id="hl_addedFrames_{el_id}" data-el-id="{el_id}" '
        f'x="{x}" y="{y}" width="{w}" height="{h}" '
        f'style="fill:none;stroke:{FRAME_COLOR};stroke-width:3;stroke-opacity:1" />'
    )
    # 2) Corner stack labels — one "<h>H x 4W" per physical frame.
    label_lines = [f"{int(ht)}H x 4W" for ht in heights]
    els.append(_corner_text(f"layers_addedFrames_{el_id}", x + 3, y + h / 2.0,
                            FRAME_COLOR, label_lines))
    # 3) Crossbar X's — left half + right half, one full-height X per layer.
    n_rows = max(1, len(per_side))
    yt, yb = y + INSET, y + h - INSET
    mid = x + w / 2.0
    cells = [(x + INSET, mid - HALF_GAP / 2.0),
             (mid + HALF_GAP / 2.0, x + w - INSET)]
    base = f"crossbar_line_addedFrame_{el_id}"
    for si, (cx0, cx1) in enumerate(cells):
        for ci in range(n_rows):
            color_hex = layer_colors[ci % len(layer_colors)]
            off = ci * GAP
            b = f"{base}_s{si + 1}_c{ci + 1}"
            els += _tri_color_diagonal(f"{b}_d1", (cx0 + off, yt), (cx1 + off, yb), color_hex, STROKE)
            els += _tri_color_diagonal(f"{b}_d2", (cx1 + off, yt), (cx0 + off, yb), color_hex, STROKE)

    # Crossbar count: one crossbar per stack LAYER per side (== frame_count),
    # matching how the pipeline tallies (one colored X-line per frame).
    crossbar_count = frame_count
    return els, frame_count, heights, crossbar_count, color_name


def _inject_before_svg_close(svg, elements):
    """Insert element strings just before </svg>."""
    if not elements:
        return svg, False
    block = "\n" + "\n".join(elements) + "\n"
    return svg.replace("</svg>", block + "</svg>", 1), True


# ─────────────────────────────── orchestration ───────────────────────────────

def apply_corrections(tracking_url, corrections):
    """Apply a list of corrections to the record identified by tracking_url.

    corrections: [{"id": str, "action": "remove"|"reclassify", "new_type"?: str}]

    Steps: read current record -> group corrections by layer -> fetch+edit each
    affected layer SVG -> re-upload -> POST correct.php with new svg_files (so
    the DB refreshes URLs and recomputes counts + identified_elements).

    Returns a dict: {success, applied, skipped, svg_files, counts, error?}.
    """
    from cloudinary_manager import upload_svgs_to_api  # lazy: heavy import

    # ── 1. Load the current record (identified_elements + svg_files) ──
    try:
        r = requests.get(READ_PHP_URL, params={'tracking_url': tracking_url}, timeout=60)
        r.raise_for_status()
        record = r.json().get('data') or {}
    except Exception as e:
        return {'success': False, 'error': f'read.php failed: {e}'}

    elements = record.get('identified_elements') or {}
    svg_files = record.get('svg_files') or {}
    if not svg_files:
        return {'success': False, 'error': 'record has no svg_files to edit'}

    # ── 2. Group corrections by layer; skip unknown/absent ids ──
    #    An ADD targets a gray path NOT yet in identified_elements, so its
    #    category comes from new_type. It's recolored in step11 (where the gray
    #    path lives) in step 3b below, so it doesn't need a category-layer group.
    by_layer = {}          # layer -> list of (correction, entry)
    skipped = []
    for c in corrections:
        el_id = c.get('id', '')
        action = c.get('action')
        if action in ('add', 'add_frame'):
            continue  # handled in dedicated passes below
        entry = elements.get(el_id)
        if el_id == '' or entry is None:
            skipped.append({'id': el_id, 'reason': 'not found in identified_elements'})
            continue
        category = _category_of(el_id, entry)
        layer = _layer_for_category(category)
        if layer is None:
            skipped.append({'id': el_id, 'reason': f'no editable layer for {category}'})
            continue
        by_layer.setdefault(layer, []).append(c)

    has_add = any(c.get('action') in ('add', 'add_frame') for c in corrections)
    if not by_layer and not has_add:
        return {'success': False, 'error': 'no applicable corrections', 'skipped': skipped}

    # ── 3. Fetch, edit, and re-upload each affected layer SVG ──
    applied = []
    edited_paths = []      # (layer, local_path, label) for concurrent upload
    tmp_dir = os.environ.get('CORRECTION_TMP', '/tmp')
    os.makedirs(tmp_dir, exist_ok=True)

    for layer, cs in by_layer.items():
        url = svg_files.get(layer)
        if not url:
            for c in cs:
                skipped.append({'id': c.get('id'), 'reason': f'no {layer} svg url'})
            continue
        try:
            svg = _fetch_svg(url)
        except Exception as e:
            for c in cs:
                skipped.append({'id': c.get('id'), 'reason': f'fetch {layer} failed: {e}'})
            continue

        editor = _EDITORS[layer]
        layer_changed = False
        for c in cs:
            el_id = c['id']
            action = c.get('action')
            new_type = c.get('new_type')
            svg, changed = editor(svg, el_id, action, new_type)
            if changed:
                applied.append({'id': el_id, 'action': action,
                                **({'new_type': new_type} if new_type else {})})
                layer_changed = True
            else:
                skipped.append({'id': el_id, 'reason': f'{el_id} not found in {layer}.svg'})

        if layer_changed:
            local = os.path.join(tmp_dir, f'{layer}_corrected.svg')
            with open(local, 'w', encoding='utf-8') as f:
                f.write(svg)
            edited_paths.append((layer, local, layer))

    # ── 3b. Also edit the MAIN drawing (step11.svg) so corrections show on the
    #        default view, not just the category layer. Reloading the Main view
    #        would otherwise bring a removed false-positive back. ──
    step11_url = svg_files.get('step11')
    if step11_url:
        try:
            s11 = _fetch_svg(step11_url)
            s11_changed = False
            for c in corrections:
                el_id = c.get('id', '')
                action = c.get('action')
                new_type = c.get('new_type')
                if action == 'add':
                    # Category comes from new_type (the path isn't in the index).
                    category = _category_for_type(new_type)
                else:
                    entry = elements.get(el_id)
                    if entry is None:
                        continue
                    category = _category_of(el_id, entry)
                s11, ch = _edit_step11(s11, el_id, action, new_type, category)
                if ch and action == 'add':
                    applied.append({'id': el_id, 'action': 'add', 'new_type': new_type})
                elif not ch and action == 'add':
                    skipped.append({'id': el_id, 'reason': f'{el_id} not found in step11.svg'})
                s11_changed = s11_changed or ch
            if s11_changed:
                local = os.path.join(tmp_dir, 'step11_corrected.svg')
                with open(local, 'w', encoding='utf-8') as f:
                    f.write(s11)
                edited_paths.append(('step11', local, 'step11'))
        except Exception as e:
            print(f"⚠️  corrections: could not edit step11.svg: {e}")

    # ── 3c. ADD_FRAME: synthesize a full frame (box + stack labels + crossbar
    #        X's) at the clicked path's bbox, injected into step11 + frames +
    #        crossbars. Enrich each correction with the computed frame_count/
    #        heights/crossbar info so correct.php can update the index + counts. ──
    frame_adds = [c for c in corrections if c.get('action') == 'add_frame']
    if frame_adds:
        # Cache each affected layer's SVG once, mutate, re-upload.
        layer_svgs = {}     # layer -> current svg text
        layer_touched = set()
        # Prefer an already-edited step11 (from 3b) if present.
        edited_step11 = next((p for (lyr, p, _l) in edited_paths if lyr == 'step11'), None)
        def _get_layer(layer):
            if layer in layer_svgs:
                return layer_svgs[layer]
            if layer == 'step11' and edited_step11:
                txt = open(edited_step11, 'r', encoding='utf-8').read()
            else:
                url = svg_files.get(layer)
                txt = _fetch_svg(url) if url else None
            layer_svgs[layer] = txt
            return txt

        for c in frame_adds:
            el_id = c.get('id', '')
            bbox = c.get('bbox')
            per_side = [int(h) for h in (c.get('per_side_heights') or []) if h]
            sides = int(c.get('sides') or 2)
            crossbar_type = c.get('crossbar_type') or 'crossbar_Yellow'
            frame_type = c.get('new_type') or 'greenFrame'
            if not el_id or not bbox or not per_side:
                skipped.append({'id': el_id, 'reason': 'add_frame needs id + bbox + per_side_heights'})
                continue
            try:
                x = float(bbox['x']); y = float(bbox['y'])
                w = float(bbox['w']); h = float(bbox['h'])
            except (KeyError, TypeError, ValueError):
                skipped.append({'id': el_id, 'reason': 'add_frame bad bbox'})
                continue

            els, frame_count, heights, cb_count, cb_color = _synthesize_frame_elements(
                el_id, (x, y, w, h), per_side, sides, crossbar_type)

            # Inject into step11 (main view) and the frames + crossbars layers.
            for layer in ('step11', 'frames', 'crossbars'):
                txt = _get_layer(layer)
                if not txt:
                    continue
                # frames layer: box + labels; crossbars layer: the X lines;
                # step11: everything (box + labels + X's all show on the drawing).
                if layer == 'frames':
                    inject = [e for e in els if 'crossbar_line_' not in e]
                elif layer == 'crossbars':
                    inject = [e for e in els if 'crossbar_line_' in e]
                else:
                    inject = els
                new_txt, ch = _inject_before_svg_close(txt, inject)
                if ch:
                    layer_svgs[layer] = new_txt
                    layer_touched.add(layer)

            # Enrich the correction in place so correct.php gets the details it
            # needs to update identified_elements + counts.
            c['_frame_count'] = frame_count
            c['_heights'] = heights
            c['_frame_type'] = frame_type
            c['_crossbar_count'] = cb_count
            c['_crossbar_color'] = cb_color
            applied.append({'id': el_id, 'action': 'add_frame',
                            'frame_count': frame_count, 'heights': heights})

        # Write + queue the touched layers for upload (replace any prior queue
        # entry for the same layer so we upload the fully-mutated version).
        for layer in layer_touched:
            local = os.path.join(tmp_dir, f'{layer}_corrected.svg')
            with open(local, 'w', encoding='utf-8') as f:
                f.write(layer_svgs[layer])
            edited_paths = [(l, p, lbl) for (l, p, lbl) in edited_paths if l != layer]
            edited_paths.append((layer, local, layer))

    if not edited_paths:
        return {'success': False, 'error': 'no SVG edits took effect',
                'applied': applied, 'skipped': skipped}

    # ── 4. Upload edited SVGs concurrently -> new public URLs ──
    new_urls = upload_svgs_to_api(edited_paths)   # {layer: url}
    if not new_urls:
        return {'success': False, 'error': 'SVG re-upload failed',
                'applied': applied, 'skipped': skipped}

    # ── 5. Persist: correct.php mutates identified_elements + recomputes counts
    #        + refreshes svg_files with the new URLs. ──
    try:
        resp = requests.post(CORRECT_PHP_URL, json={
            'tracking_url': tracking_url,
            'api_key': CORRECT_API_KEY,
            'corrections': corrections,
            'svg_files': new_urls,
        }, headers={'Content-Type': 'application/json'}, timeout=60)
        resp.raise_for_status()
        php = resp.json()
    except Exception as e:
        return {'success': False, 'error': f'correct.php failed: {e}',
                'applied': applied, 'skipped': skipped, 'svg_files': new_urls}

    if not php.get('success'):
        return {'success': False, 'error': php.get('error', 'correct.php error'),
                'applied': applied, 'skipped': skipped, 'svg_files': new_urls}

    return {
        'success': True,
        'applied': applied,
        'skipped': skipped + (php.get('skipped') or []),
        'svg_files': new_urls,
        'counts': php.get('counts'),
        'identified_elements_count': php.get('identified_elements_count'),
    }
