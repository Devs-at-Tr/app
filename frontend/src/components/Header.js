import React, { useState } from 'react';
import { Button } from './ui/button';
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator
} from './ui/dropdown-menu';
import { Sheet, SheetContent, SheetTrigger } from './ui/sheet';
import { LogOut, User, Menu } from 'lucide-react';
import { useIsMobile } from '../hooks/useMediaQuery';

const Header = ({ user, onLogout, onMenuClick }) => {
  const isMobile = useIsMobile();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="bg-[#1a1a2e] border-b border-gray-800 sticky top-0 z-50" data-testid="dashboard-header">
      <div className="px-4 md:px-6 py-3 md:py-4 flex items-center justify-between">
        <div className="flex items-center space-x-2 md:space-x-3" data-testid="header-branding">
          {/* Mobile Menu Button */}
          {isMobile && onMenuClick && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onMenuClick}
              className="md:hidden p-2 min-w-[44px] min-h-[44px]"
            >
              <Menu className="w-5 h-5 text-white" />
            </Button>
          )}
          
          <img
            src="/favicon.png"
            alt="TickleGram logo"
            className="w-8 h-8 md:w-10 md:h-10 rounded-lg"
          />
          <div className="hidden sm:block">
            <h1 className="text-lg md:text-xl font-bold text-white">TickleGram Dashboard</h1>
            <p className="text-xs text-gray-400 hidden md:block">DM Management</p>
          </div>
          <h1 className="text-lg font-bold text-white sm:hidden">TickleGram</h1>
        </div>

        {/* Desktop View */}
        <div className="hidden md:flex items-center space-x-4">
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

        {/* Mobile View - User Dropdown */}
        <div className="md:hidden">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button 
                variant="ghost" 
                size="sm"
                className="p-2 min-w-[44px] min-h-[44px]"
              >
                <div className="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center">
                  <User className="w-5 h-5 text-white" />
                </div>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent 
              align="end" 
              className="bg-[#1a1a2e] border-gray-700 w-56"
            >
              <div className="px-3 py-2 border-b border-gray-700">
                <p className="text-sm font-medium text-white" data-testid="user-name-mobile">{user.name}</p>
                <p className="text-xs text-gray-400 capitalize" data-testid="user-role-mobile">{user.role}</p>
              </div>
              <DropdownMenuSeparator className="bg-gray-700" />
              <DropdownMenuItem 
                onClick={onLogout}
                className="text-red-400 hover:bg-red-500/10 cursor-pointer min-h-[44px]"
                data-testid="logout-button-mobile"
              >
                <LogOut className="w-4 h-4 mr-2" />
                Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
};

export default Header;
