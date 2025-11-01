import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';

function Result() {
  const { bill_id } = useParams();
  const navigate = useNavigate();
  const [billData, setBillData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showJSON, setShowJSON] = useState(false);

  useEffect(() => {
    const fetchBillData = async () => {
      try {
        const response = await axios.get(`http://localhost:8000/bill/${bill_id}`);
        setBillData(response.data);
        setLoading(false);
      } catch (err) {
        setError(err.response?.data?.error || 'Bill not found');
        setLoading(false);
      }
    };

    fetchBillData();
  }, [bill_id]);

  const downloadBill = async () => {
    try {
      const response = await axios.get(
        `http://localhost:8000/bill/${bill_id}/download`,
        { responseType: 'blob' }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `bill_${bill_id}.jpg`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert('Download failed');
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="loading">
          <h2>⏳ Loading bill data...</h2>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="container">
          <div className="error-message">{error}</div>
          <button onClick={() => navigate('/')} className="btn">
            ← Back to Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="result-container">
      <div className="header">
        <h1>Bill Processed Successfully!</h1>
        <div className="bill-id-badge">Bill ID: {bill_id}</div>
      </div>

      {/* Bill Image */}
      <div className="card">
        <h2>📷 Original Bill</h2>
        <img
          src={`http://localhost:8000/bill/${bill_id}/view`}
          alt="Bill"
          style={{ maxWidth: '100%', borderRadius: '8px' }}
        />
      </div>

      {/* Split Results */}
      <div className="card">
        <h2>💰 Split Breakdown</h2>
        
        {billData?.split_result?.breakdown ? (
          billData.split_result.breakdown.map((split, index) => (
            <div key={index} className="split-item">
              <span className="person-name">Person {split.person}</span>
              <span className="person-amount">
                ${split.total.toFixed(2)}
              </span>
            </div>
          ))
        ) : (
          <p>No split data available.</p>
        )}
        
        <span className="toggle-json" onClick={() => setShowJSON(!showJSON)}>
          {showJSON ? 'Hide Raw JSON' : 'Show Raw JSON'}
        </span>
        {showJSON && (
          <pre>{JSON.stringify(billData, null, 2)}</pre>
        )}
      </div>

      {/* Actions */}
      <div className="actions">
        <button onClick={downloadBill} className="btn btn-download">
          📥 Download Bill
        </button>
        <button onClick={() => navigate('/')} className="btn btn-primary">
          ← Back to Home
        </button>
      </div>
    </div>
  );
}

export default Result;

