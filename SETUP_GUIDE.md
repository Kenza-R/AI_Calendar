# 🚀 AI Calendar - Setup & Running Guide

## ✅ Everything is Now Running!

### Access the Application

**Open your browser and go to:**
```
http://localhost:5173
```

### Login Credentials
- **Email:** demo@example.com
- **Password:** demo123

---

## 📋 How the Setup Works

### Backend (Port 8000)
- **Status:** ✅ Running at `http://localhost:8000`
- **API Docs:** `http://localhost:8000/docs` (interactive API documentation)
- **Health Check:** `http://localhost:8000/health`

### Frontend (Port 5173)
- **Status:** ✅ Running at `http://localhost:5173`
- **Built with:** React + Vite

---

## 🛠️ Manual Setup Steps (if you need to restart)

### 1. Start Backend (Terminal 1)

```bash
cd backend
source venv/bin/activate
python main.py
```

Backend will start at: **http://localhost:8000**

### 2. Start Frontend (Terminal 2)

```bash
cd frontend
npm run dev
```

Frontend will start at: **http://localhost:5173**

### 3. Open in Browser
```
http://localhost:5173
```

---

## 📝 Database

- **Type:** SQLite
- **Location:** `backend/ai_calendar.db`
- **Sample User:** demo@example.com / demo123

**Note:** Sample data is included from the initial database setup. If you want to reset the database, simply delete `ai_calendar.db` and restart the backend.

---

## 🤖 Optional: Enable AI Features

To use AI-powered features (deadline extraction, prep material generation):

1. Get an OpenAI API key from [https://platform.openai.com/](https://platform.openai.com/)

2. Create/edit `.env` file in the `backend` directory:
   ```
   OPENAI_API_KEY=your-api-key-here
   ```

3. Restart the backend server

Without an OpenAI key, the app works with sample prep materials.

---

## ⚙️ Troubleshooting

### Port Already in Use?
- Backend (8000): `lsof -i :8000` and `kill -9 <PID>`
- Frontend (5173): `lsof -i :5173` and `kill -9 <PID>`

### Backend Won't Start?
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Frontend Won't Start?
```bash
cd frontend
npm install
npm run dev
```

### Database Issues?
Delete the database and restart:
```bash
rm backend/ai_calendar.db
# Restart backend
```

---

## 📚 What You Can Do

✅ **View Calendar** - See all your events in a visual calendar
✅ **Manage Tasks** - Create, edit, and track tasks with deadlines
✅ **Upload Documents** - Upload syllabi (PDF/TXT/DOCX) to extract deadlines
✅ **AI Prep Material** - Get flashcards, quiz questions, and interview prep
✅ **Auto-Schedule** - Automatically schedule prep sessions before deadlines
✅ **Track Progress** - See workload analysis and schedule overview

---

## 🔗 Useful Links

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Documentation:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

---

**Enjoy using your AI Productivity Calendar! 📅✨**
