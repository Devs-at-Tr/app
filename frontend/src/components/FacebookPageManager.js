import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Switch } from './ui/switch';
import { Plus, Trash2, RefreshCw, Check, X } from 'lucide-react';
import { Alert, AlertDescription } from './ui/alert';

const FacebookIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
  </svg>
);

const FacebookPageManager = ({ onClose }) => {
  const [pages, setPages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [formData, setFormData] = useState({
    page_id: '',
    page_name: '',
    access_token: ''
  });

  useEffect(() => {
    loadPages();
  }, []);

  const loadPages = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API}/facebook/pages`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPages(response.data);
      setError('');
    } catch (error) {
      console.error('Error loading Facebook pages:', error);
      setError('Failed to load Facebook pages');
    } finally {
      setLoading(false);
    }
  };

  const handleAddPage = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!formData.page_id || !formData.access_token) {
      setError('Page ID and Access Token are required');
      return;
    }

    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API}/facebook/pages`,
        formData,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setSuccess('Facebook page connected successfully!');
      setFormData({ page_id: '', page_name: '', access_token: '' });
      setShowAddForm(false);
      loadPages();
    } catch (error) {
      console.error('Error adding Facebook page:', error);
      setError(error.response?.data?.detail || 'Failed to connect Facebook page');
    }
  };

  const handleToggleActive = async (pageId, currentStatus, pageName) => {
    const nextState = !currentStatus;
    const actionLabel = nextState ? 'activate' : 'deactivate';
    const confirmed = window.confirm(
      `Are you sure you want to ${actionLabel} "${pageName || pageId}"?`
    );
    if (!confirmed) return;

    try {
      const token = localStorage.getItem('token');
      await axios.patch(
        `${API}/facebook/pages/${pageId}`,
        { is_active: nextState },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setSuccess(`Page ${pageName || pageId} ${nextState ? 'activated' : 'deactivated'}.`);
      loadPages();
    } catch (error) {
      console.error('Error toggling page status:', error);
      setError('Failed to update page status');
    }
  };

  const handleDeletePage = async (pageId) => {
    if (!window.confirm('Are you sure you want to delete this Facebook page?')) {
      return;
    }

    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API}/facebook/pages/${pageId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSuccess('Facebook page deleted successfully!');
      loadPages();
    } catch (error) {
      console.error('Error deleting Facebook page:', error);
      setError('Failed to delete Facebook page');
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" data-testid="facebook-page-manager">
      <Card className="bg-[#1a1a2e] border-gray-800 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <CardHeader className="border-b border-gray-800">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-blue-700 rounded-full flex items-center justify-center">
                <FacebookIcon className="w-5 h-5 text-white" />
              </div>
              <CardTitle className="text-white text-xl">Manage Facebook Pages</CardTitle>
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

          {/* Add Page Button */}
          {!showAddForm && (
            <Button
              onClick={() => setShowAddForm(true)}
              className="w-full bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800"
              data-testid="add-page-button"
            >
              <Plus className="w-4 h-4 mr-2" />
              Connect New Facebook Page
            </Button>
          )}

          {/* Add Page Form */}
          {showAddForm && (
            <form onSubmit={handleAddPage} className="bg-[#0f0f1a] rounded-lg p-4 space-y-4">
              <h3 className="text-white font-semibold mb-2">Connect Facebook Page</h3>
              
              <div>
                <label className="text-sm text-gray-400 mb-1 block">Page ID *</label>
                <Input
                  value={formData.page_id}
                  onChange={(e) => setFormData({ ...formData, page_id: e.target.value })}
                  placeholder="Enter Facebook Page ID"
                  className="bg-[#1a1a2e] border-gray-700 text-white"
                  required
                />
              </div>

              <div>
                <label className="text-sm text-gray-400 mb-1 block">Page Name (Optional)</label>
                <Input
                  value={formData.page_name}
                  onChange={(e) => setFormData({ ...formData, page_name: e.target.value })}
                  placeholder="Enter Page Name"
                  className="bg-[#1a1a2e] border-gray-700 text-white"
                />
              </div>

              <div>
                <label className="text-sm text-gray-400 mb-1 block">Page Access Token *</label>
                <Input
                  type="password"
                  value={formData.access_token}
                  onChange={(e) => setFormData({ ...formData, access_token: e.target.value })}
                  placeholder="Enter Page Access Token"
                  className="bg-[#1a1a2e] border-gray-700 text-white"
                  required
                />
              </div>

              <div className="flex space-x-2">
                <Button
                  type="submit"
                  className="flex-1 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800"
                >
                  <Check className="w-4 h-4 mr-2" />
                  Connect Page
                </Button>
                <Button
                  type="button"
                  onClick={() => {
                    setShowAddForm(false);
                    setFormData({ page_id: '', page_name: '', access_token: '' });
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

          {/* Pages List */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white font-semibold">Connected Pages</h3>
              <Button
                onClick={loadPages}
                size="sm"
                variant="outline"
                className="bg-transparent border-gray-700 text-gray-400 hover:text-white"
              >
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>

            {loading ? (
              <div className="text-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500 mx-auto"></div>
              </div>
            ) : pages.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No Facebook pages connected yet
              </div>
            ) : (
              <div className="space-y-3">
                {pages.map((page) => (
                  <div
                    key={page.id}
                    className="bg-[#0f0f1a] border border-gray-700 rounded-lg p-4 flex items-center justify-between"
                    data-testid={`facebook-page-${page.page_id}`}
                  >
                    <div className="flex items-center space-x-3 flex-1">
                      <FacebookIcon className="w-8 h-8 text-blue-500" />
                      <div>
                        <h4 className="text-white font-medium">
                          {page.page_name || `Page ${page.page_id.substring(0, 8)}...`}
                        </h4>
                        <p className="text-xs text-gray-400">ID: {page.page_id}</p>
                        <p className="text-xs text-gray-500">
                          Connected: {new Date(page.connected_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center space-x-4">
                      <div className="flex items-center space-x-2">
                        <span className="text-sm text-gray-400">Active</span>
                        <Switch
                          checked={page.is_active}
                          onCheckedChange={() => handleToggleActive(page.page_id, page.is_active, page.page_name)}
                          className="data-[state=checked]:bg-blue-600"
                        />
                      </div>
                      <Button
                        onClick={() => handleDeletePage(page.page_id)}
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
        </CardContent>
      </Card>
    </div>
  );
};

export default FacebookPageManager;
