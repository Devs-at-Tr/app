import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';

const ForgotPasswordPage = ({ forgotPasswordEnabled = true }) => {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!forgotPasswordEnabled) {
      return;
    }
    setStatus(null);
    setLoading(true);
    try {
      await axios.post(`${API}/auth/forgot-password`, { email });
      setStatus({
        type: 'success',
        message: 'If an account exists for that email, a password reset link has been sent.'
      });
    } catch (error) {
      setStatus({
        type: 'error',
        message: error.response?.data?.detail || 'Unable to send reset link. Please try again.'
      });
    } finally {
      setLoading(false);
    }
  };

  const renderStatus = () => {
    if (!status) {
      return null;
    }
    const baseClass = 'px-4 py-3 rounded-xl text-sm';
    if (status.type === 'success') {
      return (
        <div className={`${baseClass} bg-emerald-500/10 border border-emerald-500/40 text-emerald-100`}>
          {status.message}
        </div>
      );
    }
    return (
      <div className={`${baseClass} bg-red-500/10 border border-red-500/40 text-red-100`}>
        {status.message}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0f0f1a] via-[#1a1a2e] to-[#16213e] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
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

        <div className="bg-[#111328]/90 backdrop-blur-xl rounded-3xl shadow-[0_25px_70px_rgba(17,12,46,0.4)] border border-white/5 p-8 space-y-6">
          <div>
            <h2 className="text-2xl font-semibold text-white">Forgot password</h2>
            <p className="text-sm text-gray-400 mt-2">
              We'll email you a link to reset your password if your account exists.
            </p>
          </div>

          {!forgotPasswordEnabled ? (
            <div className="space-y-4">
              <div className="px-4 py-3 rounded-xl border border-yellow-500/40 bg-yellow-500/10 text-sm text-yellow-100">
                Password resets are disabled for this workspace. Please contact your admin for help.
              </div>
              <Button asChild className="w-full bg-gradient-to-r from-purple-500 to-pink-500 text-white h-12 rounded-xl">
                <Link to="/login">Return to login</Link>
              </Button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              {renderStatus()}
              <div>
                <Label htmlFor="forgot-email" className="text-gray-300 mb-2 block">
                  Email
                </Label>
                <Input
                  id="forgot-email"
                  type="email"
                  placeholder="you@company.com"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  className="bg-[#05060d]/70 border-gray-800 text-white placeholder:text-gray-500 focus:border-purple-400 focus:ring-2 focus:ring-purple-500/40 focus:ring-offset-2 focus:ring-offset-[#111328] h-12 transition"
                />
              </div>
              <Button
                type="submit"
                disabled={loading}
                className="w-full bg-gradient-to-r from-purple-500 via-pink-500 to-orange-400 hover:shadow-[0_10px_40px_rgba(168,85,247,0.35)] text-white font-semibold h-12 rounded-xl transition"
              >
                {loading ? 'Sending link...' : 'Send reset link'}
              </Button>
            </form>
          )}

          <div className="text-center text-sm text-gray-400">
            <Link to="/login" className="text-purple-300 hover:text-purple-200 font-semibold">
              Back to login
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ForgotPasswordPage;
