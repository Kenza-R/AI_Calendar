import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import CalendarView from '../components/CalendarView';
import TasksList from '../components/TasksList';
import UploadDocument from '../components/UploadDocument';
import ScheduleOverview from '../components/ScheduleOverview';
import './Dashboard.css';

const Dashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('calendar');

  useEffect(() => {
    if (!user) {
      navigate('/login');
    }
  }, [user, navigate]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (!user) {
    return <div>Loading...</div>;
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="dashboard-logo">SCHEDULY</h1>
          <div className="header-user">
            <span>Welcome, {user.full_name || user.email}</span>
            <button onClick={handleLogout} className="btn-logout">
              Logout
            </button>
          </div>
        </div>
      </header>

      <nav className="dashboard-nav">
        <button
          className={activeTab === 'calendar' ? 'active' : ''}
          onClick={() => setActiveTab('calendar')}
        >
          📅 Calendar
        </button>
        <button
          className={activeTab === 'tasks' ? 'active' : ''}
          onClick={() => setActiveTab('tasks')}
        >
          ✅ Tasks
        </button>
        <button
          className={activeTab === 'upload' ? 'active' : ''}
          onClick={() => setActiveTab('upload')}
        >
          📄 Upload Syllabus
        </button>
        <button
          className={activeTab === 'overview' ? 'active' : ''}
          onClick={() => setActiveTab('overview')}
        >
          📊 Overview
        </button>
      </nav>

      <main className="dashboard-content">
        {activeTab === 'calendar' && <CalendarView />}
        {activeTab === 'tasks' && <TasksList />}
        {activeTab === 'upload' && <UploadDocument />}
        {activeTab === 'overview' && <ScheduleOverview />}
      </main>
    </div>
  );
};

export default Dashboard;
