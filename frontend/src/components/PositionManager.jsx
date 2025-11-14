import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { API } from '../App';
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

const PositionManager = () => {
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
      if ((positionsRes.data || []).length && !form.id) {
        const next = positionsRes.data[0];
        setForm({
          id: next.id,
          name: next.name,
          slug: next.slug,
          description: next.description || '',
          permissions: next.permissions || [],
          is_system: next.is_system,
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
    fetchData();
  }, []);

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
    try {
      if (isEditing) {
        await axios.put(
          `${API}/positions/${form.id}`,
          {
            name: form.name,
            slug: form.slug,
            description: form.description,
            permissions: form.permissions,
          },
          { headers: authHeaders }
        );
      } else {
        await axios.post(
          `${API}/positions`,
          {
            name: form.name,
            slug: form.slug,
            description: form.description,
            permissions: form.permissions,
          },
          { headers: authHeaders }
        );
      }
      setSuccess('Position saved successfully.');
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
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await axios.delete(`${API}/positions/${form.id}`, { headers: authHeaders });
      resetState();
      await fetchData();
    } catch (deleteError) {
      console.error('Failed to delete position:', deleteError);
      setError(deleteError.response?.data?.detail || deleteError.message || 'Unable to delete');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm text-gray-400">Role & permission directory</p>
        <h2 className="text-2xl font-semibold text-white">Position Manager</h2>
        <p className="text-sm text-gray-500 mt-1">
          Define roles for your team, control permissions, and keep assignments tidy.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[360px_1fr]">
        <section className="space-y-4 rounded-2xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface)] p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">All Positions</p>
              <h3 className="text-lg font-semibold text-white">Roles & permissions</h3>
            </div>
            <Button variant="outline" size="sm" onClick={handleNewPosition}>
              New Position
            </Button>
          </div>

          {loading ? (
            <div className="rounded-2xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface-muted)] p-6 text-center text-sm text-[var(--tg-text-muted)]">
              Loading positions...
            </div>
          ) : (
            <ScrollArea className="h-[420px] rounded-2xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface)] p-3">
              <div className="space-y-2">
                {positions.map((position) => {
                  const isSelected = form.id === position.id;
                  return (
                    <button
                      key={position.id}
                      type="button"
                      onClick={() => handleSelectPosition(position)}
                        className={cn(
                          'w-full rounded-2xl border px-4 py-3 text-left transition-colors',
                          isSelected
                            ? 'border-purple-500 bg-purple-500/10'
                            : 'border-[var(--tg-border-soft)] bg-[var(--tg-surface-muted)] hover:border-[var(--tg-accent-soft)]'
                        )}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-base font-semibold text-white">{position.name}</p>
                          <p className="text-xs text-gray-500">{position.slug}</p>
                        </div>
                        {position.is_system && <Badge className="position-system-badge">System</Badge>}
                      </div>
                      <p className="position-description text-sm mt-2 line-clamp-2">
                        {position.description || 'No description provided.'}
                      </p>
                      <div className="mt-3 flex flex-wrap gap-1">
                        {(position.permissions || []).slice(0, 6).map((permission) => (
                          <span
                            key={permission}
                            className="position-permission-pill text-[11px] px-2 py-0.5 rounded-full"
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
                {!positions.length && (
                  <div className="rounded-xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface-muted)] p-4 text-center text-sm text-[var(--tg-text-muted)]">
                    No positions have been created yet.
                  </div>
                )}
              </div>
            </ScrollArea>
          )}
        </section>

        <section className="space-y-4 rounded-2xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface)] p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">{isEditing ? 'Edit Position' : 'Create Position'}</p>
              <h3 className="text-lg font-semibold text-white">{isEditing ? form.name || 'Untitled' : 'New Position'}</h3>
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
                  <Label className="text-[var(--tg-text-secondary)]">Position name</Label>
                  <Input
                    value={form.name}
                    onChange={(event) => handleInputChange('name', event.target.value)}
                    placeholder="e.g. Supervisor"
                    className="bg-[var(--tg-surface-muted)] border-[var(--tg-border-soft)] mt-1"
                  />
                </div>
                <div>
                  <Label className="text-[var(--tg-text-secondary)]">Slug</Label>
                  <Input
                    value={form.slug}
                    onChange={(event) => handleInputChange('slug', slugify(event.target.value))}
                    placeholder="supervisor"
                    className="bg-[var(--tg-surface-muted)] border-[var(--tg-border-soft)] mt-1"
                    disabled={isEditing}
                  />
                </div>
              </div>

              <div>
                <Label className="text-[var(--tg-text-secondary)]">Description</Label>
                <Textarea
                  value={form.description}
                  onChange={(event) => handleInputChange('description', event.target.value)}
                  placeholder="Describe what this position should do."
                  className="bg-[var(--tg-surface-muted)] border-[var(--tg-border-soft)] mt-1 min-h-[90px]"
                />
              </div>

              <div>
                <Label className="text-[var(--tg-text-secondary)] mb-2 block">Permissions</Label>
                <div className="rounded-xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface-muted)] p-4 max-h-[280px] overflow-y-auto space-y-3">
                  {permissionOptions.map((permission) => {
                    const checked = form.permissions?.includes(permission.code);
                    return (
                      <label
                        key={permission.code}
                        className="flex items-start gap-3 rounded-lg border border-transparent px-2 py-1.5 hover:border-[var(--tg-border-soft)]"
                      >
                        <Checkbox
                          checked={checked}
                          onCheckedChange={() => handleTogglePermission(permission.code)}
                          className="mt-1"
                        />
                        <div>
                          <p className="text-sm font-semibold text-[var(--tg-text-primary)]">{permission.label}</p>
                          <p className="text-xs text-[var(--tg-text-muted)]">{permission.description}</p>
                          <p className="text-[11px] text-[var(--tg-text-muted)] mt-1 uppercase tracking-wide">{permission.code}</p>
                        </div>
                      </label>
                    );
                  })}
                  {!permissionOptions.length && (
                    <p className="text-sm text-[var(--tg-text-muted)] text-center">No permission definitions found.</p>
                  )}
                </div>
              </div>
            </div>
          </section>
      </div>
    </div>
  );
};

export default PositionManager;
