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

        // The pipeline now sends ALL counts in one block: step_results. It
        // holds crossbars (crossbar_Green/Red/Yellow), per-height frames
        // (frame_4/5/6), per-size alum beams (alumBeam<size>), shores
        // (x_shores/square_shores), and — for older payloads — wood_<N>ft.
        // color_breakdown / crossbar_totals / frame_totals are read only as
        // legacy fallbacks for pre-consolidation payloads.
        $stepResults    = $data['step_results'] ?? [];
        $colorBreakdown = $data['color_breakdown'] ?? [];
        $cbShapes = $colorBreakdown['color_shapes'] ?? [];
        $cbBeams  = $colorBreakdown['alum_beams'] ?? [];
        $cbWood   = $colorBreakdown['wood'] ?? [];

        // Legacy color_breakdown entry -> count ({hex,count}); null if absent.
        $cbCount = function($group, $key) {
            if (isset($group[$key]) && is_array($group[$key]) && isset($group[$key]['count'])) {
                return (int)$group[$key]['count'];
            }
            return null;
        };
        // Read an int count from step_results (primary) with a legacy fallback.
        $srInt = function($key) use ($stepResults) {
            return isset($stepResults[$key]) && is_numeric($stepResults[$key])
                ? (int)$stepResults[$key] : null;
        };

        // Shapes. step_results: x_shores (blue X) + square_shores (red squares).
        // pink/green/orange are no longer detected separately -> 0 unless a
        // legacy color_breakdown carries them.
        $blueXShapes      = $srInt('x_shores')      ?? $cbCount($cbShapes, 'blue')   ?? 0;
        $redSquares       = $srInt('square_shores') ?? $cbCount($cbShapes, 'red')    ?? 0;
        $pinkShapes       = $srInt('pink_shapes')   ?? $cbCount($cbShapes, 'pink')   ?? 0;
        $greenRectangles  = $srInt('green_rectangles') ?? $cbCount($cbShapes, 'green')  ?? 0;
        $orangeRectangles = $srInt('orange_rectangles') ?? $cbCount($cbShapes, 'orange') ?? 0;

        // alumBeam per-size counts from step_results (fallback color_breakdown).
        $beam = function($size) use ($srInt, $cbCount, $cbBeams) {
            return $srInt($size) ?? $cbCount($cbBeams, $size);
        };
        $alumBeam4  = $beam('alumBeam4');
        $alumBeam5  = $beam('alumBeam5');
        $alumBeam6  = $beam('alumBeam6');
        $alumBeam7  = $beam('alumBeam7');
        $alumBeam8  = $beam('alumBeam8');
        $alumBeam9  = $beam('alumBeam9');
        $alumBeam10 = $beam('alumBeam10');
        // 10'6" is written "alumBeam10_6" (current) or "alumBeam106" (legacy).
        $alumBeam106 = $srInt('alumBeam106') ?? $srInt('alumBeam10_6')
                       ?? $cbCount($cbBeams, 'alumBeam10_6') ?? $cbCount($cbBeams, 'alumBeam106');
        $alumBeam11 = $beam('alumBeam11');
        $alumBeam12 = $beam('alumBeam12');
        $alumBeam13 = $beam('alumBeam13');
        $alumBeam14 = $beam('alumBeam14');
        $alumBeam16 = $beam('alumBeam16');
        $alumBeam18 = $beam('alumBeam18');
        $alumBeam20 = $beam('alumBeam20');

        // 4x6 wood-beam counts (legacy: step_results / color_breakdown.wood).
        $wood8ft  = $srInt('wood_8ft')  ?? $cbCount($cbWood, 'wood_8ft');
        $wood9ft  = $srInt('wood_9ft')  ?? $cbCount($cbWood, 'wood_9ft');
        $wood10ft = $srInt('wood_10ft') ?? $cbCount($cbWood, 'wood_10ft');
        $wood12ft = $srInt('wood_12ft') ?? $cbCount($cbWood, 'wood_12ft');

        // Crossbars: step_results per-color keys crossbar_Green/Red/Yellow ->
        // DB crossbar_5/6/7. Legacy crossbar_totals as fallback.
        $crossbarTotals = $data['crossbar_totals'] ?? [];
        $crossbar5 = $srInt('crossbar_Green')  ?? ($crossbarTotals['crossbar_Green']  ?? $crossbarTotals['crossbar_5'] ?? null);
        $crossbar6 = $srInt('crossbar_Red')    ?? ($crossbarTotals['crossbar_Red']    ?? $crossbarTotals['crossbar_6'] ?? null);
        $crossbar7 = $srInt('crossbar_Yellow') ?? ($crossbarTotals['crossbar_Yellow'] ?? $crossbarTotals['crossbar_7'] ?? null);
        $crossbarTotal = $crossbarTotals['total']
            ?? (($crossbar5 ?? 0) + ($crossbar6 ?? 0) + ($crossbar7 ?? 0));

        // Frames: step_results per-height frame_4/5/6 (physical count from
        // frames.svg). DB frame columns are frame_5/frame_6/frame_null ->
        // frame_5->frame_5, frame_6->frame_6, frame_4->frame_null. Legacy
        // frame_totals (frame_2->5, frame_4->6) as fallback.
        $frameTotals = $data['frame_totals'] ?? [];
        $frame5 = $srInt('frame_5') ?? ($frameTotals['frame_2'] ?? $frameTotals['frame_5'] ?? null);
        $frame6 = $srInt('frame_6') ?? ($frameTotals['frame_4'] ?? $frameTotals['frame_6'] ?? null);
        $frameNull = $srInt('frame_4') ?? ($frameTotals['frame_null'] ?? null);
        $frameTotal = (($frame5 ?? 0) + ($frame6 ?? 0) + ($frameNull ?? 0)) ?: ($frameTotals['total'] ?? null);

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

        // Grouped JSON columns: each element category as one {name: count} map.
        // Every listed key is emitted with null coerced to 0, so a category
        // always carries its full set (e.g. all 14 alumBeam sizes, zeros
        // included) exactly like {"alumBeam5":19,"alumBeam6":0,...}.
        $jsonZeroFill = function($map) {
            $filled = [];
            foreach ($map as $k => $v) {
                $filled[$k] = ($v === null) ? 0 : (int)$v;
            }
            return json_encode($filled, JSON_UNESCAPED_SLASHES);
        };
        $alumBeamsJson = $jsonZeroFill([
            'alumBeam5' => $alumBeam5, 'alumBeam6' => $alumBeam6,
            'alumBeam7' => $alumBeam7, 'alumBeam8' => $alumBeam8,
            'alumBeam9' => $alumBeam9, 'alumBeam10' => $alumBeam10,
            'alumBeam106' => $alumBeam106, 'alumBeam11' => $alumBeam11,
            'alumBeam12' => $alumBeam12, 'alumBeam13' => $alumBeam13,
            'alumBeam14' => $alumBeam14, 'alumBeam16' => $alumBeam16,
            'alumBeam18' => $alumBeam18, 'alumBeam20' => $alumBeam20,
        ]);
        $shapesJson = $jsonZeroFill([
            'blue_x_shapes' => $blueXShapes, 'red_squares' => $redSquares,
            'pink_shapes' => $pinkShapes, 'green_rectangles' => $greenRectangles,
            'orange_rectangles' => $orangeRectangles,
        ]);
        $crossbarsJson = $jsonZeroFill([
            'crossbar_5' => $crossbar5, 'crossbar_6' => $crossbar6,
            'crossbar_7' => $crossbar7, 'total' => $crossbarTotal,
        ]);
        $framesJson = $jsonZeroFill([
            'frame_5' => $frame5, 'frame_6' => $frame6,
            'frame_null' => $frameNull, 'total' => $frameTotal,
        ]);
        $woodJson = $jsonZeroFill([
            'wood_8ft' => $wood8ft, 'wood_9ft' => $wood9ft,
            'wood_10ft' => $wood10ft, 'wood_12ft' => $wood12ft,
        ]);

        $sql = "INSERT INTO ai_takeoff_results (tracking_url, company, jobsite,
identified_elements, svg_file, svg_files,
alumBeams, shapes, crossbars, frames, wood,
text, status, logs, processing_duration, processing_start_time, processing_end_time)
VALUES (:tracking_url, :company, :jobsite,
:identified_elements, :svg_file, :svg_files,
:alumBeams, :shapes, :crossbars, :frames, :wood,
:text, :status, :logs, :processing_duration, :processing_start_time, :processing_end_time)";

        $stmt = $conn->prepare($sql);
        $stmt->bindValue(':tracking_url', $trackingUrl, PDO::PARAM_STR);
        $stmt->bindValue(':company', $company, PDO::PARAM_STR);
        $stmt->bindValue(':jobsite', $jobsite, PDO::PARAM_STR);

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

    // Counts come from color_breakdown / object_totals (current pipeline) with
    // step_results as a legacy fallback. Require at least one of them so we
    // don't insert an empty record, but no longer mandate step_results.
    $hasCounts = (isset($inputData['color_breakdown']) && is_array($inputData['color_breakdown']))
        || (isset($inputData['object_totals']) && is_array($inputData['object_totals']))
        || (isset($inputData['step_results']) && is_array($inputData['step_results']));
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
