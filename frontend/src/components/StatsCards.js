import React from 'react';
import { MessageSquare, UserCheck, UserX, Activity, Instagram } from 'lucide-react';

const FacebookIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
  </svg>
);

const StatCard = ({ icon: Icon, label, value, color, dataTestId, subStats }) => {
  return (
    <div className={`stat-card bg-[#1a1a2e] border border-gray-800 rounded-xl p-4`} data-testid={dataTestId}>
      <div className="flex items-center justify-between mb-1.5">
        <div>
          <p className="text-gray-400 text-xs uppercase tracking-wide mb-1">{label}</p>
          <p className="text-2xl font-bold text-white">{value}</p>
        </div>
        <div className={`p-2.5 rounded-lg ${color}`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
      </div>
      {subStats && (
        <div className="flex items-center space-x-3 pt-2 mt-2 border-t border-gray-700">
          {subStats.map((stat, index) => (
            <div key={index} className="flex items-center space-x-1 text-xs">
              {stat.icon}
              <span className="text-gray-400">{stat.label}:</span>
              <span className="text-white font-semibold">{stat.value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const StatsCards = ({ stats }) => {
  if (!stats) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4" data-testid="stats-cards">
      <StatCard
        icon={MessageSquare}
        label="Total Chats"
        value={stats.total_chats}
        color="bg-gradient-to-br from-purple-600 to-purple-700"
        dataTestId="stat-total-chats"
        subStats={[
          {
            icon: <Instagram className="w-3 h-3 text-pink-400" />,
            label: 'Instagram',
            value: stats.instagram_chats || 0
          },
          {
            icon: <FacebookIcon className="w-3 h-3 text-blue-400" />,
            label: 'Facebook',
            value: stats.facebook_chats || 0
          }
        ]}
      />
      <StatCard
        icon={UserCheck}
        label="Assigned Chats"
        value={stats.assigned_chats}
        color="bg-gradient-to-br from-green-600 to-green-700"
        dataTestId="stat-assigned-chats"
      />
      <StatCard
        icon={UserX}
        label="Unassigned Chats"
        value={stats.unassigned_chats}
        color="bg-gradient-to-br from-orange-600 to-orange-700"
        dataTestId="stat-unassigned-chats"
      />
      <StatCard
        icon={Activity}
        label="Active Agents"
        value={stats.active_agents}
        color="bg-gradient-to-br from-pink-600 to-pink-700"
        dataTestId="stat-active-agents"
      />
    </div>
  );
};

export default StatsCards;
