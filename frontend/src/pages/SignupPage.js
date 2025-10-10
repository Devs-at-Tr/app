import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { ArrowLeft } from 'lucide-react';

const roleOptions = [
  { value: 'admin', label: 'Admin' },
  { value: 'supervisor', label: 'Supervisor' },
  { value: 'agent', label: 'Agent' }
];

const SignupPage = ({ onUserCreated }) => {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    role: 'agent'
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

    try {
      setLoading(true);
      await axios.post(
        `${API}/auth/signup`,
        {
          name: form.name.trim(),
          email: form.email.trim(),
          password: form.password,
          role: form.role
        },
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token') || ''}`
          }
        }
      );
      setSuccess('User created successfully. Redirecting to login...');
      if (typeof onUserCreated === 'function') {
        await onUserCreated();
      }
      navigate('/login', { replace: true });
    } catch (err) {
      const message = err.response?.data?.detail || err.response?.data?.message || err.message || 'Failed to create user.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0f0f1a] flex flex-col">
      <header className="p-6">
        <Button
          variant="ghost"
          className="text-gray-400 hover:text-white hover:bg-[#1a1a2e]"
          onClick={() => navigate(-1)}
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Dashboard
        </Button>
      </header>
      <main className="flex-1 flex items-center justify-center p-4">
        <Card className="w-full max-w-lg bg-[#1a1a2e] border border-gray-800">
          <CardHeader>
            <CardTitle className="text-white text-2xl">Create New User</CardTitle>
          </CardHeader>
          <CardContent>
            {error && (
              <div className="mb-4 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                {error}
              </div>
            )}
            {success && (
              <div className="mb-4 rounded-lg border border-green-500/40 bg-green-500/10 px-4 py-3 text-sm text-green-300">
                {success}
              </div>
            )}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="name" className="text-gray-300">
                  Full Name
                </Label>
                <Input
                  id="name"
                  required
                  value={form.name}
                  onChange={handleChange('name')}
                  placeholder="Jane Doe"
                  className="mt-1 bg-[#0f0f1a] border-gray-700 text-white"
                />
              </div>
              <div>
                <Label htmlFor="email" className="text-gray-300">
                  Email
                </Label>
                <Input
                  id="email"
                  type="email"
                  required
                  value={form.email}
                  onChange={handleChange('email')}
                  placeholder="user@example.com"
                  className="mt-1 bg-[#0f0f1a] border-gray-700 text-white"
                />
              </div>
              <div>
                <Label htmlFor="password" className="text-gray-300">
                  Password
                </Label>
                <Input
                  id="password"
                  type="password"
                  required
                  minLength={8}
                  value={form.password}
                  onChange={handleChange('password')}
                  placeholder="Minimum 8 characters"
                  className="mt-1 bg-[#0f0f1a] border-gray-700 text-white"
                />
              </div>
              <div>
                <Label className="text-gray-300">Role</Label>
                <Select value={form.role} onValueChange={handleChange('role')}>
                  <SelectTrigger className="mt-1 bg-[#0f0f1a] border-gray-700 text-white">
                    <SelectValue placeholder="Select a role" />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1a1a2e] border border-gray-800 text-white">
                    {roleOptions.map((option) => (
                      <SelectItem key={option.value} value={option.value} className="capitalize">
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center justify-between pt-4">
                <Link to="/" className="text-sm text-gray-400 hover:text-white">
                  Cancel
                </Link>
                <Button
                  type="submit"
                  disabled={loading}
                  className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
                >
                  {loading ? 'Creating...' : 'Create User'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
};

export default SignupPage;
