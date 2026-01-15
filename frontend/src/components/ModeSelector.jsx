import React from 'react';
import { Zap, MessageCircle, Brain } from 'lucide-react';

const ModeSelector = ({ currentMode, onModeChange }) => {
  const modes = [
    {
      id: 'simple',
      name: 'Simple Chat',
      icon: MessageCircle,
      time: '2-3s',
      description: 'General chat without course materials',
      color: '#3498db'
    },
    {
      id: 'fast',
      name: 'Fast RAG',
      icon: Zap,
      time: '3-5s',
      description: 'Quick answers using course materials',
      color: '#f39c12'
    },
    {
      id: 'full',
      name: 'Full Analysis',
      icon: Brain,
      time: '10-15s',
      description: 'Deep analysis with reasoning',
      color: '#9b59b6'
    }
  ];

  return (
    <div className="mode-selector">
      <h3>⚡ Response Mode</h3>
      <div className="mode-buttons">
        {modes.map(mode => {
          const Icon = mode.icon;
          return (
            <button
              key={mode.id}
              className={`mode-btn ${currentMode === mode.id ? 'active' : ''}`}
              onClick={() => onModeChange(mode.id)}
              style={{ borderColor: currentMode === mode.id ? mode.color : '#ddd' }}
            >
              <Icon size={20} />
              <div>
                <div className="mode-name">{mode.name}</div>
                <div className="mode-time">{mode.time}</div>
              </div>
            </button>
          );
        })}
      </div>
      <p className="mode-description">
        {modes.find(m => m.id === currentMode)?.description}
      </p>
    </div>
  );
};

export default ModeSelector;
