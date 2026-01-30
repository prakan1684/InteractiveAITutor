import React from 'react';
import { User, Bot, Info, Palette } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import remarkGfm from 'remark-gfm';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

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
            {msg.metadata && msg.metadata.canvas_context_count > 0 && (
              <div className="canvas-context-badge">
                <Palette size={14} />
                Using your canvas work
              </div>
            )}
            <div className="message-text">
              <ReactMarkdown
                remarkPlugins={[remarkMath, remarkGfm]}
                rehypePlugins={[rehypeKatex]}
              >
                {msg.content}
              </ReactMarkdown>
            </div>
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
