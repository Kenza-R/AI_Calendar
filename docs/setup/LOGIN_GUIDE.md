# 🔐 Login & Account Setup Guide

## Quick Access to Your Application

**Frontend:** http://localhost:5173  
**Backend API:** http://localhost:8000  
**API Docs:** http://localhost:8000/docs

---

## 🎯 Two Ways to Get Started

### Option 1: Register a New Account (Recommended)

1. Open http://localhost:5173
2. Click on **"Register"** or **"Sign Up"**
3. Fill in your details:
   - **Email:** your-email@example.com
   - **Password:** (choose a secure password)
   - **Full Name:** Your Name
4. Click **"Register"**
5. You'll be automatically logged in!

### Option 2: Use Demo Account (If Available)

The demo account exists in the database:
- **Email:** demo@example.com
- **Password:** demo123

If you see "demo account not available", it means the account might not be fully registered. Try **Option 1** instead.

---

## 🔧 Troubleshooting Login Issues

### If You Can't Login:

1. **Create a Fresh Account:**
   - Click "Register" instead of "Login"
   - Use any email (doesn't need to be real for local testing)
   - Example: test@test.com / password123

2. **Check Backend is Running:**
   - Backend should be at http://localhost:8000
   - Try opening http://localhost:8000/health - should return `{"status":"healthy"}`

3. **Clear Browser Data:**
   - Open browser DevTools (F12)
   - Go to Application > Local Storage
   - Clear localhost:5173
   - Refresh and try again

### If Registration Isn't Working:

1. **Check Backend Logs:**
   ```bash
   # Look at the terminal running the backend
   # You should see request logs
   ```

2. **Test API Directly:**
   - Open http://localhost:8000/docs
   - Try the `/auth/register` endpoint
   - Input:
     ```json
     {
       "email": "test@test.com",
       "password": "test123",
       "full_name": "Test User"
     }
     ```

---

## 🚀 After Logging In

Once you're logged in, you can:

1. **Upload Syllabi** - Navigate to "Upload Document"
   - Upload PDF, TXT, or DOCX files
   - See enhanced extraction with assessment components
   - Automatic task creation

2. **View Tasks** - See all your extracted tasks
   - Deadlines and assignments
   - Auto-generated prep sessions

3. **Calendar View** - Visualize your schedule
   - All tasks and events in calendar format

4. **Sync Calendars** - Connect external calendars
   - Google Calendar
   - Outlook

---

## 💡 Quick Test Upload

After logging in:
1. Go to **Upload Document** page
2. Upload the sample file: `/backend/uploads/30269_2223_Syllabus 12.pdf`
3. Watch the enhanced extraction in action!
4. See:
   - Assessment components extracted
   - Tasks created from deadlines
   - Class sessions detected

---

## 🆘 Still Having Issues?

Try creating a completely new user via the API:

1. Open http://localhost:8000/docs
2. Find `POST /auth/register`
3. Click "Try it out"
4. Enter:
   ```json
   {
     "email": "yourname@test.com",
     "password": "yourpassword",
     "full_name": "Your Name"
   }
   ```
5. Execute
6. Copy the `access_token` from the response
7. Go back to http://localhost:5173
8. Try logging in with your new credentials

---

## ✅ Recommended: Create Your Own Account

**Just click "Register" and create a fresh account - this is the easiest way!**

The demo account might have issues, but creating your own account will work perfectly.

---

## 📱 Contact

If you continue having issues, the registration feature should work. Just use:
- Any email format (doesn't need to be real for local dev)
- Any password (min 6 characters recommended)
- Click Register, and you're in!
