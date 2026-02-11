import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Use consistent student ID for testing (should match iOS app)
const STUDENT_ID = 'student_123';

export const chatAPI = {
  sendMessage: async (message, conversationId = null) => {
    const response = await axios.post(`${API_BASE}/chat`, {
      student_id: STUDENT_ID,
      message,
      conversation_id: conversationId
    });
    
    return response.data;
  },

  sendMessageStream: (message, conversationId = null) => {
    const controller = new AbortController();
    
    const stream = fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        student_id: STUDENT_ID,
        message,
        conversation_id: conversationId
      }),
      signal: controller.signal
    });

    return {
      abort: () => controller.abort(),
      read: async function* () {
        const response = await stream;
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const payload = JSON.parse(line.slice(6));
                yield payload;
              } catch (e) {
                // skip malformed events
              }
            }
          }
        }
      }
    };
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
