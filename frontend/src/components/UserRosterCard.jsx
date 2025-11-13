import React, { useMemo, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { ScrollArea } from './ui/scroll-area';
import { Badge } from './ui/badge';
import { Input } from './ui/input';
import { Search, Users, MessageSquare } from 'lucide-react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from './ui/select';

const RolePill = ({ label }) => (
  <span className="px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 text-[11px] font-semibold dark:bg-purple-500/10 dark:text-purple-200">
    {label || '—'}
  </span>
);

const AssignedCount = ({ count }) => (
  <span className="inline-flex items-center justify-center min-w-[38px] px-2 py-0.5 rounded-full bg-gradient-to-r from-purple-200 to-pink-200 text-sm text-purple-800 font-semibold dark:from-purple-500/30 dark:to-pink-500/30 dark:text-purple-100">
    {count}
  </span>
);

const SummaryStat = ({ icon: Icon, label, value }) => (
  <div className="flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2 dark:border-gray-700 dark:bg-[#151530]">
    <div className="rounded-full bg-purple-100 p-2 text-purple-500 dark:bg-purple-500/15 dark:text-purple-200">
      <Icon className="h-4 w-4" />
    </div>
    <div>
      <p className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-500">{label}</p>
      <p className="text-base font-semibold text-gray-900 dark:text-white">{value}</p>
    </div>
  </div>
);

const UserRosterCard = ({
  users = [],
  loading,
  onManagePositions,
  canManagePositions,
  currentUserId,
  canAssignPositions = false,
  positions = [],
  positionsLoading = false,
  onAssignPosition,
}) => {
  const [search, setSearch] = useState('');

  const stats = useMemo(() => {
    const totalUsers = users.length;
    const totalAssigned = users.reduce((sum, user) => sum + (user.assigned_chat_count || 0), 0);
    const activeAgents = users.filter((user) => (user.assigned_chat_count || 0) > 0).length;
    return { totalUsers, totalAssigned, activeAgents };
  }, [users]);

  const filteredUsers = useMemo(() => {
    if (!search.trim()) {
      return users;
    }
    const term = search.toLowerCase();
    return users.filter((user) => {
      const positionName = user.position?.name || '';
      return (
        user.name.toLowerCase().includes(term) ||
        user.email?.toLowerCase().includes(term) ||
        positionName.toLowerCase().includes(term)
      );
    });
  }, [users, search]);

  return (
    <Card className="bg-gradient-to-br from-white to-[#f5f0ff] border border-purple-100 shadow-[0_15px_35px_rgba(19,0,53,0.12)] dark:from-[#16162b] dark:to-[#100f25] dark:border-purple-800/40 dark:shadow-[0_20px_40px_rgba(5,0,30,0.7)]">
      <CardHeader className="pb-4">
        <div className="flex flex-wrap items-center gap-3 justify-between">
          <div>
            <CardTitle className="text-gray-900 text-lg dark:text-white">User Directory</CardTitle>
            <p className="text-xs text-gray-500 dark:text-gray-400">Monitor your team, spot workload spikes, and jump into assignments.</p>
          </div>
          <div className="flex items-center gap-2">
            {loading && <Badge className="bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-200">Refreshing…</Badge>}
            {canManagePositions && (
              <button
                onClick={onManagePositions}
                className="rounded-full border border-purple-200 bg-purple-100 px-4 py-1.5 text-xs font-semibold text-purple-700 hover:bg-purple-200 dark:border-purple-500/60 dark:bg-purple-500/10 dark:text-purple-100 dark:hover:bg-purple-500/20"
              >
                Manage Positions
              </button>
            )}
          </div>
        </div>
        <div className="grid gap-3 pt-4 md:grid-cols-3">
          <SummaryStat icon={Users} label="Total Users" value={stats.totalUsers} />
          <SummaryStat icon={MessageSquare} label="Chats Assigned" value={stats.totalAssigned} />
          <SummaryStat icon={Users} label="Active Agents" value={stats.activeAgents} />
        </div>
        <div className="relative mt-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 dark:text-gray-500" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search name, email, or position"
            className="pl-10 bg-white border-purple-200 text-sm text-gray-900 placeholder:text-gray-500 dark:bg-[#0f0f1a] dark:border-purple-900/40 dark:text-white"
          />
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <ScrollArea className="h-[50vh]">
          <div className="space-y-3">
            {filteredUsers.length === 0 && !loading && (
              <div className="py-8 text-center text-gray-500 text-sm">No teammates match that search.</div>
            )}
            {filteredUsers.map((user) => {
              const currentPositionId = user.position?.id || '__none__';
              const canEditRow = canAssignPositions && user.id !== currentUserId;
              return (
                <div
                  key={user.id}
                  className="flex items-center justify-between gap-4 rounded-2xl border border-gray-200 bg-white/80 px-4 py-3 hover:border-purple-300 transition-colors dark:border-white/10 dark:bg-white/5 dark:hover:border-purple-400/40"
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-gray-900 truncate dark:text-white">{user.name}</p>
                    <p className="text-xs text-gray-500 truncate dark:text-gray-400">{user.email || '—'}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <RolePill label={user.position?.name || user.role} />
                    {canEditRow && (
                      <Select
                        value={currentPositionId}
                        onValueChange={(value) =>
                          onAssignPosition?.(user.id, value === '__none__' ? null : value)
                        }
                        disabled={positionsLoading}
                      >
                        <SelectTrigger className="w-40 bg-white border-purple-200 text-xs font-medium text-gray-900 dark:bg-transparent dark:border-gray-700 dark:text-white">
                          <SelectValue placeholder="Assign position" />
                        </SelectTrigger>
                        <SelectContent className="bg-white text-gray-900 dark:bg-[#0f0f1a] dark:text-white">
                          <SelectItem value="__none__">Unassign</SelectItem>
                          {positions.map((position) => (
                            <SelectItem key={position.id} value={position.id}>
                              {position.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                    <AssignedCount count={user.assigned_chat_count || 0} />
                  </div>
                </div>
              );
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
};

export default UserRosterCard;
