# --- app.py with Notebook Management ---

import subprocess
import os
import logging
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string, send_file
import nbformat
from nbformat.v4 import new_notebook, new_code_cell, new_markdown_cell

app = Flask(__name__)

# Configure paths
WORKSPACE_DIR = Path("/app/workspace")
NOTEBOOKS_DIR = WORKSPACE_DIR / "notebooks"
ASSIGNMENTS_DIR = WORKSPACE_DIR / "assignments"

# Create directories
WORKSPACE_DIR.mkdir(exist_ok=True)
NOTEBOOKS_DIR.mkdir(exist_ok=True)
ASSIGNMENTS_DIR.mkdir(exist_ok=True)

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

logger.info("TinyTorch API Service with Notebook Management starting...")

# --- Utility Functions ---

def execute_tito_command(args, cwd=None):
    """Executes a tito command and returns its stdout output or raises an error."""
    try:
        command = ['tito'] + args
        logger.info(f"Executing tito command: {' '.join(command)}")
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=60,
            cwd=cwd or str(WORKSPACE_DIR)
        )
        
        logger.info(f"Command succeeded. Output length: {len(result.stdout)} chars")
        return result.stdout.strip()
    
    except subprocess.CalledProcessError as e:
        error_message = f"tito command failed. STDERR: {e.stderr.strip()}"
        logger.error(error_message)
        raise RuntimeError(error_message)
    
    except subprocess.TimeoutExpired:
        error_message = "tito command timed out after 60 seconds"
        logger.error(error_message)
        raise RuntimeError(error_message)
    
    except FileNotFoundError:
        error_message = "The 'tito' command was not found."
        logger.error(error_message)
        raise RuntimeError(error_message)


def py_to_notebook(py_file_path, nb_file_path):
    """Convert a .py file to .ipynb notebook format."""
    try:
        with open(py_file_path, 'r') as f:
            py_content = f.read()
        
        # Create a new notebook
        nb = new_notebook()
        
        # Split by cell delimiters (common patterns)
        # TinyTorch uses # %% or similar markers
        cells = []
        current_cell = []
        cell_type = 'code'
        
        for line in py_content.split('\n'):
            # Check for cell markers
            if line.strip().startswith('# %%') or line.strip().startswith('#%%'):
                # Save previous cell
                if current_cell:
                    content = '\n'.join(current_cell)
                    if cell_type == 'markdown':
                        cells.append(new_markdown_cell(content))
                    else:
                        cells.append(new_code_cell(content))
                    current_cell = []
                
                # Check if it's a markdown cell
                if '[markdown]' in line.lower():
                    cell_type = 'markdown'
                else:
                    cell_type = 'code'
            else:
                current_cell.append(line)
        
        # Add final cell
        if current_cell:
            content = '\n'.join(current_cell)
            if cell_type == 'markdown':
                cells.append(new_markdown_cell(content))
            else:
                cells.append(new_code_cell(content))
        
        nb['cells'] = cells
        
        # Write notebook
        with open(nb_file_path, 'w') as f:
            nbformat.write(nb, f)
        
        logger.info(f"Converted {py_file_path} to {nb_file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to convert py to notebook: {e}")
        raise


def notebook_to_py(nb_file_path, py_file_path):
    """Convert a .ipynb notebook to .py file."""
    try:
        with open(nb_file_path, 'r') as f:
            nb = nbformat.read(f, as_version=4)
        
        py_lines = []
        
        for cell in nb['cells']:
            if cell['cell_type'] == 'markdown':
                py_lines.append('# %% [markdown]')
                # Comment out markdown content
                for line in cell['source'].split('\n'):
                    py_lines.append(f'# {line}')
            elif cell['cell_type'] == 'code':
                py_lines.append('# %%')
                py_lines.append(cell['source'])
            
            py_lines.append('')  # Empty line between cells
        
        with open(py_file_path, 'w') as f:
            f.write('\n'.join(py_lines))
        
        logger.info(f"Converted {nb_file_path} to {py_file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to convert notebook to py: {e}")
        raise


def execute_notebook(nb_file_path):
    """Execute a notebook and return the result."""
    try:
        from nbconvert.preprocessors import ExecutePreprocessor
        
        with open(nb_file_path, 'r') as f:
            nb = nbformat.read(f, as_version=4)
        
        ep = ExecutePreprocessor(timeout=600, kernel_name='python3')
        ep.preprocess(nb, {'metadata': {'path': str(NOTEBOOKS_DIR)}})
        
        # Save executed notebook
        with open(nb_file_path, 'w') as f:
            nbformat.write(nb, f)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to execute notebook: {e}")
        raise


# --- API Documentation HTML ---
API_DOCS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>TinyTorch Notebook API</title>
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', sans-serif;
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
        h1 { color: #667eea; margin: 0 0 10px 0; }
        .subtitle { color: #666; margin-bottom: 30px; }
        .workflow {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #667eea;
        }
        .workflow h3 { margin-top: 0; color: #667eea; }
        .workflow ol { line-height: 1.8; }
        .endpoint { 
            background: #f8f9fa;
            padding: 25px; 
            margin: 20px 0; 
            border-radius: 10px;
            border: 1px solid #dee2e6;
        }
        .method { 
            display: inline-block;
            padding: 6px 12px; 
            border-radius: 6px; 
            font-weight: bold;
            margin-right: 10px;
            text-transform: uppercase;
            font-size: 0.85em;
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
    </style>
</head>
<body>
    <div class="container">
        <h1>📓 TinyTorch Notebook API</h1>
        <p class="subtitle">Manage and execute notebooks in the cloud</p>
        
        <div class="workflow">
            <h3>🔄 Typical Workflow</h3>
            <ol>
                <li><strong>Convert:</strong> Use <code>/api/v1/notebook/convert</code> to convert .py → .ipynb</li>
                <li><strong>Edit:</strong> Modify notebook via <code>/api/v1/notebook/update</code> or download/upload</li>
                <li><strong>Save:</strong> Notebook changes are persisted on the server</li>
                <li><strong>Run tito:</strong> Execute tito commands on the saved notebooks</li>
                <li><strong>Grade:</strong> Use tito grade commands on completed assignments</li>
            </ol>
        </div>

        <div class="endpoint">
            <span class="method post">POST</span>
            <h3>/api/v1/notebook/convert</h3>
            <p>Convert a .py file to .ipynb notebook format</p>
            <pre>{
  "source_file": "01_tensor.py",
  "target_file": "01_tensor.ipynb"
}</pre>
        </div>

        <div class="endpoint">
            <span class="method get">GET</span>
            <h3>/api/v1/notebook/list</h3>
            <p>List all notebooks in the workspace</p>
        </div>

        <div class="endpoint">
            <span class="method get">GET</span>
            <h3>/api/v1/notebook/read/{filename}</h3>
            <p>Read a specific notebook (returns JSON)</p>
        </div>

        <div class="endpoint">
            <span class="method post">POST</span>
            <h3>/api/v1/notebook/update</h3>
            <p>Update a notebook's content</p>
            <pre>{
  "filename": "01_tensor.ipynb",
  "cells": [
    {"type": "code", "source": "import torch\\nprint('hello')"},
    {"type": "markdown", "source": "# My Notes"}
  ]
}</pre>
        </div>

        <div class="endpoint">
            <span class="method post">POST</span>
            <h3>/api/v1/notebook/execute</h3>
            <p>Execute a notebook and save results</p>
            <pre>{
  "filename": "01_tensor.ipynb"
}</pre>
        </div>

        <div class="endpoint">
            <span class="method post">POST</span>
            <h3>/api/v1/notebook/save-as-py</h3>
            <p>Convert notebook back to .py format for tito grading</p>
            <pre>{
  "notebook": "01_tensor.ipynb",
  "py_file": "01_tensor.py"
}</pre>
        </div>

        <div class="endpoint">
            <span class="method get">GET</span>
            <h3>/api/v1/health</h3>
            <p>Health check - shows tito and notebook capabilities</p>
        </div>
    </div>
</body>
</html>
"""

# --- API Endpoints ---

@app.route('/', methods=['GET'])
def api_documentation():
    return render_template_string(API_DOCS_HTML)


@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check with notebook capabilities."""
    logger.info("Health check requested")
    
    tito_available = False
    notebook_support = False
    
    try:
        result = subprocess.run(['which', 'tito'], capture_output=True, text=True)
        tito_available = result.returncode == 0
        
        import nbformat, nbconvert
        notebook_support = True
    except Exception as e:
        logger.warning(f"Check failed: {e}")
    
    return jsonify({
        "status": "healthy",
        "service": "TinyTorch Notebook API",
        "tito_available": tito_available,
        "notebook_support": notebook_support,
        "workspace_dir": str(WORKSPACE_DIR),
        "notebooks_dir": str(NOTEBOOKS_DIR),
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route('/api/v1/notebook/convert', methods=['POST'])
def convert_py_to_notebook():
    """Convert .py file to .ipynb notebook."""
    logger.info("Convert endpoint called")
    
    data = request.get_json()
    if not data or 'source_file' not in data:
        return jsonify({"status": "error", "message": "Missing source_file"}), 400
    
    source = data['source_file']
    target = data.get('target_file', source.replace('.py', '.ipynb'))
    
    source_path = WORKSPACE_DIR / source
    target_path = NOTEBOOKS_DIR / target
    
    try:
        if not source_path.exists():
            return jsonify({
                "status": "error",
                "message": f"Source file not found: {source}"
            }), 404
        
        py_to_notebook(source_path, target_path)
        
        return jsonify({
            "status": "success",
            "message": "Conversion complete",
            "source": source,
            "target": target,
            "target_path": str(target_path),
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/v1/notebook/list', methods=['GET'])
def list_notebooks():
    """List all notebooks."""
    try:
        notebooks = list(NOTEBOOKS_DIR.glob('*.ipynb'))
        py_files = list(WORKSPACE_DIR.glob('*.py'))
        
        return jsonify({
            "status": "success",
            "notebooks": [nb.name for nb in notebooks],
            "py_files": [pf.name for pf in py_files],
            "notebooks_dir": str(NOTEBOOKS_DIR),
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/v1/notebook/read/<filename>', methods=['GET'])
def read_notebook(filename):
    """Read a notebook."""
    try:
        nb_path = NOTEBOOKS_DIR / filename
        
        if not nb_path.exists():
            return jsonify({"status": "error", "message": "Notebook not found"}), 404
        
        with open(nb_path, 'r') as f:
            nb = nbformat.read(f, as_version=4)
        
        # Convert to simple dict format
        cells = []
        for cell in nb['cells']:
            cells.append({
                "type": cell['cell_type'],
                "source": cell['source']
            })
        
        return jsonify({
            "status": "success",
            "filename": filename,
            "cells": cells,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/v1/notebook/update', methods=['POST'])
def update_notebook():
    """Update notebook content."""
    data = request.get_json()
    if not data or 'filename' not in data or 'cells' not in data:
        return jsonify({"status": "error", "message": "Missing filename or cells"}), 400
    
    try:
        nb_path = NOTEBOOKS_DIR / data['filename']
        
        # Create new notebook
        nb = new_notebook()
        
        for cell_data in data['cells']:
            if cell_data['type'] == 'markdown':
                nb['cells'].append(new_markdown_cell(cell_data['source']))
            else:
                nb['cells'].append(new_code_cell(cell_data['source']))
        
        with open(nb_path, 'w') as f:
            nbformat.write(nb, f)
        
        return jsonify({
            "status": "success",
            "message": "Notebook updated",
            "filename": data['filename'],
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/v1/notebook/execute', methods=['POST'])
def execute_notebook_endpoint():
    """Execute a notebook."""
    data = request.get_json()
    if not data or 'filename' not in data:
        return jsonify({"status": "error", "message": "Missing filename"}), 400
    
    try:
        nb_path = NOTEBOOKS_DIR / data['filename']
        
        if not nb_path.exists():
            return jsonify({"status": "error", "message": "Notebook not found"}), 404
        
        execute_notebook(nb_path)
        
        return jsonify({
            "status": "success",
            "message": "Notebook executed",
            "filename": data['filename'],
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/v1/notebook/save-as-py', methods=['POST'])
def save_notebook_as_py():
    """Convert notebook back to .py for tito."""
    data = request.get_json()
    if not data or 'notebook' not in data:
        return jsonify({"status": "error", "message": "Missing notebook"}), 400
    
    notebook = data['notebook']
    py_file = data.get('py_file', notebook.replace('.ipynb', '.py'))
    
    nb_path = NOTEBOOKS_DIR / notebook
    py_path = ASSIGNMENTS_DIR / py_file
    
    try:
        if not nb_path.exists():
            return jsonify({"status": "error", "message": "Notebook not found"}), 404
        
        notebook_to_py(nb_path, py_path)
        
        return jsonify({
            "status": "success",
            "message": "Saved as Python file",
            "notebook": notebook,
            "py_file": py_file,
            "py_path": str(py_path),
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/v1/tito/command', methods=['POST'])
def execute_tito_command_endpoint():
    """Execute tito commands."""
    data = request.get_json()
    if not data or 'args' not in data:
        return jsonify({"status": "error", "message": "Missing args"}), 400
    
    try:
        # Can specify working directory
        cwd = data.get('cwd', str(ASSIGNMENTS_DIR))
        output = execute_tito_command(data['args'], cwd=cwd)
        
        return jsonify({
            "status": "success",
            "command": data['args'],
            "output": output,
            "cwd": cwd,
            "timestamp": datetime.utcnow().isoformat()
        })
    except RuntimeError as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)
