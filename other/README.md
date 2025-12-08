
TinyTorch Cloud API - Correct Deployment Guide
The Core Problem (And Why You Were Right!)
TinyTorch is designed for local student development, NOT cloud deployment.
What TinyTorch Expects:
bashgit clone https://github.com/MLSysBook/TinyTorch.git
cd TinyTorch
./setup-environment.sh    # Creates venv, installs deps
source activate.sh        # Sets PATH and PYTHONPATH
tito system doctor        # Now works!
What You're Building:
HTTP → Flask API → tito commands → JSON response
The mismatch: TinyTorch's setup scripts (setup-environment.sh and activate.sh) configure environment variables for interactive shell sessions. Docker needs these set as permanent ENV variables.
The Solution (No More Circles!)
Don't try to pip install TinyTorch. Instead, replicate what the setup scripts do:

Clone the TinyTorch repo
Add bin/ directory to PATH
Add repo root to PYTHONPATH
Install dependencies manually

That's it!
Files You Need
1. Dockerfile (Cloud-Native Version)
Use the Cloud-Native Dockerfile I provided. Key sections:
dockerfile# Clone the repo (don't pip install!)
RUN git clone https://github.com/MLSysBook/TinyTorch.git /app/TinyTorch

# Replicate what activate.sh does
ENV PATH="/app/TinyTorch/bin:${PATH}"
ENV PYTHONPATH="/app/TinyTorch:${PYTHONPATH}"

# Install what setup-environment.sh would install
RUN pip install numpy torch pytest jupytext pyyaml rich...
2. app.py
Your existing app.py should work, but here's a key point:
python# tito will now be in PATH automatically
result = subprocess.run(['tito', '--version'], ...)
No need for complex path finding - Docker ENV handles it!
3. requirements.txt (Optional)
Since we're installing deps directly in Dockerfile, requirements.txt is optional. But keeping it doesn't hurt.
Deployment Steps
Step 1: Test Locally (Highly Recommended!)
bash# Make the test script executable
chmod +x test_locally.sh

# Run it
./test_locally.sh
This will:

Build the Docker image
Test if tito is accessible
Start the API
Test the health endpoint
Test a tito command
Clean up

If this works locally, it'll work on Render!
Step 2: Deploy to Render
bash# Update your files
git add Dockerfile app.py
git commit -m "Cloud-native TinyTorch setup - no more circular deps!"
git push origin main
Render will automatically:

Clone your repo
Build the Dockerfile
Start the service

Step 3: Verify Deployment
Visit your Render URL and:

Test health: GET /api/v1/health

Should show tito is available


Test version:

json   POST /api/v1/tito/command
   {"args": ["--version"]}

Test system doctor:

json   POST /api/v1/tito/command
   {"args": ["system", "doctor"]}
What Changed from Before
❌ What Didn't Work:
dockerfile# This assumes TinyTorch is a pip package (it's not!)
RUN git clone ... && cd tinytorch && pip install .
✅ What Works:
dockerfile# Clone and configure environment (like the setup scripts do)
RUN git clone https://github.com/MLSysBook/TinyTorch.git /app/TinyTorch
ENV PATH="/app/TinyTorch/bin:${PATH}"
ENV PYTHONPATH="/app/TinyTorch:${PYTHONPATH}"
Understanding the Setup Scripts
setup-environment.sh does:

Creates Python venv
Installs dependencies
May create symlinks

activate.sh does:

Exports PATH with bin/ directory
Exports PYTHONPATH with repo root
Activates venv

Docker equivalent:
dockerfile# No venv needed (Docker IS isolated)
# Just set the ENV variables permanently
ENV PATH="/app/TinyTorch/bin:${PATH}"
ENV PYTHONPATH="/app/TinyTorch:${PYTHONPATH}"

# Install deps directly
RUN pip install <dependencies>
Expected Results
After deployment, tito system doctor should show:
Environment Check
┌────────────────────────────────┬─────────────────┐
│ Python                         │      ✅ OK      │
│ Virtual Environment            │   ❌ N/A       │  ← Expected in Docker!
│ NumPy                          │      ✅ OK      │
│ Rich                           │      ✅ OK      │
│ PyYAML                         │      ✅ OK      │
│ Pytest                         │   ✅ OK         │
│ Jupytext                       │   ✅ OK         │
└────────────────────────────────┴─────────────────┘
Note: Virtual Environment will show as missing or N/A because Docker containers don't need venvs - the entire container IS the isolated environment!
Troubleshooting
"tito: command not found"

Check if /app/TinyTorch/bin/tito exists in the container
Verify PATH includes /app/TinyTorch/bin
Run: docker run --rm <image> bash -c "echo $PATH && which tito"

"No module named 'tito'"

Check if PYTHONPATH includes /app/TinyTorch
Verify Python can see the tito module
Run: docker run --rm <image> python -c "import sys; print(sys.path)"

Build takes forever

Docker is downloading torch (large package)
First build: 5-10 minutes
Subsequent builds: 2-3 minutes (caching)

Why This Approach Works

No pip install confusion - We're not forcing TinyTorch into a package structure
No circular logic - We replicate the setup scripts directly
Cloud-native - Uses Docker ENV instead of shell exports
Simple - Just PATH and PYTHONPATH configuration

This is how TinyTorch was meant to be used, just adapted for Docker instead of a local shell!
Summary

✅ Clone TinyTorch repo
✅ Add bin/ to PATH via ENV
✅ Add repo to PYTHONPATH via ENV
✅ Install dependencies directly
❌ Don't use pip install on TinyTorch
❌ Don't create venv in Docker
❌ Don't try to package TinyTorch

Result: tito commands work, your API works, everyone's happy! 🎉














TinyTorch Cloud API - Quick Reference
The One-Liner Explanation
TinyTorch isn't a pip package. Clone it, set PATH/PYTHONPATH, done.
Dockerfile Essentials
dockerfile# Clone (don't pip install!)
RUN git clone https://github.com/MLSysBook/TinyTorch.git /app/TinyTorch

# Set environment (replaces activate.sh)
ENV PATH="/app/TinyTorch/bin:${PATH}"
ENV PYTHONPATH="/app/TinyTorch:${PYTHONPATH}"

# Install dependencies (replaces setup-environment.sh)
RUN pip install numpy torch pytest jupytext pyyaml rich matplotlib jupyter...
Local Testing
bash# Build
docker build -t tinytorch-api .

# Test interactively
docker run -it --rm tinytorch-api bash
> tito --version
> tito system doctor

# Test API
docker run -d -p 10000:10000 --name test tinytorch-api
curl http://localhost:10000/api/v1/health
docker stop test && docker rm test
Deployment to Render
bashgit add Dockerfile app.py
git commit -m "Fixed TinyTorch cloud setup"
git push origin main
# Render auto-deploys
API Endpoints
bash# Health check
GET /api/v1/health

# Run any tito command
POST /api/v1/tito/command
Content-Type: application/json
{"args": ["system", "doctor"]}

# Examples
{"args": ["--version"]}
{"args": ["module", "list"]}
{"args": ["system", "info"]}
Common Issues & Fixes
IssueFix"tito not found"Add /app/TinyTorch/bin to PATH"No module named tito"Add /app/TinyTorch to PYTHONPATH"Virtual env missing"Normal in Docker! Container IS the envBuild slowTorch is big (~800MB), be patient
Key Insight
❌ TinyTorch as pip package (doesn't exist)
✅ TinyTorch as cloned repo with ENV setup
Files You Need

Dockerfile - Cloud-native version (provided)
app.py - Your existing Flask app (works as-is)
requirements.txt - Optional (deps in Dockerfile)

That's It!
No virtual envs in Docker. No pip install. Just clone, set ENV, deploy.
