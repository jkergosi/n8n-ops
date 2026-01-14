/**
 * Enhanced Loading State Component
 * Provides informative loading states with progress, ETA, and contextual messages.
 * Replaces generic spinners with transparent loading information.
 */
import * as React from "react"
import { cn } from "@/lib/utils"
import { Progress } from "./progress"
import { Loader2, Clock, CheckCircle2 } from "lucide-react"

interface LoadingStateProps extends React.HTMLAttributes<HTMLDivElement> {
  /** What's being loaded (e.g., "workflows", "environments", "credentials") */
  resource?: string
  /** Optional count of items being loaded */
  count?: number
  /** Current progress (0-100) */
  progress?: number
  /** Current step being executed */
  currentStep?: string
  /** Total number of steps */
  totalSteps?: number
  /** Current step number */
  currentStepNumber?: number
  /** Estimated time remaining in seconds */
  estimatedTimeRemaining?: number
  /** Start time of the operation (for calculating elapsed time) */
  startTime?: Date
  /** Size variant */
  size?: 'sm' | 'md' | 'lg'
  /** Whether to show in a compact inline format */
  inline?: boolean
  /** Custom loading message */
  message?: string
  /** Whether the operation is indeterminate (unknown progress) */
  indeterminate?: boolean
}

function formatTime(seconds: number): string {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`
  } else if (seconds < 3600) {
    const mins = Math.floor(seconds / 60)
    const secs = Math.round(seconds % 60)
    return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`
  } else {
    const hours = Math.floor(seconds / 3600)
    const mins = Math.floor((seconds % 3600) / 60)
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`
  }
}

function getLoadingMessage(resource?: string, count?: number): string {
  if (!resource) return "Loading..."

  const resourceLower = resource.toLowerCase()
  if (count !== undefined && count > 0) {
    return `Loading ${count} ${resourceLower}...`
  }
  return `Loading ${resourceLower}...`
}

const LoadingState = React.forwardRef<HTMLDivElement, LoadingStateProps>(
  ({
    className,
    resource,
    count,
    progress,
    currentStep,
    totalSteps,
    currentStepNumber,
    estimatedTimeRemaining,
    startTime,
    size = 'md',
    inline = false,
    message,
    indeterminate = true,
    ...props
  }, ref) => {
    const [elapsedSeconds, setElapsedSeconds] = React.useState(0)

    // Track elapsed time if startTime is provided
    React.useEffect(() => {
      if (!startTime) return

      const interval = setInterval(() => {
        const elapsed = (Date.now() - startTime.getTime()) / 1000
        setElapsedSeconds(elapsed)
      }, 1000)

      return () => clearInterval(interval)
    }, [startTime])

    const sizeClasses = {
      sm: {
        icon: 'h-4 w-4',
        text: 'text-sm',
        container: 'py-4',
        progress: 'h-1.5',
      },
      md: {
        icon: 'h-6 w-6',
        text: 'text-base',
        container: 'py-8',
        progress: 'h-2',
      },
      lg: {
        icon: 'h-8 w-8',
        text: 'text-lg',
        container: 'py-12',
        progress: 'h-2.5',
      },
    }

    const sizes = sizeClasses[size]
    const displayMessage = message || getLoadingMessage(resource, count)
    const hasProgress = progress !== undefined && !indeterminate
    const hasSteps = totalSteps !== undefined && currentStepNumber !== undefined

    if (inline) {
      return (
        <div
          ref={ref}
          className={cn("flex items-center gap-2", className)}
          {...props}
        >
          <Loader2 className={cn(sizes.icon, "animate-spin text-primary")} />
          <span className={cn(sizes.text, "text-muted-foreground")}>
            {displayMessage}
          </span>
          {hasProgress && (
            <span className="text-xs text-muted-foreground">
              ({Math.round(progress)}%)
            </span>
          )}
        </div>
      )
    }

    return (
      <div
        ref={ref}
        className={cn(
          "flex flex-col items-center justify-center",
          sizes.container,
          className
        )}
        {...props}
      >
        <Loader2 className={cn(sizes.icon, "animate-spin text-primary mb-3")} />

        <p className={cn(sizes.text, "text-muted-foreground font-medium mb-1")}>
          {displayMessage}
        </p>

        {/* Step indicator */}
        {hasSteps && currentStep && (
          <p className="text-sm text-muted-foreground mb-2">
            Step {currentStepNumber} of {totalSteps}: {currentStep}
          </p>
        )}

        {/* Progress bar */}
        {hasProgress && (
          <div className="w-full max-w-xs space-y-2 mt-2">
            <Progress value={progress} className={sizes.progress} />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{Math.round(progress)}% complete</span>
              {estimatedTimeRemaining !== undefined && estimatedTimeRemaining > 0 && (
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  ~{formatTime(estimatedTimeRemaining)} remaining
                </span>
              )}
            </div>
          </div>
        )}

        {/* Elapsed time indicator */}
        {startTime && elapsedSeconds > 3 && (
          <p className="text-xs text-muted-foreground mt-2">
            Elapsed: {formatTime(elapsedSeconds)}
          </p>
        )}
      </div>
    )
  }
)
LoadingState.displayName = "LoadingState"

/**
 * Simple inline loading indicator for buttons and small contexts
 */
interface LoadingSpinnerProps {
  size?: 'xs' | 'sm' | 'md' | 'lg'
  className?: string
  label?: string
}

const LoadingSpinner = React.forwardRef<HTMLDivElement, LoadingSpinnerProps>(
  ({ size = 'sm', className, label }, ref) => {
    const sizeClasses = {
      xs: 'h-3 w-3',
      sm: 'h-4 w-4',
      md: 'h-5 w-5',
      lg: 'h-6 w-6',
    }

    return (
      <div ref={ref} className={cn("flex items-center gap-2", className)}>
        <Loader2 className={cn(sizeClasses[size], "animate-spin")} />
        {label && <span className="text-sm">{label}</span>}
      </div>
    )
  }
)
LoadingSpinner.displayName = "LoadingSpinner"

/**
 * Multi-step loading indicator
 */
interface LoadingStep {
  id: string
  label: string
  status: 'pending' | 'loading' | 'completed' | 'error'
}

interface MultiStepLoadingProps extends React.HTMLAttributes<HTMLDivElement> {
  steps: LoadingStep[]
  title?: string
}

const MultiStepLoading = React.forwardRef<HTMLDivElement, MultiStepLoadingProps>(
  ({ className, steps, title, ...props }, ref) => {
    const completedCount = steps.filter(s => s.status === 'completed').length
    const progress = (completedCount / steps.length) * 100

    return (
      <div
        ref={ref}
        className={cn("space-y-4", className)}
        {...props}
      >
        {title && (
          <h4 className="font-medium text-sm">{title}</h4>
        )}

        <Progress value={progress} className="h-2" />

        <div className="space-y-2">
          {steps.map((step) => (
            <div
              key={step.id}
              className={cn(
                "flex items-center gap-2 text-sm",
                step.status === 'pending' && "text-muted-foreground",
                step.status === 'loading' && "text-primary",
                step.status === 'completed' && "text-green-600 dark:text-green-400",
                step.status === 'error' && "text-red-600 dark:text-red-400"
              )}
            >
              {step.status === 'pending' && (
                <div className="h-4 w-4 rounded-full border-2 border-muted" />
              )}
              {step.status === 'loading' && (
                <Loader2 className="h-4 w-4 animate-spin" />
              )}
              {step.status === 'completed' && (
                <CheckCircle2 className="h-4 w-4" />
              )}
              {step.status === 'error' && (
                <div className="h-4 w-4 rounded-full bg-red-500" />
              )}
              <span>{step.label}</span>
            </div>
          ))}
        </div>
      </div>
    )
  }
)
MultiStepLoading.displayName = "MultiStepLoading"

export {
  LoadingState,
  LoadingSpinner,
  MultiStepLoading,
  type LoadingStep
}
