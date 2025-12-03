import React, { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import AppShell from '../layouts/AppShell';
import { API } from '../App';
import { buildNavigationItems } from '../utils/navigationConfig';
import { hasPermission, hasAnyPermission } from '../utils/permissionUtils';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { ShieldCheck, Phone, Mail, MessageCircle, Loader2, Eye, EyeOff } from 'lucide-react';

const InfoRow = ({ label, value, icon: Icon }) => (
  <div className="flex items-center gap-3 rounded-xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface-muted)] px-3 py-3">
    <div className="w-9 h-9 rounded-lg bg-[var(--tg-accent-soft)] text-[var(--tg-text-primary)] flex items-center justify-center">
      <Icon className="w-4 h-4" />
    </div>
    <div className="flex-1 min-w-0">
      <p className="text-xs uppercase tracking-wide text-[var(--tg-text-muted)]">{label}</p>
      <p className="text-sm font-semibold text-[var(--tg-text-primary)] truncate">{value || '—'}</p>
    </div>
  </div>
);

const ProfilePage = ({ user, onLogout }) => {
  const [assignedChats, setAssignedChats] = useState(0);
  const [loadingRoster, setLoadingRoster] = useState(false);
  const [status, setStatus] = useState(null);
  const [resetting, setResetting] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false
  });
  const [profile, setProfile] = useState({
    name: user?.name || '',
    email: user?.email || '',
    contact_number: user?.contact_number || ''
  });
  const [isDirty, setIsDirty] = useState(false);
  const [passwords, setPasswords] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });

  const canManageTemplates = useMemo(() => hasPermission(user, 'template:manage'), [user]);
  const canManageIntegrations = useMemo(() => hasPermission(user, 'integration:manage'), [user]);
  const canManagePositions = useMemo(() => hasPermission(user, 'position:manage'), [user]);
  const canViewUserRoster = useMemo(
    () => hasAnyPermission(user, ['position:assign', 'position:manage', 'chat:assign']),
    [user]
  );
  const canInviteUsers = useMemo(() => hasPermission(user, 'user:invite'), [user]);
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

  const loadRosterEntry = useCallback(async () => {
    if (!user?.id || !canViewUserRoster) {
      setAssignedChats(0);
      setLoadingRoster(false);
      return;
    }
    setLoadingRoster(true);
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('Missing auth token');
      }
      const response = await axios.get(`${API}/users/roster`, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 20000
      });
      const me = (response.data || []).find((u) => u.id === user.id);
      if (me) {
        setAssignedChats(me.assigned_chat_count || 0);
      }
    } catch (err) {
      console.error('Failed to load roster entry', err);
    } finally {
      setLoadingRoster(false);
    }
  }, [canViewUserRoster, user]);

  useEffect(() => {
    loadRosterEntry();
  }, [loadRosterEntry]);

  useEffect(() => {
    const initial = {
      name: user?.name || '',
      email: user?.email || '',
      contact_number: user?.contact_number || ''
    };
    setIsDirty(
      profile.name.trim() !== initial.name ||
      (profile.email || '').trim() !== initial.email ||
      (profile.contact_number || '').trim() !== initial.contact_number
    );
  }, [profile, user]);

  const handlePasswordChange = async (event) => {
    event.preventDefault();
    setStatus(null);
    if (!passwords.newPassword || passwords.newPassword.length < 8) {
      setStatus({ type: 'error', message: 'New password must be at least 8 characters.' });
      return;
    }
    if (passwords.newPassword !== passwords.confirmPassword) {
      setStatus({ type: 'error', message: 'New password and confirmation do not match.' });
      return;
    }
    setResetting(true);
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('Missing auth token');
      }
      await axios.post(
        `${API}/auth/change-password`,
        {
          current_password: passwords.currentPassword,
          new_password: passwords.newPassword
        },
        { headers: { Authorization: `Bearer ${token}` }, timeout: 20000 }
      );
      setStatus({ type: 'success', message: 'Password updated successfully.' });
      setPasswords({ currentPassword: '', newPassword: '', confirmPassword: '' });
    } catch (err) {
      console.error('Password reset failed', err);
      const detail = err.response?.data?.detail;
      let message = 'Unable to update password.';
      if (typeof detail === 'string') {
        message = detail;
      } else if (Array.isArray(detail)) {
        message = detail.map((d) => d?.msg || d?.message || JSON.stringify(d)).join('; ');
      }
      setStatus({ type: 'error', message });
    } finally {
      setResetting(false);
    }
  };

  const renderStatus = () => {
    if (!status) return null;
    const base = 'px-4 py-3 rounded-xl text-sm';
    if (status.type === 'success') {
      return <div className={`${base} bg-emerald-500/10 border border-emerald-500/40 text-emerald-100`}>{status.message}</div>;
    }
    return <div className={`${base} bg-red-500/10 border border-red-500/40 text-red-100`}>{status.message}</div>;
  };

  const avatarFallback = (user?.name || 'User')
    .split(' ')
    .map((chunk) => chunk.charAt(0))
    .join('')
    .slice(0, 2)
    .toUpperCase();
  const displayName = profile.name || user?.name || 'User';
  const displayEmail = profile.email || user?.email || '';
  const displayContact = profile.contact_number || user?.contact_number || '';
  const displayEmpId = user?.emp_id || '—';

  const handleSaveProfile = async () => {
    setStatus(null);
    if (!profile.name.trim()) {
      setStatus({ type: 'error', message: 'Name cannot be empty.' });
      return;
    }
    setSavingProfile(true);
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('Missing auth token');
      }
      await axios.patch(
        `${API}/auth/me`,
        {
          name: profile.name.trim(),
          email: profile.email.trim() || null,
          contact_number: profile.contact_number.trim() || null
        },
        { headers: { Authorization: `Bearer ${token}` }, timeout: 20000 }
      );
      setStatus({ type: 'success', message: 'Profile updated successfully.' });
    } catch (err) {
      console.error('Profile update failed', err);
      const detail = err.response?.data?.detail;
      let message = 'Unable to update profile.';
      if (typeof detail === 'string') {
        message = detail;
      } else if (Array.isArray(detail)) {
        message = detail.map((d) => d?.msg || d?.message || JSON.stringify(d)).join('; ');
      }
      setStatus({ type: 'error', message });
    } finally {
      setSavingProfile(false);
    }
  };

  return (
    <AppShell user={user} onLogout={onLogout} navItems={navigationItems}>
      <div className="p-6 space-y-6">
        <div className="relative overflow-hidden rounded-3xl border border-[var(--tg-border-soft)] bg-gradient-to-br from-[#111827] via-[#0f172a] to-[#111827] p-6">
          <div className="absolute -left-20 top-0 h-40 w-40 rounded-full bg-purple-500/10 blur-3xl" />
          <div className="absolute right-6 -top-10 h-32 w-32 rounded-full bg-pink-500/10 blur-3xl" />
          <div className="relative flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-2xl bg-[var(--tg-accent-soft)] text-[var(--tg-text-primary)] flex items-center justify-center text-lg font-bold">
                {avatarFallback}
              </div>
              <div>
                <p className="text-sm text-[var(--tg-text-muted)]">Welcome back</p>
                <p className="text-2xl font-semibold text-[var(--tg-text-primary)]">{displayName}</p>
                <div className="flex items-center gap-2 mt-1">
                  <Badge className="bg-purple-500/20 text-purple-200 border border-purple-500/30">
                    {user?.position?.name || (user?.role ? user.role.toUpperCase() : 'USER')}
                  </Badge>
                  {user?.is_active === false && (
                    <Badge variant="destructive" className="bg-red-500/20 text-red-200 border border-red-500/40">
                      Inactive
                    </Badge>
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="rounded-2xl border border-purple-500/30 bg-purple-500/10 px-4 py-3 text-right">
                <p className="text-xs text-purple-100/80 uppercase tracking-wide flex items-center gap-2 justify-end">
                  <MessageCircle className="w-4 h-4" /> Assigned chats
                </p>
                <p className="text-3xl font-bold text-purple-100">
                  {loadingRoster ? <Loader2 className="w-5 h-5 animate-spin inline-block" /> : assignedChats}
                </p>
              </div>
              <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-right">
                <p className="text-xs text-emerald-100/80 uppercase tracking-wide flex items-center gap-2 justify-end">
                  <ShieldCheck className="w-4 h-4" /> Permissions
                </p>
                <p className="text-sm font-semibold text-emerald-50">
                  {(user?.permissions || []).length || 0} granted
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="grid gap-6 md:grid-cols-[2fr,1.3fr]">
          <Card className="bg-[var(--tg-surface)] border border-[var(--tg-border-soft)] shadow-card">
            <CardHeader className="flex items-center justify-between">
              <CardTitle className="text-[var(--tg-text-primary)]">Profile details</CardTitle>
              {isDirty && (
                <Button
                  size="sm"
                  onClick={handleSaveProfile}
                  disabled={savingProfile}
                  className="text-sm bg-gradient-to-r from-purple-500 via-pink-500 to-orange-400 text-white hover:shadow-[0_10px_30px_rgba(168,85,247,0.35)]"
                >
                  {savingProfile ? 'Saving...' : 'Save changes'}
                </Button>
              )}
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4">
                <div className="space-y-2">
                  <Label className="text-[var(--tg-text-secondary)] text-sm">Full name</Label>
                  <Input
                    value={profile.name}
                    onChange={(e) => setProfile((prev) => ({ ...prev, name: e.target.value }))}
                    placeholder="Your name"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-[var(--tg-text-secondary)] text-sm">Email</Label>
                  <Input
                    type="email"
                    value={profile.email}
                    onChange={(e) => setProfile((prev) => ({ ...prev, email: e.target.value }))}
                    placeholder="you@example.com"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-[var(--tg-text-secondary)] text-sm">Contact number</Label>
                  <Input
                    value={profile.contact_number}
                    onChange={(e) => setProfile((prev) => ({ ...prev, contact_number: e.target.value }))}
                    placeholder="+1 555 000 0000"
                  />
                </div>
                <InfoRow label="Employee ID" value={user?.emp_id || '—'} icon={ShieldCheck} />
                <InfoRow label="Position / Role" value={user?.position?.name || user?.role || '-'} icon={ShieldCheck} />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-[var(--tg-surface)] border border-[var(--tg-border-soft)] shadow-card">
            <CardHeader>
              <CardTitle className="text-[var(--tg-text-primary)]">Reset password</CardTitle>
            </CardHeader>
            <CardContent>
              {renderStatus()}
              <form className="space-y-4 mt-4" onSubmit={handlePasswordChange}>
                <div>
                  <Label className="text-[var(--tg-text-secondary)] text-sm">Current password</Label>
                  <div className="relative">
                    <Input
                      type={showPasswords.current ? 'text' : 'password'}
                      value={passwords.currentPassword}
                      onChange={(e) => setPasswords((prev) => ({ ...prev, currentPassword: e.target.value }))}
                      placeholder="••••••••"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPasswords((prev) => ({ ...prev, current: !prev.current }))}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--tg-text-muted)] hover:text-[var(--tg-text-primary)]"
                    >
                      {showPasswords.current ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <div>
                  <Label className="text-[var(--tg-text-secondary)] text-sm">New password</Label>
                  <div className="relative">
                    <Input
                      type={showPasswords.new ? 'text' : 'password'}
                      value={passwords.newPassword}
                      onChange={(e) => setPasswords((prev) => ({ ...prev, newPassword: e.target.value }))}
                      minLength={8}
                      placeholder="At least 8 characters"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPasswords((prev) => ({ ...prev, new: !prev.new }))}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--tg-text-muted)] hover:text-[var(--tg-text-primary)]"
                    >
                      {showPasswords.new ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <div>
                  <Label className="text-[var(--tg-text-secondary)] text-sm">Confirm new password</Label>
                  <div className="relative">
                    <Input
                      type={showPasswords.confirm ? 'text' : 'password'}
                      value={passwords.confirmPassword}
                      onChange={(e) => setPasswords((prev) => ({ ...prev, confirmPassword: e.target.value }))}
                      minLength={8}
                      placeholder="Repeat new password"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPasswords((prev) => ({ ...prev, confirm: !prev.confirm }))}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--tg-text-muted)] hover:text-[var(--tg-text-primary)]"
                    >
                      {showPasswords.confirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <Button
                  type="submit"
                  disabled={resetting}
                  className="w-full bg-gradient-to-r from-purple-500 via-pink-500 to-orange-400 text-white"
                >
                  {resetting ? 'Updating...' : 'Update password'}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  );
};

export default ProfilePage;
