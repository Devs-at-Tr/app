import React from 'react';
import { Dialog, DialogContent } from './ui/dialog';
import UserRosterCard from './UserRosterCard';

const UserRosterModal = ({
  open,
  onClose,
  users,
  loading,
  canManagePositions,
  currentUserId,
  canAssignPositions,
  positions = [],
  positionsLoading = false,
  onManagePositions,
  onAssignPosition,
}) => (
  <Dialog open={open} onOpenChange={(value) => !value && onClose?.()}>
    <DialogContent className="max-w-4xl w-full p-0 border border-slate-200 text-slate-900 bg-white shadow-2xl dark:border-gray-900 dark:bg-[#0f0f1a] dark:text-white max-h-[85vh] overflow-hidden">
      <div className="p-4 md:p-6 max-h-[85vh] overflow-y-auto">
        <UserRosterCard
          users={users}
          loading={loading}
          canManagePositions={canManagePositions}
          currentUserId={currentUserId}
          canAssignPositions={canAssignPositions}
          positions={positions}
          positionsLoading={positionsLoading}
          onManagePositions={onManagePositions}
          onAssignPosition={onAssignPosition}
        />
      </div>
    </DialogContent>
  </Dialog>
);

export default UserRosterModal;
