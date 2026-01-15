import React, { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';
import { chatAPI } from '../services/api';
import MessageList from './MessageList';

const ChatInterface = ({ speedMode }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    
    setMessages(prev => [...prev, { type: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const result = await chatAPI.sendMessage(userMessage, speedMode);
      
      setMessages(prev => [...prev, {
        type: 'ai',
        content: result.response,
        metadata: speedMode === 'full' ? {
          intent: result.intent,
          confidence: result.confidence,
          course_context_count: result.course_context_count,
          canvas_context_count: result.canvas_context_count
        } : null
      }]);
    } catch (error) {
      setMessages(prev => [...prev, {
        type: 'system',
        content: `Error: ${error.message}`
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chat-interface">
      <MessageList messages={messages} />
      <div ref={messagesEndRef} />
      
      <div className="chat-input-container">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Ask a question..."
          disabled={loading}
          className="chat-input"
        />
        <button
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          className="send-button"
        >
          <Send size={20} />
        </button>
      </div>
    </div>
  );
};

export default ChatInterface;
