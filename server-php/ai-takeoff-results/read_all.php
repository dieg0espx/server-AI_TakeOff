<?php
  /**
   * AI TakeOff Results - Read All API Endpoint
   *                                                                                                                            
   * Retrieves all processing results with pagination support
   *                                                                                                                            
   * Method: GET                                                                                                              
   * Parameters:
   *   - limit (optional, default: 50) - Number of records to return                                                            
   *   - offset (optional, default: 0) - Number of records to skip
   *   - company (optional) - Filter by company name                                                                            
   *   - jobsite (optional) - Filter by jobsite name                                                                          
   *                                                                                                                            
   * Example: read_all.php?limit=20&offset=0                                                                                  
   */                                                                                                                           
                                                                                                                              
  error_reporting(E_ALL);
  ini_set('display_errors', 0);
                                                                                                                                
  header("Access-Control-Allow-Origin: *");
  header("Access-Control-Allow-Methods: GET, OPTIONS");                                                                         
  header("Access-Control-Allow-Headers: Content-Type");                                                                       
  header('Content-Type: application/json');                                                                                     
   
  if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {                                                                               
      http_response_code(200);                                                                                                
      exit();                                                                                                                   
  }
                                                                                                                                
  if ($_SERVER['REQUEST_METHOD'] !== 'GET') {                                                                                 
      http_response_code(405);
      echo json_encode([
          'success' => false,
          'error' => 'Method not allowed. Only GET requests are accepted.'                                                      
      ]);
      exit();                                                                                                                   
  }                                                                                                                           

  $host = 'localhost';
  $dbname = 'u969084943_name';
  $username = 'u969084943_username';                                                                                            
  $password = 'Construction2020?';
                                                                                                                                
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
                                                                                                                              
  function getTotalCount($conn, $filters) {
      try {
          $sql = "SELECT COUNT(*) as total FROM ai_takeoff_results";
          $conditions = [];                                                                                                     
          $params = [];
                                                                                                                                
          if (!empty($filters['company'])) {                                                                                  
              $conditions[] = "company = :company";
              $params['company'] = $filters['company'];                                                                         
          }
                                                                                                                                
          if (!empty($filters['jobsite'])) {                                                                                  
              $conditions[] = "jobsite = :jobsite";
              $params['jobsite'] = $filters['jobsite'];                                                                         
          }
                                                                                                                                
          if (!empty($conditions)) {                                                                                          
              $sql .= " WHERE " . implode(" AND ", $conditions);
          }                                                                                                                     
   
          $stmt = $conn->prepare($sql);                                                                                         
          $stmt->execute($params);                                                                                            
          $result = $stmt->fetch();
                                                                                                                                
          return (int)$result['total'];
      } catch (PDOException $e) {                                                                                               
          error_log("Count query error: " . $e->getMessage());                                                                
          return 0;                                                                                                             
      }
  }                                                                                                                             
                                                                                                                              
  function getAllResults($conn, $limit, $offset, $filters) {
      try {
          $sql = "SELECT
              id, tracking_url, run_date, company, jobsite,
              svg_file, svg_files, text, status, created_at,
              identified_elements,
              alumBeams, shapes, crossbars, frames, wood,
              logs
          FROM ai_takeoff_results";                                                                                             
                                                                                                                                
          $conditions = [];
          $params = [];                                                                                                         
                                                                                                                              
          if (!empty($filters['company'])) {
              $conditions[] = "company = :company";
              $params['company'] = $filters['company'];
          }
                                                                                                                                
          if (!empty($filters['jobsite'])) {
              $conditions[] = "jobsite = :jobsite";                                                                             
              $params['jobsite'] = $filters['jobsite'];                                                                       
          }                                                                                                                     
   
          if (!empty($conditions)) {                                                                                            
              $sql .= " WHERE " . implode(" AND ", $conditions);                                                              
          }

          $sql .= " ORDER BY created_at DESC LIMIT :limit OFFSET :offset";                                                      
   
          $stmt = $conn->prepare($sql);                                                                                         
                                                                                                                              
          foreach ($params as $key => $value) {
              $stmt->bindValue(':' . $key, $value);
          }                                                                                                                     
   
          $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);                                                                   
          $stmt->bindValue(':offset', $offset, PDO::PARAM_INT);                                                               
                                                                                                                                
          $stmt->execute();                                                                                                   
          $results = $stmt->fetchAll();
                                                                                                                                
          // Counts now live in the grouped JSON columns. Decode each into an
          // associative array ({} / null -> empty array) and read counts by key.
          $decode = function($json) {
              if ($json === null || $json === '') return [];
              $arr = json_decode($json, true);
              return is_array($arr) ? $arr : [];
          };
          $g = function($arr, $key) { return (int)($arr[$key] ?? 0); };

          $formattedResults = [];
          foreach ($results as $result) {
              $shapes    = $decode($result['shapes'] ?? null);
              $alumBeams = $decode($result['alumBeams'] ?? null);
              $wood      = $decode($result['wood'] ?? null);
              $crossbars = $decode($result['crossbars'] ?? null);
              $frames    = $decode($result['frames'] ?? null);

              $totalDetections =
                  $g($shapes, 'blue_x_shapes') +
                  $g($shapes, 'red_squares') +
                  $g($shapes, 'pink_shapes') +
                  $g($shapes, 'green_rectangles') +
                  $g($shapes, 'orange_rectangles');

              $totalAlumBeams =
                  $g($alumBeams, 'alumBeam4') + $g($alumBeams, 'alumBeam5') +
                  $g($alumBeams, 'alumBeam6') + $g($alumBeams, 'alumBeam7') +
                  $g($alumBeams, 'alumBeam8') + $g($alumBeams, 'alumBeam9') +
                  $g($alumBeams, 'alumBeam10') + $g($alumBeams, 'alumBeam106') +
                  $g($alumBeams, 'alumBeam11') + $g($alumBeams, 'alumBeam12') +
                  $g($alumBeams, 'alumBeam13') + $g($alumBeams, 'alumBeam14') +
                  $g($alumBeams, 'alumBeam16') + $g($alumBeams, 'alumBeam18') +
                  $g($alumBeams, 'alumBeam20');

              $totalWoodBeams =
                  $g($wood, 'wood_8ft') + $g($wood, 'wood_9ft') +
                  $g($wood, 'wood_10ft') + $g($wood, 'wood_12ft');

              $crossbar5 = $g($crossbars, 'crossbar_5');
              $crossbar6 = $g($crossbars, 'crossbar_6');
              $crossbar7 = $g($crossbars, 'crossbar_7');
              $crossbarTotal = $g($crossbars, 'total');
              if ($crossbarTotal === 0) {
                  $crossbarTotal = $crossbar5 + $crossbar6 + $crossbar7;
              }

              $frame5 = $g($frames, 'frame_5');
              $frame6 = $g($frames, 'frame_6');
              $frameNull = $g($frames, 'frame_null');
              $frameTotal = $g($frames, 'total');
              if ($frameTotal === 0) {
                  $frameTotal = $frame5 + $frame6 + $frameNull;
              }

              $formattedResults[] = [
                  'id' => (int)$result['id'],
                  'tracking_url' => $result['tracking_url'],
                  'run_date' => $result['run_date'],
                  'created_at' => $result['created_at'],
                  'status' => $result['status'],
                  'company' => $result['company'],
                  'jobsite' => $result['jobsite'],
                  'text' => $result['text'] ?? '',
                  'svg_file' => $result['svg_file'] ?? '',
                  // svg_files holds the per-layer URL map as JSON in the DB;
                  // decode it so clients get an object, {} when unset.
                  'svg_files' => (isset($result['svg_files']) && $result['svg_files'] !== '')
                      ? (json_decode($result['svg_files'], true) ?: new stdClass())
                      : new stdClass(),
                  'step_results' => [
                      'blue_x_shapes' => $g($shapes, 'blue_x_shapes'),
                      'red_squares' => $g($shapes, 'red_squares'),
                      'pink_shapes' => $g($shapes, 'pink_shapes'),
                      'green_rectangles' => $g($shapes, 'green_rectangles'),
                      'orange_rectangles' => $g($shapes, 'orange_rectangles'),
                      'total_detections' => $totalDetections,
                      'aluminum_beams' => $totalAlumBeams,
                      'alumBeam4' => $g($alumBeams, 'alumBeam4'),
                      'alumBeam5' => $g($alumBeams, 'alumBeam5'),
                      'alumBeam6' => $g($alumBeams, 'alumBeam6'),
                      'alumBeam7' => $g($alumBeams, 'alumBeam7'),
                      'alumBeam8' => $g($alumBeams, 'alumBeam8'),
                      'alumBeam9' => $g($alumBeams, 'alumBeam9'),
                      'alumBeam10' => $g($alumBeams, 'alumBeam10'),
                      'alumBeam106' => $g($alumBeams, 'alumBeam106'),
                      'alumBeam11' => $g($alumBeams, 'alumBeam11'),
                      'alumBeam12' => $g($alumBeams, 'alumBeam12'),
                      'alumBeam13' => $g($alumBeams, 'alumBeam13'),
                      'alumBeam14' => $g($alumBeams, 'alumBeam14'),
                      'alumBeam16' => $g($alumBeams, 'alumBeam16'),
                      'alumBeam18' => $g($alumBeams, 'alumBeam18'),
                      'alumBeam20' => $g($alumBeams, 'alumBeam20'),
                  'wood_8ft' => $g($wood, 'wood_8ft'),
                  'wood_9ft' => $g($wood, 'wood_9ft'),
                  'wood_10ft' => $g($wood, 'wood_10ft'),
                  'wood_12ft' => $g($wood, 'wood_12ft'),
                  'wood_4x6_total' => $totalWoodBeams
                  ],
                  'crossbar_totals' => [
                      'crossbar_5' => $crossbar5,
                      'crossbar_6' => $crossbar6,
                      'crossbar_7' => $crossbar7,
                      'crossbar_total' => $crossbarTotal
                  ],
                  'frame_totals' => [
                      'frame_5' => $frame5,
                      'frame_6' => $frame6,
                      'frame_null' => $frameNull,
                      'frame_total' => $frameTotal
                  ],
                  // Canonical per-element path-id index: { path_id: {category, type} }.
                  'identified_elements' => (isset($result['identified_elements']) && $result['identified_elements'] !== '')
                      ? (json_decode($result['identified_elements'], true) ?: new stdClass())
                      : new stdClass(),
                  'cloudinary_urls' => [],
                  'logs' => $result['logs'] ?? ''
              ];
          }
                                                                                                                                
          return [                                                                                                            
              'success' => true,
              'data' => $formattedResults
          ];

      } catch (PDOException $e) {                                                                                               
          error_log("Database query error: " . $e->getMessage());
          return [                                                                                                              
              'success' => false,                                                                                             
              'error' => 'Database error occurred'
          ];
      }
  }                                                                                                                             
   
  try {                                                                                                                         
      $limit = isset($_GET['limit']) ? (int)$_GET['limit'] : 50;                                                              
      $offset = isset($_GET['offset']) ? (int)$_GET['offset'] : 0;
                                                                                                                                
      if ($limit < 1) {
          $limit = 50;                                                                                                          
      }                                                                                                                         
      if ($limit > 100) {
          $limit = 100;                                                                                                         
      }                                                                                                                       

      if ($offset < 0) {
          $offset = 0;
      }

      $filters = [                                                                                                              
          'company' => isset($_GET['company']) ? trim($_GET['company']) : null,
          'jobsite' => isset($_GET['jobsite']) ? trim($_GET['jobsite']) : null                                                  
      ];                                                                                                                        
   
      $conn = getDbConnection($host, $dbname, $username, $password);                                                            
      if (!$conn) {                                                                                                           
          http_response_code(500);                                                                                              
          echo json_encode([
              'success' => false,                                                                                               
              'error' => 'Database connection failed'                                                                         
          ]);
          exit();
      }

      $totalCount = getTotalCount($conn, $filters);                                                                             
      $result = getAllResults($conn, $limit, $offset, $filters);
                                                                                                                                
      if ($result['success']) {                                                                                               
          $result['pagination'] = [
              'total' => $totalCount,                                                                                           
              'count' => count($result['data']),
              'limit' => $limit,                                                                                                
              'offset' => $offset,                                                                                            
              'hasMore' => ($offset + count($result['data'])) < $totalCount                                                     
          ];
                                                                                                                                
          http_response_code(200);                                                                                              
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