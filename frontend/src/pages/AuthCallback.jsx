import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { API_URL } from '../config';

function AuthCallback() {
  const navigate = useNavigate();

  useEffect(() => {
    const hash = window.location.hash.substring(1);
    const params = new URLSearchParams(hash);
    const accessToken = params.get("access_token");

    if (accessToken) {
      localStorage.setItem("access_token", accessToken);
      fetch(`${API_URL}/auth/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ access_token: accessToken }),
      })
        .then((res) => res.json())
        .then((data) => {
          console.log("Verified user:", data);
          localStorage.setItem("user", data.user.email);
          navigate("/");
        })
        .catch((err) => {
          console.error("Verification failed:", err);
          navigate("/login");
        });
    } else {
      navigate("/login");
    }
  }, [navigate]);

  return <p>Signing you in...</p>;
}

export default AuthCallback;