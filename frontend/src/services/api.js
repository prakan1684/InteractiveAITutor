import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Use consistent student ID for testing (should match iOS app)
const STUDENT_ID = 'student_123';

export const chatAPI = {
  sendMessage: async (message, speedMode, conversationId = null) => {
    const use_rag = speedMode !== 'simple';
    const fast_mode = speedMode === 'fast';
    
    const response = await axios.post(`${API_BASE}/chat`, {
      student_id: STUDENT_ID,
      message,
      use_rag,
      fast_mode,
      conversation_id: conversationId
    });
    
    return response.data;
  },
  
  getConversations: async () => {
    const response = await axios.get(`${API_BASE}/conversations/${STUDENT_ID}`);
    return response.data;
  },
  
  getConversation: async (conversationId) => {
    const response = await axios.get(`${API_BASE}/conversation/${conversationId}`);
    return response.data;
  },
  
  deleteConversation: async (conversationId) => {
    const response = await axios.delete(`${API_BASE}/conversation/${conversationId}`);
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
