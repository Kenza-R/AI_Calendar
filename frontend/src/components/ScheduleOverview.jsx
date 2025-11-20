import React, { useState, useEffect } from 'react';
import { calendarAPI, tasksAPI, eventsAPI } from '../services/api';
import './ScheduleOverview.css';

const ScheduleOverview = () => {
  const [overview, setOverview] = useState(null);
  const [upcomingTasks, setUpcomingTasks] = useState([]);
  const [upcomingEvents, setUpcomingEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [daysAhead, setDaysAhead] = useState(7);

  useEffect(() => {
    fetchData();
  }, [daysAhead]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [overviewRes, tasksRes, eventsRes] = await Promise.all([
        calendarAPI.getScheduleOverview(daysAhead),
        tasksAPI.getAll(false),
        eventsAPI.getAll()
      ]);

      setOverview(overviewRes.data);

      // Filter upcoming tasks
      const now = new Date();
      const futureDate = new Date(now.getTime() + daysAhead * 24 * 60 * 60 * 1000);
      
      const upcoming = tasksRes.data.filter(task => {
        if (!task.deadline) return false;
        const deadline = new Date(task.deadline);
        return deadline >= now && deadline <= futureDate;
      }).sort((a, b) => new Date(a.deadline) - new Date(b.deadline));

      setUpcomingTasks(upcoming);

      // Filter upcoming events
      const upcomingEvts = eventsRes.data.filter(event => {
        const start = new Date(event.start_time);
        return start >= now && start <= futureDate;
      }).sort((a, b) => new Date(a.start_time) - new Date(b.start_time));

      setUpcomingEvents(upcomingEvts);

    } catch (error) {
      console.error('Error fetching overview:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading overview...</div>;
  }

  return (
    <div className="schedule-overview">
      <div className="overview-header">
        <h2>📊 Schedule Overview</h2>
        <div className="days-selector">
          <label>View next:</label>
          <select value={daysAhead} onChange={(e) => setDaysAhead(Number(e.target.value))}>
            <option value={7}>7 days</option>
            <option value={14}>14 days</option>
            <option value={30}>30 days</option>
          </select>
        </div>
      </div>

      {overview && (
        <div className="stats-grid">
          <div className="stat-card-overview">
            <div className="stat-icon">📋</div>
            <div className="stat-info">
              <div className="stat-value">{overview.total_tasks}</div>
              <div className="stat-label">Pending Tasks</div>
            </div>
          </div>

          <div className="stat-card-overview">
            <div className="stat-icon">⏱️</div>
            <div className="stat-info">
              <div className="stat-value">{overview.total_prep_hours_needed}h</div>
              <div className="stat-label">Prep Time Needed</div>
            </div>
          </div>

          <div className="stat-card-overview">
            <div className="stat-icon">📅</div>
            <div className="stat-info">
              <div className="stat-value">{Math.round(overview.busy_hours)}h</div>
              <div className="stat-label">Scheduled Hours</div>
            </div>
          </div>

          <div className="stat-card-overview">
            <div className="stat-icon">✨</div>
            <div className="stat-info">
              <div className="stat-value">{Math.round(overview.free_hours)}h</div>
              <div className="stat-label">Free Hours</div>
            </div>
          </div>
        </div>
      )}

      {overview && (
        <div className="feasibility-card">
          <div className="feasibility-header">
            <h3>Workload Analysis</h3>
            <span className={`feasibility-badge ${overview.is_feasible ? 'feasible' : 'overloaded'}`}>
              {overview.is_feasible ? '✅ Manageable' : '⚠️ Overloaded'}
            </span>
          </div>
          <div className="utilization-bar">
            <div 
              className="utilization-fill"
              style={{ width: `${Math.min(overview.utilization_percentage, 100)}%` }}
            />
          </div>
          <p className="utilization-text">
            {Math.round(overview.utilization_percentage)}% time utilization
          </p>
          {!overview.is_feasible && (
            <p className="warning-text">
              ⚠️ You may need to adjust deadlines or reduce commitments.
            </p>
          )}
        </div>
      )}

      <div className="overview-lists">
        <div className="list-section">
          <h3>Upcoming Tasks ({upcomingTasks.length})</h3>
          {upcomingTasks.length === 0 ? (
            <p className="empty-list">No upcoming tasks</p>
          ) : (
            <div className="items-list">
              {upcomingTasks.map(task => (
                <div key={task.id} className="list-item task-item-overview">
                  <div className="item-icon">
                    {task.task_type === 'exam_prep' ? '📚' : 
                     task.task_type === 'interview_prep' ? '💼' : '📝'}
                  </div>
                  <div className="item-content">
                    <div className="item-title">{task.title}</div>
                    <div className="item-meta">
                      📅 {new Date(task.deadline).toLocaleDateString()} • 
                      ⏱️ {task.estimated_hours}h • 
                      <span className={`priority-${task.priority}`}>{task.priority}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="list-section">
          <h3>Upcoming Events ({upcomingEvents.length})</h3>
          {upcomingEvents.length === 0 ? (
            <p className="empty-list">No upcoming events</p>
          ) : (
            <div className="items-list">
              {upcomingEvents.map(event => (
                <div key={event.id} className="list-item event-item-overview">
                  <div className="item-icon">
                    {event.event_type === 'meeting' ? '👥' :
                     event.event_type === 'interview' ? '💼' :
                     event.event_type === 'exam' ? '📝' : '📅'}
                  </div>
                  <div className="item-content">
                    <div className="item-title">{event.title}</div>
                    <div className="item-meta">
                      📅 {new Date(event.start_time).toLocaleDateString()} • 
                      🕐 {new Date(event.start_time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                      {event.location && ` • 📍 ${event.location}`}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ScheduleOverview;
