import React from 'react';
import { User, Bot, Info, Palette, Loader, Image, Pencil, HelpCircle, BookOpen } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import remarkGfm from 'remark-gfm';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

const ACTION_ICONS = {
  'pencil': Pencil,
  'help-circle': HelpCircle,
  'book-open': BookOpen,
};

const MessageList = ({ messages, onActionClick }) => {
  // Filter out orphaned status messages:
  // - AI messages that still have status set but are no longer streaming (done event replaced the wrong index)
  // - AI messages with no content that aren't actively streaming
  const visibleMessages = messages.filter((msg) => {
    if (msg.type !== 'ai') return true;
    // Keep if actively streaming (even if showing status)
    if (msg.streaming) return true;
    // Hide if it only has status text and no real response content
    if (msg.status && !msg.metadata) return false;
    // Hide empty completed messages with no content
    if (!msg.content && !msg.status) return false;
    return true;
  });

  return (
    <div className="message-list">
      {visibleMessages.map((msg, idx) => (
        msg.type === 'canvas_image' ? (
          <div key={idx} className="message canvas-image-message">
            <div className="message-icon">
              <Palette size={20} />
            </div>
            <div className="message-content">
              <div className="canvas-image-label">Your canvas work</div>
              <div className="canvas-image-container">
                <img
                  src={msg.imageUrl}
                  alt="Student canvas work"
                  className="canvas-chat-image"
                  onClick={() => window.open(msg.imageUrl, '_blank')}
                />
              </div>
            </div>
          </div>
        ) : (
        <div key={idx} className={`message ${msg.type}`}>
          <div className="message-icon">
            {msg.type === 'user' && <User size={20} />}
            {msg.type === 'ai' && !msg.status && <Bot size={20} />}
            {msg.type === 'ai' && msg.status && <Loader size={20} className="spinning" />}
            {msg.type === 'system' && <Info size={20} />}
          </div>
          <div className="message-content">
            {msg.status ? (
              <div className="message-text streaming-status">
                {msg.status}
              </div>
            ) : (
              <>
                <div className="message-text">
                  <ReactMarkdown
                    remarkPlugins={[remarkMath, remarkGfm]}
                    rehypePlugins={[rehypeKatex]}
                  >
                    {msg.content}
                  </ReactMarkdown>
                  {msg.streaming && <span className="streaming-cursor">▊</span>}
                </div>
                {msg.metadata && msg.metadata.intent && (
                  <div className="message-metadata">
                    Intent: {msg.metadata.intent}
                  </div>
                )}
                {msg.actions && !msg.streaming && (
                  <div className="action-buttons">
                    {msg.actions.map((action) => {
                      const IconComponent = ACTION_ICONS[action.icon] || BookOpen;
                      return (
                        <button
                          key={action.id}
                          className="action-btn"
                          onClick={() => onActionClick && onActionClick(action.label)}
                        >
                          <IconComponent size={16} />
                          {action.label}
                        </button>
                      );
                    })}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
        )
      ))}
    </div>
  );
};

export default MessageList;
