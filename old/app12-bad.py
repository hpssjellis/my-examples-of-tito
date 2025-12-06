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
# NOTE: The <script> block below contains the required changes.
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
        .info-box {
            background: #d1ecf1;
            border: 1px solid #bee5eb;
            color: #0c5460;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
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
        .input-group input, .input-group textarea, .input-group select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ced4da;
            border-radius: 6px;
            font-size: 14px;
        }
        .input-group textarea {
            min-height: 80px;
            resize: vertical;
            font-family: monospace;
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
            margin-bottom: 10px;
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
        .command-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 10px;
            margin: 15px 0;
        }
        .command-grid button {
            margin: 0;
            font-size: 0.9em;
            padding: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔥 TinyTorch API Service</h1>
        <p class="subtitle">Interactive API Testing Interface</p>
        
        <div class="current-url">
            <strong>🌐 Service URL:</strong> <code id="base-url">Loading...</code>
        </div>

        <div class="info-box">
            <strong>📝 Available tito Commands:</strong><br>
            setup, system, module, dev, src, package, nbgrader, milestones, community, benchmark, olympics, export, test, grade, logo
        </div>

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

        <div class="endpoint">
            <div class="endpoint-header">
                <span class="method post">POST</span>
                <h3 class="endpoint-title">Quick tito Commands</h3>
            </div>
            <p class="description">Test common tito commands with one click.</p>
            <div class="test-section">
                <h4>🚀 Quick Test Commands</h4>
                <div class="command-grid">
                    <button onclick="quickCommand(['--version'])">Version</button>
                    <button onclick="quickCommand(['--help'])">Help</button>
                    <button onclick="quickCommand(['system', 'info'])">System Info</button>
                    <button onclick="quickCommand(['module', 'list'])">List Modules</button>
                    <button onclick="quickCommand(['test', '--help'])">Test Help</button>
                    <button onclick="quickCommand(['grade', '--help'])">Grade Help</button>
                    <button onclick="quickCommand(['export', '--help'])">Export Help</button>
                    <button onclick="quickCommand(['logo'])">Show Logo</button>
                </div>
                <span class="loading" id="quick-loading">Running...</span>
                <div class="response-box" id="quick-response"></div>
            </div>
        </div>

        <div class="endpoint">
            <div class="endpoint-header">
                <span class="method get">GET</span>
                <span class="method post">POST</span>
                <h3 class="endpoint-title">/api/v1/module</h3>
            </div>
            <p class="description">Work with TinyTorch modules.</p>
            <div class="test-section">
                <h4>Module Operations</h4>
                <div class="input-group">
                    <label for="module-operation">Operation:</label>
                    <select id="module-operation">
                        <option value="list">List Modules</option>
                        <option value="info">Module Info</option>
                        <option value="export">Export Module</option>
                    </select>
                </div>
                <div class="input-group">
                    <label for="module-name">Module Name (e.g., "01_tensor"):</label>
                    <input type="text" id="module-name" placeholder="01_tensor" value="01_tensor">
                </div>
                <button onclick="testModule()">📦 Execute Module Command</button>
                <span class="loading" id="module-loading">Processing...</span>
                <div class="response-box" id="module-response"></div>
            </div>
        </div>

        <div class="endpoint">
            <div class="endpoint-header">
                <span class="method post">POST</span>
                <h3 class="endpoint-title">/api/v1/grade</h3>
            </div>
            <p class="description">Grade assignments and tests.</p>
            <div class="test-section">
                <h4>Grading</h4>
                <div class="input-group">
                    <label for="assignment-name">Assignment Name:</label>
                    <input type="text" id="assignment-name" placeholder="01_tensor" value="01_tensor">
                </div>
                <button onclick="testGrade()">✅ Grade Assignment</button>
                <span class="loading" id="grade-loading">Grading...</span>
                <div class="response-box" id="grade-response"></div>
            </div>
        </div>

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
                    <textarea id="custom-args" placeholder='["system", "info"]'>["system", "info"]</textarea>
                </div>
                <button onclick="testCustomCommand()">🚀 Execute Command</button>
                <span class="loading" id="custom-loading">Running...</span>
                <div class="response-box" id="custom-response"></div>
            </div>
        </div>
    </div>

    <script>
        // Variables renamed to myCamelCase
        const myBaseUrl = window.location.origin;
        document.getElementById('base-url').textContent = myBaseUrl;

        // Use async/await structure
        async function myMakeRequest(myEndpoint, myOptions = {}) {
            try {
                const myResponse = await fetch(myBaseUrl + myEndpoint, myOptions);
                const myData = await myResponse.json();
                return {
                    myStatus: myResponse.status,
                    myData: myData
                };
            } catch (myError) {
                return {
                    myStatus: 'error',
                    myData: { myError: myError.message }
                };
            }
        }

        // Corrected function to display the raw 'output' string (with \n) or the full JSON
        function myShowResponse(myElementId, myResult) {
            const myResponseBox = document.getElementById(myElementId);
            let myOutputText = '';

            // Check if there is an 'output' field containing the command line output
            if (myResult.myData && typeof myResult.myData.output === 'string') {
                // Display only the 'output' string. Since the backend passes the real 
                // newline characters, the CSS 'white-space: pre-wrap' handles linefeeds.
                myOutputText = myResult.myData.output;
            } else {
                // Otherwise, show the whole JSON object (e.g., for errors or health check)
                myOutputText = JSON.stringify(myResult.myData, null, 2);
            }
            
            myResponseBox.textContent = myOutputText;
            myResponseBox.classList.add('show');
        }

        // Function to handle loading state
        function myShowLoading(myElementId, myShow = true) {
            const myLoading = document.getElementById(myElementId);
            if (myShow) {
                myLoading.classList.add('show');
            } else {
                myLoading.classList.remove('show');
            }
        }

        // Functions updated to use new variable/function names
        async function testHealth() {
            myShowLoading('health-loading', true);
            const myResult = await myMakeRequest('/api/v1/health');
            myShowLoading('health-loading', false);
            myShowResponse('health-response', myResult);
        }

        async function quickCommand(myArgs) {
            myShowLoading('quick-loading', true);
            const myResult = await myMakeRequest('/api/v1/tito/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ args: myArgs })
            });
            myShowLoading('quick-loading', false);
            myShowResponse('quick-response', myResult);
        }

        async function testModule() {
            const myOperation = document.getElementById('module-operation').value;
            const myModuleName = document.getElementById('module-name').value;
            
            let myArgs;
            if (myOperation === 'list') {
                myArgs = ['module', 'list'];
            } else if (myOperation === 'info') {
                myArgs = ['module', 'info', myModuleName];
            } else if (myOperation === 'export') {
                myArgs = ['src', 'export', myModuleName];
            }
            
            myShowLoading('module-loading', true);
            const myResult = await myMakeRequest('/api/v1/tito/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ args: myArgs })
            });
            myShowLoading('module-loading', false);
            myShowResponse('module-response', myResult);
        }

        async function testGrade() {
            const myAssignmentName = document.getElementById('assignment-name').value;
            if (!myAssignmentName) {
                alert('Please enter an assignment name');
                return;
            }
            
            myShowLoading('grade-loading', true);
            const myResult = await myMakeRequest('/api/v1/tito/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ args: ['grade', 'autograde', myAssignmentName] })
            });
            myShowLoading('grade-loading', false);
            myShowResponse('grade-response', myResult);
        }

        async function testCustomCommand() {
            const myArgsText = document.getElementById('custom-args').value;
            let myArgs;
            try {
                myArgs = JSON.parse(myArgsText);
            } catch (e) {
                alert('Invalid JSON format for arguments');
                return;
            }
            
            myShowLoading('custom-loading', true);
            const myResult = await myMakeRequest('/api/v1/tito/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ args: myArgs })
            });
            myShowLoading('custom-loading', false);
            myShowResponse('custom-response', myResult);
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
    
    tito_available = False
    tito_module_available = False
    tito_error = None
    tito_version = None
    
    try:
        # Check if tito command exists
        result = subprocess.run(['which', 'tito'], capture_output=True, text=True)
        tito_available = result.returncode == 0
        
        # Try to get version
        if tito_available:
            try:
                version_result = subprocess.run(
                    ['tito', '--version'], 
                    capture_output=True, 
                    text=True, 
                    timeout=5
                )
                tito_version = version_result.stdout.strip()
            except Exception as e:
                logger.warning(f"Could not get tito version: {e}")
        
        # Try to import tito module
        if tito_available:
            try:
                import tito
                tito_module_available = True
            except ImportError as e:
                tito_error = str(e)
                
    except Exception as e:
        logger.warning(f"Could not check tito availability: {e}")
        tito_error = str(e)
    
    return jsonify({
        "status": "healthy",
        "service": "TinyTorch API",
        "tito_command_available": tito_available,
        "tito_module_available": tito_module_available,
        "tito_version": tito_version,
        "tito_error": tito_error,
        "available_commands": "setup, system, module, dev, src, package, nbgrader, milestones, community, benchmark, olympics, export, test, grade, logo",
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route('/api/v1/module', methods=['GET', 'POST'])
def module_operations():
    """Handle module operations."""
    logger.info(f"Module endpoint called via {request.method}")
    
    data = request.get_json(silent=True)
    if data is None:
        data = request.args
    
    operation = data.get('operation', 'list')
    module_name = data.get('module')
    
    try:
        if operation == 'list':
            output = execute_tito_command(['module', 'list'])
        elif operation == 'info':
            if not module_name:
                return jsonify({
                    "status": "error",
                    "message": "Module name required for info operation"
                }), 400
            output = execute_tito_command(['module', 'info', module_name])
        elif operation == 'export':
            if not module_name:
                return jsonify({
                    "status": "error",
                    "message": "Module name required for export operation"
                }), 400
            output = execute_tito_command(['src', 'export', module_name])
        else:
            return jsonify({
                "status": "error",
                "message": f"Unknown operation: {operation}"
            }), 400
        
        return jsonify({
            "status": "success",
            "operation": operation,
            "output": output,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except RuntimeError as e:
        logger.error(f"Module operation failed: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@app.route('/api/v1/grade', methods=['POST'])
def grade_assignment():
    """Grade an assignment."""
    logger.info("Grade endpoint called")
    
    data = request.get_json(silent=True)
    if not data or 'assignment' not in data:
        return jsonify({
            "status": "error",
            "message": "Missing 'assignment' parameter"
        }), 400
    
    assignment = data['assignment']
    
    try:
        output = execute_tito_command(['grade', 'autograde', assignment])
        return jsonify({
            "status": "success",
            "assignment": assignment,
            "output": output,
            "timestamp": datetime.utcnow().isoformat()
        })
    except RuntimeError as e:
        logger.error(f"Grading failed: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 500


@app.route('/api/v1/tito/command', methods=['POST'])
def execute_custom_tito_command():
    """Execute arbitrary tito commands."""
    logger.info("Custom tito command endpoint called")
    
    data = request.get_json(silent=True)
    if not data or 'args' not in data:
        return jsonify({
            "status": "error",
            "message": "Missing 'args' parameter. Send JSON with 'args' array.",
            "example": {"args": ["system", "info"]},
            "timestamp": datetime.utcnow().isoformat()
        }), 400
    
    args = data['args']
    if not isinstance(args, list):
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
            "command": args,
            "output": output,
            "timestamp": datetime.utcnow().isoformat()
        })
    except RuntimeError as e:
        logger.error(f"Custom command failed: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "command": args,
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
