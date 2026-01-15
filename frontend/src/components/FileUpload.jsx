import React, { useState } from 'react';
import { Upload, File } from 'lucide-react';
import { chatAPI } from '../services/api';

const FileUpload = ({ onUploadSuccess }) => {
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState('');

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    setStatus('Uploading...');

    try {
      const result = await chatAPI.uploadFile(file);
      setStatus(`✅ ${file.name} uploaded successfully!`);
      onUploadSuccess && onUploadSuccess(result);
    } catch (error) {
      setStatus(`❌ Upload failed: ${error.message}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="file-upload">
      <h3>📚 Upload Materials</h3>
      <label className="upload-area">
        <input
          type="file"
          onChange={handleFileChange}
          accept=".pdf,.jpg,.jpeg,.png"
          disabled={uploading}
          style={{ display: 'none' }}
        />
        <Upload size={40} />
        <p>Click or drag PDF/Image</p>
      </label>
      {status && <p className="upload-status">{status}</p>}
    </div>
  );
};

export default FileUpload;
