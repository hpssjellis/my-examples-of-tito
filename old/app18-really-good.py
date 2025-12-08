import subprocess
import os
import sys
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

# --- Find tito executable ---
def find_tito_executable():
    """Find the tito executable in various possible locations"""
    possible_locations = [
        '/app/venv/bin/tito',
        '/app/TinyTorch/bin/tito',
        '/app/TinyTorch/tito',
        '/app/TinyTorch/cli/tito',
        '/usr/local/bin/tito',
    ]
    
    # Check which command
    result = subprocess.run(['which', 'tito'], capture_output=True, text=True)
    if result.returncode == 0:
        tito_path = result.stdout.strip()
        logger.info(f"Found tito via 'which': {tito_path}")
        return tito_path
    
    # Check possible locations
    for location in possible_locations:
        if os.path.exists(location) and os.access(location, os.X_OK):
            logger.info(f"Found tito at: {location}")
            return location
    
    logger.warning("Could not find tito executable in any known location")
    return None

# Find tito at startup
TITO_PATH = find_tito_executable()

# --- Utility Function to Handle CLI Output ---
def execute_tito_command(args):
    """Executes a tito command and returns its stdout output or raises an error."""
    
    if TITO_PATH is None:
        raise RuntimeError("tito executable not found. Check installation.")
    
    try:
        command = [TITO_PATH] + args
        logger.info(f"Executing tito command: {' '.join(command)}")
        
        # Set up environment to help Python find modules
        env = os.environ.copy()
        
        # Add TinyTorch to PYTHONPATH if it exists
        tinytorch_paths = ['/app/TinyTorch', '/app/tinytorch']
        for path in tinytorch_paths:
            if os.path.exists(path):
                current_pythonpath = env.get('PYTHONPATH', '')
                if current_pythonpath:
                    env['PYTHONPATH'] = f"{path}:{current_pythonpath}"
                else:
                    env['PYTHONPATH'] = path
                logger.info(f"Added {path} to PYTHONPATH")
                break
        
        # Make sure we're using the venv Python
        if os.path.exists('/app/venv/bin/python'):
            env['PYTHON'] = '/app/venv/bin/python'
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
            env=env,
            cwd='/app/TinyTorch' if os.path.exists('/app/TinyTorch') else '/app'
        )
        
        logger.info(f"Command succeeded. Output length: {len(result.stdout)} chars")
        return result.stdout.strip()
    
    except subprocess.CalledProcessError as e:
        error_message = f"tito command failed. STDERR: {e.stderr.strip()}"
        logger.error(error_message)
        logger.error(f"STDOUT: {e.stdout.strip()}")
        logger.error(f"Exit code: {e.returncode}")
        
        # Try to provide helpful debugging info
        logger.error(f"Command was: {' '.join(command)}")
        logger.error(f"Working directory: {os.getcwd()}")
        logger.error(f"PYTHONPATH: {env.get('PYTHONPATH', 'Not set')}")
        
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
</head>
<body>
    <h1>TinyTorch API Service</h1>
    <p>Interactive API Testing Interface</p>
    
    <hr>
    
    <p><strong>Service URL:</strong> <span id="base-url">Loading...</span></p>
    
    <p><strong>Available tito Commands:</strong><br>
    setup, system, module, dev, src, package, nbgrader, milestones, community, benchmark, olympics, export, test, grade, logo</p>

    <hr>

    <!-- Health Check -->
    <h2>GET /api/v1/health</h2>
    <p>Check if the service and tito are available.</p>
    <button onclick="testHealth()">Test Health Check</button>
    <span id="health-loading" style="display:none;">Testing...</span>
    <div id="health-response"></div>

    <hr>

    <!-- Quick Commands -->
    <h2>POST /api/v1/tito/command - Quick Commands</h2>
    <p>Test common tito commands with one click.</p>
    <button onclick="quickCommand(['--version'])">['--version'] </button>
    <button onclick="quickCommand(['--help'])">['--help']</button>
    <button onclick="quickCommand(['system', 'info'])">['system', 'info']</button>
    <button onclick="quickCommand(['system', 'doctor'])">['system', 'doctor']</button>
    <button onclick="quickCommand(['module', 'list'])">['module', 'list']</button>
    <button onclick="quickCommand(['test', '--help'])">['test', '--help']</button>
    <button onclick="quickCommand(['grade', '--help'])">['grade', '--help']</button>
    <button onclick="quickCommand(['export', '--help'])">['export', '--help']</button>
    <button onclick="quickCommand(['logo'])">['logo']</button>
    <br>
    <span id="quick-loading" style="display:none;">Running...</span>
    <div id="quick-response"></div>

    <hr>

    <!-- Module Operations 'start', 'resume', 'complete', 'test', 'reset', 'status', 'list -->
    <h2>GET/POST /api/v1/module</h2>
    <p>Work with TinyTorch modules.</p>
    <label for="module-operation">Operation:</label>
    <select id="module-operation">
        <option value="list">List Modules</option>
        <option value="info">Module Info</option>
        <option value="start">Module start</option>
        <option value="resume">Module resume</option>
        <option value="complete">Module complete</option>
        <option value="reset">Module reset</option>
        <option value="status">Module status</option>
        <option value="info">Module Info</option>
        <option value="export">Export Module</option>
    </select>
    <br><br>
    <label for="module-name">Module Name (e.g., "01_tensor"):</label>
    <input type="text" id="module-name" value="01_tensor" size="30">
    <br><br>
    <button onclick="testModule()">Execute Module Command</button>
    <span id="module-loading" style="display:none;">Processing...</span>
    <div id="module-response"></div>

    <hr>

    <!-- Grade Operations -->
    <h2>POST /api/v1/grade</h2>
    <p>Grade assignments and tests.</p>
    <label for="assignment-name">Assignment Name:</label>
    <input type="text" id="assignment-name" value="01_tensor" size="30">
    <br><br>
    <button onclick="testGrade()">Grade Assignment</button>
    <span id="grade-loading" style="display:none;">Grading...</span>
    <div id="grade-response"></div>

    <hr>

    <!-- Custom Command -->
    <h2>POST /api/v1/tito/command - Custom</h2>
    <p>Execute custom tito commands.</p>
    <label for="custom-args">Command Arguments (JSON array):</label><br>
    <textarea id="custom-args" rows="3" cols="50">["system", "info"]</textarea>
    <br><br>
    <button onclick="testCustomCommand()">Execute Command</button>
    <span id="custom-loading" style="display:none;">Running...</span>
    <div id="custom-response"></div>

    <script>
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
            const container = document.getElementById(elementId);
            const textarea = document.createElement('textarea');
            textarea.rows = 10;
            textarea.cols = 80;
            
            // If the response has an output field, show it directly preserves 
            // Otherwise show the full JSON
            if (result.data && result.data.output) {
                textarea.value = result.data.output;
            } else {
                textarea.value = JSON.stringify(result.data, null, 2);
            }
            
            textarea.readOnly = true;
            container.appendChild(textarea);
            container.appendChild(document.createElement('br'));
        }

        function showLoading(elementId, show = true) {
            const loading = document.getElementById(elementId);
            loading.style.display = show ? 'inline' : 'none';
        }

        async function testHealth() {
            showLoading('health-loading', true);
            const result = await makeRequest('/api/v1/health');
            showLoading('health-loading', false);
            showResponse('health-response', result);
        }

        async function quickCommand(args) {
            showLoading('quick-loading', true);
            const result = await makeRequest('/api/v1/tito/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ args: args })
            });
            showLoading('quick-loading', false);
            showResponse('quick-response', result);
        }

        async function testModule() {
            const operation = document.getElementById('module-operation').value;
            const moduleName = document.getElementById('module-name').value;
            
            let args;
            if (operation === 'list') {
                args = ['module', 'list'];
            } else if (operation === 'info') {
                args = ['module', 'info', moduleName];
            } else if (operation === 'export') {
                args = ['src', 'export', moduleName];
            }
            
            showLoading('module-loading', true);
            const result = await makeRequest('/api/v1/tito/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ args: args })
            });
            showLoading('module-loading', false);
            showResponse('module-response', result);
        }

        async function testGrade() {
            const assignmentName = document.getElementById('assignment-name').value;
            if (!assignmentName) {
                alert('Please enter an assignment name');
                return;
            }
            
            showLoading('grade-loading', true);
            const result = await makeRequest('/api/v1/tito/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ args: ['grade', 'autograde', assignmentName] })
            });
            showLoading('grade-loading', false);
            showResponse('grade-response', result);
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
    
    tito_available = TITO_PATH is not None
    tito_executable = False
    tito_version = None
    tito_error = None
    
    if tito_available:
        tito_executable = os.access(TITO_PATH, os.X_OK)
        
        # Try to get version
        try:
            version_result = subprocess.run(
                [TITO_PATH, '--version'], 
                capture_output=True, 
                text=True, 
                timeout=5,
                env=os.environ.copy()
            )
            if version_result.returncode == 0:
                tito_version = version_result.stdout.strip()
            else:
                tito_error = version_result.stderr.strip()
        except Exception as e:
            logger.warning(f"Could not get tito version: {e}")
            tito_error = str(e)
    
    return jsonify({
        "status": "healthy",
        "service": "TinyTorch API",
        "tito_path": TITO_PATH,
        "tito_found": tito_available,
        "tito_executable": tito_executable,
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
    logger.info(f"Tito path: {TITO_PATH}")
    app.run(host='0.0.0.0', port=port, debug=True)
