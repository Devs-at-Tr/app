import React, { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import AppShell from '../layouts/AppShell';
import AdminLayout from '../layouts/AdminLayout';
import { API } from '../App';
import UserRosterCard from '../components/UserRosterCard';
import { hasPermission, hasAnyPermission } from '../utils/permissionUtils';
import { buildNavigationItems } from '../utils/navigationConfig';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from '../components/ui/alert-dialog';
import { Input } from '../components/ui/input';

const UserDirectoryPage = ({ user, onLogout }) => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [positions, setPositions] = useState([]);
  const [positionsLoading, setPositionsLoading] = useState(false);
  const [error, setError] = useState('');
  const [resetModal, setResetModal] = useState({
    open: false,
    userId: null,
    userName: '',
    newPassword: '',
    confirmPassword: '',
    submitting: false
  });
  const navigate = useNavigate();

  const canManageTemplates = useMemo(() => hasPermission(user, 'template:manage'), [user]);
  const canManageIntegrations = useMemo(() => hasPermission(user, 'integration:manage'), [user]);
  const canManagePositions = useMemo(() => hasPermission(user, 'position:manage'), [user]);
  const canViewUserRoster = useMemo(
    () => hasAnyPermission(user, ['position:assign', 'position:manage', 'chat:assign']),
    [user]
  );
  const canAssignPositions = useMemo(() => hasPermission(user, 'position:assign'), [user]);
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

  const loadUserRoster = useCallback(async () => {
    if (!canViewUserRoster) {
      setUsers([]);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found');
      }
      const response = await axios.get(`${API}/users/roster`, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 30000
      });
      setUsers(response.data || []);
    } catch (loadError) {
      console.error('Error loading user roster:', loadError);
      setError(loadError.response?.data?.detail || loadError.message || 'Unable to load users');
    } finally {
      setLoading(false);
    }
  }, [canViewUserRoster]);

  const loadPositions = useCallback(async () => {
    if (!canAssignPositions) {
      setPositions([]);
      return;
    }
    setPositionsLoading(true);
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found');
      }
      const response = await axios.get(`${API}/positions`, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 30000
      });
      setPositions(response.data || []);
    } catch (positionsError) {
      console.error('Error loading positions:', positionsError);
    } finally {
      setPositionsLoading(false);
    }
  }, [canAssignPositions]);

  useEffect(() => {
    loadUserRoster();
  }, [loadUserRoster]);

  useEffect(() => {
    loadPositions();
  }, [loadPositions]);

  const handleToggleActive = useCallback(
    async (userId, isActive) => {
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          throw new Error('No authentication token found');
        }
        await axios.patch(
          `${API}/users/${userId}/active`,
          { is_active: isActive },
          { headers: { Authorization: `Bearer ${token}` }, timeout: 30000 }
        );
        await loadUserRoster();
      } catch (toggleError) {
        console.error('Error updating user status:', toggleError);
        setError(toggleError.response?.data?.detail || toggleError.message || 'Unable to update user');
      }
    },
    [loadUserRoster]
  );

  const handleAssignPosition = useCallback(
    async (userId, positionId) => {
      if (!canAssignPositions) {
        return;
      }
      try {
        const token = localStorage.getItem('token');
        if (!token) {
          throw new Error('No authentication token found');
        }
        await axios.post(
          `${API}/users/${userId}/position`,
          { position_id: positionId },
          { headers: { Authorization: `Bearer ${token}` } }
        );
        await loadUserRoster();
      } catch (assignError) {
        console.error('Error assigning position:', assignError);
      }
    },
    [canAssignPositions, loadUserRoster]
  );

  const openResetModal = useCallback((user) => {
    setResetModal({
      open: true,
      userId: user.id,
      userName: user.name || 'User',
      newPassword: '',
      confirmPassword: '',
      submitting: false
    });
  }, []);

  const closeResetModal = () => {
    setResetModal((prev) => ({ ...prev, open: false, newPassword: '', confirmPassword: '', submitting: false }));
  };

  const handleResetPassword = useCallback(async () => {
    if (!resetModal.userId) return;
    if (!resetModal.newPassword || resetModal.newPassword.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (resetModal.newPassword !== resetModal.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setResetModal((prev) => ({ ...prev, submitting: true }));
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found');
      }
      await axios.post(
        `${API}/admin/users/${resetModal.userId}/reset-password`,
        { new_password: resetModal.newPassword },
        { headers: { Authorization: `Bearer ${token}` }, timeout: 20000 }
      );
      setError('');
      closeResetModal();
      await loadUserRoster();
    } catch (resetError) {
      console.error('Error resetting password:', resetError);
      setError(resetError.response?.data?.detail || resetError.message || 'Unable to reset password');
      setResetModal((prev) => ({ ...prev, submitting: false }));
    }
  }, [loadUserRoster, resetModal]);

  return (
    <AppShell user={user} onLogout={onLogout} navItems={navigationItems}>
      <AdminLayout
        title="User Directory"
        description="Monitor your team, spot workload spikes, and jump into assignments."
      >
        <div className="flex-1 overflow-y-auto space-y-4">
          <AlertDialog open={resetModal.open} onOpenChange={(open) => !open && closeResetModal()}>
            <AlertDialogContent className="bg-[var(--tg-surface)] border border-[var(--tg-border-soft)] text-[var(--tg-text-primary)]">
              <AlertDialogHeader>
                <AlertDialogTitle>Reset password</AlertDialogTitle>
                <AlertDialogDescription className="text-[var(--tg-text-muted)]">
                  Set a new password for <strong>{resetModal.userName}</strong>. This action takes effect immediately.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="text-xs text-[var(--tg-text-secondary)]">New password</label>
                  <Input
                    type="password"
                    value={resetModal.newPassword}
                    onChange={(e) => setResetModal((prev) => ({ ...prev, newPassword: e.target.value }))}
                    placeholder="At least 8 characters"
                    autoComplete="new-password"
                    minLength={8}
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-[var(--tg-text-secondary)]">Confirm new password</label>
                  <Input
                    type="password"
                    value={resetModal.confirmPassword}
                    onChange={(e) => setResetModal((prev) => ({ ...prev, confirmPassword: e.target.value }))}
                    placeholder="Repeat password"
                    autoComplete="new-password"
                    minLength={8}
                  />
                </div>
              </div>
              <AlertDialogFooter>
                <AlertDialogCancel className="bg-transparent border border-[var(--tg-border-soft)] text-[var(--tg-text-primary)]">
                  Cancel
                </AlertDialogCancel>
                <AlertDialogAction
                  onClick={handleResetPassword}
                  disabled={resetModal.submitting}
                  className="bg-gradient-to-r from-purple-500 via-pink-500 to-orange-400 text-white"
                >
                  {resetModal.submitting ? 'Setting...' : 'Set password'}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>

          {error && (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {error}
            </div>
          )}
          {canViewUserRoster ? (
            <UserRosterCard
              users={users}
              loading={loading}
              canManagePositions={canManagePositions}
              currentUserId={user.id}
              canAssignPositions={canAssignPositions}
              positions={positions}
              positionsLoading={positionsLoading}
              onManagePositions={() => navigate('/positions')}
              onAssignPosition={handleAssignPosition}
              onToggleActive={handleToggleActive}
              canToggleActive={canManagePositions}
              canResetPasswords={user?.role === 'admin'}
              onResetPassword={openResetModal}
            />
          ) : (
            <div className="rounded-xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface)] p-6 text-sm text-[var(--tg-text-secondary)]">
              You do not have permission to view the user directory.
            </div>
          )}
        </div>
      </AdminLayout>
    </AppShell>
  );
};

export default UserDirectoryPage;
