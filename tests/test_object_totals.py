#!/usr/bin/env python3
"""
Test: object_totals must sum every color-marked/detected object.

The pipeline (main.run_pipeline_with_logging) computes data['object_totals']
from the fully-populated data.json:
    color_shapes = blue X-shores + red squares + pink/green/orange/yellow rects
    alum_beams   = sum of every alumBeam* size
    wood         = sum of every wood_*ft count
    crossbars    = crossbar_totals['total']
    frames       = frame_totals['total']
    total        = sum of the five subtotals

This test reproduces that computation and asserts the subtotals add up to the
grand total, and that non-numeric/absent values are treated as 0.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def compute_object_totals(data):
    """Same logic main.py applies after the wood merge."""
    sr = data.get("step_results", {}) or {}

    def _int(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return 0

    color_shapes = sum(_int(sr.get(k)) for k in (
        "step5_blue_X_shapes", "step6_red_squares", "step7_pink_shapes",
        "step8_green_rectangles", "step9_orange_rectangles",
        "step11_yellow_shapes"))
    alum_beams = sum(_int(v) for k, v in sr.items() if k.startswith("alumBeam"))
    wood = sum(_int(v) for k, v in sr.items() if k.startswith("wood_"))
    crossbars = _int((data.get("crossbar_totals") or {}).get("total"))
    frames = _int((data.get("frame_totals") or {}).get("total"))
    total = color_shapes + alum_beams + wood + crossbars + frames
    return {
        "color_shapes": color_shapes, "alum_beams": alum_beams,
        "wood": wood, "crossbars": crossbars, "frames": frames,
        "total": total,
    }


SAMPLE = {
    "step_results": {
        "step5_blue_X_shapes": 65, "step6_red_squares": 46,
        "step7_pink_shapes": 13, "step8_green_rectangles": 96,
        "step9_orange_rectangles": 10, "step11_yellow_shapes": 0,
        "alumBeam9": 34, "alumBeam14": 44, "alumBeam16": 54,
        "wood_9ft": 201, "wood_10ft": 63, "wood_12ft": 288,
    },
    "crossbar_totals": {"total": 238},
    "frame_totals": {"total": 106},
}


def test_subtotals_add_up_to_total():
    t = compute_object_totals(SAMPLE)
    assert t["color_shapes"] == 230
    assert t["alum_beams"] == 132   # 34+44+54
    assert t["wood"] == 552         # 201+63+288
    assert t["crossbars"] == 238
    assert t["frames"] == 106
    assert t["total"] == sum(
        (t["color_shapes"], t["alum_beams"], t["wood"],
         t["crossbars"], t["frames"]))
    assert t["total"] == 1258


def test_missing_and_nonnumeric_are_zero():
    t = compute_object_totals({
        "step_results": {"step5_blue_X_shapes": "5", "alumBeam9": None,
                         "wood_9ft": "oops"},
    })
    assert t["color_shapes"] == 5   # "5" coerced
    assert t["alum_beams"] == 0     # None -> 0
    assert t["wood"] == 0           # "oops" -> 0
    assert t["crossbars"] == 0 and t["frames"] == 0
    assert t["total"] == 5


def test_empty_data_totals_zero():
    t = compute_object_totals({})
    assert t == {"color_shapes": 0, "alum_beams": 0, "wood": 0,
                 "crossbars": 0, "frames": 0, "total": 0}


if __name__ == "__main__":
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"✅ {name}")
            passed += 1
    print(f"\n{passed} test(s) passed — object_totals sums correctly.")
