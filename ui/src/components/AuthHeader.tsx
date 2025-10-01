/**
 * Authenticated User Header Component
 * Enterprise-grade navigation for authenticated users
 * Patterns from: Amazon AWS Console, Google Cloud Console, Netflix user menu
 *
 * Features:
 * - User profile display
 * - Dropdown menu with logout
 * - Navigation links
 * - Responsive design
 * - Accessible keyboard navigation
 */

import { FileText, LogOut, ChevronDown } from 'lucide-react'
import { Button } from './ui/button'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from './ui/dropdown-menu'

export function AuthHeader() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()

  const handleLogout = () => {
    logout()
    navigate('/', { replace: true })
  }

  const isActive = (path: string) => location.pathname === path

  return (
    <header className="sticky top-0 left-0 right-0 z-50 bg-background/95 backdrop-blur-md border-b border-border/50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Brand & Navigation */}
        <div className="flex items-center gap-8">
          {/* Brand */}
          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
            aria-label="BankStatementPro Dashboard"
          >
            <div className="w-8 h-8 bg-gradient-to-br icon-brand rounded-lg flex items-center justify-center">
              <FileText className="w-4 h-4 text-white" />
            </div>
            <div className="hidden sm:block">
              <h1 className="text-base font-bold text-foreground">
                BankStatement<span className="text-blue-600">Pro</span>
              </h1>
            </div>
          </button>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1">
            <Button
              variant={isActive('/dashboard') ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => navigate('/dashboard')}
              className="font-medium"
            >
              Dashboard
            </Button>
          </nav>
        </div>

        {/* User Menu */}
        <div className="flex items-center gap-3">
          {/* User Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="flex items-center gap-2 pl-2">
                {/* User Avatar */}
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-sky-500 to-blue-500 flex items-center justify-center text-white text-sm font-semibold">
                  {user?.name?.charAt(0).toUpperCase() || 'U'}
                </div>

                {/* User Info (hidden on mobile) */}
                <div className="hidden sm:flex flex-col items-start">
                  <span className="text-sm font-medium text-foreground leading-none">
                    {user?.name || 'User'}
                  </span>
                  <span className="text-xs text-muted-foreground leading-none mt-1">
                    {user?.email}
                  </span>
                </div>

                <ChevronDown className="w-4 h-4 text-muted-foreground" />
              </Button>
            </DropdownMenuTrigger>

            <DropdownMenuContent align="end" className="w-56">
              {/* User Info Header */}
              <DropdownMenuLabel>
                <div className="flex flex-col">
                  <span className="font-medium">{user?.name || 'User'}</span>
                  <span className="text-xs text-muted-foreground font-normal">
                    {user?.email}
                  </span>
                </div>
              </DropdownMenuLabel>

              <DropdownMenuSeparator />

              {/* Future: Profile & Settings */}
              {/*
              <DropdownMenuItem onClick={() => navigate('/profile')}>
                <User className="w-4 h-4 mr-2" />
                Profile
              </DropdownMenuItem>
              */}

              {/* Logout */}
              <DropdownMenuItem onClick={handleLogout} className="text-red-600 focus:text-red-600">
                <LogOut className="w-4 h-4 mr-2" />
                Log Out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}
