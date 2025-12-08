#!/bin/bash
# Quick script to test the Docker setup locally before deploying

echo "=== Building Docker image ==="
docker build -t tinytorch-api-test .

if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

echo ""
echo "=== Testing tito availability in container ==="
docker run --rm tinytorch-api-test bash -c "
    echo 'PATH: $PATH'
    echo 'PYTHONPATH: $PYTHONPATH'
    echo ''
    echo 'Looking for tito:'
    which tito || echo 'tito not in PATH'
    echo ''
    echo 'Checking if tito exists:'
    ls -la /app/TinyTorch/bin/tito 2>/dev/null || echo 'No tito in expected location'
    echo ''
    echo 'Trying to run tito:'
    tito --version 2>&1 || echo 'tito command failed'
    echo ''
    echo 'Checking Python import:'
    python -c 'import sys; print(sys.path)' 
    echo ''
    echo 'Files in TinyTorch:'
    ls -la /app/TinyTorch/ | head -20
"

echo ""
echo "=== Starting API container ==="
docker run -d -p 10000:10000 --name tinytorch-test tinytorch-api-test

echo "Waiting for container to start..."
sleep 3

echo ""
echo "=== Testing health endpoint ==="
curl -s http://localhost:10000/api/v1/health | python3 -m json.tool

echo ""
echo "=== Testing tito command via API ==="
curl -s -X POST http://localhost:10000/api/v1/tito/command \
  -H "Content-Type: application/json" \
  -d '{"args": ["--version"]}' | python3 -m json.tool

echo ""
echo "=== Cleaning up ==="
docker stop tinytorch-test
docker rm tinytorch-test

echo ""
echo "✅ Test complete! Check the output above for any errors."
echo "If everything looks good, deploy to Render!"
