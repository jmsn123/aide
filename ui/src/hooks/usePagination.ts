import { useState, useMemo, useCallback, useRef, useEffect } from 'react'

export interface PaginationOptions {
  initialPage?: number
  initialItemsPerPage?: number
  enableKeyboardNavigation?: boolean
  debounceMs?: number
}

export interface PaginationResult<T> {
  // Data
  currentItems: T[]

  // State
  currentPage: number
  itemsPerPage: number
  totalItems: number
  totalPages: number
  startIndex: number
  endIndex: number
  isPageChanging: boolean

  // Handlers
  handlePageChange: (page: number) => void
  handleItemsPerPageChange: (newItemsPerPage: number) => void
  resetPagination: () => void
  setIsPageChanging: (isChanging: boolean) => void
}

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