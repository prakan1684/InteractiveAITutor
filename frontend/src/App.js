import React, { useState } from 'react';
import './App.css';
import ChatInterface from './components/ChatInterface';
import ModeSelector from './components/ModeSelector';
import FileUpload from './components/FileUpload';
import ConversationSidebar from './components/ConversationSidebar';
import CanvasGallery from './components/CanvasGallery';

function App() {
  const [speedMode, setSpeedMode] = useState('fast');
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [conversationKey, setConversationKey] = useState(0);

  const handleModeChange = (mode) => {
    setSpeedMode(mode);
  };

  const handleUploadSuccess = (result) => {
    console.log('Upload successful:', result);
  };

  const handleSelectConversation = (conversationId) => {
    setCurrentConversationId(conversationId);
    setConversationKey(prev => prev + 1);
  };

  const handleNewConversation = () => {
    setCurrentConversationId(null);
    setConversationKey(prev => prev + 1);
  };

  const handleConversationUpdate = (newConversationId) => {
    setCurrentConversationId(newConversationId);
  };

  return (
    <div className="App">
      <header className="app-header">
        <h1>🎓 Elara</h1>
        <p>Your AI Study Companion</p>
      </header>
      
      <div className="main-container">
        <ConversationSidebar
          currentConversationId={currentConversationId}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
        />
        
        <div className="content-area">
          <aside className="settings-sidebar">
            <ModeSelector 
              currentMode={speedMode} 
              onModeChange={handleModeChange} 
            />
            <FileUpload onUploadSuccess={handleUploadSuccess} />
            <CanvasGallery />
          </aside>
          
          <main className="chat-container">
            <ChatInterface 
              key={conversationKey}
              speedMode={speedMode}
              conversationId={currentConversationId}
              onConversationUpdate={handleConversationUpdate}
            />
          </main>
        </div>
      </div>
    </div>
  );
}

export default App;
