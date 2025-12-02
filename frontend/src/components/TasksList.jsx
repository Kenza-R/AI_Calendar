import React, { useState, useEffect } from 'react';
import { tasksAPI } from '../services/api';
import TaskModal from './TaskModal';
import './TasksList.css';

const TasksList = () => {
  const [tasks, setTasks] = useState([]);
  const [filter, setFilter] = useState('all');
  const [selectedTask, setSelectedTask] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTasks();
  }, [filter]);

  const fetchTasks = async () => {
    try {
      const completed = filter === 'completed' ? true : filter === 'active' ? false : null;
      const response = await tasksAPI.getAll(completed);
      setTasks(response.data);
    } catch (error) {
      console.error('Error fetching tasks:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleComplete = async (taskId, currentStatus) => {
    try {
      await tasksAPI.update(taskId, { completed: !currentStatus });
      fetchTasks();
    } catch (error) {
      console.error('Error updating task:', error);
    }
  };

  const handleDeleteTask = async (taskId, e) => {
    e.stopPropagation(); // Prevent card click
    if (window.confirm('Are you sure you want to delete this task?')) {
      try {
        await tasksAPI.delete(taskId);
        fetchTasks();
      } catch (error) {
        console.error('Error deleting task:', error);
        alert('Failed to delete task');
      }
    }
  };

  const handleEditTask = (task, e) => {
    e.stopPropagation(); // Prevent card click
    setSelectedTask(task);
    setShowModal(true);
  };

  const handleTaskClick = (task) => {
    setSelectedTask(task);
    setShowModal(true);
  };

  const handleNewTask = () => {
    setSelectedTask({ isNew: true });
    setShowModal(true);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setSelectedTask(null);
  };

  const handleSaveTask = async () => {
    await fetchTasks();
    handleCloseModal();
  };

  const getPriorityColor = (priority) => {
    const colors = {
      high: '#ef4444',
      medium: '#f59e0b',
      low: '#10b981'
    };
    return colors[priority] || colors.medium;
  };

  const getTaskTypeIcon = (type) => {
    const icons = {
      exam_prep: '📚',
      interview_prep: '💼',
      assignment: '📝',
      reading: '📖',
      default: '✏️'
    };
    return icons[type] || icons.default;
  };

  if (loading) {
    return <div className="loading">Loading tasks...</div>;
  }

  return (
    <div className="tasks-list">
      <div className="tasks-header">
        <h2>✅ Your Tasks</h2>
        <button onClick={handleNewTask} className="btn-new-task">
          + New Task
        </button>
      </div>

      <div className="tasks-filter">
        <button
          className={filter === 'all' ? 'active' : ''}
          onClick={() => setFilter('all')}
        >
          All ({tasks.length})
        </button>
        <button
          className={filter === 'active' ? 'active' : ''}
          onClick={() => setFilter('active')}
        >
          Active
        </button>
        <button
          className={filter === 'completed' ? 'active' : ''}
          onClick={() => setFilter('completed')}
        >
          Completed
        </button>
      </div>

      <div className="tasks-container">
        {tasks.length === 0 ? (
          <div className="empty-state">
            <p>No tasks found. Create your first task!</p>
          </div>
        ) : (
          <div className="tasks-grid">
            {tasks.map(task => (
              <div
                key={task.id}
                className={`task-card ${task.completed ? 'completed' : ''}`}
              >
                <div className="task-header-card">
                  <input
                    type="checkbox"
                    checked={task.completed}
                    onChange={() => handleToggleComplete(task.id, task.completed)}
                    className="task-checkbox"
                  />
                  <div className="task-title-section">
                    <h3 onClick={() => handleTaskClick(task)}>
                      {getTaskTypeIcon(task.task_type)} {task.title}
                    </h3>
                    <span
                      className="priority-badge"
                      style={{ backgroundColor: getPriorityColor(task.priority) }}
                    >
                      {task.priority}
                    </span>
                  </div>
                  <div className="task-actions">
                    <button
                      onClick={(e) => handleEditTask(task, e)}
                      className="btn-edit-task"
                      title="Edit task"
                    >
                      ✏️
                    </button>
                    <button
                      onClick={(e) => handleDeleteTask(task.id, e)}
                      className="btn-delete-task"
                      title="Delete task"
                    >
                      🗑️
                    </button>
                  </div>
                </div>

                {task.description && (
                  <p className="task-description">{task.description}</p>
                )}

                <div className="task-meta">
                  {task.deadline && (
                    <span className="task-deadline">
                      ⏰ {new Date(task.deadline).toLocaleDateString()}
                    </span>
                  )}
                  {task.estimated_hours && (
                    <span className="task-hours">
                      ⏱️ {task.estimated_hours}h
                    </span>
                  )}
                </div>

                {task.prep_material && (
                  <div className="task-prep-indicator">
                    ✨ Prep material available
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {showModal && (
        <TaskModal
          task={selectedTask}
          onClose={handleCloseModal}
          onSave={handleSaveTask}
        />
      )}
    </div>
  );
};

export default TasksList;
