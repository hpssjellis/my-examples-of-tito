# --- app.py ---

import subprocess
import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# --- Configure Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

logger.info("TinyTorch API Service starting up...")

# --- Utility Function to Handle CLI Output ---
def execute_tito_command(args):
    """Executes a tito command and returns its stdout output or raises an error."""
    try:
        command = ['tito'] + args
        logger.info(f"Executing tito command: {' '.join(command)}")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=60
        )
        
        logger.info(f"Command succeeded. Output length: {len(result.stdout)} chars")
        return result.stdout.strip()
    
    except subprocess.CalledProcessError as e:
        error_message = f"tito command failed. STDERR: {e.stderr.strip()}"
        logger.error(error_message)
        logger.error(f"Exit code: {e.returncode}")
        raise RuntimeError(error_message) 
    
    except subprocess.TimeoutExpired as e:
        error_message = f"tito command timed out after 60 seconds"
        logger.error(error_message)
        raise RuntimeError(error_message)
    
    except FileNotFoundError:
        error_message = "The 'tito' command was not found. Check Dockerfile and PATH."
        logger.error(error_message)
        raise RuntimeError(error_message)


# --- API Documentation with Interactive Buttons (HTML) ---
API_DOCS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>TinyTorch API - Interactive Tester</title>
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        h1 { 
            color: #667eea; 
            margin: 0 0 10px 0;
            font-size: 2.5em;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 1.1em;
        }
        .current-url {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 30px;
            border-left: 4px solid #667eea;
        }
        .current-url strong {
            color: #667eea;
        }
        .current-url code {
            background: #e9ecef;
            padding: 4px 8px;
            border-radius: 4px;
            color: #495057;
            font-size: 0.95em;
        }
        .endpoint { 
            background: #f8f9fa;
            padding: 25px; 
            margin: 20px 0; 
            border-radius: 10px;
            border: 1px solid #dee2e6;
            transition: all 0.3s ease;
        }
        .endpoint:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }
        .endpoint-header {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }
        .method { 
            display: inline-block;
            padding: 6px 12px; 
            border-radius: 6px; 
            font-weight: bold;
            font-size: 0.85em;
            margin-right: 12px;
            text-transform: uppercase;
        }
        .get { background: #61affe; color: white; }
        .post { background: #49cc90; color: white; }
        .endpoint-title {
            font-size: 1.4em;
            color: #333;
            font-weight: 600;
            margin: 0;
        }
        .description {
            color: #666;
            margin: 10px 0;
            line-height: 1.6;
        }
        .test-section {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-top: 15px;
            border: 2px solid #e9ecef;
        }
        .test-section h4 {
            margin: 0 0 15px 0;
            color: #495057;
        }
        .input-group {
            margin: 15px 0;
        }
        .input-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
            color: #495057;
        }
        .input-group input, .input-group textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ced4da;
            border-radius: 6px;
            font-size: 14px;
            font-family: monospace;
        }
        .input-group textarea {
            min-height: 80px;
            resize: vertical;
        }
        button { 
            background: #667eea;
            color: white; 
            border: none; 
            padding: 12px 24px; 
            border-radius: 6px; 
            cursor: pointer;
            font-size: 1em;
            font-weight: 600;
            transition: all 0.3s ease;
            margin-right: 10px;
        }
        button:hover { 
            background: #5568d3;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        button:active {
            transform: translateY(0);
        }
        button.secondary {
            background: #6c757d;
        }
        button.secondary:hover {
            background: #5a6268;
        }
        .response-box {
            margin-top: 15px;
            padding: 15px;
            background: #2d2d2d;
            color: #f8f8f2;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            white-space: pre-wrap;
            word-wrap: break-word;
            max-height: 400px;
            overflow-y: auto;
            display: none;
        }
        .response-box.show {
            display: block;
        }
        .loading {
            display: none;
            color: #667eea;
            font-style: italic;
        }
        .loading.show {
            display: inline-block;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: 600;
            margin-left: 10px;
        }
        .status-success { background: #d4edda; color: #155724; }
        .status-error { background: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔥 TinyTorch API Service</h1>
        <p class="subtitle">Interactive API Testing Interface</p>
        
        <div class="current-url">
            <strong>🌐 Service URL:</strong> <code id="base-url">Loading...</code>
        </div>

        <!-- Health Check -->
        <div class="endpoint">
            <div class="endpoint-header">
                <span class="method get">GET</span>
                <h3 class="endpoint-title">/api/v1/health</h3>
            </div>
            <p class="description">Check if the service and tito are available.</p>
            <div class="test-section">
                <button onclick="testHealth()">🏥 Test Health Check</button>
                <span class="loading" id="health-loading">Testing...</span>
                <div class="response-box" id="health-response"></div>
            </div>
        </div>

        <!-- Status Check -->
        <div class="endpoint">
            <div class="endpoint-header">
                <span class="method get">GET</span>
                <h3 class="endpoint-title">/api/v1/status</h3>
            </div>
            <p class="description">Get checkpoint status from tito.</p>
            <div class="test-section">
                <button onclick="testStatus()">📊 Get Status</button>
                <span class="loading" id="status-loading">Loading...</span>
                <div class="response-box" id="status-response"></div>
            </div>
        </div>

        <!-- Validate Module -->
        <div class="endpoint">
            <div class="endpoint-header">
                <span class="method get">GET</span>
                <span class="method post">POST</span>
                <h3 class="endpoint-title">/api/v1/validate</h3>
            </div>
            <p class="description">Validate a specific module.</p>
            <div class="test-section">
                <h4>Test Validation</h4>
                <div class="input-group">
                    <label for="module-id">Module ID (e.g., "01", "02"):</label>
                    <input type="text" id="module-id" placeholder="01" value="01">
                </div>
                <button onclick="testValidate()">✅ Validate Module</button>
                <span class="loading" id="validate-loading">Processing...</span>
                <div class="response-box" id="validate-response"></div>
            </div>
        </div>

        <!-- Custom Command -->
        <div class="endpoint">
            <div class="endpoint-header">
                <span class="method post">POST</span>
                <h3 class="endpoint-title">/api/v1/tito/command</h3>
            </div>
            <p class="description">Execute custom tito commands.</p>
            <div class="test-section">
                <h4>Run Custom Command</h4>
                <div class="input-group">
                    <label for="custom-args">Command Arguments (JSON array):</label>
                    <textarea id="custom-args" placeholder='["checkpoint", "status"]'>["checkpoint", "status"]</textarea>
                </div>
                <button onclick="testCustomCommand()">🚀 Execute Command</button>
                <span class="loading" id="custom-loading">Running...</span>
                <div class="response-box" id="custom-response"></div>
            </div>
        </div>
    </div>

    <script>
        // Get and display the current URL
        const baseUrl = window.location.origin;
        document.getElementById('base-url').textContent = baseUrl;

        async function makeRequest(endpoint, options = {}) {
            try {
                const response = await fetch(baseUrl + endpoint, options);
                const data = await response.json();
                return {
                    status: response.status,
                    data: data
                };
            } catch (error) {
                return {
                    status: 'error',
                    data: { error: error.message }
                };
            }
        }

        function showResponse(elementId, result) {
            const responseBox = document.getElementById(elementId);
            responseBox.textContent = JSON.stringify(result.data, null, 2);
            responseBox.classList.add('show');
        }

        function showLoading(elementId, show = true) {
            const loading = document.getElementById(elementId);
            if (show) {
                loading.classList.add('show');
            } else {
                loading.classList.remove('show');
            }
        }

        async function testHealth() {
            showLoading('health-loading', true);
            const result = await makeRequest('/api/v1/health');
            showLoading('health-loading', false);
            showResponse('health-response', result);
        }

        async function testStatus() {
            showLoading('status-loading', true);
            const result = await makeRequest('/api/v1/status');
            showLoading('status-loading', false);
            showResponse('status-response', result);
        }

        async function testValidate() {
            const moduleId = document.getElementById('module-id').value;
            if (!moduleId) {
                alert('Please enter a module ID');
                return;
            }
            
            showLoading('validate-loading', true);
            const result = await makeRequest('/api/v1/validate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ module: moduleId })
            });
            showLoading('validate-loading', false);
            showResponse('validate-response', result);
        }

        async function testCustomCommand() {
            const argsText = document.getElementById('custom-args').value;
            let args;
            try {
                args = JSON.parse(argsText);
            } catch (e) {
                alert('Invalid JSON format for arguments');
                return;
            }
            
            showLoading('custom-loading', true);
            const result = await makeRequest('/api/v1/tito/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ args: args })
            });
            showLoading('custom-loading', false);
            showResponse('custom-response', result);
        }
    </script>
</body>
</html>
"""

# --- API Endpoints ---

@app.route('/', methods=['GET'])
def api_documentation():
    """Serves the interactive API documentation page."""
    return render_template_string(API_DOCS_HTML)


@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify service is running."""
    logger.info("Health check requested")
    
    # Check if tito command exists
    tito_available = False
    tito_error = None
    try:
        result = subprocess.run(['which', 'tito'], capture_output=True, text=True)
        tito_available = result.returncode == 0
        
        # Try to import tito module
        if tito_available:
            try:
                import tito
                tito_module_available = True
            except ImportError as e:
                tito_module_available = False
                tito_error = str(e)
    except Exception as e:
        logger.warning(f"Could not check tito availability: {e}")
        tito_error = str(e)
    
    return jsonify({
        "status": "healthy",
        "service": "TinyTorch API",
        "tito_command_available": tito_available,
        "tito_module_available": tito_module_available if tito_available else False,
        "tito_error": tito_error,
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route('/api/v1/status', methods=['GET'])
def get_tito_status():
    """Returns the output of 'tito checkpoint status'."""
    logger.info("Status endpoint called")
    try:
        cli_output = execute_tito_command(['checkpoint', 'status'])
        
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
        logger.info(f"Running completion for module {module_id}")
        completion_output = execute_tito_command(['module', 'complete', module_id])
        
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
