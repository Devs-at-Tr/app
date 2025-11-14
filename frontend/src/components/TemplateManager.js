import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from './ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from './ui/table';
import { Badge } from './ui/badge';
import { FileText, Plus, Edit, Trash2, SendHorizonal, RefreshCw, CheckCircle } from 'lucide-react';
import { useToast } from '../hooks/use-toast';

const CATEGORIES = [
  { value: 'greeting', label: 'Greeting' },
  { value: 'utility', label: 'Utility' },
  { value: 'marketing', label: 'Marketing' },
  { value: 'support', label: 'Support' },
  { value: 'closing', label: 'Closing' }
];

const PLATFORMS = [
  { value: 'INSTAGRAM', label: 'Instagram' },
  { value: 'FACEBOOK', label: 'Facebook' }
];

const TemplateManager = () => {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [filterPlatform, setFilterPlatform] = useState('all');
  const [filterCategory, setFilterCategory] = useState('all');
  const [checkingStatus, setCheckingStatus] = useState({});
  const { toast } = useToast();

  const [formData, setFormData] = useState({
    name: '',
    content: '',
    category: 'greeting',
    platform: 'INSTAGRAM'
  });

  useEffect(() => {
    loadTemplates();
  }, [filterPlatform, filterCategory]);

  const loadTemplates = async () => {
    try {
      const token = localStorage.getItem('token');
      const params = {};
      if (filterPlatform !== 'all') params.platform = filterPlatform;
      if (filterCategory !== 'all') params.category = filterCategory;

      const response = await axios.get(`${API}/templates`, {
        headers: { Authorization: `Bearer ${token}` },
        params
      });
      setTemplates(response.data);
    } catch (error) {
      console.error('Error loading templates:', error);
      toast({
        title: 'Error',
        description: 'Failed to load templates',
        variant: 'destructive'
      });
    } finally {
      setLoading(false);
    }
  };

  // Submit template to Meta for approval
  const submitToMeta = async (templateId) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API}/templates/${templateId}/submit-to-meta`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast({
        title: 'Success',
        description: 'Template submitted to Meta for approval'
      });
      loadTemplates();
    } catch (error) {
      console.error('Error submitting to Meta:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to submit template to Meta',
        variant: 'destructive'
      });
    }
  };

  // Check Meta approval status
  const checkMetaStatus = async (templateId) => {
    try {
      setCheckingStatus(prev => ({ ...prev, [templateId]: true }));
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `${API}/templates/${templateId}/meta-status`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast({
        title: 'Status Update',
        description: `Template status: ${response.data.status}`
      });
      loadTemplates();
    } catch (error) {
      console.error('Error checking status:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to check template status',
        variant: 'destructive'
      });
    } finally {
      setCheckingStatus(prev => ({ ...prev, [templateId]: false }));
    }
  };

  const handleOpenDialog = (template = null) => {
    if (template) {
      setEditingTemplate(template);
      setFormData({
        name: template.name,
        content: template.content,
        category: template.category,
        platform: template.platform,
        is_meta_approved: template.is_meta_approved,
        meta_template_id: template.meta_template_id || ''
      });
    } else {
      setEditingTemplate(null);
      setFormData({
        name: '',
        content: '',
        category: 'greeting',
        platform: 'INSTAGRAM',
        is_meta_approved: false,
        meta_template_id: ''
      });
    }
    setShowDialog(true);
  };

  const handleCloseDialog = () => {
    setShowDialog(false);
    setEditingTemplate(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      // Note: We no longer require a Meta template ID since it will be assigned after approval
      const token = localStorage.getItem('token');
      const config = { headers: { Authorization: `Bearer ${token}` } };
      const payload = {
        ...formData,
        meta_template_id: formData.meta_template_id?.trim() || null,
        // Templates should start as not approved and be submitted to Meta
        is_meta_approved: false
      };

      if (editingTemplate) {
        // Update existing template
        await axios.put(`${API}/templates/${editingTemplate.id}`, payload, config);
        toast({
          title: 'Success',
          description: 'Template updated successfully'
        });
      } else {
        // Create new template
        await axios.post(`${API}/templates`, payload, config);
        toast({
          title: 'Success',
          description: 'Template created successfully'
        });
      }

      handleCloseDialog();
      loadTemplates();
    } catch (error) {
      console.error('Error saving template:', error);
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to save template',
        variant: 'destructive'
      });
    }
  };

  const handleDelete = async (templateId) => {
    if (!window.confirm('Are you sure you want to delete this template?')) {
      return;
    }

    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API}/templates/${templateId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      toast({
        title: 'Success',
        description: 'Template deleted successfully'
      });
      loadTemplates();
    } catch (error) {
      console.error('Error deleting template:', error);
      toast({
        title: 'Error',
        description: 'Failed to delete template',
        variant: 'destructive'
      });
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <FileText className="w-6 h-6" />
            Message Templates
          </h2>
          <p className="text-gray-400 mt-1">Manage pre-approved message templates</p>
        </div>
        <Button 
          onClick={() => handleOpenDialog()}
          className="bg-purple-600 hover:bg-purple-700"
        >
          <Plus className="w-4 h-4 mr-2" />
          New Template
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="w-48">
          <Select value={filterPlatform} onValueChange={setFilterPlatform}>
            <SelectTrigger className="bg-[#1a1a2e] border-gray-700">
              <SelectValue placeholder="All Platforms" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Platforms</SelectItem>
              {PLATFORMS.map(p => (
                <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="w-48">
          <Select value={filterCategory} onValueChange={setFilterCategory}>
            <SelectTrigger className="bg-[#1a1a2e] border-gray-700">
              <SelectValue placeholder="All Categories" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              {CATEGORIES.map(c => (
                <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Templates Table */}
      <div className="border border-gray-700 rounded-lg overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-[#1a1a2e] border-gray-700 hover:bg-[#1a1a2e]">
              <TableHead className="text-gray-300">Name</TableHead>
              <TableHead className="text-gray-300">Content</TableHead>
              <TableHead className="text-gray-300">Category</TableHead>
              <TableHead className="text-gray-300">Platform</TableHead>
              <TableHead className="text-gray-300">Status</TableHead>
              <TableHead className="text-gray-300 text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-gray-400 py-8">
                  Loading templates...
                </TableCell>
              </TableRow>
            ) : templates.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-gray-400 py-8">
                  No templates found. Create your first template!
                </TableCell>
              </TableRow>
            ) : (
              templates.map((template) => (
                <TableRow key={template.id} className="border-gray-700">
                  <TableCell className="font-medium text-white">
                    {template.name}
                  </TableCell>
                  <TableCell className="text-gray-300 max-w-md truncate">
                    {template.content}
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="template-pill">
                      {template.category}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant="outline" className="template-pill">
                      {template.platform}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {template.is_meta_approved ? (
                      <Badge className="bg-green-600 text-white">
                        <span className="w-2 h-2 bg-green-400 rounded-full mr-1" />
                        Approved
                      </Badge>
                    ) : template.meta_submission_status === 'pending' ? (
                      <Badge className="bg-yellow-600 text-white">
                        <span className="w-2 h-2 bg-yellow-400 rounded-full mr-1" />
                        Pending
                      </Badge>
                    ) : template.meta_submission_status === 'rejected' ? (
                      <Badge className="bg-red-600 text-white">
                        <span className="w-2 h-2 bg-red-400 rounded-full mr-1" />
                        Rejected
                      </Badge>
                    ) : (
                      <Badge className="bg-gray-600 text-white">
                        <span className="w-2 h-2 bg-gray-400 rounded-full mr-1" />
                        Not Submitted
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      {!template.is_meta_approved && (
                        <>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => submitToMeta(template.id)}
                            disabled={template.meta_submission_status === 'pending'}
                            title={template.meta_submission_status === 'pending' ? 'Pending Approval' : 'Submit for Meta Approval'}
                          >
                            <SendHorizonal className="w-4 h-4" />
                          </Button>
                          {template.meta_submission_status && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => checkMetaStatus(template.id)}
                              disabled={checkingStatus[template.id]}
                              title="Check Meta Approval Status"
                            >
                              <RefreshCw className={`w-4 h-4 ${checkingStatus[template.id] ? 'animate-spin' : ''}`} />
                            </Button>
                          )}
                        </>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleOpenDialog(template)}
                        title="Edit Template"
                      >
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(template.id)}
                        className="text-red-400 hover:text-red-300"
                        title="Delete Template"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Create/Edit Dialog */}
      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="bg-[#1a1a2e] border-gray-700 text-white sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>
              {editingTemplate ? 'Edit Template' : 'Create New Template'}
            </DialogTitle>
            <DialogDescription className="text-gray-400">
              {editingTemplate 
                ? 'Update the template details below.' 
                : 'Fill in the details to create a new message template.'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="text-sm text-gray-300 block mb-2">Template Name</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., Welcome Message"
                required
                className="bg-[#0f0f1a] border-gray-700"
              />
            </div>

            <div>
              <label className="text-sm text-gray-300 block mb-2">
                Message Content 
                <span className="text-gray-500 ml-2">(Use {'{username}'}, {'{platform}'}, {'{order_id}'} for variables)</span>
              </label>
              <Textarea
                value={formData.content}
                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                placeholder="e.g., Hi {username}! Welcome to our service..."
                required
                rows={4}
                className="bg-[#0f0f1a] border-gray-700"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-gray-300 block mb-2">Category</label>
                <Select 
                  value={formData.category} 
                  onValueChange={(value) => setFormData({ ...formData, category: value })}
                >
                  <SelectTrigger className="bg-[#0f0f1a] border-gray-700">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map(c => (
                      <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="text-sm text-gray-300 block mb-2">Platform</label>
                <Select 
                  value={formData.platform} 
                  onValueChange={(value) => setFormData({ ...formData, platform: value })}
                >
                  <SelectTrigger className="bg-[#0f0f1a] border-gray-700">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PLATFORMS.map(p => (
                      <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="meta_approved"
                  checked={formData.is_meta_approved}
                  onChange={(e) => setFormData({ ...formData, is_meta_approved: e.target.checked })}
                  className="w-4 h-4"
                />
                <label htmlFor="meta_approved" className="text-sm text-gray-300">
                  Mark as Meta-approved (Utility)
                </label>
              </div>
              {formData.is_meta_approved && (
                <Input
                  value={formData.meta_template_id}
                  onChange={(e) => setFormData({ ...formData, meta_template_id: e.target.value })}
                  placeholder="Meta Template ID (optional)"
                  className="bg-[#0f0f1a] border-gray-700"
                />
              )}
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={handleCloseDialog}>
                Cancel
              </Button>
              <Button type="submit" className="bg-purple-600 hover:bg-purple-700">
                {editingTemplate ? 'Update Template' : 'Create Template'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TemplateManager;
