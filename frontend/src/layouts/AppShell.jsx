import React, { useMemo, useState, useCallback } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Menu, LogOut, Moon, Sun, ChevronDown } from 'lucide-react';
import { Sheet, SheetContent } from '../components/ui/sheet';
import { Button } from '../components/ui/button';
import { useTheme } from '../context/ThemeContext';
import { cn } from '../lib/utils';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '../components/ui/alert-dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '../components/ui/dropdown-menu';
import FacebookPageManager from '../components/FacebookPageManager';
import InstagramAccountManager from '../components/InstagramAccountManager';

/**
 * Route + layout map
 * ------------------
 * - src/App.js mounts AppShell for every authenticated route.
 * - Sidebar links (NavLink) map to:
 *     /inbox[/channel]      -> InboxLayout + InboxWorkspace (chat list + conversation)
 *     /templates            -> TemplatesLayout
 *     /comments             -> CommentsLayout (3 columns)
 *     /user-directory       -> AdminLayout
 *     /positions            -> AdminLayout
 * - Each page renders its module-specific layout inside {children}; AppShell only handles the
 *   persistent chrome (sidebar + mobile header) and theme toggling.
 */
const AppShell = ({ user, navItems = [], onLogout, children, sidebarExtras = null }) => {
  const { theme, toggleTheme } = useTheme();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [isSidebarExpanded, setSidebarExpanded] = useState(false);
  const [showInstagramManager, setShowInstagramManager] = useState(false);
  const [showFacebookManager, setShowFacebookManager] = useState(false);
  const navigate = useNavigate();

  const roleLabel = useMemo(() => {
    if (user?.position?.name) {
      return user.position.name;
    }
    if (user?.role) {
      return user.role.charAt(0).toUpperCase() + user.role.slice(1);
    }
    return 'User';
  }, [user]);

  const initials = useMemo(() => {
    if (!user?.name) {
      return 'TG';
    }
    return user.name
      .split(' ')
      .map((chunk) => chunk.charAt(0))
      .join('')
      .slice(0, 2)
      .toUpperCase();
  }, [user]);

  const avatarUrl = useMemo(() => {
    if (user?.avatar_url) {
      return user.avatar_url;
    }
    if (!user?.name) {
      return null;
    }
    const encoded = encodeURIComponent(user.name);
    return `https://ui-avatars.com/api/?name=${encoded}&background=4b5563&color=ffffff`;
  }, [user]);

  const renderAvatar = (sizeClass = 'w-10 h-10') => {
    if (avatarUrl) {
      return (
        <img
          src={avatarUrl}
          alt={user?.name}
          className={cn(
            sizeClass,
            'rounded-full object-cover border border-[var(--tg-border-soft)] shadow-[0_10px_25px_rgba(0,0,0,0.25)]'
          )}
        />
      );
    }
    return (
      <div
        className={cn(
          sizeClass,
          'rounded-full bg-gradient-to-br from-purple-500 via-pink-500 to-orange-400 text-white flex items-center justify-center text-sm font-semibold shadow-[0_10px_25px_rgba(0,0,0,0.25)]'
        )}
      >
        {initials}
      </div>
    );
  };

  const renderLogoutButton = ({ className = '', showLabel = false }) => (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size={showLabel ? 'default' : 'icon'}
          className={className}
        >
          <LogOut className="w-4 h-4" />
          {showLabel && <span>Logout</span>}
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent className="bg-[var(--tg-surface)] border border-[var(--tg-border-soft)] text-[var(--tg-text-primary)]">
        <AlertDialogHeader>
          <AlertDialogTitle>Sign out?</AlertDialogTitle>
          <AlertDialogDescription className="text-[var(--tg-text-muted)]">
            You will be logged out of TickleGram on this device. You can log back in anytime.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel className="bg-transparent border border-[var(--tg-border-soft)] text-[var(--tg-text-primary)]">
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
  );

  const handleManageNavClick = useCallback((destination) => {
    if (destination === 'instagram') {
      setShowInstagramManager(true);
    } else if (destination === 'facebook') {
      setShowFacebookManager(true);
    }
    setMobileNavOpen(false);
  }, []);

  const renderNavList = (expanded) => (
    <nav className="flex flex-col gap-1 mt-6">
      {navItems.map((item) => {
        const Icon = item.icon;
        const content = (
          <>
            {Icon && <Icon className="w-4 h-4 shrink-0" />}
            {expanded && <span className="truncate app-nav-label">{item.label}</span>}
            {expanded && item.badge && (
              <span className="app-nav-badge text-xs font-semibold px-2 py-0.5 rounded-full shrink-0">
                {item.badge}
              </span>
            )}
          </>
        );

        if (item.type === 'manage-pages' && item.menuItems?.length) {
          const menuSide = expanded ? 'bottom' : 'right';
          const menuAlign = expanded ? 'start' : 'end';
          return (
            <DropdownMenu key={item.id}>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  className={cn(
                    'app-nav-item flex items-center gap-3 px-2.5 py-1.5 rounded-xl text-sm font-medium transition-colors',
                    'app-nav-item--idle'
                  )}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    {content}
                  </div>
                  {expanded && <ChevronDown className="w-4 h-4 ml-auto opacity-70" />}
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                side={menuSide}
                align={menuAlign}
                sideOffset={expanded ? 6 : 12}
                className="min-w-[220px] bg-[var(--tg-surface)] border border-[var(--tg-border-soft)] text-[var(--tg-text-primary)]"
              >
                <DropdownMenuLabel className="text-xs uppercase tracking-wide text-[var(--tg-text-muted)]">
                  Manage connected pages
                </DropdownMenuLabel>
                <DropdownMenuSeparator className="bg-[var(--tg-border-soft)]" />
                {item.menuItems.map((menuItem) => {
                  const MenuIcon = menuItem.icon;
                  return (
                    <DropdownMenuItem
                      key={menuItem.id}
                      className="flex items-center gap-2"
                      onSelect={() => {
                        handleManageNavClick(menuItem.id);
                      }}
                    >
                      {MenuIcon && <MenuIcon className="w-4 h-4" />}
                      <span>{menuItem.label}</span>
                    </DropdownMenuItem>
                  );
                })}
              </DropdownMenuContent>
            </DropdownMenu>
          );
        }

        if (item.disabled || !item.to) {
          return (
            <button
              key={item.id}
              type="button"
              disabled
              className="app-nav-item flex items-center gap-3 px-2.5 py-1.5 rounded-xl text-sm font-medium opacity-40 cursor-not-allowed"
            >
              {content}
            </button>
          );
        }

        return (
          <NavLink
            key={item.id}
            to={item.to}
            end={item.exact}
            className={({ isActive }) =>
              cn(
                'app-nav-item flex items-center gap-3 px-2.5 py-1.5 rounded-xl text-sm font-medium transition-colors',
                isActive ? 'app-nav-item--active' : 'app-nav-item--idle'
              )
            }
            onClick={() => setMobileNavOpen(false)}
          >
            {content}
          </NavLink>
        );
      })}
    </nav>
  );

  const SidebarContent = (expanded) => {
    const extras = typeof sidebarExtras === 'function' ? sidebarExtras(expanded) : sidebarExtras;
    return (
    <div
      className={cn(
        'flex flex-col h-full px-3 py-4',
        expanded ? 'app-sidebar-expanded' : 'app-sidebar-collapsed'
      )}
    >
      <div className={cn('flex items-center gap-3', !expanded && 'justify-center')}>
        <img src="/favicon.png" alt="TickleGram" className="w-10 h-10 rounded-xl" />
        {expanded && (
          <div>
            <p className="text-base font-semibold leading-tight">TickleGram</p>
            <p className="text-xs text-[var(--tg-text-muted)]">Inbox Suite</p>
          </div>
        )}
      </div>
      {renderNavList(expanded)}
      {extras && (
        <div className="mt-4">
          {extras}
        </div>
      )}
      <div className="mt-auto space-y-3">
        <Button
          variant="ghost"
          onClick={toggleTheme}
          className={cn('w-full app-sidebar-toggle', expanded ? 'justify-between' : 'justify-center')}
        >
          <div className="flex items-center gap-2">
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            {expanded && <span>{theme === 'dark' ? 'Light mode' : 'Dark mode'}</span>}
          </div>
        </Button>
        {expanded ? (
          <div className="flex items-center gap-3 rounded-2xl bg-[var(--tg-surface-muted)] border border-[var(--tg-border-soft)] p-3">
            <button
              type="button"
              onClick={() => navigate('/profile')}
              className="flex items-center gap-3 flex-1 min-w-0 text-left"
            >
              {renderAvatar()}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold truncate">{user?.name}</p>
                <p className="text-xs text-[var(--tg-text-muted)] truncate">{roleLabel}</p>
              </div>
            </button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => navigate('/profile')}
              className="text-xs px-3 bg-gradient-to-r from-purple-500 via-pink-500 to-orange-400 text-white"
            >
              Profile
            </Button>
            {renderLogoutButton({
              className: 'text-[var(--tg-accent-strong)] hover:text-[var(--tg-accent-strong)]/80',
              showLabel: true
            })}
          </div>
        ) : (
          <button
            type="button"
            onClick={() => navigate('/profile')}
            className="flex items-center justify-center rounded-2xl bg-[var(--tg-surface-muted)] border border-[var(--tg-border-soft)] p-3 hover:border-[var(--tg-accent-soft)] transition"
          >
            {renderAvatar('w-12 h-12')}
          </button>
        )}
      </div>
    </div>
  );
  };

  return (
    <div className="app-shell flex min-h-screen bg-[var(--tg-app-bg)] text-[var(--tg-text-primary)]">
      <aside
        className="app-sidebar hidden md:flex"
        onMouseEnter={() => setSidebarExpanded(true)}
        onMouseLeave={() => setSidebarExpanded(false)}
      >
        {SidebarContent(false)}
        {isSidebarExpanded && (
          <div className="app-sidebar-flyout transition-all duration-300 ease-out opacity-100 translate-x-0 pointer-events-auto">
            {SidebarContent(true)}
          </div>
        )}
      </aside>

      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="p-6 w-[280px] bg-[var(--tg-sidebar-bg)] border-r border-[var(--tg-border-soft)]">
          {SidebarContent(true)}
        </SheetContent>
      </Sheet>

      <div className="flex-1 flex flex-col min-h-screen">
        <div className="app-shell__topbar flex items-center justify-between px-4 py-3 border-b border-[var(--tg-border-soft)] bg-[var(--tg-surface)] md:hidden">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setMobileNavOpen(true)}
              className="text-[var(--tg-text-primary)]"
            >
              <Menu className="w-5 h-5" />
            </Button>
            <span className="font-semibold">TickleGram Inbox</span>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            className="text-[var(--tg-text-primary)]"
          >
            {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </Button>
        </div>
        <main className="app-shell__content flex-1 flex flex-col min-h-0 overflow-hidden">
          {children}
        </main>
      </div>
      {showInstagramManager && (
        <InstagramAccountManager onClose={() => setShowInstagramManager(false)} />
      )}
      {showFacebookManager && (
        <FacebookPageManager onClose={() => setShowFacebookManager(false)} />
      )}
    </div>
  );
};

export default AppShell;
