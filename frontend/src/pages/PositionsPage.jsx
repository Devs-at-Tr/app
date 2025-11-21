import React, { useMemo } from 'react';
import AppShell from '../layouts/AppShell';
import AdminLayout from '../layouts/AdminLayout';
import PositionManager from '../components/PositionManager';
import { hasPermission, hasAnyPermission } from '../utils/permissionUtils';
import { buildNavigationItems } from '../utils/navigationConfig';

const PositionsPage = ({ user, onLogout }) => {
  const canManagePositions = useMemo(() => hasPermission(user, 'position:manage'), [user]);
  const canManageTemplates = useMemo(() => hasPermission(user, 'template:manage'), [user]);
  const canManageIntegrations = useMemo(() => hasPermission(user, 'integration:manage'), [user]);
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

  return (
    <AppShell user={user} onLogout={onLogout} navItems={navigationItems}>
      <AdminLayout
        title="Positions"
        description="Define roles, permissions, and responsibilities for your team."
      >
        <div className="flex-1 overflow-y-auto space-y-4">
          {canManagePositions ? (
            <PositionManager />
          ) : (
            <div className="rounded-xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface)] p-6 text-sm text-[var(--tg-text-secondary)]">
              You do not have permission to manage positions.
            </div>
          )}
        </div>
      </AdminLayout>
    </AppShell>
  );
};

export default PositionsPage;
