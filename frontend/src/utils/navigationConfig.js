import {
  MessageCircle,
  Instagram,
  Facebook,
  PhoneCall,
  MessageSquare,
  FileText,
  Users,
  Shield,
  UserPlus,
  Activity,
  Plug,
  User
} from 'lucide-react';

export const buildNavigationItems = ({
  canManageTemplates = false,
  canViewUserRoster = false,
  canManagePositions = false,
  canInviteUsers = false,
  canViewStats = false,
  canManageIntegrations = false
} = {}) => {
  const items = [
    { id: 'inbox', label: 'Direct Messages', icon: MessageCircle, to: '/inbox', exact: true },
    // { id: 'instagram', label: 'Instagram', icon: Instagram, to: '/inbox/instagram' }, // disabled
    // { id: 'facebook', label: 'Facebook', icon: Facebook, to: '/inbox/facebook' }, // disabled
    { id: 'whatsapp', label: 'WhatsApp', icon: PhoneCall, disabled: true, badge: 'Soon' },
    { id: 'comments', label: 'Comments & Reviews', icon: MessageSquare, to: '/comments' }
  ];

  if (canManageIntegrations) {
    items.push({
      id: 'manage-pages',
      label: 'Manage connected pages',
      icon: Plug,
      type: 'manage-pages',
      menuItems: [
        { id: 'instagram', label: 'Manage Instagram', icon: Instagram },
        { id: 'facebook', label: 'Manage Facebook', icon: Facebook }
      ]
    });
  }

  if (canManageTemplates) {
    items.push({ id: 'templates', label: 'Templates', icon: FileText, to: '/templates' });
  }

  // items.push({ id: 'profile', label: 'My Profile', icon: User, to: '/profile' }); //profile page disabled

  if (canViewStats) {
    items.push({ id: 'stats', label: 'Analytics', icon: Activity, to: '/stats' });
  }

  if (canViewUserRoster) {
    items.push({ id: 'user-directory', label: 'User Directory', icon: Users, to: '/user-directory' });
  }

  if (canInviteUsers) {
    items.push({ id: 'create-user', label: 'Create User', icon: UserPlus, to: '/admin/users/new' });
  }

  if (canManagePositions) {
    items.push({ id: 'positions', label: 'Positions', icon: Shield, to: '/positions' });
  }

  return items;
};
