import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

function Upload() {
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [splitType, setSplitType] = useState('');
  const [customInstruction, setCustomInstruction] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Progress tracking state
  const [progress, setProgress] = useState({
    stage: '',
    message: '',
    progress: 0
  });
  
  // NEW: Time estimation
  const [estimatedTime, setEstimatedTime] = useState(null);
  const [startTime, setStartTime] = useState(null);
  const [billId, setBillId] = useState(null);
  
  const wsRef = useRef(null);

  const getInstruction = () => {
    if (splitType === 'custom') {
      return customInstruction || 'Split equally among 2';
    }
    const instructionMap = {
      'equal_2': 'Split equally among 2',
      'equal_3': 'Split equally among 3',
      'equal_4': 'Split equally among 4',
      'equal_5': 'Split equally among 5',
    };
    return instructionMap[splitType] || 'Split equally among 2';
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!file) {
      setError('Please select a bill image');
      return;
    }

    if (!splitType) {
      setError('Please select a split option');
      return;
    }

    setLoading(true);
    setStartTime(Date.now());
    setProgress({ stage: 'queuing', message: 'Queuing bill for processing...', progress: 5 });

    const formData = new FormData();
    formData.append('file', file);
    formData.append('instruction', getInstruction());

    try {
      const response = await axios.post('http://localhost:8000/process-bill', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const newBillId = response.data.bill_id;
      setBillId(newBillId);
      connectWebSocket(newBillId);

    } catch (err) {
      setError(err.response?.data?.error || 'Failed to process bill');
      setLoading(false);
      setProgress({ stage: '', message: '', progress: 0 });
    }
  };

  const connectWebSocket = (billIdParam) => {
    const ws = new WebSocket(`ws://localhost:8000/ws/progress/${billIdParam}`);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Progress update:', data);
      
      // Update progress state
      setProgress({
        stage: data.stage,
        message: data.message,
        progress: data.progress
      });

      // Calculate estimated time
      if (data.progress > 5 && data.progress < 100) {
        const elapsed = (Date.now() - startTime) / 1000;
        const estimatedTotal = (elapsed / data.progress) * 100;
        const remaining = Math.ceil(estimatedTotal - elapsed);
        setEstimatedTime(remaining > 0 ? remaining : 1);
      }

      // Redirect when processing is complete
      if (data.stage === 'completed') {
        setTimeout(() => {
          ws.close();
          navigate(`/result/${billIdParam}`);
        }, 1500);
      }

      // Handle errors
      if (data.stage === 'error') {
        setError(data.message);
        setLoading(false);
        ws.close();
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setError('Connection error. Please try again.');
      setLoading(false);
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
    };
  };

  const handleRetry = () => {
    setError('');
    setProgress({ stage: '', message: '', progress: 0 });
    setEstimatedTime(null);
    setStartTime(null);
    // Form will still have the file and settings, just resubmit
  };

  // Cleanup WebSocket on component unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return (
    <div className="page-container">
      <div className="container">
        <h1>💰 PayUp</h1>
        <p className="subtitle">Bill Splitting App</p>
        
        {error && (
          <div className="error-message">
            {error}
            {billId && (
              <button onClick={handleRetry} className="retry-btn">
                Try Again
              </button>
            )}
          </div>
        )}
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="bill_image">📸 Upload Bill Image</label>
            <input
              type="file"
              id="bill_image"
              accept="image/*"
              onChange={(e) => setFile(e.target.files[0])}
              required
              disabled={loading}
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="split_type">How to Split?</label>
            <select
              id="split_type"
              value={splitType}
              onChange={(e) => setSplitType(e.target.value)}
              required
              disabled={loading}
            >
              <option value="">-- Please select an option --</option>
              <option value="equal_2">Split equally among 2 people</option>
              <option value="equal_3">Split equally among 3 people</option>
              <option value="equal_4">Split equally among 4 people</option>
              <option value="equal_5">Split equally among 5 people</option>
              <option value="custom">Custom instruction</option>
            </select>
          </div>
          
          {splitType === 'custom' && (
            <div className="form-group">
              <label htmlFor="custom_instruction">✍️ Custom Instruction</label>
              <input
                type="text"
                id="custom_instruction"
                value={customInstruction}
                onChange={(e) => setCustomInstruction(e.target.value)}
                placeholder="e.g., Person A pays 60%, Person B pays 40%"
                disabled={loading}
              />
            </div>
          )}
          
          <button type="submit" className="btn" disabled={loading}>
            {loading ? '⏳ Processing...' : 'Process Bill'}
          </button>
        </form>
        
        <div className="divider">OR</div>
        
        <button
          onClick={() => navigate('/lookup')}
          className="btn btn-secondary"
          disabled={loading}
        >
          🔍 Lookup Existing Bill
        </button>
      </div>

      {/* Processing Overlay with Live Progress */}
      {loading && (
        <div className="processing-overlay">
          <div className="processing-card">
            {progress.stage === 'completed' ? (
              <div className="success-animation">
                <div className="checkmark">✓</div>
                <h3>Success!</h3>
                <p>Your bill has been split</p>
              </div>
            ) : (
              <>
                <div className="spinner"></div>
                
                <h2>Processing Your Bill</h2>
                
                <div className="progress-bar-container">
                  <div 
                    className="progress-bar-fill" 
                    style={{ width: `${progress.progress}%` }}
                  ></div>
                </div>
                
                <div className="progress-info">
                  <div className="progress-percentage">{progress.progress}%</div>
                  {estimatedTime && progress.progress < 95 && (
                    <div className="time-remaining">
                      ~{estimatedTime}s remaining
                    </div>
                  )}
                </div>
                
                <div className="processing-steps">
                  <div className={`step ${progress.stage === 'uploading' ? 'active' : progress.progress >= 30 ? 'completed' : ''}`}>
                    <span className="step-icon">📤</span>
                    <span className="step-text">
                      {progress.stage === 'uploading' ? progress.message : 'Uploading bill...'}
                    </span>
                  </div>
                  
                  <div className={`step ${progress.stage === 'ocr' ? 'active' : progress.progress >= 50 ? 'completed' : ''}`}>
                    <span className="step-icon">🔍</span>
                    <span className="step-text">
                      {progress.stage === 'ocr' ? progress.message : 'Extracting text...'}
                    </span>
                  </div>
                  
                  <div className={`step ${progress.stage === 'splitting' ? 'active' : progress.progress >= 80 ? 'completed' : ''}`}>
                    <span className="step-icon">💰</span>
                    <span className="step-text">
                      {progress.stage === 'splitting' ? progress.message : 'Calculating splits...'}
                    </span>
                  </div>
                  
                  <div className={`step ${progress.stage === 'saving' ? 'active' : progress.progress >= 95 ? 'completed' : ''}`}>
                    <span className="step-icon">💾</span>
                    <span className="step-text">
                      {progress.stage === 'saving' ? progress.message : 'Saving results...'}
                    </span>
                  </div>
                  
                  <div className={`step ${progress.stage === 'completed' ? 'active completed' : ''}`}>
                    <span className="step-icon">✅</span>
                    <span className="step-text">
                      Complete!
                    </span>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default Upload;
