import React, { useState, useEffect } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { useUser } from '../context/UserContext';
import { api } from '../api/client';
import {
  ChartBarIcon,
  ShieldCheckIcon,
  DocumentMagnifyingGlassIcon,
  WrenchScrewdriverIcon,
  CheckBadgeIcon,
  FolderArrowDownIcon,
  ExclamationCircleIcon,
  ClockIcon,
  ChatBubbleLeftRightIcon,
  UserCircleIcon,
  BuildingOfficeIcon,
  ChevronDownIcon,
  Bars3Icon,
  XMarkIcon,
  CpuChipIcon,
} from '@heroicons/react/24/outline';
import clsx from 'clsx';

const NAVIGATION = [
  { name: 'Dashboard', href: '/', icon: ChartBarIcon },
  { name: 'Compliance Monitor', href: '/compliance', icon: ShieldCheckIcon },
  { name: 'Findings Review', href: '/findings', icon: DocumentMagnifyingGlassIcon },
  { name: 'Remediation Tracker', href: '/remediations', icon: WrenchScrewdriverIcon },
  { name: 'Evidence Verifier', href: '/evidence', icon: CheckBadgeIcon },
  { name: 'Document Centre', href: '/documents', icon: FolderArrowDownIcon },
  { name: 'Risk Intelligence', href: '/risks', icon: ExclamationCircleIcon },
  { name: 'Audit History', href: '/history', icon: ClockIcon },
  { name: 'AI Audit Assistant', href: '/assistant', icon: ChatBubbleLeftRightIcon },
  { name: 'Memory Explorer', href: '/memory', icon: CpuChipIcon },
];

export const Layout: React.FC = () => {
  const { currentUser, users, organisationName, switchUser } = useUser();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const location = useLocation();

  useEffect(() => {
    // Check health once on mount
    api.getHealth()
      .then(() => setApiOnline(true))
      .catch(() => setApiOnline(false));
  }, []);

  const getRoleBadge = (role: string) => {
    switch (role) {
      case 'admin':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'compliance_officer':
        return 'bg-teal-100 text-teal-800 border-teal-200';
      case 'control_owner':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'auditor':
        return 'bg-amber-100 text-amber-800 border-amber-200';
      default:
        return 'bg-slate-100 text-slate-800 border-slate-200';
    }
  };

  const formatRole = (role?: string) => {
    if (!role) return '';
    return role.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <div className="min-h-screen flex bg-slate-50 text-slate-900 font-sans">
      {/* Mobile sidebar backdrop */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/60 lg:hidden backdrop-blur-xs"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar Desktop & Mobile */}
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-50 w-64 bg-slate-900 text-slate-300 flex flex-col transition-transform duration-300 ease-in-out lg:static lg:translate-x-0 border-r border-slate-800',
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Brand / Logo */}
        <div className="h-16 flex items-center justify-between px-6 bg-slate-950/80 border-b border-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-teal-500 flex items-center justify-center text-slate-950 font-black shadow-md shadow-teal-500/20">
              A
            </div>
            <div>
              <span className="text-base font-bold text-white tracking-tight">AuditMind AI</span>
              <span className="block text-[10px] text-teal-400 font-medium uppercase tracking-wider">
                Enterprise Assurance
              </span>
            </div>
          </div>
          <button
            type="button"
            className="lg:hidden text-slate-400 hover:text-white"
            onClick={() => setMobileMenuOpen(false)}
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Organisation identifier */}
        <div className="px-6 py-3 bg-slate-900/60 border-b border-slate-800/60 flex items-center gap-2 text-xs text-slate-400">
          <BuildingOfficeIcon className="w-4 h-4 text-slate-500 shrink-0" />
          <span className="truncate font-medium text-slate-300">{organisationName}</span>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
          {NAVIGATION.map((item) => {
            const isActive =
              item.href === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(item.href);

            const Icon = item.icon;
            return (
              <NavLink
                key={item.name}
                to={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all group',
                  isActive
                    ? 'bg-teal-600/20 text-teal-300 font-semibold border-l-3 border-teal-400 shadow-inner'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                )}
              >
                <Icon
                  className={clsx(
                    'w-5 h-5 shrink-0 transition-colors',
                    isActive ? 'text-teal-400' : 'text-slate-500 group-hover:text-slate-300'
                  )}
                />
                <span className="truncate">{item.name}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Audit Advisory Notice in Sidebar */}
        <div className="p-4 m-3 rounded-lg bg-slate-950/70 border border-slate-800/80 text-[11px] text-slate-400 space-y-1">
          <div className="font-semibold text-slate-300 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-teal-400"></span>
            AI Advisory Contract
          </div>
          <p className="leading-tight text-slate-400">
            AI findings remain Draft until explicitly approved by an authorized reviewer.
          </p>
        </div>

        {/* Backend health status badge at bottom */}
        <div className="px-4 py-3 bg-slate-950 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
          <span className="flex items-center gap-2">
            <span
              className={clsx(
                'w-2 h-2 rounded-full',
                apiOnline === true ? 'bg-emerald-400 animate-pulse' : apiOnline === false ? 'bg-rose-500' : 'bg-slate-500'
              )}
            />
            <span>{apiOnline ? 'API Connected' : 'API Connecting...'}</span>
          </span>
          <span className="text-[10px] text-slate-500 font-mono">v0.1.0</span>
        </div>
      </aside>

      {/* Main Content Viewport */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-4 sm:px-6 z-30 sticky top-0 shadow-xs">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="lg:hidden p-2 rounded-md text-slate-600 hover:text-slate-900 hover:bg-slate-100"
              onClick={() => setMobileMenuOpen(true)}
            >
              <Bars3Icon className="w-6 h-6" />
            </button>
            <div className="hidden sm:block">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                Organization:
              </span>
              <span className="ml-1.5 text-sm font-semibold text-slate-800">
                {organisationName}
              </span>
            </div>
          </div>

          {/* Quick Persona Buttons */}
          <div className="flex items-center gap-3">
            <div className="hidden xl:flex items-center gap-1.5 bg-slate-100 p-1 rounded-lg border border-slate-200">
              {users.map((u) => {
                const isSelected = currentUser?.id === u.id;
                const roleBadgeClass =
                  u.role === 'admin'
                    ? 'bg-purple-600 text-white shadow-xs'
                    : u.role === 'compliance_officer'
                    ? 'bg-teal-600 text-white shadow-xs'
                    : u.role === 'control_owner'
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'bg-amber-600 text-white shadow-xs';

                return (
                  <button
                    key={u.id}
                    type="button"
                    onClick={() => switchUser(u)}
                    className={clsx(
                      'px-2.5 py-1 text-xs font-bold rounded-md transition flex items-center gap-1',
                      isSelected
                        ? roleBadgeClass
                        : 'text-slate-600 hover:bg-slate-200 hover:text-slate-900'
                    )}
                    title={`Switch persona to ${u.name}`}
                  >
                    <span>{u.role === 'admin' ? '👑' : u.role === 'compliance_officer' ? '🛡️' : u.role === 'control_owner' ? '⚙️' : '🔍'}</span>
                    <span>{u.name.split(' ')[0]}</span>
                  </button>
                );
              })}
            </div>

            {/* User Switcher Dropdown */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setUserDropdownOpen(!userDropdownOpen)}
                className="flex items-center gap-3 p-1.5 sm:px-3 sm:py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 transition bg-white shadow-xs"
                aria-label="User switcher"
              >
              <div className="w-7 h-7 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center font-bold text-xs shrink-0">
                {currentUser?.name ? currentUser.name.charAt(0) : <UserCircleIcon className="w-5 h-5" />}
              </div>
              <div className="text-left hidden md:block">
                <div className="text-xs font-bold text-slate-800 truncate max-w-[130px]">
                  {currentUser?.name || 'Select User'}
                </div>
                <div className="text-[10px] text-slate-500 truncate max-w-[130px]">
                  {currentUser?.email || ''}
                </div>
              </div>
              <span
                className={clsx(
                  'text-[10px] font-semibold px-2 py-0.5 rounded-full border hidden sm:inline-block',
                  getRoleBadge(currentUser?.role || '')
                )}
              >
                {formatRole(currentUser?.role)}
              </span>
              <ChevronDownIcon className="w-4 h-4 text-slate-400 shrink-0" />
            </button>

            {/* Dropdown Menu */}
            {userDropdownOpen && (
              <>
                <div
                  className="fixed inset-0 z-30"
                  onClick={() => setUserDropdownOpen(false)}
                />
                <div className="absolute right-0 mt-2 w-72 rounded-xl bg-white shadow-xl border border-slate-200 z-40 py-2 divide-y divide-slate-100 animate-slide-down">
                  <div className="px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400 bg-slate-50/50">
                    Switch Test Persona (X-User-Id)
                  </div>
                  <div className="py-1">
                    {users.map((u) => {
                      const isSelected = currentUser?.id === u.id;
                      return (
                        <button
                          key={u.id || u.email}
                          type="button"
                          onClick={() => {
                            switchUser(u);
                            setUserDropdownOpen(false);
                          }}
                          className={clsx(
                            'w-full text-left px-4 py-2.5 text-xs flex items-center justify-between hover:bg-slate-50 transition',
                            isSelected && 'bg-teal-50/60 font-semibold'
                          )}
                        >
                          <div>
                            <div className="font-medium text-slate-800">{u.name}</div>
                            <div className="text-[11px] text-slate-500 font-mono">{u.email}</div>
                          </div>
                          <span
                            className={clsx(
                              'text-[10px] font-medium px-2 py-0.5 rounded-full border',
                              getRoleBadge(u.role)
                            )}
                          >
                            {formatRole(u.role)}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                  <div className="px-4 py-2 text-[10px] text-slate-400 bg-slate-50">
                    Active UUID: <span className="font-mono text-slate-600">{currentUser?.id?.slice(0, 13)}...</span>
                  </div>
                </div>
              </>
            )}
          </div>
        </header>

        {/* Dynamic Role Capabilities Banner */}
        <div
          className={clsx(
            'px-4 sm:px-6 py-2 border-b text-xs flex flex-wrap items-center justify-between gap-3 transition-colors',
            currentUser?.role === 'admin' && 'bg-purple-50 border-purple-200 text-purple-900',
            currentUser?.role === 'compliance_officer' && 'bg-teal-50 border-teal-200 text-teal-900',
            currentUser?.role === 'control_owner' && 'bg-blue-50 border-blue-200 text-blue-900',
            currentUser?.role === 'auditor' && 'bg-amber-50 border-amber-200 text-amber-900'
          )}
        >
          <div className="flex items-center gap-2">
            <span className="font-extrabold uppercase tracking-wide text-[11px] px-2 py-0.5 rounded bg-white/80 border">
              {formatRole(currentUser?.role)} Persona Active
            </span>
            <span className="font-medium text-xs">
              {currentUser?.role === 'admin'
                ? 'Superuser: full authority to configure controls, approve findings, and sign off remediations.'
                : currentUser?.role === 'compliance_officer'
                ? 'Authorized to approve AI findings, verify evidence, and sign off completed remediations.'
                : currentUser?.role === 'control_owner'
                ? 'Control Owner (IT Ops): can advance assigned remediation progress. Finding approval and closure restricted.'
                : 'Internal Auditor: independent audit oversight (Read-Only on remediations and control status changes).'}
            </span>
          </div>

          <div className="flex items-center gap-3 text-[11px]">
            <span>
              Approve Findings:{' '}
              <strong className={currentUser?.role !== 'control_owner' && currentUser?.role !== 'auditor' ? 'text-emerald-700 font-bold' : 'text-rose-600 font-bold'}>
                {currentUser?.role !== 'control_owner' && currentUser?.role !== 'auditor' ? 'YES' : 'DISABLED'}
              </strong>
            </span>
            <span>•</span>
            <span>
              Sign-off Remediations:{' '}
              <strong className={currentUser?.role === 'admin' || currentUser?.role === 'compliance_officer' ? 'text-emerald-700 font-bold' : 'text-rose-600 font-bold'}>
                {currentUser?.role === 'admin' || currentUser?.role === 'compliance_officer' ? 'YES' : 'DISABLED'}
              </strong>
            </span>
          </div>
        </div>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 bg-slate-50/70">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default Layout;
