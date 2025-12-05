# --- app.py ---

import subprocess
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- Utility Function to Handle CLI Output ---
def execute_tito_command(args):
    """Executes a tito command and returns its stdout output or raises an error."""
    try:
        # Secure execution: Pass command and arguments as a list.
        command = ['tito'] + args
        
        result = subprocess.run(
            command,
            capture_output=True, # Captures stdout and stderr
            text=True,           # Decodes output as text
            check=True           # Raise CalledProcessError for non-zero exit codes (tito failed)
        )
        return result.stdout.strip()
    
    except subprocess.CalledProcessError as e:
        # If tito ran but returned an error exit code (e.g., validation failed)
        error_message = f"tito command failed. STDERR: {e.stderr.strip()}"
        print(error_message)
        # Re-raise the error so the API endpoint can catch it and return a 500
        raise RuntimeError(error_message) 
    except FileNotFoundError:
        # If the 'tito' command itself doesn't exist on the system
        raise RuntimeError("The 'tito' command was not found. Check Dockerfile and PATH.")


# --- API Endpoints ---

# 1. System Status Endpoint (GET)
@app.route('/api/v1/status', methods=['GET'])
def get_tito_status():
    """Returns the output of 'tito checkpoint status'."""
    try:
        # Execute the command
        cli_output = execute_tito_command(['checkpoint', 'status'])
        
        # NOTE: Implement robust parsing logic here to convert the plaintext 
        # (e.g., 'Module 01: Incomplete') into a structured JSON dictionary.
        parsed_data = {"raw_output": cli_output.split('\n')} 
        
        return jsonify({
            "status": "success",
            "tito_status": parsed_data
        })
    except RuntimeError as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# 2. Assignment Validation Endpoint (POST/GET)
@app.route('/api/v1/validate', methods=['GET', 'POST'])
def run_assignment_validation():
    """Runs module completion and returns validation result."""
    
    # --- Data Retrieval Logic (Handles POST JSON OR GET URL params) ---
    data = request.get_json(silent=True)
    
    # If no JSON body (usually a GET request), fall back to reading URL parameters
    if data is None:
        data = request.args
        
    module_id = data.get('module') # Expected from PHP or URL param, e.g., '01'
    
    if not module_id:
        return jsonify({"status": "error", "message": "Missing 'module' parameter in JSON body or URL."}), 400
    
    # --- Tito Execution Logic ---
    try:
        # 1. Run the module completion/export command
        # This assumes your assignment files (e.g., 01_tensor.py) are accessible.
        completion_output = execute_tito_command(['module', 'complete', module_id])
        
        # 2. Run the validation/autograde command
        # This assumes the assignment identifier is {module_id}_tensor, per common TITO examples.
        validation_output = execute_tito_command(['grade', 'autograde', f'{module_id}_tensor']) 
        
        # NOTE: Implement parsing here to extract the final score, pass/fail status, etc.
        # For now, we return the raw output.
        
        return jsonify({
            "status": "validation_complete",
            "module": module_id,
            "completion_log": completion_output.split('\n'),
            "validation_log": validation_output.split('\n')
        })
    
    except RuntimeError as e:
        # This catches errors from the execute_tito_command utility function
        return jsonify({"status": "error", "message": str(e)}), 500


# --- Local Runner ---
if __name__ == '__main__':
    # Use environment variable for port, default to 5000 for local development
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
