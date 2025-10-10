import React, { useState } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { MessageCircle } from 'lucide-react';

const LoginPage = ({ onLogin }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

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
            <div className="bg-gradient-to-r from-purple-600 to-pink-600 p-4 rounded-2xl shadow-2xl">
              <MessageCircle className="w-12 h-12 text-white" />
            </div>
          </div>
          <h1 className="text-4xl font-bold text-white mb-2">TickleGram</h1>
          <p className="text-gray-400 text-lg">Instagram DM Management</p>
        </div>

        {/* Login Card */}
        <div className="bg-[#1a1a2e] backdrop-blur-lg rounded-2xl shadow-2xl border border-gray-800 p-8">
          <h2 className="text-2xl font-bold text-white mb-6" data-testid="login-title">Welcome Back</h2>
          
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
                className="bg-[#0f0f1a] border-gray-700 text-white placeholder:text-gray-500 focus:border-purple-500 h-12"
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
                className="bg-[#0f0f1a] border-gray-700 text-white placeholder:text-gray-500 focus:border-purple-500 h-12"
              />
            </div>

            <Button
              type="submit"
              data-testid="login-submit-button"
              disabled={loading}
              className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-semibold h-12 rounded-lg"
            >
              {loading ? 'Signing In...' : 'Sign In'}
            </Button>
          </form>

          {/* Demo Credentials */}
          <div className="mt-6 p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg">
            <p className="text-sm text-gray-400 mb-2 font-semibold">Demo Credentials:</p>
            <div className="text-xs text-gray-500 space-y-1">
              <p>Admin: admin@ticklegram.com / admin123</p>
              <p>Agent: agent1@ticklegram.com / agent123</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;