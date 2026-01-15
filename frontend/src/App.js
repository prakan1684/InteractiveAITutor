import React, { useState } from 'react';
import './App.css';
import ChatInterface from './components/ChatInterface';
import ModeSelector from './components/ModeSelector';
import FileUpload from './components/FileUpload';

function App() {
  const [speedMode, setSpeedMode] = useState('fast');

  const handleModeChange = (mode) => {
    setSpeedMode(mode);
  };

  const handleUploadSuccess = (result) => {
    console.log('Upload successful:', result);
  };

  return (
    <div className="App">
      <header className="app-header">
        <h1>🎓 Pocket Professor</h1>
        <p>Your AI Study Companion</p>
      </header>
      
      <div className="main-container">
        <aside className="sidebar">
          <ModeSelector 
            currentMode={speedMode} 
            onModeChange={handleModeChange} 
          />
          <FileUpload onUploadSuccess={handleUploadSuccess} />
        </aside>
        
        <main className="chat-container">
          <ChatInterface speedMode={speedMode} />
        </main>
      </div>
    </div>
  );
}

export default App;
