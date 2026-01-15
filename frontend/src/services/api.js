import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Generate unique student ID
const STUDENT_ID = 'student_' + Math.random().toString(36).substr(2, 9);

export const chatAPI = {
  sendMessage: async (message, speedMode) => {
    const use_rag = speedMode !== 'simple';
    const fast_mode = speedMode === 'fast';
    
    const response = await axios.post(`${API_BASE}/chat`, {
      student_id: STUDENT_ID,
      message,
      use_rag,
      fast_mode
    });
    
    return response.data;
  },
  
  uploadFile: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await axios.post(`${API_BASE}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    
    return response.data;
  },
  
  getDocuments: async () => {
    const response = await axios.get(`${API_BASE}/documents`);
    return response.data;
  }
};
