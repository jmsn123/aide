import { FileText } from 'lucide-react'
import { Button } from './ui/button'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export function HomeHeader() {
  const navigate = useNavigate()
  const { isAuthenticated } = useAuth()

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border/50">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Brand */}
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity"
          aria-label="BankStatementPro Home"
        >
          <div className="w-9 h-9 bg-gradient-to-br from-purple-600 to-blue-600 rounded-lg flex items-center justify-center">
            <FileText className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-foreground">
              BankStatement<span className="text-purple-600">Pro</span>
            </h1>
          </div>
        </button>

        {/* Navigation - Show different buttons based on auth state */}
        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <Button
              onClick={() => navigate('/dashboard')}
              className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-medium"
              size="default"
            >
              Dashboard
            </Button>
          ) : (
            <>
              <Button
                onClick={() => navigate('/login')}
                variant="ghost"
                size="default"
                className="font-medium"
              >
                Log In
              </Button>
              <Button
                onClick={() => navigate('/signup')}
                className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-medium"
                size="default"
              >
                Sign Up
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  )
}