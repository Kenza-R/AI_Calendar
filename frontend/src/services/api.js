import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests if available
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Auth API
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/token', data),
  getCurrentUser: () => api.get('/auth/me'),
};

// Events API
export const eventsAPI = {
  getAll: () => api.get('/events/'),
  getById: (id) => api.get(`/events/${id}`),
  create: (data) => api.post('/events/', data),
  update: (id, data) => api.put(`/events/${id}`, data),
  delete: (id) => api.delete(`/events/${id}`),
};

// Tasks API
export const tasksAPI = {
  getAll: (completed = null) => {
    const params = completed !== null ? { completed } : {};
    return api.get('/tasks/', { params });
  },
  getById: (id) => api.get(`/tasks/${id}`),
  create: (data, generatePrep = true) => 
    api.post('/tasks/', data, { params: { generate_prep: generatePrep } }),
  update: (id, data) => api.put(`/tasks/${id}`, data),
  delete: (id) => api.delete(`/tasks/${id}`),
  schedulePrepSessions: (id) => api.post(`/tasks/${id}/schedule`),
  regeneratePrep: (id) => api.post(`/tasks/${id}/regenerate-prep`),
};

// Documents API
export const documentsAPI = {
  uploadSyllabus: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/documents/upload-syllabus', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  // Enhanced upload with advanced AI extraction
  uploadSyllabusEnhanced: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/documents/upload-syllabus-enhanced', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  // Extract assessment components only
  extractAssessments: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/documents/extract-assessments', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  parseText: (text, context = 'general') => 
    api.post('/documents/parse-text', null, { params: { text, context } }),
};

// Calendar Sync API
export const calendarAPI = {
  getIntegrations: () => api.get('/calendar/integrations'),
  syncGoogle: () => api.post('/calendar/sync/google'),
  scanGmail: () => api.post('/calendar/sync/gmail'),
  syncOutlook: () => api.post('/calendar/sync/outlook'),
  getScheduleOverview: (daysAhead = 7) => 
    api.get('/calendar/schedule-overview', { params: { days_ahead: daysAhead } }),
};

export default api;
