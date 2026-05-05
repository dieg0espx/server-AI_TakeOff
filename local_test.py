#!/usr/bin/env python3
"""
Local test runner: converts existing original.pdf to SVG via Convertio,
then runs the processing pipeline. Skips download, cleanup, and database steps.
"""

import os
import sys
import asyncio
import json

# Ensure we're in the project root
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(__file__), 'api'))

from dotenv import load_dotenv
load_dotenv()

from api.pdf_to_svg_converter import ConvertioConverter


async def convert_pdf_to_svg():
    """Convert existing original.pdf to original.svg using Convertio."""
    pdf_path = "files/original.pdf"
    svg_path = "files/original.svg"

    if not os.path.exists(pdf_path):
        print(f"❌ {pdf_path} not found")
        return False

    if os.path.exists(svg_path):
        print(f"✅ {svg_path} already exists, skipping conversion")
        return True

    print(f"🔄 Converting {pdf_path} → {svg_path} via Convertio...")
    try:
        converter = ConvertioConverter()
        conv_id = await converter.start_conversion()
        print(f"   Conversion ID: {conv_id}")

        await converter.upload_file(conv_id, pdf_path)
        print(f"   PDF uploaded, waiting for conversion...")

        download_url = await converter.check_status(conv_id)
        print(f"   Conversion complete, downloading SVG...")

        await converter.download_file(download_url, svg_path)
        svg_size = os.path.getsize(svg_path)
        print(f"✅ SVG saved: {svg_path} ({svg_size:,} bytes)")
        return True
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        return False


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


async def main():
    # Step 1: Convert PDF to SVG
    if not await convert_pdf_to_svg():
        sys.exit(1)

    # Step 2: Run pipeline (cleanup is inside run_pipeline_with_logging,
    # so we monkey-patch it out)
    import main as main_module
    import shutil

    # Save original cleanup behavior — replace with no-op
    original_func = shutil.rmtree
    removed_files = []

    def no_remove(path, *args, **kwargs):
        print(f"   [LOCAL TEST] Skipping removal of: {path}")

    def no_os_remove(path, *args, **kwargs):
        print(f"   [LOCAL TEST] Skipping removal of: {path}")

    # Patch os.remove and shutil.rmtree to skip cleanup
    orig_os_remove = os.remove
    os.remove = no_os_remove
    shutil.rmtree = no_remove

    try:
        success = run_pipeline_no_cleanup()
    finally:
        # Restore
        os.remove = orig_os_remove
        shutil.rmtree = original_func

    if not success:
        sys.exit(1)

    # Print final data.json summary
    if os.path.exists("data.json"):
        with open("data.json", "r") as f:
            data = json.load(f)
        glyphs = data.get("container_glyphs")
        if glyphs:
            print("\n📊 Final glyph counts:")
            print(json.dumps(glyphs, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
