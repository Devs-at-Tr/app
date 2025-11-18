import React, { useMemo } from 'react';
import AppShell from '../layouts/AppShell';
import SocialComments from '../components/SocialComments';
import { buildNavigationItems } from '../utils/navigationConfig';
import { hasPermission, hasAnyPermission } from '../utils/permissionUtils';

const CommentsPage = ({ user, onLogout }) => {
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

  return (
    <AppShell user={user} navItems={navItems} onLogout={onLogout}>
      <SocialComments selectedPlatform="all" />
    </AppShell>
  );
};

export default CommentsPage;
