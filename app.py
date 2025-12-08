import subprocess
import os
import sys
import logging
import json
import shutil
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, send_file
from werkzeug.utils import secure_filename

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

# --- Configuration for notebook uploads ---
UPLOAD_FOLDER = '/tmp/notebooks_upload'
PROCESSED_FOLDER = '/tmp/notebooks_processed'
ALLOWED_EXTENSIONS = {'ipynb'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

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

# --- Notebook Processing Functions ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_module_number(filename):
    """Extract module number from filename like '01_tensor.ipynb' -> '01'"""
    base = filename.rsplit('.', 1)[0]
    if '_' in base:
        parts = base.split('_')
        if parts[0].isdigit():
            return parts[0]
    # Try to find any 2-digit number in filename
    import re
    match = re.search(r'\d{2}', filename)
    return match.group(0) if match else None

def run_tito_complete(notebook_path, module_number):
    """
    Run 'tito module complete' command on the notebook
    Returns: (success: bool, output: str, processed_path: str)
    """
    try:
        # First, we need to place the notebook in the expected location
        workspace_dir = '/tmp/tinytorch_workspace'
        module_dir = os.path.join(workspace_dir, 'modules', f'{module_number}_module')
        os.makedirs(module_dir, exist_ok=True)
        
        # Copy notebook to expected location
        dest_path = os.path.join(module_dir, os.path.basename(notebook_path))
        shutil.copy(notebook_path, dest_path)
        
        # Run tito module complete
        try:
            output = execute_tito_command(['module', 'complete', module_number])
            success = True
        except RuntimeError as e:
            output = str(e)
            success = False
        
        # Create a results notebook
        processed_notebook = create_results_notebook(
            notebook_path, 
            success,
            output,
            module_number
        )
        
        return (success, output, processed_notebook)
        
    except Exception as e:
        return (False, f"Error: {str(e)}", None)

def create_results_notebook(original_path, success, output, module_number):
    """Create a results notebook with processing information"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_name = os.path.basename(original_path).rsplit('.', 1)[0]
    result_name = f"{base_name}_results_{timestamp}.ipynb"
    result_path = os.path.join(PROCESSED_FOLDER, result_name)
    
    # Read original notebook
    with open(original_path, 'r') as f:
        original_nb = json.load(f)
    
    # Create results cell
    results_cell = {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            f"# TinyTorch Module Processing Results\n\n",
            f"**Module:** {module_number}\n\n",
            f"**Status:** {'✅ SUCCESS' if success else '❌ FAILED'}\n\n",
            f"**Timestamp:** {datetime.now().isoformat()}\n\n",
            f"## Processing Output\n\n",
            f"```\n{output}\n```\n"
        ]
    }
    
    # Add results cell at the beginning
    original_nb['cells'].insert(0, results_cell)
    
    # Save processed notebook
    with open(result_path, 'w') as f:
        json.dump(original_nb, f, indent=2)
    
    return result_path

# --- API Documentation with Interactive Buttons (HTML) - EXTENDED ---
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

    <!-- NEW: Notebook Upload & Processing Section -->
    <h2>📓 Notebook Upload & Processing (NEW)</h2>
    <p>Upload your completed .ipynb notebook to process with <code>tito module complete</code></p>
    <div style="border: 2px dashed #999; padding: 20px; text-align: center; margin: 10px 0;" 
         id="uploadZone"
         ondrop="handleDrop(event)" 
         ondragover="handleDragOver(event)"
         ondragleave="handleDragLeave(event)">
        <p>Drop .ipynb file here or click to browse</p>
        <button onclick="document.getElementById('fileInput').click()">Choose File</button>
        <input type="file" id="fileInput" accept=".ipynb" onchange="handleFileSelect(event)" style="display:none;">
    </div>
    <div id="fileInfo" style="display:none; background: #f0f0f0; padding: 10px; margin: 10px 0;"></div>
    <div id="uploadProcessing" style="display:none; background: #ffe; padding: 10px; margin: 10px 0;">
        <p>Processing notebook with tito...</p>
    </div>
    <div id="uploadResult" style="display:none; padding: 10px; margin: 10px 0;"></div>

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

    <!-- Module Operations -->
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

        // NEW: File upload handling
        let selectedFile = null;

        function handleDragOver(e) {
            e.preventDefault();
            e.currentTarget.style.background = '#eee';
        }

        function handleDragLeave(e) {
            e.currentTarget.style.background = '';
        }

        function handleDrop(e) {
            e.preventDefault();
            e.currentTarget.style.background = '';
            const files = e.dataTransfer.files;
            if (files.length > 0) handleFile(files[0]);
        }

        function handleFileSelect(e) {
            const file = e.target.files[0];
            if (file) handleFile(file);
        }

        function handleFile(file) {
            if (!file.name.endsWith('.ipynb')) {
                alert('Please select a .ipynb file');
                return;
            }
            
            selectedFile = file;
            const fileInfo = document.getElementById('fileInfo');
            fileInfo.style.display = 'block';
            fileInfo.innerHTML = `
                <b>File:</b> ${file.name} (${(file.size/1024).toFixed(1)} KB)<br>
                <button onclick="uploadNotebook()">Process with tito module complete</button>
            `;
        }

        async function uploadNotebook() {
            if (!selectedFile) return;
            
            const formData = new FormData();
            formData.append('file', selectedFile);
            
            document.getElementById('uploadProcessing').style.display = 'block';
            document.getElementById('uploadResult').style.display = 'none';
            document.getElementById('fileInfo').style.display = 'none';
            
            try {
                const response = await fetch(baseUrl + '/api/v1/notebook/process', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                document.getElementById('uploadProcessing').style.display = 'none';
                const resultDiv = document.getElementById('uploadResult');
                resultDiv.style.display = 'block';
                
                if (data.success) {
                    resultDiv.style.background = '#dfd';
                    resultDiv.innerHTML = `
                        <h3>✅ Success</h3>
                        <p>Module ${data.module_number} processed</p>
                        <a href="${baseUrl}/api/v1/notebook/download/${data.result_file}" download>
                            <button>Download Results Notebook</button>
                        </a>
                        <h4>Output:</h4>
                        <textarea rows="10" cols="80" readonly>${data.output}</textarea>
                    `;
                } else {
                    resultDiv.style.background = '#fdd';
                    resultDiv.innerHTML = `
                        <h3>❌ Failed</h3>
                        <p>${data.message}</p>
                        <textarea rows="10" cols="80" readonly>${data.output || ''}</textarea>
                    `;
                }
            } catch (error) {
                document.getElementById('uploadProcessing').style.display = 'none';
                const resultDiv = document.getElementById('uploadResult');
                resultDiv.style.display = 'block';
                resultDiv.style.background = '#fdd';
                resultDiv.innerHTML = `<h3>❌ Error</h3><p>${error.message}</p>`;
            }
        }

        // ORIGINAL FUNCTIONS PRESERVED
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

# --- API Endpoints (ALL ORIGINAL PRESERVED) ---

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


# --- NEW ENDPOINTS: Notebook Processing ---

@app.route('/api/v1/notebook/process', methods=['POST'])
def process_notebook():
    """Process uploaded notebook with tito module complete"""
    logger.info("Notebook processing endpoint called")
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Invalid file type. Only .ipynb allowed'}), 400
    
    # Save uploaded file
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_filename = f"{timestamp}_{filename}"
    filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
    file.save(filepath)
    
    logger.info(f"Saved uploaded notebook: {filepath}")
    
    # Extract module number
    module_number = extract_module_number(filename)
    if not module_number:
        return jsonify({
            'success': False, 
            'message': 'Could not determine module number. Use format like 01_tensor.ipynb'
        }), 400
    
    # Process with tito
    success, output, processed_path = run_tito_complete(filepath, module_number)
    
    if processed_path:
        result_filename = os.path.basename(processed_path)
        return jsonify({
            'success': success,
            'message': 'Notebook processed' if success else 'Processing completed with errors',
            'module_number': module_number,
            'output': output,
            'result_file': result_filename,
            'timestamp': datetime.utcnow().isoformat()
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Processing failed',
            'output': output,
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@app.route('/api/v1/notebook/download/<filename>')
def download_notebook(filename):
    """Download processed notebook"""
    logger.info(f"Download requested for: {filename}")
    filepath = os.path.join(PROCESSED_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return jsonify({'error': 'File not found'}), 404


# --- Error Handlers (ORIGINAL PRESERVED) ---
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
        "timestamp": datetime.utcnow().iso
