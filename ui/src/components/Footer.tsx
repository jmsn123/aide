import { FileText, Building2, Zap, Shield } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { SUPPORTED_BANKS } from '../constants/banks'

export function Footer() {
  const currentYear = new Date().getFullYear()
  const navigate = useNavigate()

  return (
    <footer className="bg-muted/30 border-t border-border/50 mt-auto">
      <div className="max-w-7xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-12 mb-8">
          {/* Brand Section */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 bg-gradient-to-br from-purple-600 to-blue-600 rounded-lg flex items-center justify-center">
                <FileText className="w-4 h-4 text-white" />
              </div>
              <h3 className="text-lg font-bold text-foreground">
                BankStatement<span className="text-purple-600">Pro</span>
              </h3>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed mb-4">
              Intelligent document processing for bank statements. Extract transaction data instantly with our serverless processing platform.
            </p>
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <div className="flex items-center gap-1">
                <Shield className="w-3 h-3 text-green-600" />
                <span>Secure</span>
              </div>
              <div className="flex items-center gap-1">
                <Zap className="w-3 h-3 text-yellow-600" />
                <span>Fast</span>
              </div>
              <div className="flex items-center gap-1">
                <Building2 className="w-3 h-3 text-blue-600" />
                <span>6 Banks</span>
              </div>
            </div>
          </div>

          {/* Supported Banks */}
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
              <Building2 className="w-4 h-4" />
              Supported Banks
            </h4>
            <ul className="grid grid-cols-1 gap-2 text-sm text-muted-foreground">
              {SUPPORTED_BANKS.map((bank) => (
                <li key={bank.id} className="flex items-center gap-2">
                  <div className="w-1 h-1 rounded-full bg-purple-600" />
                  {bank.name}
                </li>
              ))}
            </ul>
          </div>

          {/* Quick Actions */}
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-4">Get Started</h4>
            <button
              onClick={() => navigate('/dashboard')}
              className="w-full sm:w-auto px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white rounded-lg font-medium transition-all text-sm mb-4"
            >
              Upload Your Statement
            </button>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Support for password-protected PDFs, real-time processing, and instant Excel exports
            </p>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="border-t border-border/50 pt-6">
          <div className="flex flex-col sm:flex-row justify-center items-center gap-2 text-sm text-muted-foreground">
            <span>© {currentYear} BankStatementPro</span>
            <span className="hidden sm:inline">•</span>
            <span>Intelligent Document Processing</span>
          </div>
        </div>
      </div>
    </footer>
  )
}