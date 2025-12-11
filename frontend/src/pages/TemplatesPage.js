import React, { useMemo } from 'react';
import AppShell from '../layouts/AppShell';
import TemplatesLayout from '../layouts/TemplatesLayout';
import TemplateManager from '../components/TemplateManager';
import { buildNavigationItems } from '../utils/navigationConfig';
import { hasPermission, hasAnyPermission } from '../utils/permissionUtils';

const TemplatesPage = ({ user, onLogout }) => {
  const canManageTemplates = useMemo(() => hasPermission(user, 'template:manage'), [user]);
  const canManageIntegrations = useMemo(() => hasPermission(user, 'integration:manage'), [user]);
  const canManagePositions = useMemo(() => hasPermission(user, 'position:manage'), [user]);
  const canViewUserRoster = useMemo(
    () => hasAnyPermission(user, ['position:assign', 'position:manage']),
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
        canViewStats,
        canManageIntegrations
      }),
    [canManageTemplates, canViewUserRoster, canManagePositions, canInviteUsers, canViewStats, canManageIntegrations]
  );

  return (
    <AppShell user={user} navItems={navItems} onLogout={onLogout}>
      <TemplatesLayout
        title="Message Templates"
        description="Manage pre-approved responses for every platform."
      >
        <TemplateManager />
      </TemplatesLayout>
    </AppShell>
  );
};

export default TemplatesPage;
