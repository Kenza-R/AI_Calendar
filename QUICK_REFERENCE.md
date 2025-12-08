# 🚀 Quick Start Guide

## Your Application is Ready!

Both frontend and backend are **currently running** and ready to use:

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

---

## 📋 Quick Commands

### Check Status
```bash
./status.sh
```

### Start Services (if stopped)
```bash
./run.sh
```

### Stop Services
```bash
./stop.sh
```

---

## 🛠️ Manual Commands

### Backend Only
```bash
# Start
cd backend
../venv312/bin/python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Stop
pkill -f "uvicorn"
```

### Frontend Only
```bash
# Start
cd frontend
npm run dev

# Stop
pkill -f "vite"
```

---

## 📦 Setup (First Time Only)

### Backend Setup
```bash
# Create virtual environment
python3.12 -m venv .venv312

# Activate virtual environment
source .venv312/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### Frontend Setup
```bash
cd frontend
npm install
```

---

## 🔧 Environment Variables

Create a `.env` file in the `backend` directory with:

```env
# OpenAI API Key (required for AI features)
OPENAI_API_KEY=your_openai_api_key_here

# Database (SQLite by default)
DATABASE_URL=sqlite:///./ai_calendar.db

# JWT Secret
SECRET_KEY=your_secret_key_here

# Google Calendar (optional)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Outlook Calendar (optional)
AZURE_CLIENT_ID=your_azure_client_id
AZURE_CLIENT_SECRET=your_azure_client_secret
AZURE_TENANT_ID=your_azure_tenant_id
```

---

## 📱 Application Features

- 📅 **Calendar Management**: View and manage tasks in a calendar view
- 📄 **Document Upload**: Upload syllabi and course documents
- 🤖 **AI Extraction**: Automatically extract deadlines and tasks from documents
- ✅ **Task Management**: Create, edit, and track tasks
- 🔗 **Calendar Integration**: Sync with Google Calendar and Outlook
- 👤 **User Authentication**: Secure login and registration

---

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Check what's using the ports
lsof -i :8000
lsof -i :5173

# Kill processes if needed
./stop.sh
```

### Backend Issues
```bash
# Check backend logs
tail -f backend.log

# Verify database
cd backend
sqlite3 ai_calendar.db ".tables"
```

### Frontend Issues
```bash
# Check frontend logs
tail -f frontend.log

# Reinstall dependencies
cd frontend
rm -rf node_modules package-lock.json
npm install
```

---

## 📚 Project Structure

```
AI_Calendar/
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── models/    # Database models
│   │   ├── routers/   # API endpoints
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── services/  # Business logic
│   │   └── utils/     # Utilities & AI services
│   └── main.py        # Application entry point
├── frontend/          # React + Vite frontend
│   └── src/
│       ├── components/
│       ├── pages/
│       └── services/
└── .venv312/          # Python virtual environment
```

---

## 🎯 Next Steps

1. **Access the app**: Visit http://localhost:5173
2. **Create an account**: Register a new user
3. **Upload a document**: Try uploading a course syllabus
4. **View extracted tasks**: See AI-extracted deadlines in your calendar

---

## 💡 Tips

- Use the **API docs** at http://localhost:8000/docs to explore all endpoints
- Check the **logs** if something doesn't work
- Run `./status.sh` anytime to check if services are running
- The database file is at `backend/ai_calendar.db`

---

**Need help?** Check the other documentation files:
- `SETUP_GUIDE.md` - Detailed setup instructions
- `FEATURES.md` - List of all features
- `QUICKSTART.md` - Quick start tutorial
