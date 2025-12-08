# Quick Start Guide

Get the AI Productivity Calendar up and running in minutes!

## Prerequisites
- Python 3.8+ installed
- Node.js 16+ installed

## Quick Setup (5 minutes)

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create sample data
python seed_data.py

# Start the backend server
python main.py
```

Backend will be running at `http://localhost:8000`

### 2. Frontend Setup (in a new terminal)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

Frontend will be running at `http://localhost:5173`

### 3. Login

Open your browser to `http://localhost:5173` and login with:
- **Email:** demo@example.com
- **Password:** demo123

## What You Can Do

✅ **View Calendar** - See all your events in a visual calendar
✅ **Manage Tasks** - Create, edit, and track tasks with deadlines
✅ **Upload Documents** - Upload syllabi (PDF/TXT/DOCX) to extract deadlines
✅ **AI Prep Material** - Get flashcards, quiz questions, and interview prep
✅ **Auto-Schedule** - Automatically schedule prep sessions before deadlines
✅ **Track Progress** - See workload analysis and schedule overview

## Optional: Enable AI Features

To use AI-powered features (deadline extraction, prep material generation):

1. Get an OpenAI API key from https://platform.openai.com/
2. Create a `.env` file in the `backend` directory:
   ```bash
   cp .env.example .env
   ```
3. Add your API key:
   ```
   OPENAI_API_KEY=your-api-key-here
   ```
4. Restart the backend server

Without an OpenAI key, the app will still work but with sample prep material.

## Need Help?

- API Documentation: http://localhost:8000/docs
- Full README: See README.md in the project root

## Stopping the Servers

Press `Ctrl+C` in each terminal window to stop the backend and frontend servers.

---

Enjoy using your AI Productivity Calendar! 📅✨
