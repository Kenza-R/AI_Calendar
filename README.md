<div align="center">

# 📅 Scheduly

### AI-Powered Academic Calendar & Task Manager

[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-20232A?style=flat&logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat&logo=openai&logoColor=white)](https://openai.com/)
[![License: ISC](https://img.shields.io/badge/License-ISC-blue.svg)](https://opensource.org/licenses/ISC)

**Never miss a deadline again.** Upload your syllabus and let AI extract deadlines, create tasks, generate study materials, and auto-schedule prep sessions—all in one place.

[Features](#-features) • [Demo](#-demo) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Contributing](#-contributing)

<img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python 3.10+"/>
<img src="https://img.shields.io/badge/node-16+-green.svg" alt="Node 16+"/>

</div>

---

## 🌟 Overview

Scheduly is an intelligent productivity calendar designed for students and professionals who want to stay organized without the manual effort. Built with FastAPI and React, it leverages AI to automate deadline management and study planning.

### Why Scheduly?

- 🎓 **For Students**: Upload course syllabi and automatically extract all assignments, exams, and deadlines
- 💼 **For Job Seekers**: Track interviews and generate personalized prep materials
- 🚀 **For Everyone**: Smart scheduling that actually understands your workload and availability

### Key Highlights

| Feature | Description |
|---------|-------------|
| 🤖 **AI-Powered Extraction** | Advanced 4-agent CrewAI pipeline parses even poorly-formatted syllabi |
| 📚 **Smart Study Materials** | Auto-generates flashcards, quiz questions, and interview prep |
| 🗓️ **Intelligent Scheduling** | Automatically schedules prep sessions while avoiding conflicts |
| 🔄 **Calendar Integration** | Two-way sync with Google Calendar and Outlook |
| 📊 **Workload Analysis** | Real-time feasibility checking and time management insights |
| 🔐 **Privacy-First** | Your data stays yours—secure JWT authentication and user isolation |

---

## 🎯 Features

### 📄 Smart Syllabus Processing
- **Upload any format**: PDF, TXT, or DOCX syllabi
- **Advanced AI extraction**: Uses a 4-agent CrewAI pipeline to intelligently parse course schedules
- **Automatic task creation**: Extracts assignments, exams, quizzes, projects, and deadlines
- **Workload estimation**: AI estimates study hours needed for each task
- **Assessment breakdown**: Analyzes grading components and course structure
- **Handles messy formats**: Works with poorly formatted PDFs and broken tables

### ✅ Intelligent Task Management
- **Comprehensive task tracking**: Assignments, exams, interviews, readings, projects
- **Priority levels**: High, medium, low with visual indicators
- **Completion tracking**: Check off tasks and track progress
- **Time estimation**: AI suggests prep time needed for each task
- **Filter & sort**: View all, active only, or completed tasks
- **Quick actions**: Edit, delete, or mark complete with one click

### 🗓️ Interactive Calendar
- **Visual calendar views**: Day, week, and month views
- **Drag-and-drop**: Move events by dragging them to new times
- **Color-coded events**: Distinguish at a glance
  - 🔵 Meetings & Classes
  - 🟠 Interviews
  - 🔴 Exams & Deadlines
  - 🟣 Prep Sessions
- **Quick event creation**: Click any time slot to add events
- **Automatic event linking**: Tasks automatically create calendar events

### 🤖 AI-Generated Study Materials
For **Exam Prep** tasks, Scheduly generates:
- **Flashcards**: Question/answer pairs for memorization (10 cards)
- **Quiz Questions**: Multiple choice practice questions (5 questions with answers)
- **Key Concepts**: Important topics to review
- **Study Tips**: Personalized strategies for success
- **Regenerate anytime**: Get fresh materials with one click

For **Interview Prep** tasks, Scheduly generates:
- **Company Research**: Key facts and information
- **Common Questions**: 5-7 typical interview questions
- **Topics to Review**: Technical and soft skills to prepare
- **Success Tips**: Strategies using the STAR method

### 📊 Smart Schedule Optimization
- **Auto-schedule prep sessions**: Automatically creates study blocks before deadlines
- **Conflict detection**: Avoids scheduling over existing events
- **Optimal time distribution**: Spreads prep time intelligently
- **Urgency awareness**: More sessions closer to deadlines
- **Workload analysis**: 
  - See total prep hours needed
  - Calculate free vs. busy time
  - Get feasibility warnings if overloaded
  - Track time utilization percentage
- **Schedule overview**: View next 7, 14, or 30 days at a glance

### 🔄 Calendar Integrations
- **Google Calendar sync**: Import events from Google Calendar
- **Outlook Calendar sync**: Import events from Microsoft Outlook
- **Gmail scanning**: Extract deadlines from emails automatically
- **Two-way sync**: Changes reflect in both systems

### 🔐 Secure & Private
- **JWT authentication**: Secure, stateless user authentication
- **Password encryption**: Bcrypt hashing for password security
- **User data isolation**: Your data stays completely private
- **OAuth support**: Secure integration with Google and Microsoft

---

## 🛠️ Tech Stack

<table>
<tr>
<td>

**Backend**
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL toolkit and ORM
- [SQLite](https://www.sqlite.org/) - Embedded database (PostgreSQL ready)
- [OpenAI GPT-4](https://openai.com/) - AI extraction and generation
- [CrewAI](https://www.crewai.com/) - Multi-agent AI orchestration
- [Google APIs](https://developers.google.com/) - Calendar & Gmail integration
- [Microsoft Graph](https://developer.microsoft.com/graph) - Outlook integration

</td>
<td>

**Frontend**
- [React 18](https://react.dev/) - UI library
- [Vite](https://vitejs.dev/) - Build tool
- [React Router](https://reactrouter.com/) - Client-side routing
- [FullCalendar](https://fullcalendar.io/) - Calendar component
- [Axios](https://axios-http.com/) - HTTP client

</td>
</tr>
</table>

---

## 🎬 Demo

### Try it Out

Use the demo account to explore all features:
- **Email**: `demo@example.com`
- **Password**: `demo123`

### Screenshots

<details>
<summary>📸 Click to view screenshots</summary>

*Coming soon: Calendar view, Task management, Upload interface, AI-generated study materials*

</details>

---

## 🚀 Quick Start

> **Prerequisites**: Python 3.10+, Node.js 16+, and an [OpenAI API key](https://platform.openai.com/api-keys)

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/Kenza-R/AI_Calendar.git
cd AI_Calendar
```

### 2️⃣ Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
```

**Edit `.env` and add your OpenAI API key:**
```env
OPENAI_API_KEY=your-openai-api-key-here
SECRET_KEY=your-random-secret-key
```

```bash
# Initialize database with demo data
python scripts/seed_data.py

# Start the backend server
python main.py
```

✅ **Backend running at** `http://localhost:8000`  
📚 **API Docs at** `http://localhost:8000/docs`

### 3️⃣ Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

✅ **Frontend running at** `http://localhost:5173`

### 4️⃣ Start Using Scheduly! 🎉

Open `http://localhost:5173` and login with:
- **Email**: `demo@example.com`
- **Password**: `demo123`

---

## 📖 Usage Guide

<details open>
<summary><strong>📄 Upload a Syllabus</strong></summary>

<br>

1. Navigate to **📄 Upload Syllabus** tab
2. Select your syllabus file (PDF, TXT, or DOCX)
3. Click **Upload & Extract**
4. AI automatically extracts all deadlines and creates tasks
5. Review extracted tasks in the **✅ Tasks** tab

</details>

<details>
<summary><strong>✅ Manage Tasks</strong></summary>

<br>

1. Navigate to **✅ Tasks** tab
2. Click **+ New Task** to create a task manually
3. Set priority level and task type
4. Add deadline and estimated study hours
5. Click any task to view/edit details
6. Check off tasks when complete

</details>

<details>
<summary><strong>🤖 View AI Study Materials</strong></summary>

<br>

1. Open an **exam prep** or **interview prep** task
2. Click **Show Prep Material** to access:
   - 📇 Flashcards for memorization
   - ❓ Quiz questions with answers
   - 🎯 Key concepts to review
   - 💡 Personalized study tips
3. Click **Regenerate** anytime for fresh materials

</details>

<details>
<summary><strong>📅 Auto-Schedule Study Sessions</strong></summary>

<br>

1. Open any task with a deadline
2. Click **Schedule Prep Sessions**
3. AI creates optimal study blocks that:
   - ✅ Avoid conflicts with existing events
   - ⏰ Distribute time intelligently
   - 🔥 Prioritize urgent deadlines
4. View scheduled prep sessions in your calendar

</details>

<details>
<summary><strong>🗓️ Use the Calendar</strong></summary>

<br>

1. Navigate to **📅 Calendar** tab
2. Switch between Day, Week, or Month view
3. Drag and drop events to reschedule
4. Click events to view/edit details
5. Events are color-coded by type for quick scanning

</details>

<details>
<summary><strong>📊 Check Schedule Overview</strong></summary>

<br>

1. Navigate to **📊 Overview** tab
2. See all upcoming deadlines at a glance
3. Review workload analysis:
   - 📚 Total prep hours needed
   - ⏳ Free time available
   - ⚠️ Feasibility warnings
   - 📈 Time utilization percentage

</details>

---

## ⚙️ Configuration

### Required: OpenAI API Key
Scheduly needs an OpenAI API key for AI features:
1. Sign up at [platform.openai.com](https://platform.openai.com/)
2. Create an API key
3. Add to `.env`: `OPENAI_API_KEY=sk-...`

### Optional: Google Calendar/Gmail
For calendar sync and email scanning:
1. Create project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Google Calendar API and Gmail API
3. Create OAuth 2.0 credentials
4. Add to `.env`:
```env
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
```

### Optional: Microsoft Outlook
For Outlook calendar sync:
1. Register app in [Azure Portal](https://portal.azure.com/)
2. Configure Microsoft Graph API permissions
3. Add to `.env`:
```env
MICROSOFT_CLIENT_ID=your-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret
```

---

## 📂 Project Structure

```
AI_Calendar/
├── backend/
│   ├── app/
│   │   ├── models/           # SQLAlchemy database models
│   │   ├── routers/          # FastAPI route handlers
│   │   ├── services/         # Business logic layer
│   │   ├── schemas/          # Pydantic validation schemas
│   │   └── utils/            # Helper functions & AI services
│   ├── scripts/              # Database seeding & utilities
│   ├── main.py               # Application entry point
│   └── requirements.txt      # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── components/       # Reusable React components
│   │   ├── pages/            # Page-level components
│   │   ├── services/         # API client services
│   │   └── context/          # React context providers
│   ├── package.json          # Node dependencies
│   └── vite.config.js        # Vite build configuration
│
└── docs/                     # Extended documentation
```

---

## 💼 Use Cases

| User Type | Benefits |
|-----------|----------|
| 🎓 **Students** | Upload syllabi → Auto-extract deadlines → Generate study materials → Never miss assignments |
| 💼 **Job Seekers** | Track interviews → Prep company research → Practice common questions → Schedule prep time |
| 👔 **Professionals** | Manage deadlines → Track meetings → Balance workload → Integrate existing calendars |

---

## 📚 Documentation

- **[API Documentation](http://localhost:8000/docs)** - Interactive Swagger UI (when running)
- **[Setup Guide](docs/setup/SETUP_GUIDE.md)** - Detailed installation instructions
- **[Features Overview](docs/features/FEATURES.md)** - Complete feature documentation
- **[Deployment Guide](docs/deployment/RENDER_DEPLOYMENT.md)** - Production deployment

---

## 🐛 Troubleshooting

### Backend Issues

**"No module named 'crewai'"**
```bash
# Make sure you're using Python 3.10+
python --version
pip install crewai crewai-tools
```

**Database errors:**
```bash
# Reset database
rm backend/ai_calendar.db
python backend/scripts/seed_data.py
```

**OpenAI API errors:**
- Check your API key is correct in `.env`
- Verify you have API credits available
- App works with limited features without API key

### Frontend Issues

**Port already in use:**
```bash
# Kill process on port 5173
lsof -ti:5173 | xargs kill -9
npm run dev
```

**Module not found:**
```bash
# Clean install
rm -rf node_modules package-lock.json
npm install
```

### Common Problems

**"Tasks not showing prep material"**
- Ensure task type is "exam_prep" or "interview_prep"
- Check OpenAI API key is configured
- Try clicking "Regenerate" button

**"Upload not working"**
- Check file format (PDF, TXT, or DOCX only)
- Ensure file size is reasonable (<10MB)
- Check backend console for detailed errors

**"Calendar events not syncing"**
- OAuth credentials must be configured
- Check token expiration in database
- Re-authenticate if needed

---

## 🔌 API Reference

<details>
<summary><strong>View All Endpoints</strong></summary>

<br>

Full interactive documentation available at `http://localhost:8000/docs`

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/auth/register` | Register new user |
| `POST` | `/auth/login` | Login and receive JWT token |
| `GET` | `/auth/me` | Get current user info |

### Tasks
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/tasks/` | List all tasks with optional filters |
| `POST` | `/tasks/` | Create task (auto-generates prep material) |
| `GET` | `/tasks/{id}` | Get task details |
| `PUT` | `/tasks/{id}` | Update task |
| `DELETE` | `/tasks/{id}` | Delete task |
| `POST` | `/tasks/{id}/schedule` | Auto-schedule prep sessions |
| `POST` | `/tasks/{id}/regenerate-prep` | Regenerate prep materials |

### Events
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/events/` | List all calendar events |
| `POST` | `/events/` | Create new event |
| `PUT` | `/events/{id}` | Update event |
| `DELETE` | `/events/{id}` | Delete event |

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/documents/upload-syllabus-crewai` | Upload syllabus (4-agent AI) |
| `POST` | `/documents/extract-assessments` | Extract grading breakdown |
| `GET` | `/documents/` | List uploaded documents |
| `GET` | `/documents/{id}` | Get document details |

### Calendar Sync
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/calendar/sync/google` | Sync Google Calendar |
| `POST` | `/calendar/sync/gmail` | Scan Gmail for deadlines |
| `POST` | `/calendar/sync/outlook` | Sync Outlook Calendar |
| `GET` | `/calendar/schedule-overview` | Get workload analysis |

</details>

---

## 🧠 How It Works

<details>
<summary><strong>CrewAI 4-Agent Pipeline</strong></summary>

<br>

Scheduly uses a sophisticated multi-agent AI system for parsing syllabi:

```
Syllabus Upload → [Segmentation Agent] → [Parsing Agent] → [Workload Agent] → [Deadline Agent] → Tasks Created
```

1. **Segmentation Agent** - Breaks syllabus into structured blocks
2. **Parsing Agent** - Extracts dates, assignments, and requirements  
3. **Workload Agent** - Estimates study hours needed
4. **Deadline Agent** - Creates complete task objects with metadata

This pipeline handles poorly formatted PDFs, broken tables, and complex schedules that traditional parsers fail on.

</details>

<details>
<summary><strong>Intelligent Scheduling Algorithm</strong></summary>

<br>

When you click "Schedule Prep Sessions", Scheduly:

1. ✅ **Analyzes your calendar** for existing events and commitments
2. 🎯 **Calculates optimal distribution** based on deadline urgency
3. ⏰ **Creates time blocks** (1-3 hours for maximum productivity)
4. 🚫 **Avoids conflicts** by checking all existing events
5. 🔄 **Reschedules automatically** if conflicts are found
6. 📊 **Validates feasibility** and warns if you're overbooked

</details>

<details>
<summary><strong>Workload Analysis Engine</strong></summary>

<br>

The Schedule Overview provides real-time insights:

| Metric | Calculation |
|--------|-------------|
| **Prep Hours Needed** | Sum of estimated hours for all incomplete tasks |
| **Free Time** | Total available hours - scheduled events |
| **Utilization %** | (Busy hours / Total hours) × 100 |
| **Feasibility** | ✅ Green if free time > prep needed, ⚠️ Yellow/Red otherwise |

</details>

---

## 🚢 Deployment

<details>
<summary><strong>Deploy to Render.com (Recommended)</strong></summary>

<br>

Scheduly includes `render.yaml` for easy deployment:

1. Fork/push repository to GitHub
2. Create a [Render account](https://render.com)
3. Connect your repository
4. Add environment variables:
   - `OPENAI_API_KEY`
   - `SECRET_KEY`
5. Click "Deploy"! 🚀

[View deployment guide →](docs/deployment/RENDER_DEPLOYMENT.md)

</details>

<details>
<summary><strong>Deploy with Docker</strong></summary>

<br>

```bash
# Build the image
docker build -t scheduly .

# Run the container
docker run -p 8000:8000 -p 5173:5173 \
  -e OPENAI_API_KEY=your-key \
  -e SECRET_KEY=your-secret \
  scheduly
```

</details>

<details>
<summary><strong>Manual Deployment</strong></summary>

<br>

**Backend:**
```bash
cd backend
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

**Frontend:**
```bash
cd frontend
npm run build
# Serve dist/ folder with nginx, Apache, or CDN
```

</details>

---

## 🤝 Contributing

We welcome contributions from the community! Here's how you can help:

### Ways to Contribute

- 🐛 **Report Bugs**: Open an issue with reproduction steps
- 💡 **Suggest Features**: Share your ideas for improvements
- 📝 **Improve Documentation**: Fix typos, add examples, clarify instructions
- 🔧 **Submit PRs**: Fix bugs or implement new features

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Write/update tests if applicable
5. Commit with clear messages (`git commit -m 'Add amazing feature'`)
6. Push to your branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Style

- **Backend**: Follow PEP 8 guidelines
- **Frontend**: Use ESLint configuration provided
- **Commits**: Use clear, descriptive commit messages

<details>
<summary><strong>Setting Up Development Environment</strong></summary>

<br>

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pytest black flake8  # dev dependencies

# Frontend
cd frontend
npm install
npm run dev

# Run tests
cd backend && pytest
cd frontend && npm test
```

</details>

---

## 💡 Tips & Best Practices

<details>
<summary><strong>Getting the Most Out of Scheduly</strong></summary>

<br>

### For Students
- ✅ Upload syllabi at the start of each semester
- ✅ Review AI-extracted dates for accuracy
- ✅ Set realistic time estimates for better scheduling
- ✅ Use high/medium/low priorities effectively
- ✅ Check Schedule Overview weekly for workload insights

### For Job Seekers
- 💼 Create interview prep tasks immediately after scheduling
- 💼 Use AI-generated company research as a starting point
- 💼 Schedule multiple prep sessions spread across days
- 💼 Regenerate materials for fresh practice questions

### Calendar Tips
- 🗓️ **Arrow Keys**: Navigate between dates
- 🗓️ **Drag & Drop**: Quickly reschedule events
- 🗓️ **Double Click**: Create events fast
- 🗓️ **ESC**: Close modals

</details>

---

## 📄 License

This project is licensed under the ISC License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with incredible open-source tools:

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://react.dev/) - JavaScript UI library  
- [OpenAI](https://openai.com/) - GPT-4 language models
- [CrewAI](https://www.crewai.com/) - Multi-agent AI orchestration
- [FullCalendar](https://fullcalendar.io/) - Feature-rich calendar component

---

## 📞 Support & Community

- 📚 **[Documentation](docs/)** - Comprehensive guides and tutorials
- 🐛 **[Issue Tracker](https://github.com/Kenza-R/AI_Calendar/issues)** - Report bugs or request features
- 💬 **[Discussions](https://github.com/Kenza-R/AI_Calendar/discussions)** - Ask questions and share ideas

---

## 🗺️ Roadmap

- [ ] Mobile app (iOS & Android)
- [ ] Collaborative features (shared calendars)
- [ ] More calendar integrations (iCal, Apple Calendar)
- [ ] Voice input for task creation
- [ ] Browser extension for quick capture
- [ ] Advanced analytics dashboard
- [ ] Custom AI model fine-tuning
- [ ] Recurring tasks and events

Vote on features or suggest new ones in [Discussions](https://github.com/Kenza-R/AI_Calendar/discussions)!

---

<div align="center">

### ⭐ Star us on GitHub — it motivates us a lot!

Made with ❤️ for students and professionals who want to stay organized and prepared.

[Report Bug](https://github.com/Kenza-R/AI_Calendar/issues) · [Request Feature](https://github.com/Kenza-R/AI_Calendar/issues) · [Documentation](docs/)

</div>
