import React, { useState, useRef, useEffect } from 'react';
import { Send, Trash2 } from 'lucide-react';
import { chatAPI } from '../services/api';
import MessageList from './MessageList';

const ChatInterface = ({ conversationId: propConversationId, onConversationUpdate }) => {
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

  const aiMessageIndexRef = useRef(null);

  const _sendAndStream = async (messageText) => {
    isSendingMessageRef.current = true;
    setLoading(true);

    setMessages(prev => {
      const withUser = [...prev, { type: 'user', content: messageText }];
      aiMessageIndexRef.current = withUser.length;
      return [...withUser, { type: 'ai', content: '', streaming: true }];
    });

    try {
      const { read } = chatAPI.sendMessageStream(messageText, conversationId);

      for await (const event of read()) {
        if (event.type === 'meta') {
          if (event.conversation_id) {
            setConversationId(event.conversation_id);
            if (onConversationUpdate) onConversationUpdate(event.conversation_id);
          }
        } else if (event.type === 'canvas_image') {
          setMessages(prev => {
            const updated = [...prev];
            updated.splice(aiMessageIndexRef.current, 0, {
              type: 'canvas_image',
              imageUrl: `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}${event.image_url}`,
            });
            aiMessageIndexRef.current += 1;
            return updated;
          });
        } else if (event.type === 'status') {
          setMessages(prev => {
            const updated = [...prev];
            updated[aiMessageIndexRef.current] = {
              ...updated[aiMessageIndexRef.current],
              status: event.content || null,
            };
            return updated;
          });
        } else if (event.type === 'chunk') {
          setMessages(prev => {
            const updated = [...prev];
            const current = updated[aiMessageIndexRef.current];
            const existingContent = current.status ? '' : (current.content || '');
            updated[aiMessageIndexRef.current] = {
              ...current,
              content: existingContent + event.content,
              status: null,
            };
            return updated;
          });
        } else if (event.type === 'actions') {
          setMessages(prev => {
            const updated = [...prev];
            updated[aiMessageIndexRef.current] = {
              ...updated[aiMessageIndexRef.current],
              actions: event.actions,
            };
            return updated;
          });
        } else if (event.type === 'done') {
          setMessages(prev => {
            const updated = [...prev];
            const current = updated[aiMessageIndexRef.current];
            updated[aiMessageIndexRef.current] = {
              type: 'ai',
              content: event.response,
              streaming: false,
              metadata: { intent: event.intent },
              actions: current.actions || null,
            };
            return updated;
          });
        }
      }
    } catch (error) {
      setMessages(prev => {
        const updated = [...prev];
        updated[aiMessageIndexRef.current] = {
          type: 'system',
          content: `Error: ${error.message}`,
          streaming: false,
        };
        return updated;
      });
    } finally {
      setLoading(false);
      setTimeout(() => { isSendingMessageRef.current = false; }, 100);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMessage = input.trim();
    setInput('');
    await _sendAndStream(userMessage);
  };

  const handleActionClick = (actionLabel) => {
    if (loading) return;
    _sendAndStream(actionLabel);
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
      
      <MessageList messages={messages} onActionClick={handleActionClick} />
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
