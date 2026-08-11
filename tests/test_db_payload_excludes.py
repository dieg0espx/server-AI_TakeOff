#!/usr/bin/env python3
"""
Test: the DB payload sent by Step15.send_to_api excludes processing metadata
AND step_results (create.php now reads counts from object_totals/
color_breakdown), while leaving the caller's local data dict intact.

We stub requests.post to capture exactly what gets POSTed (the json= kwarg),
so this checks the real payload, not a reimplementation.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "processors"))

import Step15  # noqa: E402


EXCLUDED = {"processing_logs", "processing_duration",
            "processing_start_time", "processing_end_time", "step_results"}

# create.php reads counts from object_totals/color_breakdown, so step_results
# is no longer delivered.
KEPT = {"company", "jobsite", "upload_id", "svg_urls",
        "object_totals", "color_breakdown", "crossbar_totals",
        "frame_totals", "text"}


class _FakeResp:
    status_code = 200

    def json(self):
        return {"success": True, "id": 1, "tracking_url": "TESTTOKEN"}


def _make_data():
    return {
        "company": "BG-Test", "jobsite": "site",
        "upload_id": "abc123",
        "step_results": {"step5_blue_X_shapes": 65, "alumBeam16": 54},
        "crossbar_totals": {"total": 238},
        "frame_totals": {"total": 106},
        "svg_urls": {"step11": "https://x/step11.svg"},
        "object_totals": {"total": 1358},
        "color_breakdown": {"color_shapes": {}},
        "rewritten_text": "plan text",
        "processing_logs": ["a"] * 902,
        "processing_duration": 76.94,
        "processing_start_time": "2026-08-10T21:33:51",
        "processing_end_time": "2026-08-10T21:35:08",
    }


def _capture_payload(monkeypatch_post):
    captured = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        captured["json"] = json
        return _FakeResp()

    Step15.requests.post = fake_post
    return captured


def test_payload_excludes_metadata_and_step_results():
    data = _make_data()
    orig_post = Step15.requests.post
    captured = _capture_payload(orig_post)
    try:
        Step15.send_to_api(data, "http://example.test/create.php")
    finally:
        Step15.requests.post = orig_post

    payload = captured["json"]
    assert payload is not None, "nothing was POSTed"
    for field in EXCLUDED:
        assert field not in payload, f"{field} should NOT be in DB payload"
    for field in KEPT:
        assert field in payload, f"{field} should remain in DB payload"


def test_local_data_dict_untouched():
    """Excluding from the payload must not delete fields from the caller's
    dict — they stay in the local data.json for debugging."""
    data = _make_data()
    orig_post = Step15.requests.post
    _capture_payload(orig_post)
    try:
        Step15.send_to_api(data, "http://example.test/create.php")
    finally:
        Step15.requests.post = orig_post

    for field in EXCLUDED:
        assert field in data, f"{field} was wrongly stripped from local dict"
    assert len(data["processing_logs"]) == 902


if __name__ == "__main__":
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"✅ {name}")
            passed += 1
    print(f"\n{passed} test(s) passed — DB payload excludes metadata, excludes step_results.")
