#!/usr/bin/env python3
"""
Diagnostic script to debug TinyTorch/tito installation issues
Run this in your Docker container to see what's available
"""

import os
import sys
import subprocess
from pathlib import Path

def check_command(cmd):
    """Check if a command exists in PATH"""
    result = subprocess.run(['which', cmd], capture_output=True, text=True)
    return result.returncode == 0, result.stdout.strip()

def check_module(module_name):
    """Check if a Python module can be imported"""
    try:
        __import__(module_name)
        return True, "Importable"
    except ImportError as e:
        return False, str(e)

def find_files(pattern, search_paths):
    """Find files matching a pattern in given paths"""
    found = []
    for path in search_paths:
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                for file in files:
                    if pattern in file:
                        found.append(os.path.join(root, file))
    return found

def main():
    print("=" * 70)
    print("TinyTorch/tito Installation Diagnostic")
    print("=" * 70)
    
    # Check Python environment
    print("\n1. Python Environment:")
    print(f"   Python executable: {sys.executable}")
    print(f"   Python version: {sys.version}")
    print(f"   Virtual env: {os.environ.get('VIRTUAL_ENV', 'Not set')}")
    
    # Check PATH
    print("\n2. PATH:")
    for p in os.environ.get('PATH', '').split(':'):
        print(f"   {p}")
    
    # Check PYTHONPATH
    print("\n3. PYTHONPATH:")
    pythonpath = os.environ.get('PYTHONPATH', 'Not set')
    if pythonpath != 'Not set':
        for p in pythonpath.split(':'):
            print(f"   {p}")
    else:
        print(f"   {pythonpath}")
    
    # Check for tito command
    print("\n4. Checking for 'tito' command:")
    exists, path = check_command('tito')
    print(f"   In PATH: {exists}")
    if exists:
        print(f"   Location: {path}")
        print(f"   Is symlink: {os.path.islink(path)}")
        if os.path.islink(path):
            print(f"   Points to: {os.readlink(path)}")
    
    # Check for tito module
    print("\n5. Checking for 'tito' Python module:")
    can_import, msg = check_module('tito')
    print(f"   Can import: {can_import}")
    print(f"   Message: {msg}")
    
    if can_import:
        import tito
        print(f"   Module location: {tito.__file__ if hasattr(tito, '__file__') else 'Unknown'}")
        print(f"   Module dir: {dir(tito)}")
    
    # Search for tito files
    print("\n6. Searching for tito-related files:")
    search_paths = ['/app', '/app/TinyTorch', '/usr/local', os.environ.get('VIRTUAL_ENV', '')]
    tito_files = find_files('tito', search_paths)
    if tito_files:
        for f in tito_files[:10]:  # Limit to first 10
            print(f"   {f}")
        if len(tito_files) > 10:
            print(f"   ... and {len(tito_files) - 10} more")
    else:
        print("   No files found")
    
    # Check TinyTorch directory structure
    print("\n7. TinyTorch directory structure:")
    tinytorch_paths = ['/app/TinyTorch', '/app/tinytorch']
    for path in tinytorch_paths:
        if os.path.exists(path):
            print(f"   {path} exists:")
            try:
                items = os.listdir(path)
                for item in sorted(items)[:20]:  # First 20 items
                    full_path = os.path.join(path, item)
                    item_type = 'DIR' if os.path.isdir(full_path) else 'FILE'
                    print(f"      [{item_type}] {item}")
                if len(items) > 20:
                    print(f"      ... and {len(items) - 20} more items")
            except Exception as e:
                print(f"      Error listing: {e}")
        else:
            print(f"   {path} does not exist")
    
    # Check installed packages
    print("\n8. Relevant installed packages:")
    result = subprocess.run(
        ['pip', 'list', '--format=freeze'],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        relevant = [line for line in result.stdout.split('\n') 
                   if any(pkg in line.lower() for pkg in ['tito', 'tiny', 'torch', 'pytest', 'jupytext', 'rich'])]
        for line in relevant:
            print(f"   {line}")
    
    # Try to execute tito if found
    print("\n9. Attempting to execute tito:")
    if exists:
        print("   Running 'tito --version':")
        result = subprocess.run(['tito', '--version'], capture_output=True, text=True)
        print(f"   Return code: {result.returncode}")
        print(f"   STDOUT: {result.stdout}")
        print(f"   STDERR: {result.stderr}")
    else:
        print("   tito command not found, skipping execution test")
    
    # Check for setup.sh or installation scripts
    print("\n10. Looking for installation scripts:")
    scripts = ['setup.sh', 'setup-environment.sh', 'install.sh', 'setup.py', 'pyproject.toml']
    for script in scripts:
        for base_path in ['/app', '/app/TinyTorch']:
            script_path = os.path.join(base_path, script)
            if os.path.exists(script_path):
                print(f"   Found: {script_path}")
                if script.endswith('.sh'):
                    print(f"      Executable: {os.access(script_path, os.X_OK)}")
    
    print("\n" + "=" * 70)
    print("Diagnostic complete!")
    print("=" * 70)

if __name__ == '__main__':
    main()
