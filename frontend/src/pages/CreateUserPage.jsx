import React, { useCallback, useMemo, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import AppShell from '../layouts/AppShell';
import AdminLayout from '../layouts/AdminLayout';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { hasPermission, hasAnyPermission } from '../utils/permissionUtils';
import { buildNavigationItems } from '../utils/navigationConfig';

const DEFAULT_FORM = {
  name: '',
  email: '',
  contactNumber: '',
  country: '',
  empId: '',
  password: 'TempPass1',
  role: 'agent',
  positionId: ''
};

const CreateUserPage = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const [form, setForm] = useState(DEFAULT_FORM);
  const [positions, setPositions] = useState([]);
  const [positionsError, setPositionsError] = useState('');
  const [loadingPositions, setLoadingPositions] = useState(false);
  const [status, setStatus] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const canManageTemplates = useMemo(() => hasPermission(user, 'template:manage'), [user]);
  const canManageIntegrations = useMemo(() => hasPermission(user, 'integration:manage'), [user]);
  const canManagePositions = useMemo(() => hasPermission(user, 'position:manage'), [user]);
  const canViewUserRoster = useMemo(
    () => hasAnyPermission(user, ['position:assign', 'position:manage', 'chat:assign']),
    [user]
  );
  const canInviteUsers = useMemo(() => hasPermission(user, 'user:invite'), [user]);
  const canLoadPositions = useMemo(
    () => hasAnyPermission(user, ['position:assign', 'position:manage']),
    [user]
  );
  const canViewStats = useMemo(() => hasPermission(user, 'stats:view'), [user]);

  const navigationItems = useMemo(
    () =>
      buildNavigationItems({
        canManageTemplates,
        canViewUserRoster,
        canManagePositions,
        canInviteUsers,
        canViewStats,
        canManageIntegrations
      }),
    [
      canManageTemplates,
      canViewUserRoster,
      canManagePositions,
      canInviteUsers,
      canViewStats,
      canManageIntegrations
    ]
  );

  const loadPositions = useCallback(async () => {
    if (!canLoadPositions) {
      setPositions([]);
      return;
    }
    setLoadingPositions(true);
    setPositionsError('');
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('Missing auth token');
      }
      const response = await axios.get(`${API}/positions`, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 20000
      });
      setPositions(response.data || []);
    } catch (err) {
      console.error('Failed to load positions:', err);
      setPositionsError(err.response?.data?.detail || 'Unable to load positions.');
    } finally {
      setLoadingPositions(false);
    }
  }, [canLoadPositions]);

  useEffect(() => {
    loadPositions();
  }, [loadPositions]);

  const handleInputChange = (field) => (event) => {
    const value = event?.target ? event.target.value : event;
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setStatus(null);
    if (!canInviteUsers) {
      return;
    }
    if (!form.name.trim()) {
      setStatus({ type: 'error', message: 'Name is required.' });
      return;
    }
    if (!form.email.trim() && !form.contactNumber.trim()) {
      setStatus({ type: 'error', message: 'Provide at least an email or a contact number.' });
      return;
    }
    if (!form.empId.trim()) {
      setStatus({ type: 'error', message: 'Employee ID is required.' });
      return;
    }
    if (form.password.length < 8) {
      setStatus({ type: 'error', message: 'Password must be at least 8 characters.' });
      return;
    }

    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('Missing auth token');
      }
      const email = form.email.trim();
      const contactNumber = form.contactNumber.trim();
      const country = form.country.trim();
      const empId = form.empId.trim();
      await axios.post(
        `${API}/admin/users`,
        {
          name: form.name.trim(),
          email: email || null,
          contact_number: contactNumber || null,
          country: country || null,
          emp_id: empId,
          password: form.password,
          role: form.role,
          position_id: form.positionId || null
        },
        {
          headers: { Authorization: `Bearer ${token}` },
          timeout: 20000
        }
      );
      setStatus({ type: 'success', message: 'User created successfully.' });
      setForm(DEFAULT_FORM);
      if (canLoadPositions) {
        await loadPositions();
      }
    } catch (err) {
      console.error('User creation failed:', err);
      const detail = err.response?.data?.detail;
      let message = 'Unable to create user.';
      if (typeof detail === 'string') {
        message = detail;
      } else if (Array.isArray(detail)) {
        message = detail
          .map((item) => item?.msg || item?.message || JSON.stringify(item))
          .filter(Boolean)
          .join('; ');
      }
      setStatus({
        type: 'error',
        message
      });
    } finally {
      setSubmitting(false);
    }
  };

  const renderStatus = () => {
    if (!status) return null;
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
    <AppShell user={user} navItems={navigationItems} onLogout={onLogout}>
      <AdminLayout
        title="Create User"
        description="Provision a teammate account directly from the admin workspace."
        actions={
          <Button variant="ghost" onClick={() => navigate('/user-directory')}>
            Back to directory
          </Button>
        }
      >
        {!canInviteUsers ? (
          <div className="rounded-xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface)] p-6 text-sm text-[var(--tg-text-secondary)]">
            You do not have permission to create users.
          </div>
        ) : (
          <form
            onSubmit={handleSubmit}
            className="max-w-2xl rounded-2xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface)] p-6 space-y-6"
          >
            {renderStatus()}
            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="name" className="text-sm text-[var(--tg-text-secondary)]">
                  Full name
                </Label>
                <Input
                  id="name"
                  value={form.name}
                  onChange={handleInputChange('name')}
                  placeholder="Alex Mercer"
                  required
                />
              </div>
              <div>
                <Label htmlFor="email" className="text-sm text-[var(--tg-text-secondary)]">
                  Email (optional if contact number provided)
                </Label>
                <Input
                  id="email"
                  type="email"
                  value={form.email}
                  onChange={handleInputChange('email')}
                  placeholder="agent@ticklegram.com"
                />
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="contactNumber" className="text-sm text-[var(--tg-text-secondary)]">
                  Contact number
                </Label>
                <Input
                  id="contactNumber"
                  value={form.contactNumber}
                  onChange={handleInputChange('contactNumber')}
                  placeholder="+1 415 555 0100"
                />
                <p className="mt-1 text-xs text-[var(--tg-text-muted)]">
                  Required only if email is not provided.
                </p>
              </div>
              <div>
                <Label htmlFor="country" className="text-sm text-[var(--tg-text-secondary)]">
                  Country
                </Label>
                <Input
                  id="country"
                  value={form.country}
                  onChange={handleInputChange('country')}
                  placeholder="United States"
                />
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="role" className="text-sm text-[var(--tg-text-secondary)]">
                  Role
                </Label>
                <select
                  id="role"
                  value={form.role}
                  onChange={handleInputChange('role')}
                  className="w-full h-11 rounded-lg border border-[var(--tg-border-soft)] bg-[var(--tg-surface-muted)] px-3 text-sm"
                >
                  <option value="agent">Agent</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div>
                <Label htmlFor="password" className="text-sm text-[var(--tg-text-secondary)]">
                  Initial password
                </Label>
                <Input
                  id="password"
                  type="text"
                  value={form.password}
                  onChange={handleInputChange('password')}
                  minLength={8}
                  required
                />
                <p className="mt-1 text-xs text-[var(--tg-text-muted)]">
                  Prefilled with <code>TempPass1</code>. Update before sending to the user.
                </p>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="empId" className="text-sm text-[var(--tg-text-secondary)]">
                  Employee ID
                </Label>
                <Input
                  id="empId"
                  value={form.empId}
                  onChange={handleInputChange('empId')}
                  placeholder="EMP-00123"
                  required
                />
                <p className="mt-1 text-xs text-[var(--tg-text-muted)]">
                  Used for directory search and employee record keeping.
                </p>
              </div>
            </div>

            <div>
              <Label htmlFor="position" className="text-sm text-[var(--tg-text-secondary)]">
                Position
              </Label>
              {canLoadPositions ? (
                <>
                  <select
                    id="position"
                    value={form.positionId}
                    onChange={handleInputChange('positionId')}
                    className="w-full h-11 rounded-lg border border-[var(--tg-border-soft)] bg-[var(--tg-surface-muted)] px-3 text-sm"
                  >
                    <option value="">Auto-assign default for role</option>
                    {positions.map((position) => (
                      <option key={position.id} value={position.id}>
                        {position.name}
                      </option>
                    ))}
                  </select>
                  {loadingPositions && (
                    <p className="mt-1 text-xs text-[var(--tg-text-muted)]">Loading positions…</p>
                  )}
                  {positionsError && (
                    <p className="mt-1 text-xs text-red-300">{positionsError}</p>
                  )}
                </>
              ) : (
                <div className="mt-2 text-xs text-[var(--tg-text-muted)]">
                  Default {form.role === 'admin' ? 'Admin' : 'Agent'} position will be assigned automatically.
                </div>
              )}
            </div>

            <div className="flex flex-wrap gap-3">
              <Button
                type="submit"
                disabled={submitting}
                className="bg-gradient-to-r from-purple-500 via-pink-500 to-orange-400 text-white px-6"
              >
                {submitting ? 'Creating user...' : 'Create user'}
              </Button>
              <Button
                type="button"
                variant="ghost"
                disabled={submitting}
                onClick={() => setForm(DEFAULT_FORM)}
              >
                Reset form
              </Button>
            </div>
          </form>
        )}
      </AdminLayout>
    </AppShell>
  );
};

export default CreateUserPage;
