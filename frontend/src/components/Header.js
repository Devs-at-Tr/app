import React from 'react';
import { Button } from './ui/button';
import { MessageCircle, LogOut, User } from 'lucide-react';

const Header = ({ user, onLogout }) => {
  return (
    <header className="bg-[#1a1a2e] border-b border-gray-800 sticky top-0 z-50" data-testid="dashboard-header">
      <div className="px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="bg-gradient-to-r from-purple-600 to-pink-600 p-2 rounded-lg">
            <MessageCircle className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">TickleGram Dashboard</h1>
            <p className="text-xs text-gray-400">Instagram DM Management</p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 px-4 py-2 bg-[#0f0f1a] rounded-lg border border-gray-800">
            <User className="w-4 h-4 text-purple-400" />
            <div>
              <p className="text-sm font-medium text-white" data-testid="user-name">{user.name}</p>
              <p className="text-xs text-gray-400 capitalize" data-testid="user-role">{user.role}</p>
            </div>
          </div>
          
          <Button
            onClick={onLogout}
            data-testid="logout-button"
            variant="outline"
            className="bg-red-500/10 border-red-500/50 hover:bg-red-500/20 text-red-400"
          >
            <LogOut className="w-4 h-4 mr-2" />
            Logout
          </Button>
        </div>
      </div>
    </header>
  );
};

export default Header;