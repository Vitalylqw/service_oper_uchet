#!/bin/bash

# Setup Dev Network - Service Oper Uchet
echo "========================================"
echo "  Setup Dev Network - Service Oper Uchet"
echo "========================================"
echo

# Check if we're in dev-container
if [ -n "$VSCODE_EXTENSION_DEVELOPMENT_HOST" ] || [ -f /.dockerenv ]; then
    echo "Running in dev-container - Docker commands not available"
    echo "Database should be started from host machine"
    echo
    echo "On host machine run:"
    echo "docker-compose -f docker-compose.db.yml up -d"
    echo
else
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
    else
        echo "Database is not ready yet. Please wait and try again."
    fi
fi

echo
echo "========================================"
