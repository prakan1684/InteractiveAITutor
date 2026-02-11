import React from 'react';
import { User, Bot, Info, Palette, Loader, Image } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import remarkGfm from 'remark-gfm';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

const MessageList = ({ messages }) => {
  return (
    <div className="message-list">
      {messages.map((msg, idx) => (
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
