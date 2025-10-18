<?php
/**
 * AI TakeOff Results - Delete API Endpoint
 * 
 * Deletes a processing result by ID
 * 
 * Method: DELETE or GET (for compatibility)
 * Parameter: id (required)
 * 
 * Example: delete.php?id=123
 */

// Enable error reporting for debugging (disable in production)
error_reporting(E_ALL);
ini_set('display_errors', 0); // Set to 0 in production

// Allow CORS
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: DELETE, GET, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type");
header('Content-Type: application/json');

// Handle preflight OPTIONS request
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// Accept both DELETE and GET requests for compatibility
if ($_SERVER['REQUEST_METHOD'] !== 'DELETE' && $_SERVER['REQUEST_METHOD'] !== 'GET') {
    http_response_code(405);
    echo json_encode([
        'success' => false,
        'error' => 'Method not allowed. Only DELETE and GET requests are accepted.'
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
 * Delete result by ID
 */
function deleteResultById($conn, $id) {
    try {
        // First check if the record exists
        $checkSql = "SELECT id, tracking_url FROM ai_takeoff_results WHERE id = :id LIMIT 1";
        $checkStmt = $conn->prepare($checkSql);
        $checkStmt->execute(['id' => $id]);
        $result = $checkStmt->fetch();
        
        if (!$result) {
            return [
                'success' => false,
                'error' => 'Record not found with ID: ' . $id
            ];
        }
        
        // Delete the record
        $deleteSql = "DELETE FROM ai_takeoff_results WHERE id = :id";
        $deleteStmt = $conn->prepare($deleteSql);
        $deleteStmt->execute(['id' => $id]);
        
        if ($deleteStmt->rowCount() > 0) {
            return [
                'success' => true,
                'message' => 'Record deleted successfully',
                'deleted_id' => (int)$id,
                'tracking_url' => $result['tracking_url']
            ];
        } else {
            return [
                'success' => false,
                'error' => 'Failed to delete record'
            ];
        }
        
    } catch (PDOException $e) {
        error_log("Database delete error: " . $e->getMessage());
        return [
            'success' => false,
            'error' => 'Database error occurred while deleting record'
        ];
    }
}

// Main execution
try {
    // Check if id parameter is provided
    if (!isset($_GET['id']) || empty($_GET['id'])) {
        http_response_code(400);
        echo json_encode([
            'success' => false,
            'error' => 'id parameter is required',
            'usage' => 'delete.php?id=YOUR_RECORD_ID'
        ]);
        exit();
    }
    
    $id = trim($_GET['id']);
    
    // Validate ID (must be numeric)
    if (!is_numeric($id) || (int)$id <= 0) {
        http_response_code(400);
        echo json_encode([
            'success' => false,
            'error' => 'Invalid ID format. ID must be a positive integer.'
        ]);
        exit();
    }
    
    $id = (int)$id;
    
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
    
    // Delete the record
    $result = deleteResultById($conn, $id);
    
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

