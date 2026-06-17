#!/usr/bin/env python3
"""
Local test runner: runs the processing pipeline against the existing
files/original.svg. Skips PDF download, Convertio conversion, cleanup,
and database steps.
"""

import os
import sys
import json
import shutil

# Ensure we're in the project root
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(__file__), 'api'))

from dotenv import load_dotenv
load_dotenv()


def run_pipeline_no_cleanup():
    """Run the processing pipeline without cleanup or database steps."""
    from main import run_pipeline_with_logging

    print("\n🚀 Running pipeline...")
    print("=" * 60)

    success, failed_step, error_details = run_pipeline_with_logging("local_test")

    if success:
        print("\n🎉 Pipeline completed successfully!")
    else:
        print(f"\n❌ Pipeline failed at {failed_step}: {error_details}")

    return success


def main():
    svg_path = "files/original.svg"
    if not os.path.exists(svg_path):
        print(f"❌ {svg_path} not found — drop your SVG there and re-run.")
        sys.exit(1)
    print(f"✅ Using existing {svg_path} ({os.path.getsize(svg_path):,} bytes)")

    # Patch out destructive cleanup so the local run leaves files/ intact.
    orig_os_remove = os.remove
    orig_rmtree = shutil.rmtree

    def no_remove(path, *args, **kwargs):
        print(f"   [LOCAL TEST] Skipping removal of: {path}")

    os.remove = no_remove
    shutil.rmtree = no_remove

    # Skip the Step14 Gemini rewrite (costs an API call) via env var that
    # Step14.rewrite_text_with_gemini checks on entry.
    os.environ["SKIP_GEMINI"] = "1"

    try:
        success = run_pipeline_no_cleanup()
    finally:
        os.remove = orig_os_remove
        shutil.rmtree = orig_rmtree
        os.environ.pop("SKIP_GEMINI", None)

    if not success:
        sys.exit(1)

    # Remove intermediate PNGs (cairosvg renders + debug visualizations) —
    # they're only needed during detection.
    removed = 0
    for root, _dirs, files in os.walk("files"):
        for name in files:
            if name.lower().endswith(".png"):
                orig_os_remove(os.path.join(root, name))
                removed += 1
    if removed:
        print(f"\n🧹 Removed {removed} intermediate PNG(s) from files/")

    if os.path.exists("data.json"):
        with open("data.json", "r") as f:
            data = json.load(f)
        glyphs = data.get("container_glyphs")
        if glyphs:
            print("\n📊 Final glyph counts:")
            print(json.dumps(glyphs, indent=2))


if __name__ == "__main__":
    main()
