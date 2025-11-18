#!/usr/bin/env python3
"""
Test script for success notification email
Simulates a successful takeoff creation with sample data
"""

from utils.email_notifier import notify_success
from datetime import datetime

# Simulate successful takeoff results
test_upload_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# Sample results data that would come from a real pipeline run
sample_results = {
    "upload_id": test_upload_id,
    "step_results": {
        "step5_blue_X_shapes": 131,
        "step6_red_squares": 131,
        "step7_pink_shapes": 0,
        "step8_green_rectangles": 38,
        "step9_orange_rectangles": 0
    },
    "cloudinary_urls": {
        "original": "https://res.cloudinary.com/demo/image/upload/sample.jpg",
        "step4_results": "https://res.cloudinary.com/demo/image/upload/step4.png",
        "step5_results": "https://res.cloudinary.com/demo/image/upload/step5.png",
        "step6_results": "https://res.cloudinary.com/demo/image/upload/step6.png",
        "step8_results": "https://res.cloudinary.com/demo/image/upload/step8.png",
        "step10_results": "https://res.cloudinary.com/demo/image/upload/step10.png"
    },
    "tracking_url": "https://ttfconstruction.com/ai-takeoff-results/read.php?tracking_url=test123"
}

print("=" * 60)
print("Testing Success Notification Email")
print("=" * 60)
print(f"\nUpload ID: {test_upload_id}")
print(f"\nDetection Results:")
print(f"  Blue X Shapes:      {sample_results['step_results']['step5_blue_X_shapes']}")
print(f"  Red Squares:        {sample_results['step_results']['step6_red_squares']}")
print(f"  Pink Shapes:        {sample_results['step_results']['step7_pink_shapes']}")
print(f"  Green Rectangles:   {sample_results['step_results']['step8_green_rectangles']}")
print(f"  Orange Rectangles:  {sample_results['step_results']['step9_orange_rectangles']}")
print(f"  Total Detections:   {sum(sample_results['step_results'].values())}")
print(f"\nSending notification email...")
print("=" * 60)

# Sample console logs
sample_logs = """
==================================================
Running Step1...
==================================================
Removed 613 duplicate paths
✅ Step1 completed successfully:
   - Input SVG: files/original.svg
   - Processed SVG: files/Step1.svg

==================================================
Running Step2...
==================================================
Modifying colors...
✅ Step2 completed successfully:
   - Input SVG: files/Step1.svg
   - Processed SVG: files/Step2.svg

==================================================
Running Step3...
==================================================
✅ Step3 completed successfully:
   - Input SVG: files/Step2.svg
   - Processed SVG: files/Step3.svg

==================================================
Running Step4...
==================================================
Found 833 shores
Found 80 frames (6x4)
✅ Step4 completed successfully

==================================================
Running Step5...
==================================================
Found 131 blue X shapes
✅ Step5 completed successfully

==================================================
Running Step6...
==================================================
Found 131 red squares
✅ Step6 completed successfully

==================================================
Running Step8...
==================================================
Found 38 green rectangles
✅ Step8 completed successfully

============================================================
📊 Processing Summary
============================================================
Steps completed: 10/10
🎉 All steps completed successfully!
"""

# Sample processing duration (in seconds)
sample_duration = 45.67

# Send the success notification with logs
success = notify_success(test_upload_id, sample_results, sample_logs, sample_duration)

if success:
    print("\n✅ Success notification email sent!")
    print(f"Check your inbox for: ✅ [AI TakeOff] New Takeoff Created - {test_upload_id}")
else:
    print("\n❌ Failed to send success notification email.")
    print("Please check your email configuration in .env file")
