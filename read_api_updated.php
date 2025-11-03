<?php
/**
 * AI TakeOff Results - Read API Endpoint
 * 
 * Retrieves processing results by tracking URL
 * 
 * Method: GET
 * Parameter: tracking_url (required)
 * 
 * Example: read.php?tracking_url=abc123xyz789
 */

// Enable error reporting for debugging (disable in production)
error_reporting(E_ALL);
ini_set('display_errors', 0); // Set to 0 in production

// Allow CORS
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: GET, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");
header('Content-Type: application/json');

// Handle preflight OPTIONS request
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// Only accept GET requests
if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    http_response_code(405);
    echo json_encode([
        'success' => false,
        'error' => 'Method not allowed. Only GET requests are accepted.'
    ]);
    exit();
}

// Database credentials
$host = 'localhost';
$dbname = 'u969084943_name';
$username = 'u969084943_username';
$password = 'Construction2020?';

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
 * Fetch results by tracking URL
 */
function getResultsByTrackingUrl($conn, $trackingUrl) {
    try {
        $sql = "SELECT 
            id,
            tracking_url,
            run_date,
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
            status,
            created_at
        FROM ai_takeoff_results 
        WHERE tracking_url = :tracking_url
        LIMIT 1";
        
        $stmt = $conn->prepare($sql);
        $stmt->execute(['tracking_url' => $trackingUrl]);
        $result = $stmt->fetch();
        
        if (!$result) {
            return [
                'success' => false,
                'error' => 'No results found for this tracking URL'
            ];
        }
        
        // Calculate total detections
        $totalDetections = 
            (int)$result['blue_x_shapes'] + 
            (int)$result['red_squares'] + 
            (int)$result['pink_shapes'] + 
            (int)$result['green_rectangles'] + 
            (int)$result['orange_rectangles'];
        
        // Format response
        return [
            'success' => true,
            'data' => [
                'id' => (int)$result['id'],
                'tracking_url' => $result['tracking_url'],
                'run_date' => $result['run_date'],
                'created_at' => $result['created_at'],
                'status' => $result['status'],
                'company' => $result['company'],
                'jobsite' => $result['jobsite'],
                'text' => $result['text'] ?? '',
                'step_results' => [
                    'blue_x_shapes' => (int)$result['blue_x_shapes'],
                    'red_squares' => (int)$result['red_squares'],
                    'pink_shapes' => (int)$result['pink_shapes'],
                    'green_rectangles' => (int)$result['green_rectangles'],
                    'orange_rectangles' => (int)$result['orange_rectangles'],
                    'total_detections' => $totalDetections
                ],
                'cloudinary_urls' => [
                    'step4_results' => $result['url_4'],
                    'step5_results' => $result['url_5'],
                    'step6_results' => $result['url_6'],
                    'step7_results' => $result['url_7'],
                    'step8_results' => $result['url_8'],
                    'step9_results' => $result['url_9'],
                    'step10_results' => $result['url_10']
                ]
            ]
        ];
        
    } catch (PDOException $e) {
        error_log("Database query error: " . $e->getMessage());
        return [
            'success' => false,
            'error' => 'Database error occurred'
        ];
    }
}

// Main execution
try {
    // Check if tracking_url parameter is provided
    if (!isset($_GET['tracking_url']) || empty($_GET['tracking_url'])) {
        http_response_code(400);
        echo json_encode([
            'success' => false,
            'error' => 'tracking_url parameter is required',
            'usage' => 'read.php?tracking_url=YOUR_TRACKING_URL'
        ]);
        exit();
    }
    
    $trackingUrl = trim($_GET['tracking_url']);
    
    // Validate tracking URL format (alphanumeric and underscores/dots only)
    if (!preg_match('/^[a-zA-Z0-9._-]+$/', $trackingUrl)) {
        http_response_code(400);
        echo json_encode([
            'success' => false,
            'error' => 'Invalid tracking URL format'
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
    
    // Fetch results
    $result = getResultsByTrackingUrl($conn, $trackingUrl);
    
    if ($result['success']) {
        http_response_code(200);
        echo json_encode($result);
    } else {
        http_response_code(404);
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

