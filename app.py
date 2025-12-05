
# --- app.py ---

import subprocess
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- Utility Function to Handle CLI Output ---
def execute_tito_command(args):
    """Executes a tito command and returns its output or raises an error."""
    try:
        # Secure execution: Pass command and arguments as a list.
        command = ['tito'] + args
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True # Raise CalledProcessError for non-zero exit codes
        )
        return result.stdout.strip()
    
    except subprocess.CalledProcessError as e:
        # Log the error and return structured failure data
        error_message = f"tito command failed. STDERR: {e.stderr}"
        print(error_message)
        raise RuntimeError(error_message)
    except FileNotFoundError:
        raise RuntimeError("The 'tito' command was not found. Check installation.")


# --- API Endpoints ---

# Example: Run a system diagnostic (GET request)
@app.route('/api/v1/status', methods=['GET'])
def get_tito_status():
    """Returns the output of 'tito checkpoint status'."""
    try:
        # Execute the command
        cli_output = execute_tito_command(['checkpoint', 'status'])
        
        # NOTE: You MUST replace this with robust parsing logic 
        # that converts the CLI text output into a predictable JSON structure
        # for your PHP frontend.
        parsed_data = {"raw_output": cli_output.split('\n')} 
        
        return jsonify({
            "status": "success",
            "tito_status": parsed_data
        })
    except RuntimeError as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Example: Run a grading/validation command (POST request)
@app.route('/api/v1/validate', methods=['POST'])
def run_assignment_validation():
    """Runs module completion and returns validation result."""
    data = request.get_json()
    module_id = data.get('module') # Expected from PHP, e.g., '01'
    
    if not module_id:
        return jsonify({"status": "error", "message": "Missing 'module' parameter."}), 400
    
    try:
        # 1. Run the module completion/export command
        execute_tito_command(['module', 'complete', module_id])
        
        # 2. Run the validation/autograde command (assuming a CLI structure like this)
        validation_output = execute_tito_command(['grade', 'autograde', f'{module_id}_tensor']) 
        
        # NOTE: Implement parsing here to extract the final score/log details
        
        return jsonify({
            "status": "validation_complete",
            "module": module_id,
            "validation_log": validation_output.split('\n')
        })
    
    except RuntimeError as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Optional: Start server locally for testing
if __name__ == '__main__':
    # Use environment variable for port, default to 5000
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
