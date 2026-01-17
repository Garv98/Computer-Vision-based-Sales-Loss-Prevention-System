
import './App.css';
import Dashboard from './components/Dashboard';
import AuthForm from './components/AuthForm';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { Toaster } from 'react-hot-toast';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    return localStorage.getItem('isAuthenticated') === 'true';
  });

  useEffect(() => {
    // Sync authentication state with localStorage
    if (isAuthenticated) {
      localStorage.setItem('isAuthenticated', 'true');
    } else {
      localStorage.removeItem('isAuthenticated');
      localStorage.removeItem('user');
    }
  }, [isAuthenticated]);

  return (
    <Router>
      <Toaster 
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#fff',
            color: '#363636',
          },
          success: {
            iconTheme: {
              primary: '#10b981',
              secondary: '#fff',
            },
          },
          error: {
            iconTheme: {
              primary: '#ef4444',
              secondary: '#fff',
            },
          },
        }}
      />
      <Routes>
        <Route path="/login" element={
          <div className="auth-page-wrapper">
            <div className="fixed top-4 left-4 z-50">
              <img src="/RV-logo_new.png" alt="College Logo" className="h-20 w-auto" />
            </div>
            <AuthForm setIsAuthenticated={setIsAuthenticated} />
          </div>
        } />
        <Route 
          path="/dashboard" 
          element={isAuthenticated ? (
            <div className="dashboard-page-wrapper">
              <Dashboard setIsAuthenticated={setIsAuthenticated} />
            </div>
          ) : <Navigate to="/login" />} 
        />
        <Route path="/" element={<Navigate to="/login" />} />
      </Routes>
    </Router>
  );
}

export default App;
