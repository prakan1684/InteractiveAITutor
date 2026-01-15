import React from 'react';
import { User, Bot, Info } from 'lucide-react';

const MessageList = ({ messages }) => {
  return (
    <div className="message-list">
      {messages.map((msg, idx) => (
        <div key={idx} className={`message ${msg.type}`}>
          <div className="message-icon">
            {msg.type === 'user' && <User size={20} />}
            {msg.type === 'ai' && <Bot size={20} />}
            {msg.type === 'system' && <Info size={20} />}
          </div>
          <div className="message-content">
            <div className="message-text">{msg.content}</div>
            {msg.metadata && (
              <div className="message-metadata">
                📊 Intent: {msg.metadata.intent} | 
                🎯 Confidence: {(msg.metadata.confidence * 100).toFixed(0)}% | 
                📚 Course: {msg.metadata.course_context_count} | 
                📝 Canvas: {msg.metadata.canvas_context_count}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

export default MessageList;
