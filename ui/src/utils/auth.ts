/**
 * Authentication Utility Module
 * Enterprise-grade auth patterns from Amazon, Netflix, Google
 *
 * Features:
 * - Secure JWT token management
 * - Exponential backoff retry logic
 * - Client-side token validation
 * - Type-safe API interactions
 */

import { buildApiUrl } from '../config/api'

// ===========================
// Types & Interfaces
// ===========================

export interface User {
  id: string
  email: string
  name: string
  email_verified?: boolean
  created_at?: string
}

export interface AuthTokens {
  access_token: string
  id_token: string
  refresh_token: string
  expires_in: number
  token_type: string
}

export interface SignupRequest {
  name: string
  email: string
  password: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface AuthResponse {
  success: boolean
  data?: AuthTokens & { user?: User }
  error?: {
    code: string
    message: string
  }
  message?: string
}

// ===========================
// Storage Keys
// ===========================

const STORAGE_KEYS = {
  ACCESS_TOKEN: 'access_token',
  ID_TOKEN: 'id_token',
  REFRESH_TOKEN: 'refresh_token',
  USER: 'user',
  TOKEN_EXPIRY: 'token_expiry'
} as const

// ===========================
// Token Management (Secure)
// ===========================

export const tokenStorage = {
  /**
   * Save auth tokens securely to localStorage
   * Pattern: Netflix token persistence
   */
  saveTokens: (tokens: AuthTokens, user?: User): void => {
    try {
      localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, tokens.access_token)
      localStorage.setItem(STORAGE_KEYS.ID_TOKEN, tokens.id_token)
      localStorage.setItem(STORAGE_KEYS.REFRESH_TOKEN, tokens.refresh_token)

      // Calculate and store expiry timestamp
      const expiryTime = Date.now() + (tokens.expires_in * 1000)
      localStorage.setItem(STORAGE_KEYS.TOKEN_EXPIRY, expiryTime.toString())

      if (user) {
        localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user))
      }
    } catch (error) {
      console.error('Failed to save tokens:', error)
      // Fail silently - user will need to re-login
    }
  },

  /**
   * Retrieve access token for API calls
   */
  getAccessToken: (): string | null => {
    try {
      return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN)
    } catch {
      return null
    }
  },

  /**
   * Retrieve ID token (contains user claims)
   */
  getIdToken: (): string | null => {
    try {
      return localStorage.getItem(STORAGE_KEYS.ID_TOKEN)
    } catch {
      return null
    }
  },

  /**
   * Retrieve refresh token
   */
  getRefreshToken: (): string | null => {
    try {
      return localStorage.getItem(STORAGE_KEYS.REFRESH_TOKEN)
    } catch {
      return null
    }
  },

  /**
   * Get stored user data
   */
  getUser: (): User | null => {
    try {
      const userStr = localStorage.getItem(STORAGE_KEYS.USER)
      return userStr ? JSON.parse(userStr) : null
    } catch {
      return null
    }
  },

  /**
   * Check if access token is expired
   * Pattern: Google proactive token refresh
   */
  isTokenExpired: (): boolean => {
    try {
      const expiryStr = localStorage.getItem(STORAGE_KEYS.TOKEN_EXPIRY)
      if (!expiryStr) return true

      const expiry = parseInt(expiryStr, 10)
      // Add 5 minute buffer for clock skew (AWS best practice)
      return Date.now() >= (expiry - 300000)
    } catch {
      return true
    }
  },

  /**
   * Clear all auth tokens
   * Pattern: Amazon secure logout
   */
  clearTokens: (): void => {
    try {
      localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN)
      localStorage.removeItem(STORAGE_KEYS.ID_TOKEN)
      localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN)
      localStorage.removeItem(STORAGE_KEYS.USER)
      localStorage.removeItem(STORAGE_KEYS.TOKEN_EXPIRY)
    } catch (error) {
      console.error('Failed to clear tokens:', error)
    }
  }
}

// ===========================
// JWT Parsing (Client-side)
// ===========================

/**
 * Parse JWT token claims without verification (client-side only)
 * Used for extracting user info from ID token
 * Pattern: Used by all major auth providers for client-side display
 */
export const parseJWT = (token: string): any => {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )
    return JSON.parse(jsonPayload)
  } catch {
    return null
  }
}

/**
 * Extract user information from ID token
 */
export const getUserFromToken = (): User | null => {
  const idToken = tokenStorage.getIdToken()
  if (!idToken) return null

  const claims = parseJWT(idToken)
  if (!claims) return null

  return {
    id: claims.sub || claims['cognito:username'],
    email: claims.email,
    name: claims.name || claims.email?.split('@')[0],
    email_verified: claims.email_verified,
    created_at: claims.auth_time ? new Date(claims.auth_time * 1000).toISOString() : undefined
  }
}

// ===========================
// API Client with Retry Logic
// ===========================

/**
 * Exponential backoff retry configuration
 * Pattern: Netflix resilience engineering
 */
const RETRY_CONFIG = {
  MAX_RETRIES: 3,
  MAX_DELAY_MS: 10000, // 10 second
  BASE_DELAY_MS: 1000, // 1 seconds
BACKOFF_MULTIPLIER: 2

} as const ;

/**
 * Sleep utility for retry delays
 */
const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

/**
 * Calculate exponential backoff delay
 */
const getRetryDelay = (attempt: number): number => {
  const delay = RETRY_CONFIG.BASE_DELAY_MS * Math.pow(RETRY_CONFIG.BACKOFF_MULTIPLIER, attempt)
  return Math.min(delay, RETRY_CONFIG.MAX_DELAY_MS)
}

/**
 * Make API request with exponential backoff retry
 * Pattern: Google Cloud client libraries retry logic
 */
const fetchWithRetry = async (
  url: string,
  options: RequestInit,
  retryCount = 0
): Promise<Response> => {
  try {
    const response = await fetch(url, options)

    // Retry on 5xx server errors or network issues
    if (response.status >= 500 && retryCount < RETRY_CONFIG.MAX_RETRIES) {
      const delay = getRetryDelay(retryCount)
      console.warn(`Request failed with ${response.status}, retrying in ${delay}ms...`)
      await sleep(delay)
      return fetchWithRetry(url, options, retryCount + 1)
    }

    return response
  } catch (error) {
    // Network error - retry
    if (retryCount < RETRY_CONFIG.MAX_RETRIES) {
      const delay = getRetryDelay(retryCount)
      console.warn(`Network error, retrying in ${delay}ms...`, error)
      await sleep(delay)
      return fetchWithRetry(url, options, retryCount + 1)
    }
    throw error
  }
}

// ===========================
// Authentication API Calls
// ===========================

/**
 * Sign up new user
 * Pattern: Amazon Cognito signup flow
 */
export const signup = async (data: SignupRequest): Promise<AuthResponse> => {
  try {
    const url = buildApiUrl('/auth/signup')
    const response = await fetchWithRetry(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    })

    const result: AuthResponse = await response.json()

    if (response.ok && result.success && result.data) {
      // Extract user from ID token
      const user = parseJWT(result.data.id_token)
      const userData: User = {
        id: user.sub || user['cognito:username'],
        email: user.email,
        name: user.name || data.name,
        email_verified: user.email_verified
      }

      // Save tokens and user data
      tokenStorage.saveTokens(result.data, userData)
    }

    return result
  } catch (error) {
    console.error('Signup error:', error)
    return {
      success: false,
      error: {
        code: 'NETWORK_ERROR',
        message: 'Unable to connect to server. Please check your internet connection.'
      }
    }
  }
}

/**
 * Login existing user
 * Pattern: Google account signin
 */
export const login = async (data: LoginRequest): Promise<AuthResponse> => {
  try {
    const url = buildApiUrl('/auth/login')
    const response = await fetchWithRetry(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data)
    })

    const result: AuthResponse = await response.json()

    if (response.ok && result.success && result.data) {
      // Extract user from ID token
      const user = parseJWT(result.data.id_token)
      const userData: User = {
        id: user.sub || user['cognito:username'],
        email: user.email,
        name: user.name || user.email?.split('@')[0],
        email_verified: user.email_verified
      }

      // Save tokens and user data
      tokenStorage.saveTokens(result.data, userData)
    }

    return result
  } catch (error) {
    console.error('Login error:', error)
    return {
      success: false,
      error: {
        code: 'NETWORK_ERROR',
        message: 'Unable to connect to server. Please check your internet connection.'
      }
    }
  }
}

/**
 * Refresh access token using refresh token
 * Pattern: Netflix automatic token refresh
 */
export const refreshToken = async (): Promise<boolean> => {
  try {
    const refresh_token = tokenStorage.getRefreshToken()
    if (!refresh_token) return false

    const url = buildApiUrl('/auth/refresh')
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token })
    })

    const result: AuthResponse = await response.json()

    if (response.ok && result.success && result.data) {
      // Update tokens (refresh token stays the same)
      const currentUser = tokenStorage.getUser()
      tokenStorage.saveTokens(result.data, currentUser || undefined)
      return true
    }

    return false
  } catch (error) {
    console.error('Token refresh error:', error)
    return false
  }
}

/**
 * Logout user and clear session
 * Pattern: Amazon secure session termination
 */
export const logout = (): void => {
  tokenStorage.clearTokens()
}

/**
 * Check if user is authenticated
 */
export const isAuthenticated = (): boolean => {
  const accessToken = tokenStorage.getAccessToken()
  return !!accessToken && !tokenStorage.isTokenExpired()
}

/**
 * Get current authenticated user
 */
export const getCurrentUser = (): User | null => {
  if (!isAuthenticated()) return null

  // Try to get from storage first
  let user = tokenStorage.getUser()

  // If not in storage, extract from ID token
  if (!user) {
    user = getUserFromToken()
    if (user) {
      // Cache for future use
      localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user))
    }
  }

  return user
}

/**
 * Get authorization header for API requests
 * Pattern: Standard Bearer token authentication
 */
export const getAuthHeader = (): Record<string, string> => {
  const token = tokenStorage.getAccessToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}
