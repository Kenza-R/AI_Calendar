# AI Productivity Calendar

An intelligent productivity calendar application that helps students and professionals manage their schedules, deadlines, and preparation tasks. The app integrates with Google Calendar, Gmail, and Outlook to automatically extract deadlines from syllabi and emails, then uses AI to generate personalized prep materials and auto-schedule study sessions.

## Features

### 🗓️ **Smart Calendar Management**
- Visual calendar view with events, deadlines, and prep sessions
- Color-coded events by type (meetings, interviews, exams, prep sessions)
- Drag-and-drop event scheduling
- Sync with Google Calendar and Outlook

### ✅ **Intelligent Task Management**
- Create and manage tasks with deadlines and priorities
- Track completion status
- Automatic deadline extraction from documents
- Estimated time tracking

### 📄 **Document Processing**
- Upload syllabi (PDF, TXT, DOCX)
- AI-powered deadline extraction
- Automatic task creation from documents
- Email scanning for deadline information (Gmail integration)

### 🤖 **AI-Powered Prep Material**
- **Exam Prep**: Flashcards, quiz questions, key concepts, study tips
- **Interview Prep**: Company research, common questions, topics to review, success tips
- Regenerate materials with one click
- Personalized to your specific needs

### 📊 **Schedule Optimization**
- Auto-schedule prep sessions before deadlines
- Workload analysis and feasibility checking
- Free time calculation
- Conflict detection and resolution

### 🔐 **Secure Authentication**
- JWT-based authentication
- OAuth integration for Google and Microsoft accounts
- User-specific data isolation

## Tech Stack

### Backend
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: ORM for database management
- **SQLite**: Lightweight database (easily upgradeable to PostgreSQL)
- **OpenAI GPT**: AI-powered text extraction and content generation
- **Google APIs**: Calendar and Gmail integration
- **Microsoft Graph API**: Outlook integration

### Frontend
- **React**: UI library
- **Vite**: Build tool and dev server
- **React Router**: Navigation
- **FullCalendar**: Interactive calendar component
- **Axios**: HTTP client

## Installation

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn

### Backend Setup

1. **Navigate to backend directory:**
```bash
cd backend
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables:**
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```env
# Required for AI features
OPENAI_API_KEY=your-openai-api-key

# Optional: For Google Calendar/Gmail integration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Optional: For Outlook integration
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret

# Security (change in production)
SECRET_KEY=your-long-random-secret-key
```

5. **Initialize database with sample data:**
```bash
python seed_data.py
```

6. **Run the backend server:**
```bash
python main.py
```

The API will be available at `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

### Frontend Setup

1. **Navigate to frontend directory:**
```bash
cd frontend
```

2. **Install dependencies:**
```bash
npm install
```

3. **Run the development server:**
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`

## Usage

### Getting Started

1. **Login with Demo Account:**
   - Email: `demo@example.com`
   - Password: `demo123`

   Or create a new account using the registration form.

2. **Explore the Dashboard:**
   - **Calendar Tab**: View and manage events
   - **Tasks Tab**: View and manage tasks
   - **Upload Syllabus Tab**: Upload documents to extract deadlines
   - **Overview Tab**: See schedule statistics and upcoming items

### Creating Tasks

1. Click "New Task" in the Tasks tab
2. Fill in task details:
   - Title and description
   - Task type (assignment, exam prep, interview prep, etc.)
   - Deadline and estimated hours
   - Priority level
3. For exam/interview prep tasks, AI will generate study materials
4. Click "Schedule Prep" to auto-schedule preparation sessions

### Uploading Documents

1. Go to the "Upload Syllabus" tab
2. Click "Choose a file" and select a PDF, TXT, or DOCX file
3. Click "Upload & Extract"
4. Review extracted deadlines and tasks
5. Tasks are automatically created and added to your task list

### Using AI Prep Material

1. Open any exam or interview prep task
2. Click "Show Prep Material" to view:
   - **Exam Prep**: Flashcards, quiz questions, key concepts, study tips
   - **Interview Prep**: Company research, questions, topics, tips
3. Click "Regenerate" to get fresh material
4. Use "Schedule Prep" to automatically create study sessions

### Calendar Integration (Optional)

To sync with Google Calendar or Outlook:

1. Set up OAuth credentials in your `.env` file
2. Use the sync endpoints in the Calendar tab
3. Events will be automatically imported

## API Documentation

Once the backend is running, visit `http://localhost:8000/docs` for interactive API documentation with all available endpoints.

### Key Endpoints

**Authentication:**
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login and get token
- `GET /auth/me` - Get current user info

**Events:**
- `GET /events/` - List all events
- `POST /events/` - Create new event
- `PUT /events/{id}` - Update event
- `DELETE /events/{id}` - Delete event

**Tasks:**
- `GET /tasks/` - List all tasks
- `POST /tasks/` - Create new task
- `POST /tasks/{id}/schedule` - Auto-schedule prep sessions
- `POST /tasks/{id}/regenerate-prep` - Regenerate AI prep material

**Documents:**
- `POST /documents/upload-syllabus` - Upload and parse document
- `POST /documents/parse-text` - Parse text for deadlines

**Calendar Sync:**
- `POST /calendar/sync/google` - Sync Google Calendar
- `POST /calendar/sync/gmail` - Scan Gmail for deadlines
- `POST /calendar/sync/outlook` - Sync Outlook Calendar
- `GET /calendar/schedule-overview` - Get schedule statistics

## Sample Data

The application includes sample data for testing:
- Demo user account
- Sample events (lectures, interviews, exams)
- Sample tasks with AI-generated prep material

Run `python backend/seed_data.py` to reset the database with sample data.

## Configuration

### OpenAI API Key (Recommended)

To enable AI features, you need an OpenAI API key:
1. Sign up at [OpenAI](https://platform.openai.com/)
2. Generate an API key
3. Add it to your `.env` file: `OPENAI_API_KEY=your-key`

Without an OpenAI key, the app will work but with limited AI capabilities (sample prep material only).

### Google Calendar/Gmail Integration (Optional)

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Google Calendar API and Gmail API
3. Create OAuth 2.0 credentials
4. Add credentials to `.env` file

### Microsoft Outlook Integration (Optional)

1. Register app in [Azure Portal](https://portal.azure.com/)
2. Configure Microsoft Graph API permissions
3. Add credentials to `.env` file

## Development

### Backend Development

```bash
cd backend
# Install dependencies
pip install -r requirements.txt
# Run with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd frontend
# Install dependencies
npm install
# Run dev server with hot reload
npm run dev
```

### Building for Production

**Frontend:**
```bash
cd frontend
npm run build
# Output will be in dist/ directory
```

**Backend:**
```bash
cd backend
# Use production WSGI server
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Project Structure

```
AI_Calendar/
├── backend/
│   ├── app/
│   │   ├── models/          # Database models
│   │   ├── routers/         # API endpoints
│   │   ├── services/        # Business logic
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── utils/           # Helper functions
│   │   ├── config.py        # Configuration
│   │   └── database.py      # Database setup
│   ├── main.py              # FastAPI application
│   ├── seed_data.py         # Sample data script
│   ├── requirements.txt     # Python dependencies
│   └── .env.example         # Environment template
│
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   ├── services/        # API services
│   │   ├── context/         # React context
│   │   ├── App.jsx          # Main app component
│   │   └── main.jsx         # Entry point
│   ├── index.html           # HTML template
│   ├── vite.config.js       # Vite configuration
│   └── package.json         # Node dependencies
│
└── README.md                # This file
```

## Features Overview

### ✨ What Makes This App Special

1. **AI-Powered Intelligence**: Automatically extracts deadlines from documents and emails, generates personalized study materials
2. **Smart Scheduling**: Auto-schedules prep sessions based on deadlines, workload, and free time
3. **Calendar Integration**: Syncs with Google Calendar and Outlook for a unified view
4. **Comprehensive Prep Materials**: Flashcards, quiz questions, interview prep, company research
5. **Workload Analysis**: Helps you understand if your schedule is realistic
6. **Modern UI**: Clean, intuitive interface with calendar and task views
7. **Flexible**: Works with or without external API integrations

## Troubleshooting

### Backend Issues

**Database errors:**
```bash
# Reset database
rm ai_calendar.db
python seed_data.py
```

**Import errors:**
```bash
# Ensure you're in virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Frontend Issues

**Build errors:**
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

**API connection issues:**
- Ensure backend is running on port 8000
- Check CORS settings in `backend/app/config.py`

## Contributing

This is a demonstration project. Feel free to fork and customize for your needs.

## License

ISC

## Support

For issues and questions, please refer to the API documentation at `http://localhost:8000/docs` when the backend is running.

---

**Built with ❤️ using FastAPI, React, and AI**
