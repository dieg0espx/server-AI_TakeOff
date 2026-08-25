<?php
/**
 * AI TakeOff Results - Create API Endpoint
 */

error_reporting(E_ALL);
ini_set('display_errors', 0);

header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");
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

function generateTrackingUrl($conn) {
    $characters = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';
    for ($attempt = 0; $attempt < 10; $attempt++) {
        $trackingUrl = '';
        for ($i = 0; $i < 12; $i++) {
            $trackingUrl .= $characters[rand(0, strlen($characters) - 1)];
        }
        $stmt = $conn->prepare("SELECT COUNT(*) FROM ai_takeoff_results WHERE tracking_url = :tracking_url");
        $stmt->execute(['tracking_url' => $trackingUrl]);
        if ($stmt->fetchColumn() == 0) {
            return $trackingUrl;
        }
    }
    return uniqid('track_', true);
}

function getDbConnection($host, $dbname, $username, $password) {
    try {
        $conn = new PDO("mysql:host=$host;dbname=$dbname;charset=utf8mb4", $username, $password, [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
            PDO::ATTR_EMULATE_PREPARES => false
        ]);
        return $conn;
    } catch (PDOException $e) {
        error_log("Database connection failed: " . $e->getMessage());
        return null;
    }
}

function insertResults($conn, $data) {
    try {
        $trackingUrl = generateTrackingUrl($conn);

        // Count sources, in priority order:
        //   1. color_breakdown / object_totals — the current pipeline's clean
        //      per-color and per-category summaries.
        //   2. step_results — legacy raw counts, kept as a fallback so old
        //      payloads (and any that still send it) still populate columns.
        $stepResults = $data['step_results'] ?? [];
        $colorBreakdown = $data['color_breakdown'] ?? [];
        $cbShapes = $colorBreakdown['color_shapes'] ?? [];
        $cbBeams  = $colorBreakdown['alum_beams'] ?? [];
        $cbWood   = $colorBreakdown['wood'] ?? [];

        // Pull a per-color count out of color_breakdown (each entry is
        // {hex, count} / {hex,color,count}); null if that group is absent.
        $cbCount = function($group, $key) {
            if (isset($group[$key]) && is_array($group[$key]) && isset($group[$key]['count'])) {
                return (int)$group[$key]['count'];
            }
            return null;
        };
        // Prefer breakdown value; fall back to a step_results key; else default.
        $pick = function($primary, $fallback, $default = null) {
            if ($primary !== null) return $primary;
            if ($fallback !== null) return $fallback;
            return $default;
        };

        $blueXShapes      = $pick($cbCount($cbShapes, 'blue'),   $stepResults['step5_blue_X_shapes'] ?? null, 0);
        $redSquares       = $pick($cbCount($cbShapes, 'red'),    $stepResults['step6_red_squares'] ?? null, 0);
        $pinkShapes       = $pick($cbCount($cbShapes, 'pink'),   $stepResults['step7_pink_shapes'] ?? null, 0);
        $greenRectangles  = $pick($cbCount($cbShapes, 'green'),  $stepResults['step8_green_rectangles'] ?? null, 0);
        $orangeRectangles = $pick($cbCount($cbShapes, 'orange'), $stepResults['step9_orange_rectangles'] ?? null, 0);

        // alumBeam counts: prefer color_breakdown.alum_beams[<size>].count,
        // fall back to step_results[<size>].
        $beam = function($size) use ($cbCount, $cbBeams, $stepResults) {
            return $cbCount($cbBeams, $size) ?? ($stepResults[$size] ?? null);
        };
        $alumBeam4  = $beam('alumBeam4');
        $alumBeam5  = $beam('alumBeam5');
        $alumBeam6  = $beam('alumBeam6');
        $alumBeam7  = $beam('alumBeam7');
        $alumBeam8  = $beam('alumBeam8');
        $alumBeam9  = $beam('alumBeam9');
        $alumBeam10 = $beam('alumBeam10');
        // 10'6" is written "alumBeam10_6" (current) or "alumBeam106" (legacy).
        $alumBeam106 = $cbCount($cbBeams, 'alumBeam10_6') ?? $cbCount($cbBeams, 'alumBeam106')
                       ?? $stepResults['alumBeam10_6'] ?? $stepResults['alumBeam106'] ?? null;
        $alumBeam11 = $beam('alumBeam11');
        $alumBeam12 = $beam('alumBeam12');
        $alumBeam13 = $beam('alumBeam13');
        $alumBeam14 = $beam('alumBeam14');
        $alumBeam16 = $beam('alumBeam16');
        $alumBeam18 = $beam('alumBeam18');
        $alumBeam20 = $beam('alumBeam20');

        // 4x6 wood-beam counts: prefer color_breakdown.wood[wood_Nft].count.
        $wood8ft  = $cbCount($cbWood, 'wood_8ft')  ?? ($stepResults['wood_8ft'] ?? null);
        $wood9ft  = $cbCount($cbWood, 'wood_9ft')  ?? ($stepResults['wood_9ft'] ?? null);
        $wood10ft = $cbCount($cbWood, 'wood_10ft') ?? ($stepResults['wood_10ft'] ?? null);
        $wood12ft = $cbCount($cbWood, 'wood_12ft') ?? ($stepResults['wood_12ft'] ?? null);

        // Crossbar counts live in step_results as per-color keys (crossbar_
        // Green/Red/Yellow); the DB columns are crossbar_5/6/7. Map Green->5,
        // Red->6, Yellow->7. Fall back to the legacy crossbar_totals block /
        // crossbar_5/6/7 keys for old payloads.
        $stepResults = $data['step_results'] ?? [];
        $crossbarTotals = $data['crossbar_totals'] ?? [];
        $cbSrc = $stepResults + $crossbarTotals;  // step_results wins
        $crossbar5 = $cbSrc['crossbar_Green']  ?? $cbSrc['crossbar_5'] ?? null;
        $crossbar6 = $cbSrc['crossbar_Red']    ?? $cbSrc['crossbar_6'] ?? null;
        $crossbar7 = $cbSrc['crossbar_Yellow'] ?? $cbSrc['crossbar_7'] ?? null;
        $crossbarTotal = $crossbarTotals['total']
            ?? (($crossbar5 ?? 0) + ($crossbar6 ?? 0) + ($crossbar7 ?? 0));

        // Frame totals. Pipeline sends frame_2/frame_4; DB columns are
        // frame_5/frame_6/frame_null. Map frame_2->5, frame_4->6, keeping the
        // legacy frame_5/6/null keys as fallback.
        $frameTotals = $data['frame_totals'] ?? [];
        $frame5 = $frameTotals['frame_2'] ?? $frameTotals['frame_5'] ?? null;
        $frame6 = $frameTotals['frame_4'] ?? $frameTotals['frame_6'] ?? null;
        $frameNull = $frameTotals['frame_null'] ?? null;
        $frameTotal = $frameTotals['total'] ?? null;

        $text = $data['text'] ?? '';
        $company = $data['company'] ?? 'Unknown Company';
        $jobsite = $data['jobsite'] ?? 'Unknown Jobsite';

        // Process log data
        $logs = '';
        if (isset($data['processing_logs']) && is_array($data['processing_logs'])) {
            $logs = json_encode($data['processing_logs'], JSON_UNESCAPED_UNICODE);
        }

        // Identified elements map { element_id: classification } stored as JSON.
        // NULL (not "[]") when absent so the column stays cleanly empty.
        $identifiedElements = null;
        if (isset($data['identified_elements']) && is_array($data['identified_elements'])) {
            $identifiedElements = json_encode($data['identified_elements'], JSON_UNESCAPED_UNICODE);
        }

        // SVG URLs uploaded by the pipeline: { "step11": url, "alumBeams": url,
        // "crossbars": url, "frames": url, "shores": url, "wood": url }.
        // svg_file keeps the step11 URL for existing consumers; the whole map
        // is stored as JSON in svg_files. update_svg.php can still overwrite
        // both later if the upload finished after this insert.
        $svgFiles = null;
        $svgFile = null;
        if (isset($data['svg_urls']) && is_array($data['svg_urls']) && count($data['svg_urls']) > 0) {
            $svgFiles = json_encode($data['svg_urls'], JSON_UNESCAPED_SLASHES);
            $svgFile = $data['svg_urls']['step11'] ?? null;
        }

        $processingDuration = $data['processing_duration'] ?? null;
        $processingStartTime = $data['processing_start_time'] ?? null;
        $processingEndTime = $data['processing_end_time'] ?? null;

        // Grouped JSON columns: each element category as one {name: count} map,
        // built from the same resolved values used for the discrete columns.
        // Null-count entries are dropped so a category only lists what it has.
        $jsonOrNull = function($map) {
            $clean = array_filter($map, function($v) { return $v !== null; });
            return empty($clean) ? null
                : json_encode($clean, JSON_UNESCAPED_SLASHES);
        };
        $alumBeamsJson = $jsonOrNull([
            'alumBeam4' => $alumBeam4, 'alumBeam5' => $alumBeam5,
            'alumBeam6' => $alumBeam6, 'alumBeam7' => $alumBeam7,
            'alumBeam8' => $alumBeam8, 'alumBeam9' => $alumBeam9,
            'alumBeam10' => $alumBeam10, 'alumBeam106' => $alumBeam106,
            'alumBeam11' => $alumBeam11, 'alumBeam12' => $alumBeam12,
            'alumBeam13' => $alumBeam13, 'alumBeam14' => $alumBeam14,
            'alumBeam16' => $alumBeam16, 'alumBeam18' => $alumBeam18,
            'alumBeam20' => $alumBeam20,
        ]);
        $shapesJson = $jsonOrNull([
            'blue_x_shapes' => $blueXShapes, 'red_squares' => $redSquares,
            'pink_shapes' => $pinkShapes, 'green_rectangles' => $greenRectangles,
            'orange_rectangles' => $orangeRectangles,
        ]);
        $crossbarsJson = $jsonOrNull([
            'crossbar_5' => $crossbar5, 'crossbar_6' => $crossbar6,
            'crossbar_7' => $crossbar7, 'total' => $crossbarTotal,
        ]);
        $framesJson = $jsonOrNull([
            'frame_5' => $frame5, 'frame_6' => $frame6,
            'frame_null' => $frameNull, 'total' => $frameTotal,
        ]);
        $woodJson = $jsonOrNull([
            'wood_8ft' => $wood8ft, 'wood_9ft' => $wood9ft,
            'wood_10ft' => $wood10ft, 'wood_12ft' => $wood12ft,
        ]);

        $sql = "INSERT INTO ai_takeoff_results (tracking_url, company, jobsite,
blue_x_shapes, red_squares, pink_shapes, green_rectangles, orange_rectangles,
alumBeam4, alumBeam5, alumBeam6, alumBeam7, alumBeam8, alumBeam9, alumBeam10, alumBeam106, alumBeam11, alumBeam12, alumBeam13, alumBeam14, alumBeam16, alumBeam18, alumBeam20,
wood_8ft, wood_9ft, wood_10ft, wood_12ft,
crossbar_5, crossbar_6, crossbar_7, crossbar_total, frame_5, frame_6, frame_null, frame_total,
identified_elements, svg_file, svg_files,
alumBeams, shapes, crossbars, frames, wood,
text, status, logs, processing_duration, processing_start_time, processing_end_time)
VALUES (:tracking_url, :company, :jobsite, :blue_x_shapes, :red_squares,
:pink_shapes, :green_rectangles, :orange_rectangles,
:alumBeam4, :alumBeam5, :alumBeam6, :alumBeam7, :alumBeam8, :alumBeam9, :alumBeam10, :alumBeam106, :alumBeam11, :alumBeam12, :alumBeam13, :alumBeam14, :alumBeam16, :alumBeam18, :alumBeam20,
:wood_8ft, :wood_9ft, :wood_10ft, :wood_12ft,
:crossbar_5, :crossbar_6, :crossbar_7, :crossbar_total, :frame_5, :frame_6, :frame_null, :frame_total,
:identified_elements, :svg_file, :svg_files,
:alumBeams, :shapes, :crossbars, :frames, :wood,
:text, :status, :logs, :processing_duration, :processing_start_time, :processing_end_time)";

        $stmt = $conn->prepare($sql);
        $stmt->bindValue(':tracking_url', $trackingUrl, PDO::PARAM_STR);
        $stmt->bindValue(':company', $company, PDO::PARAM_STR);
        $stmt->bindValue(':jobsite', $jobsite, PDO::PARAM_STR);
        $stmt->bindValue(':blue_x_shapes', $blueXShapes, PDO::PARAM_INT);
        $stmt->bindValue(':red_squares', $redSquares, PDO::PARAM_INT);
        $stmt->bindValue(':pink_shapes', $pinkShapes, PDO::PARAM_INT);
        $stmt->bindValue(':green_rectangles', $greenRectangles, PDO::PARAM_INT);
        $stmt->bindValue(':orange_rectangles', $orangeRectangles, PDO::PARAM_INT);

        // Bind all alumBeam parameters
        $stmt->bindValue(':alumBeam4', $alumBeam4, PDO::PARAM_INT);
        $stmt->bindValue(':alumBeam5', $alumBeam5, PDO::PARAM_INT);
        $stmt->bindValue(':alumBeam6', $alumBeam6, PDO::PARAM_INT);
        $stmt->bindValue(':alumBeam7', $alumBeam7, PDO::PARAM_INT);
        $stmt->bindValue(':alumBeam8', $alumBeam8, PDO::PARAM_INT);
        $stmt->bindValue(':alumBeam9', $alumBeam9, PDO::PARAM_INT);
        $stmt->bindValue(':alumBeam10', $alumBeam10, PDO::PARAM_INT);
        $stmt->bindValue(':alumBeam106', $alumBeam106, PDO::PARAM_INT);
        $stmt->bindValue(':alumBeam11', $alumBeam11, PDO::PARAM_INT);
        $stmt->bindValue(':alumBeam12', $alumBeam12, PDO::PARAM_INT);
        $stmt->bindValue(':alumBeam13', $alumBeam13, PDO::PARAM_INT);
        $stmt->bindValue(':alumBeam14', $alumBeam14, PDO::PARAM_INT);
        $stmt->bindValue(':alumBeam16', $alumBeam16, PDO::PARAM_INT);
        $stmt->bindValue(':alumBeam18', $alumBeam18, PDO::PARAM_INT);
        $stmt->bindValue(':alumBeam20', $alumBeam20, PDO::PARAM_INT);

        // Bind 4x6 wood-beam parameters
        $stmt->bindValue(':wood_8ft', $wood8ft, PDO::PARAM_INT);
        $stmt->bindValue(':wood_9ft', $wood9ft, PDO::PARAM_INT);
        $stmt->bindValue(':wood_10ft', $wood10ft, PDO::PARAM_INT);
        $stmt->bindValue(':wood_12ft', $wood12ft, PDO::PARAM_INT);

        // Bind crossbar and frame parameters
        $stmt->bindValue(':crossbar_5', $crossbar5, PDO::PARAM_INT);
        $stmt->bindValue(':crossbar_6', $crossbar6, PDO::PARAM_INT);
        $stmt->bindValue(':crossbar_7', $crossbar7, PDO::PARAM_INT);
        $stmt->bindValue(':crossbar_total', $crossbarTotal, PDO::PARAM_INT);
        $stmt->bindValue(':frame_5', $frame5, PDO::PARAM_INT);
        $stmt->bindValue(':frame_6', $frame6, PDO::PARAM_INT);
        $stmt->bindValue(':frame_null', $frameNull, PDO::PARAM_INT);
        $stmt->bindValue(':frame_total', $frameTotal, PDO::PARAM_INT);

        // JSON string, or SQL NULL when no map was supplied.
        if ($identifiedElements === null) {
            $stmt->bindValue(':identified_elements', null, PDO::PARAM_NULL);
        } else {
            $stmt->bindValue(':identified_elements', $identifiedElements, PDO::PARAM_STR);
        }

        if ($svgFile === null) {
            $stmt->bindValue(':svg_file', null, PDO::PARAM_NULL);
        } else {
            $stmt->bindValue(':svg_file', $svgFile, PDO::PARAM_STR);
        }
        if ($svgFiles === null) {
            $stmt->bindValue(':svg_files', null, PDO::PARAM_NULL);
        } else {
            $stmt->bindValue(':svg_files', $svgFiles, PDO::PARAM_STR);
        }

        // Grouped JSON columns (LONGTEXT string, or SQL NULL when empty).
        foreach ([':alumBeams' => $alumBeamsJson, ':shapes' => $shapesJson,
                  ':crossbars' => $crossbarsJson, ':frames' => $framesJson,
                  ':wood' => $woodJson] as $ph => $val) {
            if ($val === null) {
                $stmt->bindValue($ph, null, PDO::PARAM_NULL);
            } else {
                $stmt->bindValue($ph, $val, PDO::PARAM_STR);
            }
        }

        $stmt->bindValue(':text', $text, PDO::PARAM_STR);
        $stmt->bindValue(':status', 'completed', PDO::PARAM_STR);
        $stmt->bindValue(':logs', $logs, PDO::PARAM_STR);
        $stmt->bindValue(':processing_duration', $processingDuration, PDO::PARAM_STR);
        $stmt->bindValue(':processing_start_time', $processingStartTime, PDO::PARAM_STR);
        $stmt->bindValue(':processing_end_time', $processingEndTime, PDO::PARAM_STR);
        $stmt->execute();

        $insertedId = $conn->lastInsertId();
        $totalDetections = $blueXShapes + $redSquares + $pinkShapes + $greenRectangles + $orangeRectangles;

        return [
            'success' => true,
            'id' => (int)$insertedId,
            'tracking_url' => $trackingUrl,
            'data' => [
                'company' => $company,
                'jobsite' => $jobsite,
                'blue_x_shapes' => $blueXShapes,
                'red_squares' => $redSquares,
                'pink_shapes' => $pinkShapes,
                'green_rectangles' => $greenRectangles,
                'orange_rectangles' => $orangeRectangles,
                'alumBeam4' => $alumBeam4,
                'alumBeam5' => $alumBeam5,
                'alumBeam6' => $alumBeam6,
                'alumBeam7' => $alumBeam7,
                'alumBeam8' => $alumBeam8,
                'alumBeam9' => $alumBeam9,
                'alumBeam10' => $alumBeam10,
                'alumBeam106' => $alumBeam106,
                'alumBeam11' => $alumBeam11,
                'alumBeam12' => $alumBeam12,
                'alumBeam13' => $alumBeam13,
                'alumBeam14' => $alumBeam14,
                'alumBeam16' => $alumBeam16,
                'alumBeam18' => $alumBeam18,
                'alumBeam20' => $alumBeam20,
                'wood_8ft' => $wood8ft,
                'wood_9ft' => $wood9ft,
                'wood_10ft' => $wood10ft,
                'wood_12ft' => $wood12ft,
                'crossbar_5' => $crossbar5,
                'crossbar_6' => $crossbar6,
                'crossbar_7' => $crossbar7,
                'crossbar_total' => $crossbarTotal,
                'frame_5' => $frame5,
                'frame_6' => $frame6,
                'frame_null' => $frameNull,
                'frame_total' => $frameTotal,
                'total_detections' => $totalDetections,
                'svg_file' => $svgFile,
                'svg_files' => $data['svg_urls'] ?? null,
                'identified_elements_count' => is_array($data['identified_elements'] ?? null) ? count($data['identified_elements']) : 0,
                'text_length' => strlen($text),
                'logs_entries' => isset($data['processing_logs']) ? count($data['processing_logs']) : 0,
                'processing_duration' => $processingDuration
            ]
        ];
    } catch (PDOException $e) {
        error_log("Database insert error: " . $e->getMessage());
        return ['success' => false, 'error' => 'Database error occurred'];
    }
}

try {
    $rawInput = file_get_contents('php://input');
    if (empty($rawInput)) {
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'No data received']);
        exit();
    }

    $inputData = json_decode($rawInput, true);
    if (json_last_error() !== JSON_ERROR_NONE) {
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'Invalid JSON format']);
        exit();
    }

    // Counts come from step_results (crossbars, per-height frames, per-size
    // beams, shores); color_breakdown / object_totals are accepted as legacy
    // sources. Require at least one so we don't insert an empty record.
    $hasCounts = (isset($inputData['step_results']) && is_array($inputData['step_results']))
        || (isset($inputData['color_breakdown']) && is_array($inputData['color_breakdown']))
        || (isset($inputData['object_totals']) && is_array($inputData['object_totals']));
    if (!$hasCounts) {
        http_response_code(400);
        echo json_encode(['success' => false, 'error' => 'color_breakdown, object_totals, or step_results is required']);
        exit();
    }

    $conn = getDbConnection($host, $dbname, $username, $password);
    if (!$conn) {
        http_response_code(500);
        echo json_encode(['success' => false, 'error' => 'Database connection failed']);
        exit();
    }

    $result = insertResults($conn, $inputData);
    http_response_code($result['success'] ? 201 : 500);
    echo json_encode($result);

} catch (Exception $e) {
    error_log("Unexpected error: " . $e->getMessage());
    http_response_code(500);
    echo json_encode(['success' => false, 'error' => 'An unexpected error occurred']);
}
?>
