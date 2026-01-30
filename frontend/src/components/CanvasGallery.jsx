import React, { useState, useEffect } from 'react';
import { Image, Calendar, Eye, X } from 'lucide-react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const STUDENT_ID = 'student_123';

const CanvasGallery = () => {
  const [canvasSessions, setCanvasSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);

  useEffect(() => {
    fetchCanvasSessions();
  }, []);

  const fetchCanvasSessions = async () => {
    setLoading(true);
    try {
      console.log('Fetching canvas sessions for:', STUDENT_ID);
      const response = await axios.get(`${API_BASE}/canvas-sessions/${STUDENT_ID}`);
      console.log('Canvas sessions response:', response.data);
      console.log('Sessions array:', response.data.sessions);
      setCanvasSessions(response.data.sessions || []);
    } catch (error) {
      console.error('Error fetching canvas sessions:', error);
      setCanvasSessions([]);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="canvas-gallery">
      <div className="canvas-gallery-header">
        <h3>
          <Image size={18} />
          Canvas History
        </h3>
        <button onClick={fetchCanvasSessions} className="refresh-btn" title="Refresh">
          🔄
        </button>
      </div>

      {loading ? (
        <div className="canvas-loading">Loading canvas history...</div>
      ) : canvasSessions.length === 0 ? (
        <div className="canvas-empty">
          <Image size={48} style={{ opacity: 0.3 }} />
          <p>No canvas submissions yet</p>
          <small>Submit work from your iOS app</small>
        </div>
      ) : (
        <div className="canvas-grid">
          {canvasSessions.map((session, idx) => {
            console.log(`Session ${idx}:`, {
              session_id: session.session_id,
              canvas_image_url: session.canvas_image_url,
              symbol_count: session.symbol_count,
              timestamp: session.timestamp
            });
            return (
            <div 
              key={session.session_id || idx} 
              className="canvas-card"
              onClick={() => setSelectedImage(session)}
            >
              <div className="canvas-thumbnail">
                {session.canvas_image_url ? (
                  <img 
                    src={session.canvas_image_url} 
                    alt="Canvas work"
                    onLoad={() => console.log('Image loaded successfully:', session.canvas_image_url)}
                    onError={(e) => {
                      console.error('Image failed to load:', session.canvas_image_url);
                      e.target.style.display = 'none';
                      e.target.nextSibling.style.display = 'flex';
                    }}
                  />
                ) : null}
                <div className="canvas-placeholder" style={{ display: session.canvas_image_url ? 'none' : 'flex' }}>
                  <Image size={32} />
                </div>
              </div>
              
              <div className="canvas-info">
                <div className="canvas-symbols">
                  {session.symbol_count > 0 ? (
                    <span>✏️ {session.symbol_count} symbols</span>
                  ) : (
                    <span style={{ opacity: 0.5 }}>No symbols detected</span>
                  )}
                </div>
                <div className="canvas-time">
                  <Calendar size={12} />
                  {formatDate(session.timestamp)}
                </div>
              </div>
            </div>
            );
          })}
        </div>
      )}

      {selectedImage && (
        <div className="canvas-lightbox" onClick={() => setSelectedImage(null)}>
          <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
            <button className="lightbox-close" onClick={() => setSelectedImage(null)}>
              <X size={24} />
            </button>
            
            <img 
              src={selectedImage.canvas_image_url} 
              alt="Canvas work full size"
              className="lightbox-image"
            />
            
            <div className="lightbox-details">
              <h4>Canvas Details</h4>
              <p><strong>Symbols:</strong> {selectedImage.symbol_count}</p>
              {selectedImage.latex_expressions && selectedImage.latex_expressions.length > 0 && (
                <p><strong>Expressions:</strong> {selectedImage.latex_expressions.join(', ')}</p>
              )}
              <p><strong>Date:</strong> {new Date(selectedImage.timestamp).toLocaleString()}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CanvasGallery;
