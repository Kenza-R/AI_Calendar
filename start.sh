#!/bin/bash

# AI Calendar Startup Script

echo "🚀 Starting AI Calendar..."

# Kill any existing processes
echo "Cleaning up old processes..."
pkill -9 -f "npm run dev" 2>/dev/null
pkill -9 -f "python.*main" 2>/dev/null
pkill -9 -f "uvicorn" 2>/dev/null
sleep 2

PROJECT_DIR="/Users/annaepple/AI_Calendar-1/AI_Calendar"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

# Start Backend
echo "📦 Starting Backend on port 8000..."
cd "$BACKEND_DIR"
/Users/annaepple/AI_Calendar-1/AI_Calendar/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"
sleep 3

# Start Frontend
echo "🎨 Starting Frontend on port 5173..."
cd "$FRONTEND_DIR"
npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID)"
sleep 3

echo ""
echo "═══════════════════════════════════════════"
echo "✨ AI Calendar is Ready!"
echo "═══════════════════════════════════════════"
echo ""
echo "🌐 Frontend: http://localhost:5173"
echo "📡 Backend:  http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "🔑 Login Credentials:"
echo "   Email:    demo@example.com"
echo "   Password: demo123"
echo ""
echo "📋 Logs:"
echo "   Backend:  tail -f /tmp/backend.log"
echo "   Frontend: tail -f /tmp/frontend.log"
echo ""
echo "To stop: Press Ctrl+C or run 'pkill -f \"npm run dev\"; pkill -f python'"
echo ""

# Wait for both processes
wait
