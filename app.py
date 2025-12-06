# --- app.py ---

import subprocess
import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# --- Configure Logging ---
# This will log to both console (for Render logs) and optionally to a file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output (visible in Render logs)
        # Uncomment below to also save to file (optional)
        # logging.FileHandler('tito_service.log')
    ]
)
logger = logging.getLogger(__name__)

# Log startup
logger.info("TinyTorch API Service starting up...")

# --- Utility Function to Handle CLI Output ---
def execute_tito_command(args):
    """Executes a tito command and returns its stdout output or raises an error."""
    try:
        # Secure execution: Pass command and arguments as a list.
        command = ['tito'] + args
        logger.info(f"Executing tito command: {' '.join(command)}")
        
        result = subprocess.run(
            command,
            capture_output=True,  # Captures stdout and stderr
            text=True,            # Decodes output as text
            check=True,           # Raise CalledProcessError for non-zero exit codes
            timeout=60            # 60 second timeout to prevent hanging
        )
        
        logger.info(f"Command succeeded. Output length: {len(result.stdout)} chars")
        return result.stdout.strip()
    
    except subprocess.CalledProcessError as e:
        # If tito ran but returned an error exit code
        error_message = f"tito command failed. STDERR: {e.stderr.strip()}"
        logger.error(error_message)
        logger.error(f"Exit code: {e.returncode}")
        raise RuntimeError(error_message) 
    
    except subprocess.TimeoutExpired as e:
        error_message = f"tito command timed out after 60 seconds"
        logger.error(error_message)
        raise RuntimeError(error_message)
    
    except FileNotFoundError:
        # If the 'tito' command itself doesn't exist on the system
        error_message = "The 'tito' command was not found. Check Dockerfile and PATH."
        logger.error(error_message)
        raise RuntimeError(error_message)


# --- API Documentation (HTML) ---
API_DOCS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>TinyTorch API Documentation</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            max-width: 900px; 
            margin: 50px auto; 
            padding: 20px;
            background: #f5f5f5;
        }
        .endpoint { 
            background: white; 
            padding: 20px; 
            margin: 20px 0; 
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .method { 
            display: inline-block;
            padding: 5px 10px; 
            border-radius: 4px; 
            font-weight: bold;
            margin-right: 10px;
        }
        .get { background: #61affe; color: white; }
        .post { background: #49cc90; color: white; }
        code { 
            background: #f4f4f4; 
            padding: 2px 6px; 
            border-radius: 3px;
            font-family: monospace;
        }
        pre { 
            background: #2d2d2d; 
            color: #f8f8f2; 
            padding: 15px; 
            border-radius: 5px;
            overflow-x: auto;
        }
        h1 { color: #333; }
        h2 { color: #555; margin-top: 0; }
        .param { color: #e74c3c; }
        .example-url { color: #3498db; word-break: break-all; }
    </style>
</head>
<body>
    <h1>🔥 TinyTorch API Service</h1>
    <p>This microservice provides HTTP endpoints to interact with the TinyTorch (tito) CLI tool.</p>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <h2>/</h2>
        <p>Returns this API documentation page.</p>
    </div>

    <div class="endpoint">
        <span class="method get">GET</span>
        <h2>/api/v1/health</h2>
        <p>Health check endpoint. Returns service status and tito availability.</p>
        <h3>Example Response:</h3>
        <pre>{
  "status": "healthy",
  "service": "TinyTorch API",
  "tito_available": true,
  "timestamp": "2025-12-05T10:30:00"
}</pre>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <h2>/api/v1/status</h2>
        <p>Returns the output of <code>tito checkpoint status</code>.</p>
        <h3>Example Response:</h3>
        <pre>{
  "status": "success",
  "tito_status": {
    "raw_output": ["Module 01: Complete", "Module 02: Incomplete"]
  }
}</pre>
        <h3>Try it:</h3>
        <p class="example-url">GET https://your-service.onrender.com/api/v1/status</p>
    </div>
    
    <div class="endpoint">
        <span class="method get">GET</span>
        <span class="method post">POST</span>
        <h2>/api/v1/validate</h2>
        <p>Runs module completion and validation. Accepts <span class="param">module</span> parameter.</p>
        
        <h3>Parameters:</h3>
        <ul>
            <li><code class="param">module</code> (required) - Module ID, e.g., "01", "02"</li>
        </ul>
        
        <h3>GET Example:</h3>
        <p class="example-url">GET https://your-service.onrender.com/api/v1/validate?module=01</p>
        
        <h3>POST Example (JSON):</h3>
        <pre>POST https://your-service.onrender.com/api/v1/validate
Content-Type: application/json

{
  "module": "01"
}</pre>
        
        <h3>Example Response:</h3>
        <pre>{
  "status": "validation_complete",
  "module": "01",
  "completion_log": ["Running module 01...", "Complete"],
  "validation_log": ["Validating...", "Score: 100%"]
}</pre>
    </div>

    <div class="endpoint">
        <span class="method post">POST</span>
        <h2>/api/v1/tito/command</h2>
        <p>Execute arbitrary tito commands (advanced users only).</p>
        
        <h3>Parameters:</h3>
        <ul>
            <li><code class="param">args</code> (required) - Array of command arguments</li>
        </ul>
        
        <h3>POST Example:</h3>
        <pre>POST https://your-service.onrender.com/api/v1/tito/command
Content-Type: application/json

{
  "args": ["checkpoint", "status"]
}</pre>
        
        <h3>Example Response:</h3>
        <pre>{
  "status": "success",
  "output": "Module 01: Complete\\nModule 02: Incomplete"
}</pre>
    </div>
    
    <div class="endpoint">
        <h2>Error Responses</h2>
        <p>All endpoints return appropriate HTTP status codes:</p>
        <ul>
            <li><code>400</code> - Bad Request (missing parameters)</li>
            <li><code>500</code> - Internal Server Error (tito command failed)</li>
        </ul>
        <h3>Example Error:</h3>
        <pre>{
  "status": "error",
  "message": "Missing 'module' parameter in JSON body or URL.",
  "timestamp": "2025-12-05T10:30:00"
}</pre>
    </div>
</body>
</html>
"""

# --- API Endpoints ---

@app.route('/', methods=['GET'])
def api_documentation():
    """Serves the API documentation page."""
    return render_template_string(API_DOCS_HTML)


@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify service is running."""
    logger.info("Health check requested")
    
    # Check if tito command exists
    tito_available = False
    try:
        result = subprocess.run(['which', 'tito'], capture_output=True, text=True)
        tito_available = result.returncode == 0
    except Exception as e:
        logger.warning(f"Could not check tito availability: {e}")
    
    return jsonify({
        "status": "healthy",
        "service": "TinyTorch API",
        "tito_available": tito_available,
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route('/api/v1/status', methods=['GET'])
def get_tito_status():
    """Returns the output of 'tito checkpoint status'."""
    logger.info("Status endpoint called")
    try:
        cli_output = execute_tito_command(['checkpoint', 'status'])
        
        # Parse the output (basic parsing for now)
        parsed_data = {"raw_output": cli_output.split('\n')} 
        
        return jsonify({
            "status": "success",
            "tito_status": parsed_data,
            "timestamp": datetime.utcnow().isoformat()
        })
    except RuntimeError as e:
        logger.error(f"Status check failed: {e}")
        return jsonify({
            "status": "error", 
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@app.route('/api/v1/validate', methods=['GET', 'POST'])
def run_assignment_validation():
    """Runs module completion and returns validation result."""
    logger.info(f"Validation endpoint called via {request.method}")
    
    # Handle both JSON (POST) and URL params (GET)
    data = request.get_json(silent=True)
    if data is None:
        data = request.args
        
    module_id = data.get('module')
    
    if not module_id:
        logger.warning("Validation request missing 'module' parameter")
        return jsonify({
            "status": "error", 
            "message": "Missing 'module' parameter in JSON body or URL.",
            "timestamp": datetime.utcnow().isoformat()
        }), 400
    
    logger.info(f"Validating module: {module_id}")
    
    try:
        # Run module completion
        logger.info(f"Running completion for module {module_id}")
        completion_output = execute_tito_command(['module', 'complete', module_id])
        
        # Run validation
        logger.info(f"Running autograde for module {module_id}")
        validation_output = execute_tito_command(['grade', 'autograde', f'{module_id}_tensor']) 
        
        logger.info(f"Module {module_id} validation complete")
        
        return jsonify({
            "status": "validation_complete",
            "module": module_id,
            "completion_log": completion_output.split('\n'),
            "validation_log": validation_output.split('\n'),
            "timestamp": datetime.utcnow().isoformat()
        })
    
    except RuntimeError as e:
        logger.error(f"Validation failed for module {module_id}: {e}")
        return jsonify({
            "status": "error", 
            "message": str(e),
            "module": module_id,
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@app.route('/api/v1/tito/command', methods=['POST'])
def execute_custom_tito_command():
    """Execute arbitrary tito commands (advanced users)."""
    logger.info("Custom tito command endpoint called")
    
    data = request.get_json(silent=True)
    if not data or 'args' not in data:
        logger.warning("Custom command request missing 'args' parameter")
        return jsonify({
            "status": "error",
            "message": "Missing 'args' parameter. Send JSON with 'args' array.",
            "example": {"args": ["checkpoint", "status"]},
            "timestamp": datetime.utcnow().isoformat()
        }), 400
    
    args = data['args']
    if not isinstance(args, list):
        logger.warning("Custom command 'args' is not a list")
        return jsonify({
            "status": "error",
            "message": "'args' must be an array of strings",
            "timestamp": datetime.utcnow().isoformat()
        }), 400
    
    logger.info(f"Executing custom tito command: {args}")
    
    try:
        output = execute_tito_command(args)
        return jsonify({
            "status": "success",
            "output": output,
            "timestamp": datetime.utcnow().isoformat()
        })
    except RuntimeError as e:
        logger.error(f"Custom command failed: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


# --- Error Handlers ---
@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404 error: {request.url}")
    return jsonify({
        "status": "error",
        "message": "Endpoint not found. Visit / for API documentation.",
        "timestamp": datetime.utcnow().isoformat()
    }), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {error}")
    return jsonify({
        "status": "error",
        "message": "Internal server error. Check logs for details.",
        "timestamp": datetime.utcnow().isoformat()
    }), 500


# --- Local Runner ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)


