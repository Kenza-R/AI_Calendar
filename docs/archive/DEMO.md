# Demo Walkthrough

This guide walks you through the key features of the AI Productivity Calendar.

## 1. Login & Dashboard

1. Open http://localhost:5173
2. Click "Try Demo Account" or login with:
   - Email: demo@example.com
   - Password: demo123
3. You'll see the main dashboard with 4 tabs

## 2. Calendar View

**What you see:**
- Interactive calendar with weekly/monthly views
- Color-coded events:
  - 🔵 Blue = Meetings
  - 🟠 Orange = Interviews
  - 🔴 Red = Exams
  - 🟣 Purple = Prep Sessions

**Try this:**
- Click on any event to view/edit details
- Click on empty time slot to create new event
- Drag events to reschedule them

**Sample Events Included:**
- CS 101 Lecture (tomorrow)
- Job Interview at TechCorp (3 days)
- Midterm Exam - Data Structures (7 days)

## 3. Tasks View

**What you see:**
- List of all tasks with checkboxes
- Filter by: All, Active, Completed
- Color-coded priority badges
- Estimated time and deadlines

**Try this:**
1. Click "New Task" to create a task
2. Choose task type: "Exam Prep" or "Interview Prep"
3. Set deadline and estimated hours
4. Save - AI will generate prep material!

**Sample Tasks Included:**
- Complete Python Assignment (5 days)
- Prepare for TechCorp Interview (3 days) - with AI prep material
- Study for Data Structures Midterm (7 days) - with AI prep material
- Read Chapter 6 - Algorithms (4 days)

**AI Prep Material:**
- Click any task with ✨ indicator
- Click "Show Prep Material" button
- See:
  - **For Exams:** Flashcards, quiz questions, key concepts, study tips
  - **For Interviews:** Company research, common questions, topics, tips

## 4. Upload Syllabus

**What you see:**
- File upload area
- Processing results
- Automatically created tasks

**Try this:**
1. Create a test document with content like:
   ```
   CS 101 Syllabus
   
   Assignment 1: Due March 15, 2024
   Midterm Exam: April 20, 2024
   Final Project: May 5, 2024
   ```
2. Save as PDF or TXT
3. Upload in the "Upload Syllabus" tab
4. AI extracts deadlines and creates tasks automatically!

**What happens:**
- Document is parsed
- AI identifies deadlines
- Tasks are created with:
  - Title (e.g., "Assignment 1")
  - Deadline date
  - Task type
  - Estimated hours

## 5. Schedule Overview

**What you see:**
- Schedule statistics for next 7/14/30 days
- Pending tasks count
- Total prep hours needed
- Scheduled hours vs free hours
- Workload analysis (Manageable ✅ or Overloaded ⚠️)
- Lists of upcoming tasks and events

**Try this:**
1. Change time range: 7 days, 14 days, or 30 days
2. Check if workload is feasible
3. Review upcoming tasks by priority
4. See next events chronologically

## 6. Auto-Schedule Prep Sessions

**Try this:**
1. Go to Tasks view
2. Click any task with a deadline
3. Click "Schedule Prep" button
4. System analyzes:
   - Days until deadline
   - Estimated hours needed
   - Your existing events
   - Available free time
5. Suggests optimal prep session times
6. Creates sessions automatically!

**Smart Features:**
- Avoids conflicts with existing events
- Distributes prep time optimally
- More sessions closer to deadline
- 1-3 hour sessions for better focus

## 7. Task Management Features

**Mark Complete:**
- Click checkbox on any task
- Completed tasks get strike-through
- Filter to see only active or completed

**Edit Tasks:**
- Click on task title
- Update details, deadline, priority
- For exam/interview prep: regenerate AI material

**Priority Levels:**
- 🔴 High (red badge)
- 🟠 Medium (orange badge)
- 🟢 Low (green badge)

## 8. API Features (Advanced)

Visit http://localhost:8000/docs to see:
- All available API endpoints
- Interactive API documentation
- Test endpoints directly
- See request/response formats

**Key API Endpoints:**
- POST /auth/register - Create new user
- POST /auth/login - Get authentication token
- GET /tasks/ - List all tasks
- POST /tasks/ - Create task with AI prep
- POST /documents/upload-syllabus - Upload & parse document
- GET /calendar/schedule-overview - Get schedule statistics

## Sample Data Included

The demo account comes with:
- **3 Events:** Lecture, Interview, Exam
- **4 Tasks:** Including exam and interview prep with AI-generated material
- **AI Prep Material:** Pre-generated flashcards, questions, and tips

## Tips for Best Experience

1. **Create Realistic Tasks:** Add deadlines and estimated hours
2. **Use AI Features:** Try exam_prep or interview_prep task types
3. **Upload Documents:** Test with real syllabi or schedules
4. **Check Overview:** Monitor workload feasibility
5. **Auto-Schedule:** Let AI find optimal prep times

## Troubleshooting

**Backend not responding:**
- Check http://localhost:8000 is running
- See QUICKSTART.md for setup instructions

**Frontend not loading:**
- Check http://localhost:5173 is accessible
- Run `npm run dev` in frontend directory

**AI features not working:**
- Add OPENAI_API_KEY to backend/.env
- Restart backend server
- Without API key, you'll see sample prep material

## Next Steps

1. **Customize:** Create your own tasks and events
2. **Integrate:** Add Google Calendar or Outlook (see README.md)
3. **Explore:** Try all features with your own data
4. **Extend:** Check API docs for integration possibilities

---

Happy scheduling! 📅✨
