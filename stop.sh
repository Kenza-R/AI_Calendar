#!/bin/bash

# AI Calendar - Stop Script
# This script stops both backend and frontend services

echo "🛑 Stopping AI Calendar Application..."
echo ""

# Stop backend (uvicorn)
BACKEND_PIDS=$(lsof -ti :8000)
if [ ! -z "$BACKEND_PIDS" ]; then
    echo "Stopping Backend (port 8000)..."
    kill $BACKEND_PIDS 2>/dev/null
    sleep 1
    echo "✅ Backend stopped"
else
    echo "ℹ️  Backend is not running"
fi

# Stop frontend (vite)
FRONTEND_PIDS=$(lsof -ti :5173)
if [ ! -z "$FRONTEND_PIDS" ]; then
    echo "Stopping Frontend (port 5173)..."
    kill $FRONTEND_PIDS 2>/dev/null
    sleep 1
    echo "✅ Frontend stopped"
else
    echo "ℹ️  Frontend is not running"
fi

echo ""
echo "✅ All services stopped"
echo ""
