#!/usr/bin/env python3
"""
Step 13b: Print per-container crossbar and frame from data.json
"""

import os
import json


def run_step13b():
    """Print crossbar and frame for each individual container."""
    try:
        current_dir = os.getcwd()
        base = ".." if current_dir.endswith('processors') else "."
        data_path = f"{base}/data.json"

        if not os.path.exists(data_path):
            print("❌ data.json not found")
            return False

        with open(data_path, 'r') as f:
            data = json.load(f)

        # The per-container detail used to live in `container_glyphs_detail`
        # but was dropped from data.json (bloated the payload without being
        # consumed downstream). Use the aggregate totals Step13 still writes.
        crossbar_totals = data.get('crossbar_totals') or {}
        frame_totals = data.get('frame_totals') or {}

        if not crossbar_totals and not frame_totals:
            print("⚠️  No crossbar/frame totals found in data.json")
            return True

        print("\n📊 Crossbar & Frame Totals")
        print("=" * 60)

        if crossbar_totals:
            print("\n  Crossbars:")
            for k, v in crossbar_totals.items():
                print(f"    {k}: {v}")

        if frame_totals:
            print("\n  Frames:")
            for k, v in frame_totals.items():
                print(f"    {k}: {v}")

        print("\n" + "=" * 60)
        print("✅ Step13b completed")
        return True

    except Exception as e:
        print(f"❌ Error in Step13b: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    return run_step13b()


if __name__ == '__main__':
    from pathlib import Path
    os.chdir(Path(__file__).parent.parent)
    main()
