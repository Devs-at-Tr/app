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
import { Switch } from './ui/switch';
import { Button } from './ui/button';

const RolePill = ({ label }) => (
  <span className="px-2 py-0.5 rounded-full bg-[var(--tg-accent-soft)] text-[var(--tg-text-primary)] text-[11px] font-semibold">
    {label || '—'}
  </span>
);

const AssignedCount = ({ count }) => (
  <span className="inline-flex items-center justify-center min-w-[38px] px-2 py-0.5 rounded-full bg-[var(--tg-chat-active)] text-sm text-[var(--tg-text-primary)] font-semibold">
    {count}
  </span>
);

const SummaryStat = ({ icon: Icon, label, value }) => (
  <div className="flex items-center gap-2 rounded-xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface-muted)] px-3 py-2">
    <div className="rounded-full bg-[var(--tg-accent-soft)] text-[var(--tg-text-primary)] p-2">
      <Icon className="h-4 w-4" />
    </div>
    <div>
      <p className="text-xs uppercase tracking-wide text-[var(--tg-text-muted)]">{label}</p>
      <p className="text-base font-semibold text-[var(--tg-text-primary)]">{value}</p>
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
  onToggleActive,
  canToggleActive = false,
  canResetPasswords = false,
  onResetPassword,
}) => {
  const [search, setSearch] = useState('');

  const stats = useMemo(() => {
    const totalUsers = users.length;
    const totalAssigned = users.reduce((sum, user) => sum + (user.assigned_chat_count || 0), 0);
    const activeUsers = users.filter((user) => user.is_active !== false).length;
    const inactiveUsers = totalUsers - activeUsers;
    return { totalUsers, totalAssigned, activeUsers, inactiveUsers };
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

  const activeList = filteredUsers.filter((user) => user.is_active !== false);
  const inactiveList = filteredUsers.filter((user) => user.is_active === false);

  return (
    <Card className="bg-[var(--tg-surface)] border border-[var(--tg-border-soft)] shadow-card">
      <CardHeader className="pb-4">
        <div className="flex flex-wrap items-center gap-3 justify-between">
          <div>
            <CardTitle className="text-lg text-[var(--tg-text-primary)]">User Directory</CardTitle>
            <p className="text-xs text-[var(--tg-text-muted)]">Monitor your team, spot workload spikes, and jump into assignments.</p>
          </div>
          <div className="flex items-center gap-2">
            {loading && <Badge className="bg-[var(--tg-accent-soft)] text-[var(--tg-text-primary)]">Refreshing…</Badge>}
            {canManagePositions && (
              <button
                onClick={onManagePositions}
                className="rounded-full border border-[var(--tg-border-soft)] bg-[var(--tg-surface-muted)] px-4 py-1.5 text-xs font-semibold text-[var(--tg-text-primary)] hover:bg-[var(--tg-chat-hover)]"
              >
                Manage Positions
              </button>
            )}
          </div>
        </div>
        <div className="grid gap-3 pt-4 md:grid-cols-3">
          <SummaryStat icon={Users} label="Total Users" value={stats.totalUsers} />
          <SummaryStat icon={MessageSquare} label="Chats Assigned" value={stats.totalAssigned} />
          <SummaryStat icon={Users} label="Active Users" value={stats.activeUsers} />
        </div>
        <div className="relative mt-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--tg-text-muted)]" />
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search name, email, or position"
            autoComplete="off"
            className="pl-10 bg-[var(--tg-surface-muted)] border-[var(--tg-border-soft)] text-sm text-[var(--tg-text-primary)] placeholder:text-[var(--tg-text-muted)]"
          />
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <ScrollArea className="h-[50vh]">
          <div className="space-y-3">
            {filteredUsers.length === 0 && !loading && (
              <div className="py-8 text-center text-[var(--tg-text-muted)] text-sm">No teammates match that search.</div>
            )}
            {activeList.map((user) => {
              const currentPositionId = user.position?.id || '__none__';
              const canEditRow = canAssignPositions && user.id !== currentUserId;
              return (
                <div
                  key={user.id}
                  className="flex items-center justify-between gap-4 rounded-2xl border border-[var(--tg-border-soft)] bg-[var(--tg-surface)] px-4 py-3 hover:border-[var(--tg-accent-soft)] transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-[var(--tg-text-primary)] truncate">{user.name}</p>
                    <p className="text-xs text-[var(--tg-text-muted)] truncate">
                      {user.email || '—'}
                      {user.contact_number ? ` · ${user.contact_number}` : ''}
                    </p>
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
                        <SelectTrigger className="w-40 bg-[var(--tg-surface-muted)] border-[var(--tg-border-soft)] text-xs font-medium text-[var(--tg-text-primary)]">
                          <SelectValue placeholder="Assign position" />
                        </SelectTrigger>
                        <SelectContent className="bg-[var(--tg-surface)] text-[var(--tg-text-primary)]">
                          <SelectItem value="__none__">Unassign</SelectItem>
                          {positions.map((position) => (
                            <SelectItem key={position.id} value={position.id}>
                              {position.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                    {canToggleActive && (
                      <div className="flex items-center gap-2 text-xs text-[var(--tg-text-muted)]">
                        <span>Active</span>
                        <Switch
                          checked={user.is_active !== false}
                          onCheckedChange={(checked) => onToggleActive?.(user.id, checked)}
                        />
                      </div>
                    )}
                    {canResetPasswords && (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => onResetPassword?.(user)}
                        className="text-xs"
                      >
                        Reset password
                      </Button>
                    )}
                    <AssignedCount count={user.assigned_chat_count || 0} />
                  </div>
                </div>
              );
            })}
            {inactiveList.length > 0 && (
              <div className="pt-6 space-y-3">
                <p className="text-xs uppercase tracking-wide text-[var(--tg-text-muted)]">Inactive users</p>
                {inactiveList.map((user) => (
                  <div
                    key={user.id}
                    className="flex items-center justify-between gap-4 rounded-2xl border border-dashed border-[var(--tg-border-soft)] bg-[var(--tg-surface-muted)] px-4 py-3"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-[var(--tg-text-primary)] truncate">{user.name}</p>
                      <p className="text-xs text-[var(--tg-text-muted)] truncate">
                        {user.email || '—'}
                        {user.contact_number ? ` · ${user.contact_number}` : ''}
                      </p>
                    </div>
                    {canToggleActive && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => onToggleActive?.(user.id, true)}
                        className="text-xs"
                      >
                        Activate
                      </Button>
                    )}
                    {canResetPasswords && (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => onResetPassword?.(user)}
                        className="text-xs"
                      >
                        Reset password
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
};

export default UserRosterCard;
