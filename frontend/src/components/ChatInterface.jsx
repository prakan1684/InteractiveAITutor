import React, { useState, useRef, useEffect } from 'react';
import { Send, Trash2 } from 'lucide-react';
import { chatAPI } from '../services/api';
import MessageList from './MessageList';

const ChatInterface = ({ speedMode, conversationId: propConversationId, onConversationUpdate }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState(propConversationId);
  const messagesEndRef = useRef(null);
  const isSendingMessageRef = useRef(false);

  // Load conversation when conversationId prop changes
  useEffect(() => {
    // Don't reload if we're currently sending a message
    if (isSendingMessageRef.current) {
      console.log('Skipping reload - currently sending message');
      return;
    }
    
    if (propConversationId) {
      // Load the conversation from backend
      loadConversation(propConversationId);
    } else {
      // New conversation requested
      setMessages([]);
      setConversationId(null);
    }
  }, [propConversationId]);

  const loadConversation = async (convId) => {
    try {
      const result = await chatAPI.getConversation(convId);
      console.log('Loading conversation:', convId, 'Result:', result);
      
      if (!result.messages || result.messages.length === 0) {
        console.log('No messages found for conversation:', convId);
        setMessages([]);
        return;
      }
      
      const loadedMessages = result.messages.map(msg => ({
        type: msg.role === 'user' ? 'user' : 'ai',
        content: msg.content,
        metadata: msg.metadata || null // Backend already parses JSON
      }));
      
      console.log('Loaded messages:', loadedMessages);
      setMessages(loadedMessages);
      setConversationId(convId);
    } catch (error) {
      console.error('Error loading conversation:', error);
      setMessages([]);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(scrollToBottom, [messages]);

  const clearHistory = async () => {
    if (window.confirm('Are you sure you want to clear this conversation?')) {
      if (conversationId) {
        try {
          await chatAPI.deleteConversation(conversationId);
        } catch (error) {
          console.error('Error deleting conversation:', error);
        }
      }
      setMessages([]);
      setConversationId(null);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    
    // Set flag to prevent conversation reload during send
    isSendingMessageRef.current = true;
    
    setMessages(prev => [...prev, { type: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const result = await chatAPI.sendMessage(userMessage, speedMode, conversationId);
      
      // Update conversation ID from response
      if (result.conversation_id) {
        setConversationId(result.conversation_id);
        if (onConversationUpdate) {
          onConversationUpdate(result.conversation_id);
        }
      }
      
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
      // Clear flag after a short delay to ensure state updates complete
      setTimeout(() => {
        isSendingMessageRef.current = false;
      }, 100);
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
      <div className="chat-header">
        <h3>💬 Conversation {conversationId ? `(${conversationId.slice(0, 8)}...)` : ''}</h3>
        {messages.length > 0 && (
          <button onClick={clearHistory} className="clear-history-btn" title="Clear conversation">
            <Trash2 size={18} />
            Clear History
          </button>
        )}
      </div>
      
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
