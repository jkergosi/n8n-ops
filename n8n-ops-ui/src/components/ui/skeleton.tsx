import * as React from "react"
import { cn } from "@/lib/utils"

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Width of the skeleton (can be Tailwind class or CSS value) */
  width?: string
  /** Height of the skeleton (can be Tailwind class or CSS value) */
  height?: string
  /** Whether this is a circular skeleton (for avatars, icons) */
  circle?: boolean
}

const Skeleton = React.forwardRef<HTMLDivElement, SkeletonProps>(
  ({ className, width, height, circle, style, ...props }, ref) => {
    const inlineStyle: React.CSSProperties = {
      ...style,
      ...(width && !width.startsWith('w-') ? { width } : {}),
      ...(height && !height.startsWith('h-') ? { height } : {}),
    }

    return (
      <div
        ref={ref}
        className={cn(
          "animate-pulse bg-muted",
          circle ? "rounded-full" : "rounded-md",
          width?.startsWith('w-') && width,
          height?.startsWith('h-') && height,
          className
        )}
        style={inlineStyle}
        {...props}
      />
    )
  }
)
Skeleton.displayName = "Skeleton"

// Pre-built skeleton variants for common use cases
interface SkeletonTextProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Number of lines to show */
  lines?: number
  /** Whether to show varied line widths */
  varied?: boolean
}

const SkeletonText = React.forwardRef<HTMLDivElement, SkeletonTextProps>(
  ({ className, lines = 3, varied = true, ...props }, ref) => {
    const widths = varied ? ['w-full', 'w-4/5', 'w-3/4', 'w-5/6', 'w-2/3'] : ['w-full']

    return (
      <div ref={ref} className={cn("space-y-2", className)} {...props}>
        {Array.from({ length: lines }).map((_, i) => (
          <Skeleton
            key={i}
            className={cn("h-4", widths[i % widths.length])}
          />
        ))}
      </div>
    )
  }
)
SkeletonText.displayName = "SkeletonText"

// Skeleton for table rows
interface SkeletonTableRowsProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Number of rows */
  rows?: number
  /** Number of columns */
  columns?: number
}

const SkeletonTableRows = React.forwardRef<HTMLDivElement, SkeletonTableRowsProps>(
  ({ className, rows = 5, columns = 4, ...props }, ref) => {
    return (
      <div ref={ref} className={cn("space-y-3", className)} {...props}>
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div key={rowIndex} className="flex gap-4 items-center">
            {Array.from({ length: columns }).map((_, colIndex) => (
              <Skeleton
                key={colIndex}
                className={cn(
                  "h-10 flex-1",
                  colIndex === 0 && "max-w-[200px]",
                  colIndex === columns - 1 && "max-w-[100px]"
                )}
              />
            ))}
          </div>
        ))}
      </div>
    )
  }
)
SkeletonTableRows.displayName = "SkeletonTableRows"

// Skeleton for cards
interface SkeletonCardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Whether to show a header */
  showHeader?: boolean
  /** Whether to show an avatar/icon */
  showAvatar?: boolean
  /** Number of content lines */
  contentLines?: number
}

const SkeletonCard = React.forwardRef<HTMLDivElement, SkeletonCardProps>(
  ({ className, showHeader = true, showAvatar = false, contentLines = 3, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "rounded-lg border bg-card p-6 space-y-4",
          className
        )}
        {...props}
      >
        {showHeader && (
          <div className="flex items-center gap-4">
            {showAvatar && (
              <Skeleton circle className="h-10 w-10" />
            )}
            <div className="space-y-2 flex-1">
              <Skeleton className="h-5 w-1/3" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          </div>
        )}
        <SkeletonText lines={contentLines} />
      </div>
    )
  }
)
SkeletonCard.displayName = "SkeletonCard"

// Skeleton for list items
interface SkeletonListProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Number of items */
  items?: number
  /** Whether to show icons/avatars */
  showIcons?: boolean
}

const SkeletonList = React.forwardRef<HTMLDivElement, SkeletonListProps>(
  ({ className, items = 5, showIcons = true, ...props }, ref) => {
    return (
      <div ref={ref} className={cn("space-y-3", className)} {...props}>
        {Array.from({ length: items }).map((_, i) => (
          <div key={i} className="flex items-center gap-3">
            {showIcons && (
              <Skeleton circle className="h-8 w-8 shrink-0" />
            )}
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          </div>
        ))}
      </div>
    )
  }
)
SkeletonList.displayName = "SkeletonList"

export {
  Skeleton,
  SkeletonText,
  SkeletonTableRows,
  SkeletonCard,
  SkeletonList
}
