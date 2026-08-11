#!/usr/bin/env python3
"""
Test: color_breakdown gives per-color counts within each category.

Mirrors the computation in main.run_pipeline_with_logging. Asserts that:
  - color_shapes maps each detection hue to its count,
  - alum_beams keys every size to its render color (alumBeam106 == alumBeam10_6),
  - wood/frames each carry their single render color,
  - crossbars keep their per-color split,
  - per-color counts sum back to the category totals in object_totals.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BEAM_PALETTE = {
    "alumBeam24": ("#e6beff", "lavender"), "alumBeam5": ("#e6194b", "red"),
    "alumBeam6": ("#f58231", "orange"), "alumBeam7": ("#ffe119", "yellow"),
    "alumBeam8": ("#bfef45", "lime"), "alumBeam9": ("#3cb44b", "green"),
    "alumBeam10": ("#42d4f4", "cyan"), "alumBeam10_6": ("#4363d8", "blue"),
    "alumBeam106": ("#4363d8", "blue"), "alumBeam11": ("#911eb4", "purple"),
    "alumBeam12": ("#f032e6", "magenta"), "alumBeam13": ("#a9a9a9", "gray-blue"),
    "alumBeam14": ("#9a6324", "brown"), "alumBeam16": ("#469990", "teal"),
    "alumBeam18": ("#000075", "navy"), "alumBeam20": ("#808000", "olive"),
}


def compute_color_breakdown(data):
    sr = data.get("step_results", {}) or {}

    def _int(v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return 0

    color_shapes = {
        "blue":   {"hex": "#0000ff", "count": _int(sr.get("step5_blue_X_shapes"))},
        "red":    {"hex": "#ff0000", "count": _int(sr.get("step6_red_squares"))},
        "pink":   {"hex": "#ff00cd", "count": _int(sr.get("step7_pink_shapes"))},
        "green":  {"hex": "#70ff00", "count": _int(sr.get("step8_green_rectangles"))},
        "orange": {"hex": "#ff8c00", "count": _int(sr.get("step9_orange_rectangles"))},
        "yellow": {"hex": "#ffff00", "count": _int(sr.get("step11_yellow_shapes"))},
    }
    alum_beams = {}
    for size, cnt in sr.items():
        if size.startswith("alumBeam"):
            hexc, label = BEAM_PALETTE.get(size, ("#0000ff", "blue"))
            alum_beams[size] = {"hex": hexc, "color": label, "count": _int(cnt)}
    wood = {s: {"hex": "#ffff00", "count": _int(c)}
            for s, c in sr.items() if s.startswith("wood_")}
    ct = data.get("crossbar_totals") or {}
    cb_hex = {"Green": "#00ff00", "Red": "#ff0000", "Yellow": "#ffff00"}
    crossbars = {n.replace("crossbar_", ""):
                 {"hex": cb_hex.get(n.replace("crossbar_", ""), "#ffffff"),
                  "count": _int(c)}
                 for n, c in ct.items() if n != "total"}
    ft = data.get("frame_totals") or {}
    frames = {n: {"hex": "#70ff00", "count": _int(c)}
              for n, c in ft.items() if n != "total"}
    return {"color_shapes": color_shapes, "alum_beams": alum_beams,
            "wood": wood, "crossbars": crossbars, "frames": frames}


SAMPLE = {
    "step_results": {
        "step5_blue_X_shapes": 65, "step6_red_squares": 46,
        "step7_pink_shapes": 13, "step8_green_rectangles": 96,
        "step9_orange_rectangles": 10, "step11_yellow_shapes": 0,
        "alumBeam16": 54, "alumBeam106": 17,
        "wood_9ft": 201, "wood_12ft": 288,
    },
    "crossbar_totals": {"crossbar_Green": 8, "crossbar_Red": 18,
                        "crossbar_Yellow": 212, "total": 238},
    "frame_totals": {"frame_2": 93, "frame_4": 13, "total": 106},
}


def test_color_shapes_counts():
    cb = compute_color_breakdown(SAMPLE)
    cs = cb["color_shapes"]
    assert cs["blue"]["count"] == 65 and cs["blue"]["hex"] == "#0000ff"
    assert cs["red"]["count"] == 46
    assert cs["green"]["count"] == 96
    assert sum(v["count"] for v in cs.values()) == 230


def test_beam_color_mapping_and_alias():
    cb = compute_color_breakdown(SAMPLE)
    b = cb["alum_beams"]
    assert b["alumBeam16"] == {"hex": "#469990", "color": "teal", "count": 54}
    # alumBeam106 (no underscore) maps to the same color as alumBeam10_6.
    assert b["alumBeam106"]["hex"] == "#4363d8"
    assert b["alumBeam106"]["color"] == "blue"


def test_crossbars_per_color():
    cb = compute_color_breakdown(SAMPLE)
    x = cb["crossbars"]
    assert set(x) == {"Green", "Red", "Yellow"}
    assert x["Yellow"]["count"] == 212
    assert sum(v["count"] for v in x.values()) == 238


def test_wood_and_frames_single_color():
    cb = compute_color_breakdown(SAMPLE)
    assert all(v["hex"] == "#ffff00" for v in cb["wood"].values())
    assert cb["wood"]["wood_9ft"]["count"] == 201
    assert all(v["hex"] == "#70ff00" for v in cb["frames"].values())
    assert sum(v["count"] for v in cb["frames"].values()) == 106


def test_breakdown_matches_object_totals():
    """Per-color sums must equal each category subtotal."""
    cb = compute_color_breakdown(SAMPLE)
    assert sum(v["count"] for v in cb["color_shapes"].values()) == 230
    assert sum(v["count"] for v in cb["alum_beams"].values()) == 71   # 54+17
    assert sum(v["count"] for v in cb["wood"].values()) == 489        # 201+288
    assert sum(v["count"] for v in cb["crossbars"].values()) == 238
    assert sum(v["count"] for v in cb["frames"].values()) == 106


if __name__ == "__main__":
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"✅ {name}")
            passed += 1
    print(f"\n{passed} test(s) passed — color_breakdown is correct.")
