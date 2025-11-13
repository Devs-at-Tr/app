import React from 'react';
import { Button } from './ui/button';
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator
} from './ui/dropdown-menu';
import { Sheet, SheetContent, SheetTrigger } from './ui/sheet';
import { LogOut, User, Menu, Sun, Moon } from 'lucide-react';
import { useIsMobile } from '../hooks/useMediaQuery';
import { useTheme } from '../context/ThemeContext';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogTrigger
} from './ui/alert-dialog';

const Header = ({ user, onLogout, onMenuClick }) => {
  const isMobile = useIsMobile();
  const { theme, toggleTheme } = useTheme();
  const roleLabel = React.useMemo(() => {
    if (user?.position?.name) {
      return user.position.name;
    }
    if (user?.role) {
      return user.role.charAt(0).toUpperCase() + user.role.slice(1);
    }
    return 'User';
  }, [user]);

  const themeToggleText = theme === 'dark' ? 'Light Mode' : 'Dark Mode';
  const themeToggleIcon = theme === 'dark' ? <Sun className="w-4 h-4 mr-2" /> : <Moon className="w-4 h-4 mr-2" />;
  const themeToggleClass =
    theme === 'dark'
      ? 'theme-toggle theme-toggle--dark'
      : 'theme-toggle theme-toggle--light';

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
          <Button
            variant="ghost"
            onClick={toggleTheme}
            className={themeToggleClass}
            data-testid="theme-toggle"
          >
            {themeToggleIcon}
            {themeToggleText}
          </Button>
          <div className="flex items-center space-x-2 px-4 py-2 bg-[#0f0f1a] rounded-lg border border-gray-800">
            <User className="w-4 h-4 text-purple-400" />
            <div>
              <p className="text-sm font-medium text-white" data-testid="user-name">{user.name}</p>
              <p className="text-xs text-gray-400" data-testid="user-role">{roleLabel}</p>
            </div>
          </div>
          
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                data-testid="logout-button"
                variant="outline"
                className="bg-red-500/10 border-red-500/50 hover:bg-red-500/20 text-red-400"
              >
                <LogOut className="w-4 h-4 mr-2" />
                Logout
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent className="bg-[#1a1a2e] border-gray-700 text-white">
              <AlertDialogHeader>
                <AlertDialogTitle>Sign out?</AlertDialogTitle>
                <AlertDialogDescription className="text-gray-400">
                  You will be logged out of TickleGram on this device. You can log back in anytime.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel className="bg-transparent border border-gray-700 text-gray-300 hover:bg-gray-800">
                  Stay
                </AlertDialogCancel>
                <AlertDialogAction
                  onClick={onLogout}
                  className="bg-gradient-to-r from-red-500 to-rose-500 text-white hover:from-red-600 hover:to-rose-600"
                >
                  Logout
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
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
                <p className="text-xs text-gray-400" data-testid="user-role-mobile">{roleLabel}</p>
              </div>
              <DropdownMenuItem
                onClick={toggleTheme}
                className="text-sm text-gray-200 hover:bg-purple-500/10 cursor-pointer min-h-[44px]"
              >
                {theme === 'dark' ? (
                  <>
                    <Sun className="w-4 h-4 mr-2 text-amber-300" />
                    Light Mode
                  </>
                ) : (
                  <>
                    <Moon className="w-4 h-4 mr-2 text-purple-400" />
                    Dark Mode
                  </>
                )}
              </DropdownMenuItem>
              <DropdownMenuSeparator className="bg-gray-700" />
              <DropdownMenuItem asChild data-testid="logout-button-mobile">
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <button className="w-full text-left text-red-400 hover:bg-red-500/10 cursor-pointer min-h-[44px] flex items-center">
                      <LogOut className="w-4 h-4 mr-2" />
                      Logout
                    </button>
                  </AlertDialogTrigger>
                  <AlertDialogContent className="bg-[#1a1a2e] border-gray-700 text-white">
                    <AlertDialogHeader>
                      <AlertDialogTitle>Sign out?</AlertDialogTitle>
                      <AlertDialogDescription className="text-gray-400">
                        You will be logged out of TickleGram on this device. You can log back in anytime.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel className="bg-transparent border border-gray-700 text-gray-300 hover:bg-gray-800">
                        Stay
                      </AlertDialogCancel>
                      <AlertDialogAction
                        onClick={onLogout}
                        className="bg-gradient-to-r from-red-500 to-rose-500 text-white hover:from-red-600 hover:to-rose-600"
                      >
                        Logout
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
};

export default Header;
