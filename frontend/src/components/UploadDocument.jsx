import React, { useState } from 'react';
import { documentsAPI } from '../services/api';
import './UploadDocument.css';

const UploadDocument = () => {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      // Validate file type
      const allowedTypes = ['.pdf', '.txt', '.docx'];
      const fileExtension = '.' + selectedFile.name.split('.').pop().toLowerCase();
      
      if (!allowedTypes.includes(fileExtension)) {
        setError(`File type not supported. Please upload ${allowedTypes.join(', ')} files.`);
        setFile(null);
        return;
      }

      setFile(selectedFile);
      setError('');
      setResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first.');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Use enhanced upload endpoint for better extraction
      const response = await documentsAPI.uploadSyllabusEnhanced(file);
      setResult(response.data);
      setFile(null);
      // Reset file input
      document.getElementById('file-input').value = '';
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to upload document. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="upload-document">
      <div className="upload-card">
        <h2>📄 Upload Syllabus or Document</h2>
        <p className="upload-description">
          Upload a PDF, TXT, or DOCX file containing course information, deadlines, 
          or assignments. Our AI will extract dates and create tasks automatically.
        </p>

        <div className="upload-section">
          <div className="file-input-wrapper">
            <input
              type="file"
              id="file-input"
              accept=".pdf,.txt,.docx"
              onChange={handleFileChange}
              disabled={loading}
            />
            <label htmlFor="file-input" className={loading ? 'disabled' : ''}>
              {file ? file.name : 'Choose a file...'}
            </label>
          </div>

          <button
            onClick={handleUpload}
            className="btn-upload"
            disabled={!file || loading}
          >
            {loading ? 'Processing...' : 'Upload & Extract'}
          </button>
        </div>

        {error && (
          <div className="error-message">
            ❌ {error}
          </div>
        )}

        {result && (
          <div className="result-section">
            <div className="success-message">
              ✅ {result.message}
            </div>

            <div className="result-stats">
              <div className="stat-card">
                <div className="stat-number">{result.tasks_created}</div>
                <div className="stat-label">Tasks Created</div>
              </div>
              {result.assessment_count > 0 && (
                <div className="stat-card">
                  <div className="stat-number">{result.assessment_count}</div>
                  <div className="stat-label">Assessments Found</div>
                </div>
              )}
              {result.class_sessions > 0 && (
                <div className="stat-card">
                  <div className="stat-number">{result.class_sessions}</div>
                  <div className="stat-label">Class Sessions</div>
                </div>
              )}
            </div>

            {result.assessment_components && result.assessment_components.length > 0 && (
              <div className="extracted-tasks">
                <h3>Assessment Components:</h3>
                <div className="tasks-list-simple">
                  {result.assessment_components.map((comp, idx) => (
                    <div key={idx} className="task-item">
                      <div className="task-item-header">
                        <strong>{comp.name}</strong>
                        <span className="task-type-badge">{comp.type}</span>
                      </div>
                      <div className="task-deadline">
                        ⚖️ Weight: {comp.weight_percent}% | Applies to: {comp.applies_to}
                      </div>
                      {comp.description && (
                        <div className="task-description">{comp.description}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {result.tasks && result.tasks.length > 0 && (
              <div className="extracted-tasks">
                <h3>Extracted Tasks:</h3>
                <div className="tasks-list-simple">
                  {result.tasks.map((task, idx) => (
                    <div key={idx} className="task-item">
                      <div className="task-item-header">
                        <strong>{task.title}</strong>
                        <span className="task-type-badge">{task.type}</span>
                      </div>
                      <div className="task-deadline">
                        📅 {new Date(task.deadline).toLocaleDateString()}
                      </div>
                      {task.description && (
                        <div className="task-description">{task.description}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {result.extracted_text_preview && (
              <details className="text-preview">
                <summary>View extracted text preview</summary>
                <pre>{result.extracted_text_preview}</pre>
              </details>
            )}
          </div>
        )}

        <div className="upload-tips">
          <h3>💡 Tips for best results:</h3>
          <ul>
            <li>Use clear, well-formatted documents</li>
            <li>Include specific dates (e.g., "Due: March 15, 2024")</li>
            <li>Label assignments clearly (e.g., "Assignment 1", "Midterm Exam")</li>
            <li>Documents should be in English for best extraction accuracy</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default UploadDocument;
