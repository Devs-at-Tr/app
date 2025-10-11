import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';

const SignupPage = () => {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleChange = (field) => (event) => {
    const value = event?.target ? event.target.value : event;
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');

    // Validate password match
    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    // Validate password length
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    try {
      setLoading(true);
      await axios.post(
        `${API}/auth/signup`,
        {
          name: form.name.trim(),
          email: form.email.trim(),
          password: form.password,
          role: 'agent' // Always create agents
        }
      );
      setSuccess('Account created successfully! Redirecting to login...');
      setTimeout(() => {
        navigate('/login', { replace: true });
      }, 2000);
    } catch (err) {
      const message = err.response?.data?.detail || err.response?.data?.message || err.message || 'Failed to create account.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0f0f1a] via-[#1a1a2e] to-[#16213e] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo & Header */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <img
              src="/favicon.png"
              alt="TickleGram logo"
              className="w-16 h-16 rounded-2xl shadow-2xl"
            />
          </div>
          <h1 className="text-4xl font-bold text-white mb-2">TickleGram</h1>
          <p className="text-gray-400 text-lg">Create Your Agent Account</p>
        </div>

        {/* Signup Card */}
        <div className="bg-[#1a1a2e] backdrop-blur-lg rounded-2xl shadow-2xl border border-gray-800 p-8">
          <h2 className="text-2xl font-bold text-white mb-6">Sign Up</h2>
          
          {error && (
            <div className="bg-red-500/10 border border-red-500/50 text-red-400 px-4 py-3 rounded-lg mb-6">
              {error}
            </div>
          )}

          {success && (
            <div className="bg-green-500/10 border border-green-500/50 text-green-400 px-4 py-3 rounded-lg mb-6">
              {success}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <Label htmlFor="name" className="text-gray-300 mb-2 block">Full Name</Label>
              <Input
                id="name"
                type="text"
                placeholder="John Doe"
                value={form.name}
                onChange={handleChange('name')}
                required
                className="bg-[#0f0f1a] border-gray-700 text-white placeholder:text-gray-500 focus:border-purple-500 h-12"
              />
            </div>

            <div>
              <Label htmlFor="email" className="text-gray-300 mb-2 block">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="agent@example.com"
                value={form.email}
                onChange={handleChange('email')}
                required
                className="bg-[#0f0f1a] border-gray-700 text-white placeholder:text-gray-500 focus:border-purple-500 h-12"
              />
            </div>

            <div>
              <Label htmlFor="password" className="text-gray-300 mb-2 block">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={form.password}
                onChange={handleChange('password')}
                required
                minLength={8}
                className="bg-[#0f0f1a] border-gray-700 text-white placeholder:text-gray-500 focus:border-purple-500 h-12"
              />
            </div>

            <div>
              <Label htmlFor="confirmPassword" className="text-gray-300 mb-2 block">Confirm Password</Label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder="••••••••"
                value={form.confirmPassword}
                onChange={handleChange('confirmPassword')}
                required
                minLength={8}
                className="bg-[#0f0f1a] border-gray-700 text-white placeholder:text-gray-500 focus:border-purple-500 h-12"
              />
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-semibold h-12 rounded-lg"
            >
              {loading ? 'Creating Account...' : 'Create Account'}
            </Button>
          </form>

          {/* Login Link */}
          <div className="mt-6 text-center">
            <p className="text-sm text-gray-400">
              Already have an account?{' '}
              <Link to="/login" className="text-purple-400 hover:text-purple-300 font-semibold">
                Sign In
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SignupPage;
