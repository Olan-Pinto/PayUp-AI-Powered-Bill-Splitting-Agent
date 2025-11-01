import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Upload from './pages/Upload';
import Lookup from './pages/Lookup';
import Result from './pages/Result';
import Login from './pages/Login'; 
import AuthCallback from './pages/AuthCallback';
import './App.css';
import ProtectedRoute from "./pages/ProtectedRoute";

function App() {
  return (
    <Router>
      <Routes>
        {/* Public route */}
        <Route path="/login" element={<Login />} />
        <Route path="/auth/callback" element={<AuthCallback />} />
        
        {/* Protected routes */}
        <Route path="/" element={
          <ProtectedRoute>
            <Upload />
          </ProtectedRoute>
        } />
        
        <Route path="/result/:bill_id" element={
          <ProtectedRoute>
            <Result />
          </ProtectedRoute>
        } />
        
        <Route path="/lookup" element={
          <ProtectedRoute>
            <Lookup />
          </ProtectedRoute>
        } />
      </Routes>
    </Router>
  );
}

export default App;