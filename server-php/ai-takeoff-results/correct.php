<?php
/**
 * AI TakeOff Results - Element Corrections API Endpoint
 *
 * Applies user corrections to a stored takeoff record:
 *   - "remove"      : a false-positive detection is deleted from
 *                     identified_elements and the matching count column is
 *                     decremented.
 *   - "reclassify"  : a detection's type is changed (e.g. alumBeam14 ->
 *                     alumBeam12, or greenFrame -> pinkFrame); counts move from
 *                     the old bucket to the new one.
 *
 * The canonical source of truth is the identified_elements JSON column; the
 * grouped count columns (alumBeams/shapes/crossbars/frames) are recomputed from
 * it after each correction so read.php stays consistent. Optionally refreshes
 * svg_file/svg_files when the Python edit re-uploaded layer SVGs.
 *
 * Guarded by a shared API key (X-Api-Key header or api_key body field) matched
 * against the AITAKEOFF_CORRECT_KEY env var (falls back to a baked default so
 * local dev works without extra config).
 *
 * POST body:
 * {
 *   "tracking_url": "abc123...",
 *   "api_key": "…",                     // or send X-Api-Key header
 *   "corrections": [
 *     { "id": "path14514", "action": "remove" },
 *     { "id": "green_container_3", "action": "reclassify", "new_type": "pinkFrame" }
 *   ],
 *   "svg_files": { "alumBeams": "https://…", ... }  // optional, refreshes URLs
 * }
 */

error_reporting(E_ALL);
ini_set('display_errors', 0);

header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, X-Api-Key");
header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['success' => false, 'error' => 'Method not allowed']);
    exit();
}

$host = 'localhost';
$dbname = 'u969084943_name';
$username = 'u969084943_username';
$password = 'Construction2020?';

// ── Shared-secret guard ──
// The endpoints here have no other auth, so at minimum require a key that only
// our own frontend/pipeline knows. Env override for prod; default for local.
$EXPECTED_KEY = getenv('AITAKEOFF_CORRECT_KEY') ?: 'ttf-correct-2026';

$rawInput = file_get_contents('php://input');
$data = json_decode($rawInput, true);
if (!is_array($data)) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'Invalid JSON body']);
    exit();
}

$providedKey = $_SERVER['HTTP_X_API_KEY'] ?? ($data['api_key'] ?? '');
if (!hash_equals($EXPECTED_KEY, (string)$providedKey)) {
    http_response_code(401);
    echo json_encode(['success' => false, 'error' => 'Unauthorized']);
    exit();
}

$trackingUrl = $data['tracking_url'] ?? '';
$corrections = $data['corrections'] ?? [];
if ($trackingUrl === '' || !is_array($corrections) || count($corrections) === 0) {
    http_response_code(400);
    echo json_encode(['success' => false, 'error' => 'tracking_url and non-empty corrections[] required']);
    exit();
}

/**
 * Map an identified-element {category, type} to the count buckets it occupies,
 * as [['col'=>..., 'key'=>..., 'weight'=>N], ...]. Used to compute the DELTA a
 * single correction applies — we do NOT recompute all counts from the index,
 * because identified_elements and the count columns are not 1:1 (crossbars are
 * indexed per line-SEGMENT, and shore/frame index granularity differs from the
 * detection counts). Delta-adjusting the stored columns keeps every untouched
 * count exactly as the pipeline produced it.
 *
 * Returns [] when the element isn't count-bearing (only identified_elements
 * changes then). A crossbar element is ONE line segment; a whole crossbar is 6
 * segments, so a segment's weight toward the logical crossbar count is 1/6 —
 * callers dedupe by crossbar base so a "remove crossbar" decrements by 1.
 */
function countTargets($entry) {
    if (!is_array($entry)) return [];
    $cat = $entry['category'] ?? '';
    $type = $entry['type'] ?? '';

    if ($cat === 'alumBeams') {
        $key = ($type === 'alumBeam10_6') ? 'alumBeam106' : $type;
        return [['col' => 'alumBeams', 'key' => $key, 'weight' => 1]];
    }
    if ($cat === 'shores') {
        $key = ($type === 'shore_x') ? 'blue_x_shapes'
             : (($type === 'shore_square') ? 'red_squares' : null);
        return $key ? [['col' => 'shapes', 'key' => $key, 'weight' => 1]] : [];
    }
    if ($cat === 'frames') {
        // A frame box holds multiple physical frames split by height. The DB
        // stores counts DOUBLED (2 sides per annotation) — the read layer shows
        // frame_5/frame_6 as physical frames. Use the enriched heights when
        // present; each height is one physical frame in the box's per-side stack
        // duplicated across both sides, i.e. heights already lists every frame.
        $heights = (isset($entry['heights']) && is_array($entry['heights']))
            ? $entry['heights'] : [];
        $targets = [];
        if (count($heights) > 0) {
            foreach ($heights as $h) {
                $hk = ((int)$h === 5) ? 'frame_5'
                    : (((int)$h === 6) ? 'frame_6' : 'frame_null');
                $targets[] = ['col' => 'frames', 'key' => $hk, 'weight' => 1];
            }
        } else {
            $targets[] = ['col' => 'frames', 'key' => 'frame_null', 'weight' => 1];
        }
        return $targets;
    }
    if ($cat === 'crossbars') {
        $map = [
            'crossbar_Green' => 'crossbar_5',
            'crossbar_Red'   => 'crossbar_6',
            'crossbar_Yellow'=> 'crossbar_7',
            'crossbar_Blue'  => 'crossbar_7',
        ];
        $key = $map[$type] ?? 'crossbar_7';
        return [['col' => 'crossbars', 'key' => $key, 'weight' => 1]];
    }
    return [];
}

/** Logical crossbar base for a crossbar_line id, so all 6 segments of one
 *  crossbar collapse to a single unit for counting. */
function crossbarBase($id) {
    if (preg_match('/(crossbar_line_.+?_s\d+_c\d+)/', $id, $m)) return $m[1];
    return $id;
}

/**
 * Apply DELTA adjustments for one correction to the live count column arrays
 * (passed by reference). `sign` is -1 for remove, and for reclassify we call
 * twice: -1 on the old entry then +1 synthesised on the new type.
 */
function applyDelta(&$alumBeams, &$shapes, &$crossbars, &$frames, $entry, $sign) {
    foreach (countTargets($entry) as $t) {
        $col = $t['col']; $key = $t['key']; $w = $t['weight'] * $sign;
        if ($col === 'alumBeams' && array_key_exists($key, $alumBeams)) {
            $alumBeams[$key] = max(0, $alumBeams[$key] + $w);
        } elseif ($col === 'shapes' && array_key_exists($key, $shapes)) {
            $shapes[$key] = max(0, $shapes[$key] + $w);
        } elseif ($col === 'crossbars') {
            $crossbars[$key] = max(0, ($crossbars[$key] ?? 0) + $w);
            $crossbars['total'] = max(0, ($crossbars['total'] ?? 0) + $w);
        } elseif ($col === 'frames') {
            $frames[$key] = max(0, ($frames[$key] ?? 0) + $w);
            $frames['total'] = max(0, ($frames['total'] ?? 0) + $w);
        }
    }
}

try {
    $conn = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $username, $password);
    $conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    // ── Load the current record ──
    $stmt = $conn->prepare("SELECT id, identified_elements, svg_file, svg_files
                            FROM ai_takeoff_results WHERE tracking_url = :t LIMIT 1");
    $stmt->execute(['t' => $trackingUrl]);
    $row = $stmt->fetch(PDO::FETCH_ASSOC);
    if (!$row) {
        http_response_code(404);
        echo json_encode(['success' => false, 'error' => 'Record not found']);
        exit();
    }

    $elements = json_decode($row['identified_elements'] ?? '', true);
    if (!is_array($elements)) $elements = [];

    // ── Apply corrections to identified_elements ──
    // ── Load the CURRENT count columns; we delta-adjust these (never recompute
    //    from the index, which has different granularity than the counts). ──
    $decodeCol = function($json, $defaults) {
        $v = json_decode($json ?? '', true);
        if (!is_array($v)) return $defaults;
        return array_merge($defaults, $v);
    };
    $colStmt = $conn->prepare("SELECT alumBeams, shapes, crossbars, frames
                               FROM ai_takeoff_results WHERE tracking_url = :t LIMIT 1");
    $colStmt->execute(['t' => $trackingUrl]);
    $cols = $colStmt->fetch(PDO::FETCH_ASSOC) ?: [];
    $alumBeams = $decodeCol($cols['alumBeams'] ?? null, [
        'alumBeam5'=>0,'alumBeam6'=>0,'alumBeam7'=>0,'alumBeam8'=>0,'alumBeam9'=>0,
        'alumBeam10'=>0,'alumBeam106'=>0,'alumBeam11'=>0,'alumBeam12'=>0,'alumBeam13'=>0,
        'alumBeam14'=>0,'alumBeam16'=>0,'alumBeam18'=>0,'alumBeam20'=>0]);
    $shapes = $decodeCol($cols['shapes'] ?? null, [
        'blue_x_shapes'=>0,'red_squares'=>0,'pink_shapes'=>0,
        'green_rectangles'=>0,'orange_rectangles'=>0]);
    $crossbars = $decodeCol($cols['crossbars'] ?? null,
        ['crossbar_5'=>0,'crossbar_6'=>0,'crossbar_7'=>0,'total'=>0]);
    $frames = $decodeCol($cols['frames'] ?? null,
        ['frame_5'=>0,'frame_6'=>0,'frame_null'=>0,'total'=>0]);

    // ── Apply each correction: mutate identified_elements AND delta the counts.
    //    Crossbars are indexed per line-segment (6 per crossbar); collapse to
    //    the logical crossbar base so one crossbar counts/deletes exactly once
    //    even if several of its segment ids are sent. ──
    $applied = [];
    $skipped = [];
    $crossbarDone = [];   // base -> true, so we delta a crossbar only once
    foreach ($corrections as $c) {
        $id = $c['id'] ?? '';
        $action = $c['action'] ?? '';

        // ── ADD: assign a type to a previously-undetected element. The id is a
        //    gray path/element NOT yet in identified_elements, so handle it
        //    before the "must exist" guard below. ──
        if ($action === 'add') {
            $newType = $c['new_type'] ?? '';
            if ($id === '' || $newType === '') {
                $skipped[] = ['id' => $id, 'reason' => 'add needs id + new_type'];
                continue;
            }
            if (isset($elements[$id])) {
                $skipped[] = ['id' => $id, 'reason' => 'already assigned'];
                continue;
            }
            $newCat = (substr($newType, 0, 8) === 'alumBeam') ? 'alumBeams'
                : ((substr($newType, -5) === 'Frame') ? 'frames'
                : ((substr($newType, 0, 6) === 'shore_') ? 'shores'
                : ((substr($newType, 0, 9) === 'crossbar_') ? 'crossbars' : 'other')));
            $newEntry = ['category' => $newCat, 'type' => $newType];
            applyDelta($alumBeams, $shapes, $crossbars, $frames, $newEntry, +1);
            $elements[$id] = $newEntry;
            $applied[] = ['id' => $id, 'action' => 'add', 'new_type' => $newType];
            continue;
        }

        // ── ADD_FRAME: a manually-built frame (box + stack + crossbars). The
        //    Python side enriched it with the computed physical-frame breakdown
        //    (_frame_count/_heights) and crossbar info (_crossbar_count/_color).
        //    Store the enriched frame entry and delta frame + crossbar counts. ──
        if ($action === 'add_frame') {
            $newType = $c['new_type'] ?? 'greenFrame';
            $heights = (isset($c['_heights']) && is_array($c['_heights'])) ? $c['_heights'] : [];
            $frameCount = (int)($c['_frame_count'] ?? count($heights));
            if ($id === '' || $frameCount <= 0) {
                $skipped[] = ['id' => $id, 'reason' => 'add_frame needs id + frames'];
                continue;
            }
            if (isset($elements[$id])) {
                $skipped[] = ['id' => $id, 'reason' => 'already assigned'];
                continue;
            }
            // Frame counts: split heights into frame_5/6/null.
            foreach ($heights as $hh) {
                $hk = ((int)$hh === 5) ? 'frame_5' : (((int)$hh === 6) ? 'frame_6' : 'frame_null');
                $frames[$hk] = ($frames[$hk] ?? 0) + 1;
                $frames['total'] = ($frames['total'] ?? 0) + 1;
            }
            // Crossbar counts: each layer has its OWN crossbar, so the Python
            // side tallied per-bucket counts in _crossbar_buckets ({bucket:n}).
            $cbBuckets = (isset($c['_crossbar_buckets']) && is_array($c['_crossbar_buckets']))
                ? $c['_crossbar_buckets'] : [];
            foreach ($cbBuckets as $bk => $bn) {
                if (!in_array($bk, ['crossbar_5','crossbar_6','crossbar_7'], true)) continue;
                $crossbars[$bk] = ($crossbars[$bk] ?? 0) + (int)$bn;
                $crossbars['total'] = ($crossbars['total'] ?? 0) + (int)$bn;
            }
            // Enriched frame entry (mirrors auto-detected frames).
            $sizeStr = implode(' + ', array_map(function($h){ return ((int)$h)."H x 4W"; },
                array_values(array_unique($heights))));
            $elements[$id] = [
                'category' => 'frames', 'type' => $newType,
                'frame_count' => $frameCount, 'heights' => array_map('intval', $heights),
                'frame_size' => $sizeStr,
            ];
            $applied[] = ['id' => $id, 'action' => 'add_frame', 'frame_count' => $frameCount];
            continue;
        }

        if ($id === '' || !isset($elements[$id])) {
            $skipped[] = ['id' => $id, 'reason' => 'not found'];
            continue;
        }
        $entry = $elements[$id];
        $isCrossbar = ($entry['category'] ?? '') === 'crossbars';
        $base = $isCrossbar ? crossbarBase($id) : $id;
        $firstTimeForUnit = !$isCrossbar || empty($crossbarDone[$base]);

        if ($action === 'remove') {
            if ($firstTimeForUnit) {
                applyDelta($alumBeams, $shapes, $crossbars, $frames, $entry, -1);
                if ($isCrossbar) $crossbarDone[$base] = true;
            }
            if ($isCrossbar) {
                // Drop ALL segment entries of this crossbar from the index.
                foreach (array_keys($elements) as $ek) {
                    if (strpos($ek, $base) === 0) unset($elements[$ek]);
                }
            } else {
                unset($elements[$id]);
            }
            $applied[] = ['id' => $id, 'action' => 'remove'];
        } elseif ($action === 'reclassify') {
            $newType = $c['new_type'] ?? '';
            if ($newType === '') {
                $skipped[] = ['id' => $id, 'reason' => 'missing new_type'];
                continue;
            }
            // Delta: -1 old bucket, +1 new bucket (once per logical unit).
            if ($firstTimeForUnit) {
                applyDelta($alumBeams, $shapes, $crossbars, $frames, $entry, -1);
                $newEntry = $entry; $newEntry['type'] = $newType;
                applyDelta($alumBeams, $shapes, $crossbars, $frames, $newEntry, +1);
                if ($isCrossbar) $crossbarDone[$base] = true;
            }
            // Update type/category on the index entr(y/ies).
            $newCat = (substr($newType, 0, 8) === 'alumBeam') ? 'alumBeams'
                : ((substr($newType, -5) === 'Frame') ? 'frames'
                : ((substr($newType, 0, 6) === 'shore_') ? 'shores'
                : ((substr($newType, 0, 9) === 'crossbar_') ? 'crossbars'
                : ($entry['category'] ?? ''))));
            if ($isCrossbar) {
                foreach (array_keys($elements) as $ek) {
                    if (strpos($ek, $base) === 0) {
                        $elements[$ek]['type'] = $newType;
                        $elements[$ek]['category'] = $newCat;
                    }
                }
            } else {
                $elements[$id]['type'] = $newType;
                $elements[$id]['category'] = $newCat;
            }
            $applied[] = ['id' => $id, 'action' => 'reclassify', 'new_type' => $newType];
        } else {
            $skipped[] = ['id' => $id, 'reason' => 'unknown action'];
        }
    }

    // ── Optional SVG-URL refresh (Python re-uploaded edited layer SVGs) ──
    $svgFilesJson = $row['svg_files'];
    $svgFile = $row['svg_file'];
    if (isset($data['svg_files']) && is_array($data['svg_files']) && count($data['svg_files']) > 0) {
        $existing = json_decode($row['svg_files'] ?? '', true);
        if (!is_array($existing)) $existing = [];
        $merged = array_merge($existing, $data['svg_files']);
        $svgFilesJson = json_encode($merged, JSON_UNESCAPED_SLASHES);
        if (isset($merged['step11'])) $svgFile = $merged['step11'];
    }

    // ── Persist ──
    $identifiedJson = count($elements) > 0
        ? json_encode($elements, JSON_UNESCAPED_UNICODE) : null;

    $update = $conn->prepare(
        "UPDATE ai_takeoff_results SET
            identified_elements = :ie,
            alumBeams = :ab, shapes = :sh, crossbars = :cb, frames = :fr,
            svg_file = :svgf, svg_files = :svgs
         WHERE tracking_url = :t");
    $update->bindValue(':ie', $identifiedJson, $identifiedJson === null ? PDO::PARAM_NULL : PDO::PARAM_STR);
    $update->bindValue(':ab', json_encode($alumBeams, JSON_UNESCAPED_SLASHES), PDO::PARAM_STR);
    $update->bindValue(':sh', json_encode($shapes, JSON_UNESCAPED_SLASHES), PDO::PARAM_STR);
    $update->bindValue(':cb', json_encode($crossbars, JSON_UNESCAPED_SLASHES), PDO::PARAM_STR);
    $update->bindValue(':fr', json_encode($frames, JSON_UNESCAPED_SLASHES), PDO::PARAM_STR);
    $update->bindValue(':svgf', $svgFile, $svgFile === null ? PDO::PARAM_NULL : PDO::PARAM_STR);
    $update->bindValue(':svgs', $svgFilesJson, $svgFilesJson === null ? PDO::PARAM_NULL : PDO::PARAM_STR);
    $update->bindValue(':t', $trackingUrl, PDO::PARAM_STR);
    $update->execute();

    echo json_encode([
        'success' => true,
        'tracking_url' => $trackingUrl,
        'applied' => $applied,
        'skipped' => $skipped,
        'counts' => [
            'alumBeams' => $alumBeams,
            'shapes' => $shapes,
            'crossbars' => $crossbars,
            'frames' => $frames,
        ],
        'identified_elements_count' => count($elements),
    ]);

} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'Database error: ' . $e->getMessage()]);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => $e->getMessage()]);
}
