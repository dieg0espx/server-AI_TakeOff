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

        detail = data.get('container_glyphs_detail')
        if not detail:
            print("⚠️  No container_glyphs_detail data found in data.json")
            return True

        print("\n📊 Per-Container Details")
        print("=" * 60)

        # Group containers by type
        grouped = {}
        for container_id, info in detail.items():
            ctype = container_id.rsplit('_', 1)[0]
            num = int(container_id.rsplit('_', 1)[1])
            grouped.setdefault(ctype, []).append((num, container_id, info))

        for ctype in sorted(grouped.keys()):
            label = ctype.replace('_', ' ').title()
            containers = sorted(grouped[ctype], key=lambda x: x[0])
            print(f"\n  {label} ({len(containers)} containers)")
            print(f"  {'-' * 56}")

            for num, container_id, info in containers:
                crossbar = info.get('crossbar', 7)
                frame = info.get('frame')
                parts = [f"crossbar={crossbar}"]
                if frame is not None:
                    parts.append(f"frame={frame}")
                print(f"    {container_id}: {' | '.join(parts)}")

        # Totals
        print("\n" + "=" * 60)
        print("  TOTALS")
        print("  " + "-" * 56)

        crossbar_totals = {}
        frame_totals = {}
        for container_id, info in detail.items():
            cb = info.get('crossbar', 7)
            fr = info.get('frame')
            crossbar_totals[cb] = crossbar_totals.get(cb, 0) + 1
            if fr is not None:
                frame_totals[fr] = frame_totals.get(fr, 0) + 1

        print("\n  Crossbars:")
        for val in sorted(crossbar_totals.keys()):
            print(f"    crossbar {val}: {crossbar_totals[val]}")
        print(f"    total: {sum(crossbar_totals.values())}")

        print("\n  Frames:")
        for val in sorted(frame_totals.keys()):
            print(f"    frame {val}: {frame_totals[val]}")
        print(f"    total: {sum(frame_totals.values())}")

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
