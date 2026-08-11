#!/usr/bin/env python3
"""
Test: Step11.svg must have NO gray background.

Two ways a gray full-canvas rect could end up in Step11's output:
  1. Step11 used to inject its own #1c1c1c <rect id="background">.
  2. Step2 leaves a #4e4e4e <rect id="background"> backdrop in the base SVG.

This test asserts that after Step11 builds the SVG:
  - it does NOT inject a #1c1c1c background rect (add_containers_to_svg), and
  - the inherited #4e4e4e background rect is stripped (_BG_4E_RECT_RE),
so the final canvas is transparent.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "processors"))

import Step11  # noqa: E402


# A minimal base SVG that mimics Step2's output: a full-canvas #4e4e4e
# background rect plus one ordinary drawing path.
BASE_SVG = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 3456 2304" '
    'width="3456" height="2304">'
    '<rect id="background" x="0" y="0" width="3456" height="2304" '
    'style="fill:#4e4e4e;stroke:none" />'
    '<path id="path100" style="fill:#4e4e4e;stroke:none" d="M 1 1 H 2 V 2 Z" />'
    '</svg>'
)


def _final_svg():
    """Reproduce Step11's SVG-building + background-strip on the base SVG."""
    built = Step11.add_containers_to_svg(
        BASE_SVG,
        green_rectangles=[],
        pink_rectangles=[],
        x_shapes=[],
        red_squares=[],
        orange_rectangles=[],
        yellow_rectangles=[],
    )
    assert built is not None, "add_containers_to_svg returned None"
    # Same strip Step11.run_step11 applies before saving.
    return Step11._BG_4E_RECT_RE.sub("\n", built)


def test_no_injected_1c1c1c_background():
    """Step11 must not inject its own dark-gray background rect."""
    built = Step11.add_containers_to_svg(
        BASE_SVG, [], [], [], [], [], [],
    )
    assert "#1c1c1c" not in built, (
        "Step11 injected a #1c1c1c background rect; it should not."
    )


def test_no_full_canvas_gray_rect_remains():
    """After the #4e4e4e strip, no gray background rect should survive."""
    final = _final_svg()
    bg_rects = re.findall(
        r'<rect\s+id="background"[^>]*/>', final, re.IGNORECASE
    )
    assert bg_rects == [], f"gray background rect(s) survived: {bg_rects}"
    # No full-canvas gray rect of any id should remain either. (Drawing
    # <path>s may still be #4e4e4e — only full-canvas <rect>s form a backdrop.)
    for r in re.findall(r'<rect\b[^>]*/>', final):
        assert "#4e4e4e" not in r and "#1c1c1c" not in r, (
            f"gray full-canvas rect survived: {r}"
        )


def test_drawing_paths_preserved():
    """Removing the background must not drop the actual drawing content."""
    final = _final_svg()
    assert 'id="path100"' in final, "drawing path was lost"
    assert final.strip().endswith("</svg>"), "SVG is malformed"


if __name__ == "__main__":
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"✅ {name}")
            passed += 1
    print(f"\n{passed} test(s) passed — Step11 has no gray background.")
