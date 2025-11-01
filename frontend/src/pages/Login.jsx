

import { useNavigate } from "react-router-dom";
import "../App.css";

export default function Login() {
  const navigate = useNavigate();

  const handleGoogleLogin = () => {
    window.location.href = "http://localhost:8000/auth/google";
  };

  return (
    <div className="page-container">
      <div className="container">
        <h1>💰 PayUp</h1>
        <p className="subtitle">Split bills effortlessly</p>

        <button className="btn btn-download" onClick={handleGoogleLogin}>
          <img src="/google-icon.svg" alt="Google" style={{ width: "20px", marginRight: "8px" , height: "30px"}} />
          Continue with Google
        </button>
      </div>
    </div>
  );
}