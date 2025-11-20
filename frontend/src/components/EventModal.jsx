import React, { useState, useEffect } from 'react';
import { eventsAPI } from '../services/api';
import './EventModal.css';

const EventModal = ({ event, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    start_time: '',
    end_time: '',
    location: '',
    event_type: 'meeting'
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (event && !event.isNew) {
      setFormData({
        title: event.title || '',
        description: event.description || '',
        start_time: event.start_time?.slice(0, 16) || '',
        end_time: event.end_time?.slice(0, 16) || '',
        location: event.location || '',
        event_type: event.event_type || 'meeting'
      });
    } else if (event?.isNew) {
      setFormData(prev => ({
        ...prev,
        start_time: event.start_time?.slice(0, 16) || '',
        end_time: event.end_time?.slice(0, 16) || ''
      }));
    }
  }, [event]);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const eventData = {
        ...formData,
        start_time: new Date(formData.start_time).toISOString(),
        end_time: new Date(formData.end_time).toISOString()
      };

      if (event?.isNew) {
        await eventsAPI.create(eventData);
      } else {
        await eventsAPI.update(event.id, eventData);
      }

      onSave();
    } catch (error) {
      console.error('Error saving event:', error);
      alert('Failed to save event. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this event?')) {
      return;
    }

    setLoading(true);
    try {
      await eventsAPI.delete(event.id);
      onSave();
    } catch (error) {
      console.error('Error deleting event:', error);
      alert('Failed to delete event. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{event?.isNew ? 'Create Event' : 'Edit Event'}</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Title *</label>
            <input
              type="text"
              name="title"
              value={formData.title}
              onChange={handleChange}
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label>Event Type</label>
            <select
              name="event_type"
              value={formData.event_type}
              onChange={handleChange}
              disabled={loading}
            >
              <option value="meeting">Meeting</option>
              <option value="interview">Interview</option>
              <option value="exam">Exam</option>
              <option value="deadline">Deadline</option>
              <option value="prep_session">Prep Session</option>
            </select>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Start Time *</label>
              <input
                type="datetime-local"
                name="start_time"
                value={formData.start_time}
                onChange={handleChange}
                required
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label>End Time *</label>
              <input
                type="datetime-local"
                name="end_time"
                value={formData.end_time}
                onChange={handleChange}
                required
                disabled={loading}
              />
            </div>
          </div>

          <div className="form-group">
            <label>Location</label>
            <input
              type="text"
              name="location"
              value={formData.location}
              onChange={handleChange}
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label>Description</label>
            <textarea
              name="description"
              value={formData.description}
              onChange={handleChange}
              rows={4}
              disabled={loading}
            />
          </div>

          <div className="modal-actions">
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Saving...' : 'Save'}
            </button>
            {!event?.isNew && (
              <button
                type="button"
                className="btn-danger"
                onClick={handleDelete}
                disabled={loading}
              >
                Delete
              </button>
            )}
            <button
              type="button"
              className="btn-secondary"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default EventModal;
