/**
 * Supported Banks Configuration
 * Single source of truth for all bank-related data across the application
 */

export interface BankInfo {
  id: string
  name: string
  color: string
}

export const SUPPORTED_BANKS: BankInfo[] = [
  { id: 'SBI', name: 'State Bank of India', color: 'from-blue-600 to-blue-800' },
  { id: 'AXIS', name: 'Axis Bank', color: 'from-red-600 to-rose-600' },
  { id: 'BOI', name: 'Bank of India', color: 'from-orange-600 to-amber-600' },
  { id: 'CANARA', name: 'Canara Bank', color: 'from-yellow-600 to-orange-600' },
  { id: 'UNION', name: 'Union Bank of India', color: 'from-green-600 to-emerald-600' },
  { id: 'APGVB', name: 'AP Grameena Bank', color: 'from-teal-600 to-cyan-600' },
]

export const BANK_COUNT = SUPPORTED_BANKS.length