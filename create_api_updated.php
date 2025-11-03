<?php
/**
 * AI TakeOff Results - Create API Endpoint
 * 
 * Receives processing results and stores them in MySQL database
 * Returns a tracking URL for retrieving the data
 * 
 * Method: POST
 * Content-Type: application/json
 */

// Enable error reporting for debugging (disable in production)
error_reporting(E_ALL);
ini_set('display_errors', 0); // Set to 0 in production

// Allow CORS
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: POST, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");
header('Content-Type: application/json');

// Handle preflight OPTIONS request
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// Only accept POST requests
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode([
        'success' => false,
        'error' => 'Method not allowed. Only POST requests are accepted.'
    ]);
    exit();
}

// Database credentials
$host = 'localhost';
$dbname = 'u969084943_name';
$username = 'u969084943_username';
$password = 'Construction2020?';

/**
 * Generate a unique tracking URL
 */
function generateTrackingUrl($conn) {
    // Generate a random 12-character alphanumeric string
    $characters = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ';
    $maxAttempts = 10;
    
    for ($attempt = 0; $attempt < $maxAttempts; $attempt++) {
        $trackingUrl = '';
        for ($i = 0; $i < 12; $i++) {
            $trackingUrl .= $characters[rand(0, strlen($characters) - 1)];
        }
        
        // Check if this tracking URL already exists
        $stmt = $conn->prepare("SELECT COUNT(*) FROM ai_takeoff_results WHERE tracking_url = :tracking_url");
        $stmt->execute(['tracking_url' => $trackingUrl]);
        $count = $stmt->fetchColumn();
        
        if ($count == 0) {
            return $trackingUrl;
        }
    }
    
    // If we couldn't generate a unique URL after max attempts, use timestamp + random
    return uniqid('track_', true);
}

/**
 * Create database connection
 */
function getDbConnection($host, $dbname, $username, $password) {
    try {
        $conn = new PDO(
            "mysql:host=" . $host . ";dbname=" . $dbname . ";charset=utf8mb4",
            $username,
            $password,
            [
                PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES => false
            ]
        );
        return $conn;
    } catch (PDOException $e) {
        error_log("Database connection failed: " . $e->getMessage());
        return null;
    }
}

/**
 * Validate and sanitize input data
 */
function validateInput($data) {
    $errors = [];
    
    // Check if step_results exists
    if (!isset($data['step_results']) || !is_array($data['step_results'])) {
        $errors[] = 'step_results is required and must be an object';
    }
    
    // Check if cloudinary_urls exists
    if (!isset($data['cloudinary_urls']) || !is_array($data['cloudinary_urls'])) {
        $errors[] = 'cloudinary_urls is required and must be an object';
    }
    
    return $errors;
}

/**
 * Insert results into database
 */
function insertResults($conn, $data) {
    try {
        // Generate unique tracking URL
        $trackingUrl = generateTrackingUrl($conn);
        
        // Extract step results
        $stepResults = $data['step_results'] ?? [];
        $blueXShapes = $stepResults['step5_blue_X_shapes'] ?? 0;
        $redSquares = $stepResults['step6_red_squares'] ?? 0;
        $pinkShapes = $stepResults['step7_pink_shapes'] ?? 0;
        $greenRectangles = $stepResults['step8_green_rectangles'] ?? 0;
        $orangeRectangles = $stepResults['step9_orange_rectangles'] ?? 0;
        
        // Extract Cloudinary URLs
        $cloudinaryUrls = $data['cloudinary_urls'] ?? [];
        $url4 = $cloudinaryUrls['step4_results'] ?? null;
        $url5 = $cloudinaryUrls['step5_results'] ?? null;
        $url6 = $cloudinaryUrls['step6_results'] ?? null;
        $url7 = $cloudinaryUrls['step7_results'] ?? null;
        $url8 = $cloudinaryUrls['step8_results'] ?? null;
        $url9 = $cloudinaryUrls['step9_results'] ?? null;
        $url10 = $cloudinaryUrls['step10_results'] ?? null;
        
        // Extract text (professionally rewritten from Step12)
        $text = $data['text'] ?? '';
        
        // Hardcoded company and jobsite values
        $company = 'Test Company';
        $jobsite = 'Test Jobsite';
        
        // Prepare SQL statement
        $sql = "INSERT INTO ai_takeoff_results (
            tracking_url,
            company,
            jobsite,
            blue_x_shapes,
            red_squares,
            pink_shapes,
            green_rectangles,
            orange_rectangles,
            url_4,
            url_5,
            url_6,
            url_7,
            url_8,
            url_9,
            url_10,
            text,
            status
        ) VALUES (
            :tracking_url,
            :company,
            :jobsite,
            :blue_x_shapes,
            :red_squares,
            :pink_shapes,
            :green_rectangles,
            :orange_rectangles,
            :url_4,
            :url_5,
            :url_6,
            :url_7,
            :url_8,
            :url_9,
            :url_10,
            :text,
            :status
        )";
        
        $stmt = $conn->prepare($sql);
        
        // Bind parameters
        $stmt->bindValue(':tracking_url', $trackingUrl, PDO::PARAM_STR);
        $stmt->bindValue(':company', $company, PDO::PARAM_STR);
        $stmt->bindValue(':jobsite', $jobsite, PDO::PARAM_STR);
        $stmt->bindValue(':blue_x_shapes', $blueXShapes, PDO::PARAM_INT);
        $stmt->bindValue(':red_squares', $redSquares, PDO::PARAM_INT);
        $stmt->bindValue(':pink_shapes', $pinkShapes, PDO::PARAM_INT);
        $stmt->bindValue(':green_rectangles', $greenRectangles, PDO::PARAM_INT);
        $stmt->bindValue(':orange_rectangles', $orangeRectangles, PDO::PARAM_INT);
        $stmt->bindValue(':url_4', $url4, PDO::PARAM_STR);
        $stmt->bindValue(':url_5', $url5, PDO::PARAM_STR);
        $stmt->bindValue(':url_6', $url6, PDO::PARAM_STR);
        $stmt->bindValue(':url_7', $url7, PDO::PARAM_STR);
        $stmt->bindValue(':url_8', $url8, PDO::PARAM_STR);
        $stmt->bindValue(':url_9', $url9, PDO::PARAM_STR);
        $stmt->bindValue(':url_10', $url10, PDO::PARAM_STR);
        $stmt->bindValue(':text', $text, PDO::PARAM_STR);
        $stmt->bindValue(':status', 'completed', PDO::PARAM_STR);
        
        // Execute the statement
        $stmt->execute();
        
        // Get the inserted ID
        $insertedId = $conn->lastInsertId();
        
        // Calculate total detections
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
                'total_detections' => $totalDetections,
                'text_length' => strlen($text)
            ]
        ];
        
    } catch (PDOException $e) {
        error_log("Database insert error: " . $e->getMessage());
        return [
            'success' => false,
            'error' => 'Database error occurred'
        ];
    }
}

// Main execution
try {
    // Get raw POST data
    $rawInput = file_get_contents('php://input');
    
    if (empty($rawInput)) {
        http_response_code(400);
        echo json_encode([
            'success' => false,
            'error' => 'No data received'
        ]);
        exit();
    }
    
    // Decode JSON
    $inputData = json_decode($rawInput, true);
    
    if (json_last_error() !== JSON_ERROR_NONE) {
        http_response_code(400);
        echo json_encode([
            'success' => false,
            'error' => 'Invalid JSON format: ' . json_last_error_msg()
        ]);
        exit();
    }
    
    // Validate input
    $validationErrors = validateInput($inputData);
    if (!empty($validationErrors)) {
        http_response_code(400);
        echo json_encode([
            'success' => false,
            'errors' => $validationErrors
        ]);
        exit();
    }
    
    // Connect to database
    $conn = getDbConnection($host, $dbname, $username, $password);
    if (!$conn) {
        http_response_code(500);
        echo json_encode([
            'success' => false,
            'error' => 'Database connection failed'
        ]);
        exit();
    }
    
    // Insert data
    $result = insertResults($conn, $inputData);
    
    if ($result['success']) {
        http_response_code(201);
        echo json_encode($result);
    } else {
        http_response_code(500);
        echo json_encode($result);
    }
    
} catch (Exception $e) {
    error_log("Unexpected error: " . $e->getMessage());
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'An unexpected error occurred'
    ]);
}
?>

