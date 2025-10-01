/**
 * Login Page Component
 * Enterprise-grade signin experience
 * Design patterns from: Amazon login, Google signin, Netflix authentication
 *
 * Features:
 * - Clean, minimal design (Netflix-style)
 * - Real-time validation
 * - Password visibility toggle
 * - "Remember me" state management
 * - Deep linking support (return to intended page)
 * - Accessible form design (WCAG 2.1 AA)
 */

import React, { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Alert } from '../components/ui/alert'
import { Card } from '../components/ui/card'
import { Checkbox } from '../components/ui/checkbox'

// ===========================
// Types
// ===========================

interface FormErrors {
  email?: string
  password?: string
}

// ===========================
// Component
// ===========================

export const LoginPage: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { login, isAuthenticated, isLoading } = useAuth()

  // ===========================
  // State
  // ===========================

  const [formData, setFormData] = useState({
    email: '',
    password: '',
    rememberMe: false
  })

  const [errors, setErrors] = useState<FormErrors>({})
  const [apiError, setApiError] = useState<string>('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  // ===========================
  // Effects
  // ===========================

  /**
   * Redirect if already authenticated
   * Pattern: Google redirect logic with deep linking
   */
  useEffect(() => {
    if (isAuthenticated) {
      // Get intended destination or default to dashboard
      const from = (location.state as any)?.from?.pathname || '/dashboard'
      navigate(from, { replace: true })
    }
  }, [isAuthenticated, navigate, location])

  /**
   * Load saved email if "remember me" was used
   * Pattern: Amazon remembered email
   */
  useEffect(() => {
    const savedEmail = localStorage.getItem('remembered_email')
    if (savedEmail) {
      setFormData(prev => ({ ...prev, email: savedEmail, rememberMe: true }))
    }
  }, [])

  // ===========================
  // Validation
  // ===========================

  /**
   * Basic client-side validation
   * Pattern: Fail-fast validation to reduce API calls
   */
  const validateForm = (): boolean => {
    const newErrors: FormErrors = {}

    // Email validation
    if (!formData.email) {
      newErrors.email = 'Email is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email address'
    }

    // Password validation
    if (!formData.password) {
      newErrors.password = 'Password is required'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  // ===========================
  // Event Handlers
  // ===========================

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }))

    // Clear field error on change
    if (errors[name as keyof FormErrors]) {
      setErrors(prev => ({ ...prev, [name]: undefined }))
    }

    // Clear API error on any change
    if (apiError) {
      setApiError('')
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Client-side validation
    if (!validateForm()) return

    setIsSubmitting(true)
    setApiError('')

    try {
      const response = await login({
        email: formData.email.toLowerCase().trim(),
        password: formData.password
      })

      if (response.success) {
        // Handle "remember me"
        if (formData.rememberMe) {
          localStorage.setItem('remembered_email', formData.email)
        } else {
          localStorage.removeItem('remembered_email')
        }

        // Success - user will be auto-redirected by useEffect
      } else if (response.error) {
        // Generic error message (security: don't leak user existence)
        setApiError(response.error.message)
      }
    } catch (err) {
      setApiError('An unexpected error occurred. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  // ===========================
  // Render
  // ===========================

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-sky-100">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
          <p className="mt-2 text-sm text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-sky-100 px-4 py-12">
      <Card className="w-full max-w-md p-8 space-y-6 bg-white shadow-xl">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900">Welcome Back</h1>
          <p className="mt-2 text-sm text-gray-600">
            Sign in to access your bank statements
          </p>
        </div>

        {/* API Error Alert */}
        {apiError && (
          <Alert variant="destructive" className="text-sm">
            {apiError}
          </Alert>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Email Field */}
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              Email Address
            </label>
            <Input
              id="email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="john@example.com"
              className={errors.email ? 'border-red-500' : ''}
              disabled={isSubmitting}
              autoComplete="email"
              autoFocus
            />
            {errors.email && (
              <p className="mt-1 text-xs text-red-600">{errors.email}</p>
            )}
          </div>

          {/* Password Field */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Password
              </label>
              {/* Future: Password reset link */}
              {/* <Link to="/forgot-password" className="text-xs text-blue-600 hover:text-blue-700">
                Forgot password?
              </Link> */}
            </div>
            <div className="relative">
              <Input
                id="password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                value={formData.password}
                onChange={handleChange}
                placeholder="Enter your password"
                className={errors.password ? 'border-red-500' : ''}
                disabled={isSubmitting}
                autoComplete="current-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
                tabIndex={-1}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? '👁️' : '👁️‍🗨️'}
              </button>
            </div>
            {errors.password && (
              <p className="mt-1 text-xs text-red-600">{errors.password}</p>
            )}
          </div>

          {/* Remember Me Checkbox */}
          <div className="flex items-center">
            <Checkbox
              id="rememberMe"
              name="rememberMe"
              checked={formData.rememberMe}
              onCheckedChange={(checked) =>
                setFormData(prev => ({ ...prev, rememberMe: checked as boolean }))
              }
              disabled={isSubmitting}
            />
            <label
              htmlFor="rememberMe"
              className="ml-2 text-sm text-gray-700 cursor-pointer"
            >
              Remember my email
            </label>
          </div>

          {/* Submit Button */}
          <Button
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <span className="flex items-center justify-center gap-2">
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-solid border-white border-r-transparent"></span>
                Signing in...
              </span>
            ) : (
              'Sign In'
            )}
          </Button>
        </form>

        {/* Signup Link */}
        <div className="text-center text-sm">
          <span className="text-gray-600">Don't have an account? </span>
          <Link to="/signup" className="text-blue-600 hover:text-blue-700 font-medium">
            Create one now
          </Link>
        </div>

        {/* Security Notice */}
        <p className="text-xs text-center text-gray-500">
          Your connection is encrypted and secure.
        </p>
      </Card>
    </div>
  )
}
