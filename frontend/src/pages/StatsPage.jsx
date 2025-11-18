import React, { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import AppShell from '../layouts/AppShell';
import AdminLayout from '../layouts/AdminLayout';
import StatsCards from '../components/StatsCards';
import { API } from '../App';
import { Button } from '../components/ui/button';
import { hasPermission, hasAnyPermission } from '../utils/permissionUtils';
import { buildNavigationItems } from '../utils/navigationConfig';

const StatsPage = ({ user, onLogout }) => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const canManageTemplates = useMemo(() => hasPermission(user, 'template:manage'), [user]);
  const canManagePositions = useMemo(() => hasPermission(user, 'position:manage'), [user]);
  const canViewUserRoster = useMemo(
    () => hasAnyPermission(user, ['position:assign', 'position:manage', 'chat:assign']),
    [user]
  );
  const canInviteUsers = useMemo(() => hasPermission(user, 'user:invite'), [user]);
  const canViewStats = useMemo(() => hasPermission(user, 'stats:view'), [user]);

  const navItems = useMemo(
    () =>
      buildNavigationItems({
        canManageTemplates,
        canViewUserRoster,
        canManagePositions,
        canInviteUsers,
        canViewStats
      }),
    [canManageTemplates, canViewUserRoster, canManagePositions, canInviteUsers, canViewStats]
  );

  const loadStats = useCallback(async () => {
    if (!canViewStats) {
      return;
    }
    setLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('No authentication token found');
      }
      const response = await axios.get(`${API}/dashboard/stats`, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 30000
      });
      setStats(response.data);
    } catch (fetchError) {
      console.error('Failed to load analytics:', fetchError);
      setError(fetchError.response?.data?.detail || fetchError.message || 'Unable to load analytics');
    } finally {
      setLoading(false);
    }
  }, [canViewStats]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  return (
    <AppShell user={user} navItems={navItems} onLogout={onLogout}>
      <AdminLayout
        title="Analytics"
        description="Monitor DM volume, load distribution, and agent availability."
        actions={
          canViewStats && (
            <Button variant="outline" onClick={loadStats} disabled={loading}>
              {loading ? 'Refreshing...' : 'Refresh'}
            </Button>
          )
        }
      >
        <div className="flex-1 min-h-0">
          {!canViewStats ? (
            <div className="rounded-xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface)] p-6 text-sm text-[var(--tg-text-secondary)]">
              You do not have permission to view analytics.
            </div>
          ) : error ? (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-6 text-sm text-red-100">
              {error}
            </div>
          ) : loading && !stats ? (
            <div className="rounded-xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface)] p-6 flex justify-center">
              <div className="h-10 w-10 rounded-full border-t-2 border-b-2 border-purple-500 animate-spin" />
            </div>
          ) : (
            <div className="space-y-6">
              <StatsCards stats={stats} className="max-w-4xl" />
              <div className="rounded-xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface)] p-4 text-sm text-[var(--tg-text-secondary)]">
                Analytics update automatically when webhooks create or assign chats. Use this page to
                audit workloads before reshuffling teams.
              </div>
            </div>
          )}
        </div>
      </AdminLayout>
    </AppShell>
  );
};

export default StatsPage;
