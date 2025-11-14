import {
  MessageCircle,
  Instagram,
  Facebook,
  PhoneCall,
  MessageSquare,
  FileText,
  Users,
  Shield,
  UserPlus
} from 'lucide-react';

export const buildNavigationItems = ({
  canManageTemplates,
  canViewUserRoster,
  canManagePositions,
  canInviteUsers
}) => {
  const items = [
    { id: 'inbox', label: 'Direct Messages', icon: MessageCircle, to: '/inbox', exact: true },
    { id: 'instagram', label: 'Instagram', icon: Instagram, to: '/inbox/instagram' },
    { id: 'facebook', label: 'Facebook', icon: Facebook, to: '/inbox/facebook' },
    { id: 'whatsapp', label: 'WhatsApp', icon: PhoneCall, disabled: true, badge: 'Soon' },
    { id: 'comments', label: 'Comments & Reviews', icon: MessageSquare, to: '/comments' }
  ];

  if (canManageTemplates) {
    items.push({ id: 'templates', label: 'Templates', icon: FileText, to: '/templates' });
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
