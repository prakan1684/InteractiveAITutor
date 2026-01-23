import React, { useState, useEffect } from 'react';
import { MessageSquare, Plus, Trash2, Search, Clock } from 'lucide-react';
import { chatAPI } from '../services/api';

const ConversationSidebar = ({ currentConversationId, onSelectConversation, onNewConversation }) => {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [hoveredId, setHoveredId] = useState(null);

  useEffect(() => {
    loadConversations();
  }, []);

  // Refresh when currentConversationId changes (new conversation created)
  useEffect(() => {
    if (currentConversationId) {
      // Small delay to ensure backend has stored the message
      const timer = setTimeout(() => {
        loadConversations();
      }, 500);
      return () => clearTimeout(timer);
    }
  }, [currentConversationId]);

  const loadConversations = async () => {
    try {
      setLoading(true);
      const result = await chatAPI.getConversations();
      setConversations(result.conversations || []);
    } catch (error) {
      console.error('Error loading conversations:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (conversationId, e) => {
    e.stopPropagation();
    
    if (window.confirm('Delete this conversation?')) {
      try {
        await chatAPI.deleteConversation(conversationId);
        setConversations(prev => prev.filter(c => c.conversation_id !== conversationId));
        
        // If deleting current conversation, start new one
        if (conversationId === currentConversationId) {
          onNewConversation();
        }
      } catch (error) {
        console.error('Error deleting conversation:', error);
      }
    }
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const filteredConversations = conversations.filter(conv =>
    conv.last_message.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="conversation-sidebar">
      <div className="sidebar-header">
        <h2>💬 Conversations</h2>
        <button 
          className="new-conversation-btn"
          onClick={onNewConversation}
          title="New Conversation"
        >
          <Plus size={20} />
        </button>
      </div>

      <div className="sidebar-search">
        <Search size={18} />
        <input
          type="text"
          placeholder="Search conversations..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="search-input"
        />
      </div>

      <div className="conversations-list">
        {loading ? (
          <div className="loading-conversations">
            <div className="spinner"></div>
            <p>Loading conversations...</p>
          </div>
        ) : filteredConversations.length === 0 ? (
          <div className="empty-state">
            <MessageSquare size={48} />
            <p>{searchQuery ? 'No conversations found' : 'No conversations yet'}</p>
            <p className="empty-subtitle">Start a new conversation to begin!</p>
          </div>
        ) : (
          filteredConversations.map((conv) => (
            <div
              key={conv.conversation_id}
              className={`conversation-item ${conv.conversation_id === currentConversationId ? 'active' : ''}`}
              onClick={() => onSelectConversation(conv.conversation_id)}
              onMouseEnter={() => setHoveredId(conv.conversation_id)}
              onMouseLeave={() => setHoveredId(null)}
            >
              <div className="conversation-content">
                <div className="conversation-preview">
                  {conv.last_message}
                </div>
                <div className="conversation-meta">
                  <Clock size={12} />
                  <span>{formatTimestamp(conv.timestamp)}</span>
                  <span className="message-count">• {conv.message_count} messages</span>
                </div>
              </div>
              {(hoveredId === conv.conversation_id || conv.conversation_id === currentConversationId) && (
                <button
                  className="delete-conversation-btn"
                  onClick={(e) => handleDelete(conv.conversation_id, e)}
                  title="Delete conversation"
                >
                  <Trash2 size={16} />
                </button>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default ConversationSidebar;
