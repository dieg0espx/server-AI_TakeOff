# Pipeline Fixes - Data.json Step Results Update

**Date:** November 18, 2025

## Issues Fixed

### 1. Step Results Showing Incorrect/Old Values
**Problem:** The `step_results` field in data.json was not being updated with current detection counts.

**Root Causes:**
- Step11 (yellow shape detection) was missing from the pipeline steps list
- Step10 was not updating data.json with the final counts
- The extraction pattern in processors/index.py was missing Step11

**Fixes Applied:**

#### A. Updated `processors/index.py`
**Location:** Lines 104-111, 221-232, 248-258, 298-313

**Changes:**
1. Added Step11 to the `extract_count_from_output` function pattern dictionary
2. Added Step11 to the pipeline steps list (between Step9 and Step10)
3. Added Step11 to the `step_descriptions` dictionary with key "yellow_shapes"
4. Fixed API submission step reference from Step11 to Step12

**Before:**
```python
steps = [
    "Step1", "Step2", "Step3", "Step4",
    "Step5", "Step6", "Step7", "Step8", "Step9",
    "Step10"  # Missing Step11!
]
```

**After:**
```python
steps = [
    "Step1", "Step2", "Step3", "Step4",
    "Step5", "Step6", "Step7", "Step8", "Step9",
    "Step11",  # Yellow shape detection
    "Step10"   # Final summary
]
```

#### B. Updated `processors/Step10.py`
**Location:** Lines 282-312, 370-378

**Changes:**
1. Added `update_data_json_with_counts()` function to update data.json with final counts
2. Integrated the update function into `run_step10()` to automatically update data.json

**New Function Added:**
```python
def update_data_json_with_counts(green_count, pink_count, x_count, red_count, orange_count, yellow_count):
    """Update data.json with current step results"""
    # Loads existing data.json
    # Updates step_results with current counts
    # Writes back to data.json
```

**Integration:**
```python
# In run_step10(), after loading all data:
update_data_json_with_counts(
    len(green_rectangles),
    len(pink_rectangles),
    len(filtered_x_shapes),  # Note: X shapes are filtered for overlaps
    len(red_squares),
    len(orange_rectangles),
    len(yellow_rectangles)
)
```

---

## Current Data.json Structure

After fixes, data.json now contains:

```json
{
    "step_results": {
        "step5_blue_X_shapes": 0,        // Filtered due to overlaps
        "step6_red_squares": 133,
        "step7_pink_shapes": 14,
        "step8_green_rectangles": 97,
        "step9_orange_rectangles": 19,
        "step11_yellow_shapes": 0
    },
    "cloudinary_urls": { ... },
    "extracted_text": "...",
    "rewritten_text": "...",
    "company": "...",
    "jobsite": "...",
    "upload_id": "...",
    "tracking_url": "..."
}
```

---

## Pipeline Execution Flow

### Updated Pipeline Order:
1. **Step1:** Remove duplicate paths
2. **Step2:** Modify colors
3. **Step3:** Add background
4. **Step4:** Apply color coding to patterns
5. **Step5:** Detect blue X shapes
6. **Step6:** Detect red squares
7. **Step7:** Detect pink shapes
8. **Step8:** Detect green rectangles
9. **Step9:** Detect orange rectangles
10. **Step11:** Detect yellow traffic light shapes
11. **Step10:** Draw all containers + **UPDATE DATA.JSON**
12. **Step12:** Send results to API

---

## Helper Script Created

**File:** `update_data_json.py`

A standalone script to manually update data.json with current counts from JSON files:

```bash
python3 update_data_json.py
```

This script:
- Loads all detection JSON files from `files/tempData/`
- Extracts counts for each shape type
- Updates `data.json` with current `step_results`

---

## Testing

### Test Results:
```
✅ Step10 now automatically updates data.json
✅ step_results contains correct counts:
   - Blue X Shapes: 0 (filtered)
   - Red Squares: 133
   - Pink Shapes: 14
   - Green Rectangles: 97
   - Orange Rectangles: 19
   - Yellow Shapes: 0
✅ Total: 263 objects detected
```

### Manual Pipeline Test:
```bash
python3 processors/Step1.py && \
python3 processors/Step2.py && \
python3 processors/Step3.py && \
python3 processors/Step4.py && \
python3 processors/Step5.py && \
python3 processors/Step6.py && \
python3 processors/Step7.py && \
python3 processors/Step8.py && \
python3 processors/Step9.py && \
python3 processors/Step11.py && \
python3 processors/Step10.py
```

Result: ✅ All steps complete, data.json updated correctly

---

## Important Notes

### X Shapes Filtering
- Step5 detects 125 X shapes initially
- Step10 filters out X shapes that overlap with red squares
- Final count in data.json: 0 (all X shapes overlapped with red squares)
- This is **expected behavior** and not a bug

### Yellow Shapes
- Step11 detection is working correctly
- Current count: 0 (no yellow shapes in original.svg match the patterns)
- Pattern variations have been added to PatternComponents.py
- Will detect shapes when matching patterns are present

### Extracted Text
- The `extracted_text` and `rewritten_text` fields are populated by the PDF extraction process
- These fields are **NOT** managed by the shape detection pipeline
- They remain in data.json from the PDF processing step
- If they appear empty, the issue is in the PDF extraction API, not the shape detection pipeline

---

## Files Modified

1. **processors/index.py**
   - Added Step11 to pipeline
   - Fixed Step11 pattern extraction
   - Fixed API submission reference (Step11 → Step12)

2. **processors/Step10.py**
   - Added update_data_json_with_counts() function
   - Integrated automatic data.json updates

3. **update_data_json.py** (new file)
   - Standalone script for manual data.json updates

---

## Verification Commands

### Check data.json step_results:
```bash
cat data.json | python3 -m json.tool | grep -A 10 "step_results"
```

### Check all JSON detection files:
```bash
ls -lh files/tempData/*.json
```

### Run manual update:
```bash
python3 update_data_json.py
```

---

*End of Pipeline Fixes Document*
