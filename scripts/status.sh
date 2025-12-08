#!/bin/bash

# AI Calendar - Status Check Script
# This script checks the status of both services

echo "🔍 AI Calendar Application Status"
echo "=================================="
echo ""

# Check Backend
if lsof -i :8000 | grep LISTEN > /dev/null; then
    BACKEND_PID=$(lsof -ti :8000)
    echo "✅ Backend: Running on http://localhost:8000 (PID: $BACKEND_PID)"
else
    echo "❌ Backend: Not running"
fi

# Check Frontend
if lsof -i :5173 | grep LISTEN > /dev/null; then
    FRONTEND_PID=$(lsof -ti :5173)
    echo "✅ Frontend: Running on http://localhost:5173 (PID: $FRONTEND_PID)"
else
    echo "❌ Frontend: Not running"
fi

echo ""
echo "📚 Quick Links:"
echo "   Frontend: http://localhost:5173"
echo "   API Docs: http://localhost:8000/docs"
echo ""
