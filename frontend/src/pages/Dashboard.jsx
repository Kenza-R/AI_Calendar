import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { tasksAPI } from '../services/api';
import CalendarView from '../components/CalendarView';
import TasksList from '../components/TasksList';
import UploadDocument from '../components/UploadDocument';
import ScheduleOverview from '../components/ScheduleOverview';
import './Dashboard.css';

const Dashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('calendar');
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (!user) {
      navigate('/login');
    } else {
      // Sync task events on mount to ensure all tasks have calendar events
      syncTaskEvents();
    }
  }, [user, navigate]);

  const syncTaskEvents = async () => {
    try {
      await tasksAPI.syncEvents();
    } catch (error) {
      console.error('Error syncing task events:', error);
      // Silent fail - don't interrupt user experience
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleUploadSuccess = () => {
    // Refresh data by incrementing key
    setRefreshKey(prev => prev + 1);
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
        {activeTab === 'calendar' && <CalendarView key={`calendar-${refreshKey}`} />}
        {activeTab === 'tasks' && <TasksList key={`tasks-${refreshKey}`} />}
        {activeTab === 'upload' && <UploadDocument onUploadSuccess={handleUploadSuccess} />}
        {activeTab === 'overview' && <ScheduleOverview key={`overview-${refreshKey}`} />}
      </main>
    </div>
  );
};

export default Dashboard;
