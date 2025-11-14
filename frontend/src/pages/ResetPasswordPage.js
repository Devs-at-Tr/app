import React, { useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';

const ResetPasswordPage = ({ forgotPasswordEnabled = true }) => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = useMemo(() => searchParams.get('token') || '', [searchParams]);
  const [form, setForm] = useState({ password: '', confirmPassword: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!forgotPasswordEnabled) {
      return;
    }
    if (!token) {
      setError('Reset link is missing or invalid.');
      return;
    }
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setError('');
    setLoading(true);
    try {
      await axios.post(`${API}/auth/reset-password`, {
        token,
        password: form.password
      });
      navigate('/login', {
        replace: true,
        state: { success: 'Password updated. You can now sign in with your new password.' }
      });
    } catch (resetError) {
      setError(resetError.response?.data?.detail || 'Unable to reset password. The link may have expired.');
    } finally {
      setLoading(false);
    }
  };

  const disabledState = !forgotPasswordEnabled || !token;

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
            <h2 className="text-2xl font-semibold text-white">Reset password</h2>
            <p className="text-sm text-gray-400 mt-2">
              Create a new password for your account. Make sure it&apos;s at least 8 characters long.
            </p>
          </div>

          {error && (
            <div className="px-4 py-3 rounded-xl border border-red-500/40 bg-red-500/10 text-sm text-red-100">
              {error}
            </div>
          )}

          {disabledState ? (
            <div className="space-y-4">
              <div className="px-4 py-3 rounded-xl border border-yellow-500/40 bg-yellow-500/10 text-sm text-yellow-100">
                {forgotPasswordEnabled
                  ? 'This reset link is missing or invalid. Please request a new link.'
                  : 'Password resets are disabled for this workspace. Contact your admin for help.'}
              </div>
              <div className="flex flex-col gap-2">
                <Button asChild className="w-full bg-gradient-to-r from-purple-500 to-pink-500 text-white h-12 rounded-xl">
                  <Link to={forgotPasswordEnabled ? '/forgot-password' : '/login'}>
                    {forgotPasswordEnabled ? 'Request another link' : 'Back to login'}
                  </Link>
                </Button>
                {forgotPasswordEnabled && (
                  <Button variant="ghost" asChild className="w-full text-white/70 hover:text-white">
                    <Link to="/login">Return to login</Link>
                  </Button>
                )}
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <Label htmlFor="new-password" className="text-gray-300 mb-2 block">
                  New password
                </Label>
                <Input
                  id="new-password"
                  type="password"
                  placeholder="••••••••"
                  value={form.password}
                  onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
                  required
                  minLength={8}
                  className="bg-[#05060d]/70 border-gray-800 text-white placeholder:text-gray-500 focus:border-purple-400 focus:ring-2 focus:ring-purple-500/40 focus:ring-offset-2 focus:ring-offset-[#111328] h-12 transition"
                />
              </div>
              <div>
                <Label htmlFor="confirm-password" className="text-gray-300 mb-2 block">
                  Confirm password
                </Label>
                <Input
                  id="confirm-password"
                  type="password"
                  placeholder="••••••••"
                  value={form.confirmPassword}
                  onChange={(event) => setForm((prev) => ({ ...prev, confirmPassword: event.target.value }))}
                  required
                  minLength={8}
                  className="bg-[#05060d]/70 border-gray-800 text-white placeholder:text-gray-500 focus:border-purple-400 focus:ring-2 focus:ring-purple-500/40 focus:ring-offset-2 focus:ring-offset-[#111328] h-12 transition"
                />
              </div>
              <Button
                type="submit"
                disabled={loading}
                className="w-full bg-gradient-to-r from-purple-500 via-pink-500 to-orange-400 hover:shadow-[0_10px_40px_rgba(168,85,247,0.35)] text-white font-semibold h-12 rounded-xl transition"
              >
                {loading ? 'Updating password...' : 'Reset password'}
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

export default ResetPasswordPage;
