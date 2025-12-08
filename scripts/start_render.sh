#!/bin/bash
# Render startup script for AI Calendar Backend

# Change to backend directory
cd backend

# Start the FastAPI application
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
