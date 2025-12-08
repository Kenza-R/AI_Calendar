#!/bin/bash

# Simple Start Script for AI Calendar
# This script starts both backend and frontend servers

echo "🚀 Starting AI Calendar with Enhanced Features..."
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# Function to check if a port is in use
check_port() {
    lsof -ti:$1 >/dev/null 2>&1
}

# Function to kill process on port
kill_port() {
    if check_port $1; then
        echo "⚠️  Port $1 is in use. Killing existing process..."
        lsof -ti:$1 | xargs kill -9 2>/dev/null
        sleep 2
    fi
}

# Clean up any existing processes
kill_port 8000
kill_port 5173

echo "═══════════════════════════════════════════"
echo "📦 STARTING BACKEND"
echo "═══════════════════════════════════════════"
echo ""

# Check if virtual environment exists
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo "📥 Creating Python virtual environment..."
    cd "$BACKEND_DIR"
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment and start backend
echo "📥 Installing/updating dependencies..."
cd "$BACKEND_DIR"
source venv/bin/activate
pip install -q -r requirements.txt

echo ""
echo "🚀 Starting backend server on port 8000..."
uvicorn main:app --reload --port 8000 > /tmp/ai_calendar_backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"
echo "📋 Backend logs: tail -f /tmp/ai_calendar_backend.log"

sleep 3

echo ""
echo "═══════════════════════════════════════════"
echo "🎨 STARTING FRONTEND"
echo "═══════════════════════════════════════════"
echo ""

# Install frontend dependencies if needed
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "📥 Installing frontend dependencies..."
    cd "$FRONTEND_DIR"
    npm install
fi

echo "🚀 Starting frontend server on port 5173..."
cd "$FRONTEND_DIR"
npm run dev > /tmp/ai_calendar_frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID)"
echo "📋 Frontend logs: tail -f /tmp/ai_calendar_frontend.log"

sleep 3

echo ""
echo "═══════════════════════════════════════════"
echo "✨ AI CALENDAR IS READY!"
echo "═══════════════════════════════════════════"
echo ""
echo "🌐 Application Links:"
echo "   Frontend:     http://localhost:5173"
echo "   Backend API:  http://localhost:8000"
echo "   API Docs:     http://localhost:8000/docs"
echo ""
echo "📄 Enhanced Features:"
echo "   ✅ Advanced syllabus parsing"
echo "   ✅ Assessment component extraction"
echo "   ✅ Class session detection"
echo "   ✅ Context-aware deadline extraction"
echo ""
echo "🔑 Default Login (if demo user exists):"
echo "   Email:    demo@example.com"
echo "   Password: demo123"
echo ""
echo "📋 View Logs:"
echo "   Backend:  tail -f /tmp/ai_calendar_backend.log"
echo "   Frontend: tail -f /tmp/ai_calendar_frontend.log"
echo ""
echo "🛑 To stop servers:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo "   OR: pkill -f 'uvicorn|npm run dev'"
echo ""
echo "💡 Make sure to set your OPENAI_API_KEY in backend/.env"
echo ""

# Keep script running
echo "Press Ctrl+C to stop all servers..."
wait
