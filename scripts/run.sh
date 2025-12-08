#!/bin/bash

# AI Calendar - Quick Start Script
# This script starts both backend and frontend services

echo "🚀 Starting AI Calendar Application..."
echo ""

# Get the project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$PROJECT_DIR/.venv312"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Python virtual environment not found at $VENV_PATH"
    echo "Please create it with: python3.12 -m venv .venv312"
    exit 1
fi

# Check if node_modules exists
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "❌ Node modules not found. Installing..."
    cd "$FRONTEND_DIR"
    npm install
    cd "$PROJECT_DIR"
fi

# Check if services are already running
BACKEND_RUNNING=$(lsof -i :8000 | grep LISTEN || echo "")
FRONTEND_RUNNING=$(lsof -i :5173 | grep LISTEN || echo "")

if [ ! -z "$BACKEND_RUNNING" ]; then
    echo "⚠️  Backend is already running on port 8000"
else
    echo "🔧 Starting Backend on http://localhost:8000..."
    cd "$BACKEND_DIR"
    "$VENV_PATH/bin/python" -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
    BACKEND_PID=$!
    echo "   Backend PID: $BACKEND_PID"
    sleep 2
fi

if [ ! -z "$FRONTEND_RUNNING" ]; then
    echo "⚠️  Frontend is already running on port 5173"
else
    echo "🎨 Starting Frontend on http://localhost:5173..."
    cd "$FRONTEND_DIR"
    npm run dev > ../frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo "   Frontend PID: $FRONTEND_PID"
    sleep 2
fi

echo ""
echo "✅ Services started successfully!"
echo ""
echo "📍 Access your application:"
echo "   Frontend: http://localhost:5173"
echo "   Backend API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "📝 Logs:"
echo "   Backend: tail -f $PROJECT_DIR/backend.log"
echo "   Frontend: tail -f $PROJECT_DIR/frontend.log"
echo ""
echo "🛑 To stop services, run: ./stop.sh"
echo ""
