import React, { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';

const LoginPage = ({ onLogin, allowPublicSignup = false, forgotPasswordEnabled = true }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState(null);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    if (!location.state) {
      return;
    }
    const { success, info, error: stateError } = location.state;
    if (success) {
      setNotice({ type: 'success', message: success });
    } else if (info) {
      setNotice({ type: 'info', message: info });
    } else if (stateError) {
      setNotice({ type: 'error', message: stateError });
    }
    navigate(location.pathname, { replace: true });
  }, [location, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await axios.post(`${API}/auth/login`, {
        email,
        password
      });
      onLogin(response.data.user, response.data.access_token);
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0f0f1a] via-[#1a1a2e] to-[#16213e] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo & Header */}
        <div className="text-center mb-8" data-testid="login-header">
          <div className="flex justify-center mb-4">
            <img
              src="/favicon.png"
              alt="TickleGram logo"
              className="w-16 h-16 rounded-2xl shadow-2xl"
            />
          </div>
          <h1 className="text-4xl font-bold text-white mb-2">TickleGram</h1>
          <p className="text-gray-400 text-lg">DM Management</p>
        </div>

        {/* Login Card */}
        <div className="bg-[#111328]/90 backdrop-blur-xl rounded-3xl shadow-[0_25px_70px_rgba(17,12,46,0.4)] border border-white/5 p-8 space-y-6">
          <h2 className="text-2xl font-bold text-white mb-6" data-testid="login-title">Welcome Back</h2>

          {notice && (
            <div
              className={`px-4 py-3 rounded-xl text-sm ${
                notice.type === 'success'
                  ? 'bg-emerald-500/10 border border-emerald-500/40 text-emerald-200'
                  : notice.type === 'error'
                    ? 'bg-red-500/10 border border-red-500/40 text-red-200'
                    : 'bg-indigo-500/10 border border-indigo-500/40 text-indigo-100'
              }`}
            >
              {notice.message}
            </div>
          )}
          
          {error && (
            <div className="bg-red-500/10 border border-red-500/50 text-red-400 px-4 py-3 rounded-lg mb-6" data-testid="login-error">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <Label htmlFor="email" className="text-gray-300 mb-2 block">Email</Label>
              <Input
                id="email"
                type="email"
                data-testid="login-email-input"
                placeholder="admin@ticklegram.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="bg-[#05060d]/70 border-gray-800 text-white placeholder:text-gray-500 focus:border-purple-400 focus:ring-2 focus:ring-purple-500/40 focus:ring-offset-2 focus:ring-offset-[#111328] h-12 transition"
              />
            </div>

            <div>
              <Label htmlFor="password" className="text-gray-300 mb-2 block">Password</Label>
              <Input
                id="password"
                type="password"
                data-testid="login-password-input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="bg-[#05060d]/70 border-gray-800 text-white placeholder:text-gray-500 focus:border-purple-400 focus:ring-2 focus:ring-purple-500/40 focus:ring-offset-2 focus:ring-offset-[#111328] h-12 transition"
              />
            </div>

            {forgotPasswordEnabled && (
              <div className="flex justify-end">
                <Link
                  to="/forgot-password"
                  className="text-sm font-medium text-purple-300 hover:text-purple-200 transition"
                >
                  Forgot password?
                </Link>
              </div>
            )}

            <Button
              type="submit"
              data-testid="login-submit-button"
              disabled={loading}
              className="w-full bg-gradient-to-r from-purple-500 via-pink-500 to-orange-400 hover:shadow-[0_10px_40px_rgba(168,85,247,0.35)] text-white font-semibold h-12 rounded-xl transition"
            >
              {loading ? 'Signing In...' : 'Sign In'}
            </Button>
          </form>

          {!allowPublicSignup && (
            <div className="text-center text-sm text-gray-400">
              Access is restricted. Contact your workspace admin for an account.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
