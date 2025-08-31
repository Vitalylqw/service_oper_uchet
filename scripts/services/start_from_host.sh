#!/bin/bash

# Start Project from Host - Service Oper Uchet
echo "========================================"
echo "  Start Project from Host - Service Oper Uchet"
echo "========================================"
echo

echo "This script should be run from host machine (not from dev-container)"
echo

echo "Creating devnet network if it doesn't exist..."
docker network create devnet 2>/dev/null || echo "Network devnet already exists"

echo "Starting PostgreSQL database..."
docker-compose -f docker-compose.db.yml up -d

echo "Waiting for database to be ready..."
sleep 5

echo "Checking database connection..."
docker exec so_pg pg_isready -U so_user -d so_uchet

if [ $? -eq 0 ]; then
    echo "Database is ready!"
    echo
    echo "Now you can:"
    echo "1. Open project in Cursor"
    echo "2. Choose 'Reopen in Container'"
    echo "3. In dev-container run: ./scripts/services/start_backend.sh"
    echo
    echo "Or run backend directly from host:"
    echo "./scripts/services/start_backend.sh"
else
    echo "Database is not ready yet. Please wait and try again."
fi

echo
echo "========================================"
