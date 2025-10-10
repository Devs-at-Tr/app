import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Plus, Trash2, RefreshCw, Check, X, Instagram } from 'lucide-react';
import { Alert, AlertDescription } from './ui/alert';

const InstagramIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z"/>
  </svg>
);

const InstagramAccountManager = ({ onClose }) => {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [formData, setFormData] = useState({
    page_id: '',
    username: '',
    access_token: ''
  });

  useEffect(() => {
    loadAccounts();
  }, []);

  const loadAccounts = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/instagram/accounts`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAccounts(response.data);
      setError('');
    } catch (error) {
      console.error('Error loading Instagram accounts:', error);
      setError('Failed to load Instagram accounts');
    } finally {
      setLoading(false);
    }
  };

  const handleAddAccount = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!formData.page_id || !formData.access_token) {
      setError('Instagram Account ID and Access Token are required');
      return;
    }

    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API}/instagram/accounts`,
        formData,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setSuccess('Instagram account connected successfully!');
      setFormData({ page_id: '', username: '', access_token: '' });
      setShowAddForm(false);
      loadAccounts();
    } catch (error) {
      console.error('Error adding Instagram account:', error);
      setError(error.response?.data?.detail || 'Failed to connect Instagram account');
    }
  };

  const handleDeleteAccount = async (accountId) => {
    if (!window.confirm('Are you sure you want to disconnect this Instagram account?')) {
      return;
    }

    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API}/instagram/accounts/${accountId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSuccess('Instagram account disconnected successfully!');
      loadAccounts();
    } catch (error) {
      console.error('Error deleting Instagram account:', error);
      setError('Failed to disconnect Instagram account');
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" data-testid="instagram-account-manager">
      <Card className="bg-[#1a1a2e] border-gray-800 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <CardHeader className="border-b border-gray-800">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-pink-600 to-purple-600 rounded-full flex items-center justify-center">
                <InstagramIcon className="w-5 h-5 text-white" />
              </div>
              <CardTitle className="text-white text-xl">Manage Instagram Accounts</CardTitle>
            </div>
            <Button
              onClick={onClose}
              variant="ghost"
              size="sm"
              className="text-gray-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>
        </CardHeader>

        <CardContent className="p-6 space-y-6">
          {/* Error/Success Messages */}
          {error && (
            <Alert className="bg-red-500/10 border-red-500/50 text-red-400">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {success && (
            <Alert className="bg-green-500/10 border-green-500/50 text-green-400">
              <AlertDescription>{success}</AlertDescription>
            </Alert>
          )}

          {/* Info Alert */}
          <Alert className="bg-blue-500/10 border-blue-500/50">
            <AlertDescription className="text-blue-300 text-sm">
              <strong>Note:</strong> You need an Instagram Business Account connected to a Facebook Page. 
              Get your Instagram Account ID and Access Token from Facebook Developer Console.
            </AlertDescription>
          </Alert>

          {/* Add Account Button */}
          {!showAddForm && (
            <Button
              onClick={() => setShowAddForm(true)}
              className="w-full bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-700 hover:to-purple-700"
              data-testid="add-account-button"
            >
              <Plus className="w-4 h-4 mr-2" />
              Connect New Instagram Account
            </Button>
          )}

          {/* Add Account Form */}
          {showAddForm && (
            <form onSubmit={handleAddAccount} className="bg-[#0f0f1a] rounded-lg p-4 space-y-4">
              <h3 className="text-white font-semibold mb-2">Connect Instagram Business Account</h3>
              
              <div>
                <label className="text-sm text-gray-400 mb-1 block">Instagram Account ID *</label>
                <Input
                  value={formData.page_id}
                  onChange={(e) => setFormData({ ...formData, page_id: e.target.value })}
                  placeholder="Enter Instagram Account ID"
                  className="bg-[#1a1a2e] border-gray-700 text-white"
                  required
                />
                <p className="text-xs text-gray-500 mt-1">
                  This is your Instagram Business Account ID (numeric)
                </p>
              </div>

              <div>
                <label className="text-sm text-gray-400 mb-1 block">Username (Optional)</label>
                <Input
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  placeholder="@username"
                  className="bg-[#1a1a2e] border-gray-700 text-white"
                />
              </div>

              <div>
                <label className="text-sm text-gray-400 mb-1 block">Access Token *</label>
                <Input
                  type="password"
                  value={formData.access_token}
                  onChange={(e) => setFormData({ ...formData, access_token: e.target.value })}
                  placeholder="Enter Page Access Token"
                  className="bg-[#1a1a2e] border-gray-700 text-white"
                  required
                />
                <p className="text-xs text-gray-500 mt-1">
                  Use the Page Access Token from your connected Facebook Page
                </p>
              </div>

              <div className="flex space-x-2">
                <Button
                  type="submit"
                  className="flex-1 bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-700 hover:to-purple-700"
                >
                  <Check className="w-4 h-4 mr-2" />
                  Connect Account
                </Button>
                <Button
                  type="button"
                  onClick={() => {
                    setShowAddForm(false);
                    setFormData({ page_id: '', username: '', access_token: '' });
                  }}
                  variant="outline"
                  className="bg-transparent border-gray-700 text-gray-400 hover:text-white"
                >
                  <X className="w-4 h-4 mr-2" />
                  Cancel
                </Button>
              </div>
            </form>
          )}

          {/* Accounts List */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white font-semibold">Connected Accounts</h3>
              <Button
                onClick={loadAccounts}
                size="sm"
                variant="outline"
                className="bg-transparent border-gray-700 text-gray-400 hover:text-white"
              >
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>

            {loading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-pink-500 mx-auto"></div>
              </div>
            ) : accounts.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No Instagram accounts connected yet
              </div>
            ) : (
              <div className="space-y-3">
                {accounts.map((account) => (
                  <div
                    key={account.id}
                    className="bg-[#0f0f1a] border border-gray-700 rounded-lg p-4 flex items-center justify-between"
                    data-testid={`instagram-account-${account.page_id}`}
                  >
                    <div className="flex items-center space-x-3 flex-1">
                      <div className="w-12 h-12 bg-gradient-to-br from-pink-600 to-purple-600 rounded-full flex items-center justify-center">
                        <InstagramIcon className="w-6 h-6 text-white" />
                      </div>
                      <div>
                        <h4 className="text-white font-medium">
                          @{account.username || `Account ${account.page_id.substring(0, 8)}...`}
                        </h4>
                        <p className="text-xs text-gray-400">ID: {account.page_id}</p>
                        <p className="text-xs text-gray-500">
                          Connected: {new Date(account.connected_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-4">
                      <div className="px-3 py-1 bg-green-500/10 border border-green-500/30 rounded-full">
                        <span className="text-xs text-green-400">Active</span>
                      </div>
                      <Button
                        onClick={() => handleDeleteAccount(account.id)}
                        size="sm"
                        variant="ghost"
                        className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Setup Instructions */}
          <div className="bg-[#0f0f1a] border border-gray-700 rounded-lg p-4">
            <h4 className="text-white font-semibold mb-2 text-sm">Setup Instructions</h4>
            <ol className="text-xs text-gray-400 space-y-1 list-decimal list-inside">
              <li>Convert your Instagram account to a Business Account</li>
              <li>Connect it to a Facebook Page</li>
              <li>Get your Instagram Account ID from Facebook Graph API Explorer</li>
              <li>Generate a Page Access Token with instagram_basic and instagram_manage_messages permissions</li>
              <li>Configure webhook subscriptions for messages</li>
            </ol>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default InstagramAccountManager;
