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
    by_layer = {}          # layer -> list of (correction, entry)
    skipped = []
    for c in corrections:
        el_id = c.get('id', '')
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

    if not by_layer:
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
