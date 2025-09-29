import { useState, useMemo, useCallback, useRef, useEffect } from 'react'

/**
 * Configuration options for the usePagination hook
 */
export interface PaginationOptions {
  /** Initial page to start on (default: 1) */
  initialPage?: number
  /** Initial number of items per page (default: 10) */
  initialItemsPerPage?: number
  /** Enable keyboard navigation with arrow keys (default: true) */
  enableKeyboardNavigation?: boolean
  /** Debounce delay for keyboard navigation in milliseconds (default: 150) */
  debounceMs?: number
}

/**
 * Return type for the usePagination hook containing pagination state and handlers
 * @template T The type of items being paginated
 */
export interface PaginationResult<T> {
  // Data
  /** Array of items for the current page */
  currentItems: T[]

  // State
  /** Current active page number (1-based) */
  currentPage: number
  /** Number of items displayed per page */
  itemsPerPage: number
  /** Total number of items in the dataset */
  totalItems: number
  /** Total number of pages available */
  totalPages: number
  /** Zero-based start index for current page items */
  startIndex: number
  /** Zero-based end index for current page items */
  endIndex: number
  /** Whether a page change animation is in progress */
  isPageChanging: boolean

  // Handlers
  /** Navigate to a specific page with validation and smooth scrolling */
  handlePageChange: (page: number) => void
  /** Change the number of items displayed per page */
  handleItemsPerPageChange: (newItemsPerPage: number) => void
  /** Reset pagination to first page and clear loading states */
  resetPagination: () => void
  /** Manually control the page changing loading state */
  setIsPageChanging: (isChanging: boolean) => void
}

/**
 * Custom hook for managing pagination state and behavior with advanced features
 *
 * Features:
 * - Automatic validation of page numbers and items per page
 * - Smooth scrolling to table top on page changes
 * - Debounced keyboard navigation (arrow keys)
 * - Input field detection to prevent navigation conflicts
 * - Loading states with opacity transitions
 * - Error boundary compatible design
 *
 * @template T The type of items being paginated
 * @param items Array of items to paginate
 * @param options Configuration options for pagination behavior
 * @returns Pagination state, handlers, and computed values
 *
 * @example
 * ```tsx
 * const pagination = usePagination(bankStatements, {
 *   initialItemsPerPage: 10,
 *   enableKeyboardNavigation: true,
 *   debounceMs: 150
 * })
 *
 * // Use in JSX
 * <PaginationInfo
 *   currentPage={pagination.currentPage}
 *   totalPages={pagination.totalPages}
 *   totalItems={pagination.totalItems}
 *   itemsPerPage={pagination.itemsPerPage}
 *   onItemsPerPageChange={pagination.handleItemsPerPageChange}
 * />
 * ```
 */
export function usePagination<T>(
  items: T[],
  options: PaginationOptions = {}
): PaginationResult<T> {
  const {
    initialPage = 1,
    initialItemsPerPage = 10,
    enableKeyboardNavigation = true,
    debounceMs = 150
  } = options

  // State
  const [currentPage, setCurrentPage] = useState(initialPage)
  const [itemsPerPage, setItemsPerPage] = useState(initialItemsPerPage)
  const [isPageChanging, setIsPageChanging] = useState(false)

  // Debouncing for keyboard navigation
  const debounceTimer = useRef<NodeJS.Timeout | undefined>(undefined)

  // Validation helper
  const validatePage = useCallback((page: number, maxPages: number): number => {
    if (page < 1) return 1
    if (page > maxPages) return maxPages
    return page
  }, [])

  const validateItemsPerPage = useCallback((value: number): number => {
    if (value < 1) return 1
    if (value > 1000) return 1000 // Reasonable upper limit
    return value
  }, [])

  // Pagination calculations with validation
  const paginationData = useMemo(() => {
    const totalItems = items.length
    const validItemsPerPage = validateItemsPerPage(itemsPerPage)
    const totalPages = Math.max(1, Math.ceil(totalItems / validItemsPerPage))
    const validCurrentPage = validatePage(currentPage, totalPages)

    const startIndex = (validCurrentPage - 1) * validItemsPerPage
    const endIndex = startIndex + validItemsPerPage
    const currentItems = items.slice(startIndex, endIndex)

    return {
      totalItems,
      totalPages,
      currentItems,
      startIndex,
      endIndex,
      validCurrentPage,
      validItemsPerPage
    }
  }, [items, currentPage, itemsPerPage, validatePage, validateItemsPerPage])

  // Update state if validation changed the values
  useEffect(() => {
    if (paginationData.validCurrentPage !== currentPage) {
      setCurrentPage(paginationData.validCurrentPage)
    }
    if (paginationData.validItemsPerPage !== itemsPerPage) {
      setItemsPerPage(paginationData.validItemsPerPage)
    }
  }, [paginationData.validCurrentPage, paginationData.validItemsPerPage, currentPage, itemsPerPage])

  // Handlers
  const handlePageChange = useCallback((page: number) => {
    const validPage = validatePage(page, paginationData.totalPages)

    if (validPage === currentPage) return

    setIsPageChanging(true)
    setCurrentPage(validPage)

    // Smooth scroll to table with transition
    const tableElement = document.querySelector('.statements-table')
    if (tableElement) {
      tableElement.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      })

      // Listen for scroll end to reset loading state
      const handleTransitionEnd = () => {
        setTimeout(() => setIsPageChanging(false), 100)
      }

      // Fallback timeout in case scroll doesn't trigger
      setTimeout(handleTransitionEnd, 300)
    } else {
      // Fallback if element not found
      setTimeout(() => setIsPageChanging(false), 300)
    }
  }, [currentPage, paginationData.totalPages, validatePage])

  const handleItemsPerPageChange = useCallback((newItemsPerPage: number) => {
    const validItemsPerPage = validateItemsPerPage(newItemsPerPage)
    setItemsPerPage(validItemsPerPage)
    setCurrentPage(1) // Reset to first page when changing items per page
  }, [validateItemsPerPage])

  const resetPagination = useCallback(() => {
    setCurrentPage(1)
    setIsPageChanging(false)
  }, [])

  // Debounced keyboard navigation
  const debouncedPageChange = useCallback((page: number) => {
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current)
    }

    debounceTimer.current = setTimeout(() => {
      handlePageChange(page)
    }, debounceMs)
  }, [handlePageChange, debounceMs])

  // Keyboard navigation
  useEffect(() => {
    if (!enableKeyboardNavigation) return

    const handleKeyDown = (event: KeyboardEvent) => {
      // Don't handle keyboard events when focus is on input elements
      const target = event.target as HTMLElement
      if (target && (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.tagName === 'SELECT' ||
        target.contentEditable === 'true'
      )) {
        return
      }

      // Ignore if modifier keys are pressed
      if (event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) {
        return
      }

      if (event.key === 'ArrowLeft' && paginationData.validCurrentPage > 1) {
        event.preventDefault()
        debouncedPageChange(paginationData.validCurrentPage - 1)
      } else if (event.key === 'ArrowRight' && paginationData.validCurrentPage < paginationData.totalPages) {
        event.preventDefault()
        debouncedPageChange(paginationData.validCurrentPage + 1)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current)
      }
    }
  }, [enableKeyboardNavigation, paginationData.validCurrentPage, paginationData.totalPages, debouncedPageChange])

  return {
    // Data
    currentItems: paginationData.currentItems,

    // State
    currentPage: paginationData.validCurrentPage,
    itemsPerPage: paginationData.validItemsPerPage,
    totalItems: paginationData.totalItems,
    totalPages: paginationData.totalPages,
    startIndex: paginationData.startIndex,
    endIndex: paginationData.endIndex,
    isPageChanging,

    // Handlers
    handlePageChange,
    handleItemsPerPageChange,
    resetPagination,
    setIsPageChanging
  }
}