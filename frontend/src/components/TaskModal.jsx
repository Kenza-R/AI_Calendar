import React, { useState, useEffect } from 'react';
import { tasksAPI } from '../services/api';
import './TaskModal.css';

const TaskModal = ({ task, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    deadline: '',
    priority: 'medium',
    task_type: 'assignment',
    estimated_hours: 5,
    is_optional: false,
    conditions: ''
  });
  const [loading, setLoading] = useState(false);
  const [prepMaterial, setPrepMaterial] = useState(null);
  const [showPrep, setShowPrep] = useState(false);

  useEffect(() => {
    if (task && !task.isNew) {
      setFormData({
        title: task.title || '',
        description: task.description || '',
        deadline: task.deadline?.slice(0, 16) || '',
        priority: task.priority || 'medium',
        task_type: task.task_type || 'assignment',
        // Phase 5 Task 5.2: Use nullish coalescing to preserve 0-hour tasks
        estimated_hours: task.estimated_hours ?? 5,  // Only default if null/undefined, not if 0
        is_optional: task.is_optional || false,
        conditions: task.conditions || ''
      });
      
      if (task.prep_material) {
        try {
          setPrepMaterial(JSON.parse(task.prep_material));
        } catch (e) {
          console.error('Error parsing prep material:', e);
        }
      }
    }
  }, [task]);

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
      const taskData = {
        ...formData,
        deadline: formData.deadline ? new Date(formData.deadline).toISOString() : null,
        estimated_hours: parseInt(formData.estimated_hours)
      };

      if (task?.isNew) {
        await tasksAPI.create(taskData, true);
      } else {
        await tasksAPI.update(task.id, taskData);
      }

      onSave();
    } catch (error) {
      console.error('Error saving task:', error);
      alert('Failed to save task. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this task?')) {
      return;
    }

    setLoading(true);
    try {
      await tasksAPI.delete(task.id);
      onSave();
    } catch (error) {
      console.error('Error deleting task:', error);
      alert('Failed to delete task. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSchedulePrep = async () => {
    setLoading(true);
    try {
      const response = await tasksAPI.schedulePrepSessions(task.id);
      alert(`${response.data.message}\n\nSuggested ${response.data.suggested_sessions.length} prep sessions.`);
    } catch (error) {
      console.error('Error scheduling prep sessions:', error);
      alert('Failed to schedule prep sessions.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegeneratePrep = async () => {
    setLoading(true);
    try {
      const response = await tasksAPI.regeneratePrep(task.id);
      setPrepMaterial(JSON.parse(response.data.prep_material));
      setShowPrep(true);
      alert('Prep material regenerated successfully!');
    } catch (error) {
      console.error('Error regenerating prep:', error);
      alert('Failed to regenerate prep material.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content task-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{task?.isNew ? 'Create Task' : 'Edit Task'}</h2>
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

          <div className="form-row">
            <div className="form-group">
              <label>Task Type</label>
              <select
                name="task_type"
                value={formData.task_type}
                onChange={handleChange}
                disabled={loading}
              >
                <option value="assignment">Assignment</option>
                <option value="exam_prep">Exam Prep</option>
                <option value="interview_prep">Interview Prep</option>
                <option value="reading">Reading</option>
              </select>
            </div>

            <div className="form-group">
              <label>Priority</label>
              <select
                name="priority"
                value={formData.priority}
                onChange={handleChange}
                disabled={loading}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Deadline</label>
              <input
                type="datetime-local"
                name="deadline"
                value={formData.deadline}
                onChange={handleChange}
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label>Estimated Hours</label>
              <input
                type="number"
                name="estimated_hours"
                value={formData.estimated_hours}
                onChange={handleChange}
                min="1"
                max="100"
                disabled={loading}
              />
            </div>
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

          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                name="is_optional"
                checked={formData.is_optional}
                onChange={(e) => setFormData({ ...formData, is_optional: e.target.checked })}
                disabled={loading}
              />
              <span>This is an optional task</span>
            </label>
          </div>

          {formData.is_optional && (
            <div className="form-group">
              <label>Conditions (When does this apply?)</label>
              <textarea
                name="conditions"
                value={formData.conditions}
                onChange={handleChange}
                rows={2}
                placeholder="e.g., Only for students without Core Negotiations background"
                disabled={loading}
              />
            </div>
          )}

          <div className="modal-actions">
            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? 'Saving...' : 'Save'}
            </button>
            {!task?.isNew && (
              <>
                <button
                  type="button"
                  className="btn-schedule"
                  onClick={handleSchedulePrep}
                  disabled={loading}
                >
                  Schedule Prep
                </button>
                {(formData.task_type === 'exam_prep' || formData.task_type === 'interview_prep') && (
                  <button
                    type="button"
                    className="btn-prep"
                    onClick={() => setShowPrep(!showPrep)}
                    disabled={loading}
                  >
                    {showPrep ? 'Hide' : 'Show'} Prep Material
                  </button>
                )}
                <button
                  type="button"
                  className="btn-danger"
                  onClick={handleDelete}
                  disabled={loading}
                >
                  Delete
                </button>
              </>
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

        {showPrep && prepMaterial && (
          <div className="prep-material-section">
            <div className="prep-header">
              <h3>📚 Prep Material</h3>
              <button
                type="button"
                className="btn-regenerate"
                onClick={handleRegeneratePrep}
                disabled={loading}
              >
                🔄 Regenerate
              </button>
            </div>

            {formData.task_type === 'exam_prep' && (
              <div className="prep-content">
                {prepMaterial.flashcards && (
                  <div className="prep-section">
                    <h4>Flashcards</h4>
                    {prepMaterial.flashcards.map((card, idx) => (
                      <div key={idx} className="flashcard">
                        <strong>Q:</strong> {card.question}<br />
                        <strong>A:</strong> {card.answer}
                      </div>
                    ))}
                  </div>
                )}

                {prepMaterial.quiz_questions && (
                  <div className="prep-section">
                    <h4>Quiz Questions</h4>
                    {prepMaterial.quiz_questions.map((q, idx) => (
                      <div key={idx} className="quiz-question">
                        <p><strong>{idx + 1}. {q.question}</strong></p>
                        <ul>
                          {q.options?.map((opt, i) => (
                            <li key={i} className={opt === q.correct ? 'correct' : ''}>
                              {opt}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                )}

                {prepMaterial.key_concepts && (
                  <div className="prep-section">
                    <h4>Key Concepts</h4>
                    <ul>
                      {prepMaterial.key_concepts.map((concept, idx) => (
                        <li key={idx}>{concept}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {formData.task_type === 'interview_prep' && (
              <div className="prep-content">
                {prepMaterial.company_research && (
                  <div className="prep-section">
                    <h4>Company Research</h4>
                    <ul>
                      {prepMaterial.company_research.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {prepMaterial.questions && (
                  <div className="prep-section">
                    <h4>Common Interview Questions</h4>
                    <ol>
                      {prepMaterial.questions.map((q, idx) => (
                        <li key={idx}>{q}</li>
                      ))}
                    </ol>
                  </div>
                )}

                {prepMaterial.tips && (
                  <div className="prep-section">
                    <h4>Tips for Success</h4>
                    <ul>
                      {prepMaterial.tips.map((tip, idx) => (
                        <li key={idx}>{tip}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default TaskModal;
