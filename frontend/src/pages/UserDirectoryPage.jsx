import React, { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import AppShell from '../layouts/AppShell';
import AdminLayout from '../layouts/AdminLayout';
import { API } from '../App';
import UserRosterCard from '../components/UserRosterCard';
import { hasPermission, hasAnyPermission } from '../utils/permissionUtils';
import { buildNavigationItems } from '../utils/navigationConfig';

const UserDirectoryPage = ({ user, onLogout }) => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [positions, setPositions] = useState([]);
  const [positionsLoading, setPositionsLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const canManageTemplates = useMemo(() => hasPermission(user, 'template:manage'), [user]);
  const canManagePositions = useMemo(() => hasPermission(user, 'position:manage'), [user]);
  const canViewUserRoster = useMemo(
    () => hasAnyPermission(user, ['position:assign', 'position:manage', 'chat:assign']),
    [user]
  );
  const canAssignPositions = useMemo(() => hasPermission(user, 'position:assign'), [user]);

  const navigationItems = useMemo(
    () =>
      buildNavigationItems({
        canManageTemplates,
        canViewUserRoster,
        canManagePositions
      }),
    [canManageTemplates, canViewUserRoster, canManagePositions]
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

  return (
    <AppShell user={user} onLogout={onLogout} navItems={navigationItems}>
      <AdminLayout
        title="User Directory"
        description="Monitor your team, spot workload spikes, and jump into assignments."
      >
        <div className="flex-1 overflow-y-auto space-y-4">
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
