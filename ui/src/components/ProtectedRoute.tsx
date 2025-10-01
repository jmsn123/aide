/**
 * Protected Route Component
 * Enterprise-grade route protection with deep linking
 * Patterns from: Amazon route guards, Google auth flows, Netflix protected content
 *
 * Features:
 * - Client-side auth check (no API call needed)
 * - Deep linking support (save intended destination)
 * - Loading state during auth initialization
 * - Automatic redirect to login
 * - Type-safe with TypeScript
 */

import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

// ===========================
// Types
// ===========================

interface ProtectedRouteProps {
  children: React.ReactNode
}

// ===========================
// Component
// ===========================

/**
 * ProtectedRoute - Wrapper component for authenticated routes
 *
 * Usage:
 * ```tsx
 * <Route path="/dashboard" element={
 *   <ProtectedRoute>
 *     <DashboardPage />
 *   </ProtectedRoute>
 * } />
 * ```
 *
 * Pattern: Amazon AWS Console route protection
 */
export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  // ===========================
  // Loading State
  // ===========================

  /**
   * Show loading spinner while checking authentication
   * Pattern: Netflix loading experience
   */
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="inline-block h-12 w-12 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
          <p className="mt-4 text-sm text-gray-600">Verifying authentication...</p>
        </div>
      </div>
    )
  }

  // ===========================
  // Authentication Check
  // ===========================

  /**
   * Redirect to login if not authenticated
   * Save current location for post-login redirect (deep linking)
   *
   * Pattern: Google account prompt with return URL
   */
  if (!isAuthenticated) {
    // Save intended destination in location state
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // ===========================
  // Render Protected Content
  // ===========================

  return <>{children}</>
}
