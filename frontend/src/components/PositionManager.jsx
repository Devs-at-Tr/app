import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { API } from '../App';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from './ui/dialog';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { Checkbox } from './ui/checkbox';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import { Label } from './ui/label';
import { cn } from '@/lib/utils';

const DEFAULT_FORM = {
  id: null,
  name: '',
  slug: '',
  description: '',
  permissions: [],
  is_system: false,
};

const slugify = (value = '') =>
  value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');

const PositionManager = ({ open, onClose }) => {
  const [positions, setPositions] = useState([]);
  const [permissionOptions, setPermissionOptions] = useState([]);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const token = useMemo(() => localStorage.getItem('token'), []);
  const authHeaders = useMemo(() => ({ Authorization: `Bearer ${token}` }), [token]);

  const isEditing = Boolean(form.id);

  const resetState = () => {
    setForm(DEFAULT_FORM);
    setError('');
    setSuccess('');
  };

  const handleClose = () => {
    resetState();
    onClose?.();
  };

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const [positionsRes, permissionsRes] = await Promise.all([
        axios.get(`${API}/positions`, { headers: authHeaders }),
        axios.get(`${API}/permissions/codes`, { headers: authHeaders }),
      ]);
      setPositions(positionsRes.data || []);
      setPermissionOptions(permissionsRes.data || []);
      if (positionsRes.data?.length && !form.id) {
        setForm({
          ...positionsRes.data[0],
          description: positionsRes.data[0].description || '',
          permissions: positionsRes.data[0].permissions || [],
        });
      }
    } catch (fetchError) {
      console.error('Failed to load positions:', fetchError);
      setError(fetchError.response?.data?.detail || fetchError.message || 'Unable to load positions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchData();
    } else {
      resetState();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const handleSelectPosition = (position) => {
    setForm({
      id: position.id,
      name: position.name,
      slug: position.slug,
      description: position.description || '',
      permissions: position.permissions || [],
      is_system: position.is_system,
    });
    setSuccess('');
    setError('');
  };

  const handleNewPosition = () => {
    resetState();
  };

  const handleInputChange = (field, value) => {
    setForm((prev) => {
      const next = { ...prev, [field]: value };
      if (field === 'name' && !isEditing) {
        next.slug = slugify(value);
      }
      return next;
    });
  };

  const handleTogglePermission = (code) => {
    setForm((prev) => {
      const permissions = new Set(prev.permissions || []);
      if (permissions.has(code)) {
        permissions.delete(code);
      } else {
        permissions.add(code);
      }
      return { ...prev, permissions: Array.from(permissions) };
    });
  };

  const handleSave = async () => {
    setSaving(true);
    setError('');
    setSuccess('');

    const payload = {
      name: form.name.trim(),
      description: form.description?.trim() || null,
      permissions: form.permissions,
    };

    if (!payload.name) {
      setSaving(false);
      setError('Position name is required.');
      return;
    }

    try {
      if (isEditing) {
        await axios.put(`${API}/positions/${form.id}`, payload, { headers: authHeaders });
      } else {
        await axios.post(
          `${API}/positions`,
          {
            ...payload,
            slug: form.slug.trim() || slugify(form.name),
            is_system: false,
          },
          { headers: authHeaders }
        );
      }
      setSuccess(isEditing ? 'Position updated successfully.' : 'Position created successfully.');
      await fetchData();
    } catch (saveError) {
      console.error('Failed to save position:', saveError);
      setError(saveError.response?.data?.detail || saveError.message || 'Unable to save position');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!isEditing || form.is_system) {
      return;
    }
    const confirmDelete = window.confirm(`Delete ${form.name}? This cannot be undone.`);
    if (!confirmDelete) {
      return;
    }
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await axios.delete(`${API}/positions/${form.id}`, { headers: authHeaders });
      setSuccess('Position deleted.');
      await fetchData();
      resetState();
    } catch (deleteError) {
      console.error('Failed to delete position:', deleteError);
      setError(deleteError.response?.data?.detail || deleteError.message || 'Unable to delete position');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(value) => !value && handleClose()}>
      <DialogContent className="max-w-6xl bg-[#1a1a2e] text-white border border-gray-800">
        <DialogHeader>
          <DialogTitle>Position & Permission Manager</DialogTitle>
          <DialogDescription className="text-gray-400">
            Create roles, assign permissions, and keep your agent experience locked down.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-400">Positions</h3>
              <Button size="sm" variant="outline" onClick={handleNewPosition}>
                + New
              </Button>
            </div>
            <div className="rounded-xl border border-gray-800 bg-[#0f0f1a]">
              <ScrollArea className="h-[420px]">
                <div className="divide-y divide-gray-800">
                  {loading && (
                    <div className="p-4 text-center text-gray-400 text-sm">Loading positions…</div>
                  )}
                  {!loading && positions.length === 0 && (
                    <div className="p-4 text-center text-gray-500 text-sm">No positions yet.</div>
                  )}
                  {positions.map((position) => {
                    const isActive = form.id === position.id;
                    return (
                      <button
                        key={position.id}
                        onClick={() => handleSelectPosition(position)}
                        className={cn(
                          'w-full text-left p-4 transition-colors focus:outline-none',
                          isActive ? 'bg-purple-600/20 border-l-2 border-purple-500' : 'hover:bg-white/5'
                        )}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="font-semibold text-white">{position.name}</p>
                            <p className="text-xs uppercase tracking-wide text-gray-500">/{position.slug}</p>
                          </div>
                          {position.is_system ? (
                            <Badge className="bg-gray-700 text-xs">System</Badge>
                          ) : (
                            <Badge variant="outline" className="text-xs border-gray-600 text-gray-300">
                              Custom
                            </Badge>
                          )}
                        </div>
                        <p className="mt-2 text-sm text-gray-400 line-clamp-2">
                          {position.description || 'No description provided.'}
                        </p>
                        <div className="mt-3 flex flex-wrap gap-1">
                          {(position.permissions || []).slice(0, 6).map((permission) => (
                            <span
                              key={permission}
                              className="bg-purple-500/10 text-purple-200 text-[11px] px-2 py-0.5 rounded-full"
                            >
                              {permission}
                            </span>
                          ))}
                          {position.permissions?.length > 6 && (
                            <span className="text-[11px] text-gray-500">
                              +{position.permissions.length - 6} more
                            </span>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </ScrollArea>
            </div>
          </section>

          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400">{isEditing ? 'Edit Position' : 'Create Position'}</p>
                <h3 className="text-lg font-semibold">{isEditing ? form.name || 'Untitled' : 'New Position'}</h3>
              </div>
              <div className="flex items-center gap-2">
                {isEditing && !form.is_system && (
                  <Button variant="ghost" size="sm" onClick={handleDelete} disabled={saving}>
                    Delete
                  </Button>
                )}
                <Button onClick={handleSave} disabled={saving}>
                  {saving ? 'Saving...' : 'Save'}
                </Button>
              </div>
            </div>

            {error && (
              <div className="rounded-lg border border-red-500/50 bg-red-500/10 p-3 text-sm text-red-300">{error}</div>
            )}
            {success && (
              <div className="rounded-lg border border-emerald-500/50 bg-emerald-500/10 p-3 text-sm text-emerald-300">
                {success}
              </div>
            )}

            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label className="text-gray-300">Position name</Label>
                  <Input
                    value={form.name}
                    onChange={(event) => handleInputChange('name', event.target.value)}
                    placeholder="e.g. Supervisor"
                    className="bg-[#0f0f1a] border-gray-700 mt-1"
                  />
                </div>
                <div>
                  <Label className="text-gray-300">Slug</Label>
                  <Input
                    value={form.slug}
                    onChange={(event) => handleInputChange('slug', slugify(event.target.value))}
                    placeholder="supervisor"
                    className="bg-[#0f0f1a] border-gray-700 mt-1"
                    disabled={isEditing}
                  />
                </div>
              </div>

              <div>
                <Label className="text-gray-300">Description</Label>
                <Textarea
                  value={form.description}
                  onChange={(event) => handleInputChange('description', event.target.value)}
                  placeholder="Describe what this position should do."
                  className="bg-[#0f0f1a] border-gray-700 mt-1 min-h-[90px]"
                />
              </div>

              <div>
                <Label className="text-gray-300 mb-2 block">Permissions</Label>
                <div className="rounded-xl border border-gray-800 bg-[#0f0f1a] p-4 max-h-[280px] overflow-y-auto space-y-3">
                  {permissionOptions.map((permission) => {
                    const checked = form.permissions?.includes(permission.code);
                    return (
                      <label
                        key={permission.code}
                        className="flex items-start gap-3 rounded-lg border border-transparent px-2 py-1.5 hover:border-gray-700"
                      >
                        <Checkbox
                          checked={checked}
                          onCheckedChange={() => handleTogglePermission(permission.code)}
                          className="mt-1"
                        />
                        <div>
                          <p className="text-sm font-semibold text-white">{permission.label}</p>
                          <p className="text-xs text-gray-400">{permission.description}</p>
                          <p className="text-[11px] text-gray-500 mt-1 uppercase tracking-wide">{permission.code}</p>
                        </div>
                      </label>
                    );
                  })}
                  {!permissionOptions.length && (
                    <p className="text-sm text-gray-500 text-center">No permission definitions found.</p>
                  )}
                </div>
              </div>
            </div>
          </section>
        </div>

        <div className="flex items-center justify-end gap-3">
          <Button variant="ghost" onClick={handleClose}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default PositionManager;
