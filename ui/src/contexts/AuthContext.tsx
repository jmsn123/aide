/**
 * Authentication Context Provider
 * Enterprise-grade global state management
 * Patterns from: Amazon AWS Amplify, Netflix authentication, Google Identity Platform
 *
 * Features:
 * - Global auth state with React Context
 * - Automatic token refresh
 * - Persistent sessions across page reloads
 * - Type-safe authentication methods
 * - Loading states for async operations
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import {
  type User,
  type AuthResponse,
  type SignupRequest,
  type LoginRequest,
  signup as signupAPI,
  login as loginAPI,
  logout as logoutAPI,
  getCurrentUser,
  isAuthenticated as checkAuth,
  refreshToken,
  tokenStorage
} from '../utils/auth'

// ===========================
// Context Types
// ===========================

interface AuthContextType {
  // State
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null

  // Methods
  signup: (data: SignupRequest) => Promise<AuthResponse>
  login: (data: LoginRequest) => Promise<AuthResponse>
  logout: () => void
  refreshUserSession: () => Promise<boolean>
  clearError: () => void
}

// ===========================
// Context Creation
// ===========================

const AuthContext = createContext<AuthContextType | undefined>(undefined)

// ===========================
// Provider Component
// ===========================

interface AuthProviderProps {
  children: React.ReactNode
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  // ===========================
  // State Management
  // ===========================

  const [user, setUser] = useState<User | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false)
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  // ===========================
  // Initialize Auth State
  // ===========================

  /**
   * Check for existing session on mount
   * Pattern: Netflix auto-login on page load
   */
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        // Check if user has valid session
        if (checkAuth()) {
          const currentUser = getCurrentUser()
          if (currentUser) {
            setUser(currentUser)
            setIsAuthenticated(true)

            // Check if token needs refresh (proactive refresh)
            if (tokenStorage.isTokenExpired()) {
              await refreshUserSession()
            }
          }
        }
      } catch (err) {
        console.error('Auth initialization error:', err)
        // Clear invalid session
        logoutAPI()
      } finally {
        setIsLoading(false)
      }
    }

    initializeAuth()
  }, [])

  // ===========================
  // Token Refresh Management
  // ===========================

  /**
   * Refresh user session tokens
   * Pattern: Google automatic token refresh
   */
  const refreshUserSession = useCallback(async (): Promise<boolean> => {
    try {
      const success = await refreshToken()
      if (success) {
        // Update user data from refreshed token
        const updatedUser = getCurrentUser()
        if (updatedUser) {
          setUser(updatedUser)
          setIsAuthenticated(true)
        }
        return true
      } else {
        // Refresh failed - logout user
        handleLogout()
        return false
      }
    } catch (err) {
      console.error('Token refresh failed:', err)
      handleLogout()
      return false
    }
  }, [])

  /**
   * Setup automatic token refresh
   * Pattern: Amazon Cognito automatic refresh before expiry
   */
  useEffect(() => {
    if (!isAuthenticated) return

    // Check token expiry every 5 minutes
    const REFRESH_INTERVAL = 5 * 60 * 1000 // 5 minutes

    const intervalId = setInterval(async () => {
      if (tokenStorage.isTokenExpired()) {
        console.log('Token expired, refreshing...')
        await refreshUserSession()
      }
    }, REFRESH_INTERVAL)

    return () => clearInterval(intervalId)
  }, [isAuthenticated, refreshUserSession])

  // ===========================
  // Authentication Methods
  // ===========================

  /**
   * Sign up new user
   * Pattern: Amazon Cognito signup with auto-login
   */
  const handleSignup = async (data: SignupRequest): Promise<AuthResponse> => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await signupAPI(data)

      if (response.success) {
        // Auto-login after successful signup
        const currentUser = getCurrentUser()
        if (currentUser) {
          setUser(currentUser)
          setIsAuthenticated(true)
        }
      } else if (response.error) {
        setError(response.error.message)
      }

      return response
    } catch (err) {
      const errorMessage = 'An unexpected error occurred during signup'
      setError(errorMessage)
      return {
        success: false,
        error: {
          code: 'UNKNOWN_ERROR',
          message: errorMessage
        }
      }
    } finally {
      setIsLoading(false)
    }
  }

  /**
   * Login existing user
   * Pattern: Google account signin with session persistence
   */
  const handleLogin = async (data: LoginRequest): Promise<AuthResponse> => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await loginAPI(data)

      if (response.success) {
        // Set user state from token
        const currentUser = getCurrentUser()
        if (currentUser) {
          setUser(currentUser)
          setIsAuthenticated(true)
        }
      } else if (response.error) {
        setError(response.error.message)
      }

      return response
    } catch (err) {
      const errorMessage = 'An unexpected error occurred during login'
      setError(errorMessage)
      return {
        success: false,
        error: {
          code: 'UNKNOWN_ERROR',
          message: errorMessage
        }
      }
    } finally {
      setIsLoading(false)
    }
  }

  /**
   * Logout user and clear session
   * Pattern: Amazon secure logout with state cleanup
   */
  const handleLogout = useCallback(() => {
    logoutAPI()
    setUser(null)
    setIsAuthenticated(false)
    setError(null)
  }, [])

  /**
   * Clear error state
   */
  const clearError = useCallback(() => {
    setError(null)
  }, [])

  // ===========================
  // Context Value
  // ===========================

  const value: AuthContextType = {
    // State
    user,
    isAuthenticated,
    isLoading,
    error,

    // Methods
    signup: handleSignup,
    login: handleLogin,
    logout: handleLogout,
    refreshUserSession,
    clearError
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// ===========================
// Custom Hook
// ===========================

/**
 * useAuth Hook - Access authentication context
 * Pattern: React best practices for context consumption
 *
 * Usage:
 * ```tsx
 * const { user, isAuthenticated, login, logout } = useAuth()
 * ```
 */
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext)

  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }

  return context
}

// Export context for advanced usage
export { AuthContext }
