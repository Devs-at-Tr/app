import React, { useState, useEffect } from 'react';
import './App.css';
import axios from 'axios';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { WebSocketProvider } from './context/WebSocketContext';
import { ThemeProvider } from './context/ThemeContext';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import InboxPage from './pages/InboxPage';
import TemplatesPage from './pages/TemplatesPage';
import CommentsPage from './pages/CommentsPage';
import UserDirectoryPage from './pages/UserDirectoryPage';
import PositionsPage from './pages/PositionsPage';

// Get backend URL from environment or use relative path for Kubernetes ingress
export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
export const API = BACKEND_URL ? `${BACKEND_URL}/api` : '/api';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [appError, setAppError] = useState('');

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = localStorage.getItem('token');
    if (token) {
      try {
        const response = await axios.get(`${API}/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
          timeout: 10000 // 10 second timeout
        });
        setUser(response.data);
      } catch (error) {
        console.error('Auth check failed:', error.message);
        localStorage.removeItem('token');
        // Show error in loading state if it's a network error
        if (error.message === 'Network Error') {
          setAppError('Cannot connect to server. Please check your internet connection.');
        }
      }
    }
    setLoading(false);
  };

  const handleLogin = (userData, token) => {
    localStorage.setItem('token', token);
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0f0f1a] flex items-center justify-center">
        {appError ? (
          <div className="text-center text-gray-400">
            <p className="mb-2">{appError}</p>
            <p className="text-sm text-gray-500">Retrying...</p>
          </div>
        ) : (
          <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500"></div>
        )}
      </div>
    );
  }

  return (
    <ThemeProvider>
      <WebSocketProvider token={user ? localStorage.getItem('token') : null}>
        <BrowserRouter>
          <Routes>
            <Route
              path="/login"
              element={
                !user ? (
                  <LoginPage onLogin={handleLogin} />
                ) : (
                  <Navigate to="/" replace />
                )
              }
            />
            <Route
              path="/signup"
              element={
                !user ? (
                  <SignupPage />
                ) : (
                  <Navigate to="/" replace />
                )
              }
            />
            <Route
              path="/"
              element={<Navigate to="/inbox" replace />}
            />
            <Route
              path="/inbox"
              element={
                user ? (
                  <InboxPage user={user} onLogout={handleLogout} />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />
            <Route
              path="/inbox/:channel"
              element={
                user ? (
                  <InboxPage user={user} onLogout={handleLogout} />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />
            <Route
              path="/templates"
              element={
                user ? (
                  <TemplatesPage user={user} onLogout={handleLogout} />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />
            <Route
              path="/comments"
              element={
                user ? (
                  <CommentsPage user={user} onLogout={handleLogout} />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />
            <Route
              path="/user-directory"
              element={
                user ? (
                  <UserDirectoryPage user={user} onLogout={handleLogout} />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />
            <Route
              path="/positions"
              element={
                user ? (
                  <PositionsPage user={user} onLogout={handleLogout} />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />
          </Routes>
        </BrowserRouter>
      </WebSocketProvider>
    </ThemeProvider>
  );
}

export default App;
