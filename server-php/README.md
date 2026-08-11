# Server-side PHP (reference copies)

These PHP endpoints run on the TTF hosting server, NOT from this Python repo:

    ttfconstruction.com/public_html/ai-takeoff-results/

They are checked in here for version tracking only. Editing a file here does
NOT deploy it — upload via SSH/SCP to the server path above.

## create.php
Receives the pipeline payload (Step15.send_to_api POSTs to create.php) and
inserts a row into `ai_takeoff_results`, returning a tracking_url.

Counts are read from, in priority order:
  1. color_breakdown / object_totals  (current pipeline summaries)
  2. step_results                      (legacy fallback)

step_results is NO LONGER required or sent — the Python side excludes it
(processors/Step15.py DB_EXCLUDE). Crossbar/frame color keys are mapped into
the existing DB columns: crossbar_Green/Red/Yellow -> crossbar_5/6/7,
frame_2/frame_4 -> frame_5/frame_6.

Server backup before this change:
  create.php.bak_before_totals_20260810_2215
