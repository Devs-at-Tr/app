import React, { useMemo, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { Menu, LogOut, Moon, Sun } from 'lucide-react';
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
            'rounded-full object-cover border border-[var(--tg-border-soft)]'
          )}
        />
      );
    }
    return (
      <div
        className={cn(
          sizeClass,
          'rounded-full bg-[var(--tg-accent-strong)] text-white flex items-center justify-center text-sm font-semibold'
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

  const renderNavList = (expanded) => (
    <nav className="flex flex-col gap-1 mt-6">
      {navItems.map((item) => {
        const content = (
          <>
            {item.icon && <item.icon className="w-4 h-4 shrink-0" />}
            {expanded && <span className="truncate app-nav-label">{item.label}</span>}
            {expanded && item.badge && (
              <span className="app-nav-badge text-xs font-semibold px-2 py-0.5 rounded-full shrink-0">
                {item.badge}
              </span>
            )}
          </>
        );

        if (item.disabled || !item.to) {
          return (
            <button
              key={item.id}
              type="button"
              disabled
              className="app-nav-item flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium opacity-40 cursor-not-allowed"
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
                'app-nav-item flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-colors',
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
        'flex flex-col h-full px-3 py-6',
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
            {renderAvatar()}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold truncate">{user?.name}</p>
              <p className="text-xs text-[var(--tg-text-muted)] truncate">{roleLabel}</p>
            </div>
            {renderLogoutButton({
              className: 'text-[var(--tg-accent-strong)] hover:text-[var(--tg-accent-strong)]/80',
              showLabel: true
            })}
          </div>
        ) : (
          <div className="flex items-center justify-center rounded-2xl bg-[var(--tg-surface-muted)] border border-[var(--tg-border-soft)] p-3">
            {renderAvatar('w-12 h-12')}
          </div>
        )}
      </div>
    </div>
  );
  };

  return (
    <div className="app-shell flex min-h-screen bg-[var(--tg-app-bg)] text-[var(--tg-text-primary)]">
      <aside
        className="app-sidebar hidden lg:flex"
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
        <div className="app-shell__topbar flex items-center justify-between px-4 py-3 border-b border-[var(--tg-border-soft)] bg-[var(--tg-surface)] lg:hidden">
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
    </div>
  );
};

export default AppShell;
