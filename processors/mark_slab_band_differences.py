#!/usr/bin/env python3
"""
Mark Slab Band Differences: Add * markers to annotations hidden by slab band.

Simple: Extract all annotation positions from both SVGs, mark those in no_slab
that don't exist in with_slab.
"""

import re
from pathlib import Path


def extract_all_annotation_positions(svg_path):
    """
    Extract all annotation positions from SVG.
    Returns: set of (x, y) positions
    """
    positions = set()

    try:
        with open(svg_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()

        # Find all text annotations (numbered labels with our colors)
        # Pattern: <text ... x="X" y="Y" ... style="...fill:#COLOR..."...>NUMBER</text>
        pattern = r'<text[^>]*x="([^"]+)"[^>]*y="([^"]+)"[^>]*style="[^"]*fill:#(?:0000ff|70ff00|00ff00|ff69b4|ff00cd|fb7905|ff7f00|fb0505|ff0000)[^"]*"[^>]*>\d+\*?</text>'

        for match in re.finditer(pattern, svg_content):
            x = float(match.group(1))
            y = float(match.group(2))
            positions.add((x, y))

        return positions

    except Exception as e:
        print(f"  Error reading {svg_path}: {e}")
        return None


def mark_differences(base_dir=None):
    """
    Compare both SVGs and mark annotations that don't exist in with_slab_band.
    """
    print("=" * 60)
    print("Marking Slab Band Differences")
    print("=" * 60)

    if base_dir is None:
        base_dir = Path(__file__).parent.parent
    else:
        base_dir = Path(base_dir)

    svg_no_slab = base_dir / "files" / "Step10_no_slab_band.svg"
    svg_with_slab = base_dir / "files" / "Step10_with_slab_band.svg"

    if not svg_no_slab.exists():
        print(f"  ⚠️  {svg_no_slab} not found")
        return False

    if not svg_with_slab.exists():
        print(f"  ⚠️  {svg_with_slab} not found")
        return False

    # Extract ALL annotation positions from both SVGs
    print(f"  Reading: {svg_no_slab.name}")
    positions_no_slab = extract_all_annotation_positions(svg_no_slab)

    print(f"  Reading: {svg_with_slab.name}")
    positions_with_slab = extract_all_annotation_positions(svg_with_slab)

    if positions_no_slab is None or positions_with_slab is None:
        return False

    print(f"  No slab band: {len(positions_no_slab)} annotations")
    print(f"  With slab band: {len(positions_with_slab)} annotations")

    # Find positions in no_slab that are NOT in with_slab
    missing_positions = positions_no_slab - positions_with_slab

    print(f"  Missing (hidden by slab): {len(missing_positions)} annotations")

    if len(missing_positions) == 0:
        print("  No differences found - no markers to add")
        return True

    # Read the SVG and add asterisks to annotations at missing positions
    with open(svg_no_slab, 'r', encoding='utf-8') as f:
        svg_content = f.read()

    modified_count = 0

    for (x, y) in missing_positions:
        # Find the text element at this exact position and add *
        pattern = rf'(<text[^>]*x="{x}"[^>]*y="{y}"[^>]*>)(\d+)(</text>)'

        new_content = re.sub(pattern, rf'\g<1>\g<2>*\g<3>', svg_content, count=1)

        if new_content != svg_content:
            svg_content = new_content
            modified_count += 1

    # Save the modified SVG
    with open(svg_no_slab, 'w', encoding='utf-8') as f:
        f.write(svg_content)

    print(f"\n  ✅ Added {modified_count} asterisk markers to {svg_no_slab.name}")
    print("=" * 60)
    return True


def run_mark_slab_band_differences():
    """Entry point for the marking script"""
    return mark_differences()


if __name__ == "__main__":
    mark_differences()
