#!/bin/bash

# FastAPI Server - Service Oper Uchet
echo "========================================"
echo "  FastAPI Server - Service Oper Uchet"
echo "========================================"
echo

echo "Starting FastAPI server on http://localhost:8000"
echo "Press CTRL+C to stop server"
echo

echo "Demo credentials:"
echo "- admin / password (Administrator)"
echo "- analyst / password (Analyst)"
echo "- viewer / password (Viewer)"
echo

echo "========================================"
python -m uvicorn src.presentation.api.main:app --reload --host 0.0.0.0 --port 8000

echo
echo "Server stopped!"
