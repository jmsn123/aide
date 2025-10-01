import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'

interface PaginationInfoProps {
  currentPage: number
  totalPages: number
  totalItems: number
  itemsPerPage: number
  onItemsPerPageChange: (value: number) => void
  className?: string
}

export function PaginationInfo({
  currentPage,
  totalPages,
  totalItems,
  itemsPerPage,
  onItemsPerPageChange,
  className
}: PaginationInfoProps) {
  const startItem = (currentPage - 1) * itemsPerPage + 1
  const endItem = Math.min(currentPage * itemsPerPage, totalItems)

  const itemsPerPageOptions = [5, 10, 20, 50, 100]

  return (
    <div className={`flex items-center justify-between gap-4 px-2 transition-all duration-300 ${className}`}>
      <div className="flex items-center gap-6 text-sm text-muted-foreground">
        <div className="flex items-center gap-2 animate-in fade-in duration-300">
          <span className="hidden sm:inline">Showing</span>
          <span className="font-medium text-foreground transition-colors duration-200 bg-gradient-to-r from-blue-600 to-sky-600 bg-clip-text text-transparent">
            {totalItems === 0 ? '0' : `${startItem}-${endItem}`}
          </span>
          <span className="hidden sm:inline">of</span>
          <span className="font-medium text-foreground transition-colors duration-200">
            {totalItems.toLocaleString()}
          </span>
          <span className="hidden sm:inline">results</span>
        </div>

        {totalPages > 1 && (
          <div className="hidden md:flex items-center gap-2 animate-in slide-in-from-left duration-300">
            <span className="px-2 py-1 bg-muted rounded-md text-xs font-medium">
              Page {currentPage} of {totalPages}
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-2 animate-in fade-in duration-500">
        <span className="text-sm text-muted-foreground hidden sm:inline">Rows per page:</span>
        <Select
          value={itemsPerPage.toString()}
          onValueChange={(value) => onItemsPerPageChange(Number(value))}
        >
          <SelectTrigger className="h-8 w-[70px] transition-all duration-200 hover:shadow-md hover:scale-105 border-muted-foreground/20">
            <SelectValue />
          </SelectTrigger>
          <SelectContent side="top" className="animate-in fade-in slide-in-from-bottom duration-200">
            {itemsPerPageOptions.map((option) => (
              <SelectItem
                key={option}
                value={option.toString()}
                className="transition-colors duration-150 hover:bg-primary/10"
              >
                {option}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}