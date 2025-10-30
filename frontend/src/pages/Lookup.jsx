import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

function Lookup() {
  const navigate = useNavigate();
  const [billId, setBillId] = useState('');
  const [error, setError] = useState('');

  const viewBill = () => {
    if (!billId.trim()) {
      setError('Please enter a Bill ID');
      return;
    }
    navigate(`/result/${billId.trim()}`);
  };

  const downloadBill = async () => {
    if (!billId.trim()) {
      setError('Please enter a Bill ID');
      return;
    }

    try {
      const response = await axios.get(
        `http://localhost:8000/bill/${billId.trim()}/download`,
        { responseType: 'blob' }
      );

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `bill_${billId}.jpg`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      setError('Bill not found or download failed');
    }
  };

  return (
    <div className="page-container">
      <div className="container">
        <h1>🔍 Lookup Bill</h1>
        <p className="subtitle">Enter your Bill ID to view or download</p>
        
        {error && <div className="error-message">{error}</div>}
        
        <div className="form-group">
          <label htmlFor="bill_id">Bill ID</label>
          <input
            type="text"
            id="bill_id"
            value={billId}
            onChange={(e) => {
              setBillId(e.target.value);
              setError('');
            }}
            placeholder="e.g., 9e2db42e-ac21-467a-8011-b38af91db5fa"
          />
        </div>
        
        <div className="button-group">
          <button onClick={viewBill} className="btn">
            👁️ View Bill
          </button>
          <button onClick={downloadBill} className="btn btn-download">
            📥 Download
          </button>
        </div>
        
        <button onClick={() => navigate('/')} className="btn btn-secondary">
          ← Back to Home
        </button>
      </div>
    </div>
  );
}

export default Lookup;
