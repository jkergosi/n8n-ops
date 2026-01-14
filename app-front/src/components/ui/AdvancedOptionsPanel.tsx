import * as React from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AdvancedOptionsPanelProps {
  title: string;
  description?: string;
  defaultExpanded?: boolean;
  children: React.ReactNode;
  className?: string;
}

/**
 * A collapsible panel component for grouping advanced/optional options.
 *
 * Features:
 * - Smooth expand/collapse animation (150-200ms)
 * - Proper ARIA attributes for accessibility
 * - Keyboard navigation support (Enter/Space to toggle)
 * - Respects prefers-reduced-motion
 */
export function AdvancedOptionsPanel({
  title,
  description,
  defaultExpanded = false,
  children,
  className,
}: AdvancedOptionsPanelProps) {
  const [isExpanded, setIsExpanded] = React.useState(defaultExpanded);
  const contentId = React.useId();
  const prefersReducedMotion = usePrefersReducedMotion();

  const handleToggle = () => {
    setIsExpanded((prev) => !prev);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleToggle();
    }
  };

  return (
    <div className={cn('rounded-lg border bg-card', className)}>
      <button
        type="button"
        onClick={handleToggle}
        onKeyDown={handleKeyDown}
        aria-expanded={isExpanded}
        aria-controls={contentId}
        className={cn(
          'flex w-full items-center justify-between p-4 text-left',
          'hover:bg-accent/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
          'rounded-lg transition-colors'
        )}
      >
        <div className="flex-1">
          <span className="text-sm font-medium">{title}</span>
          {description && (
            <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>
          )}
        </div>
        <ChevronDown
          className={cn(
            'h-4 w-4 shrink-0 text-muted-foreground',
            !prefersReducedMotion && 'transition-transform duration-200',
            isExpanded && 'rotate-180'
          )}
          aria-hidden="true"
        />
      </button>
      <div
        id={contentId}
        role="region"
        aria-hidden={!isExpanded}
        className={cn(
          'overflow-hidden',
          !prefersReducedMotion && 'transition-all duration-200 ease-in-out',
          isExpanded ? 'opacity-100' : 'max-h-0 opacity-0'
        )}
        style={{
          // Use maxHeight for animation instead of height to avoid layout shifts
          maxHeight: isExpanded ? '2000px' : '0px',
        }}
      >
        <div className="border-t px-4 pb-4 pt-4">{children}</div>
      </div>
    </div>
  );
}

/**
 * Custom hook to detect if user prefers reduced motion
 */
function usePrefersReducedMotion(): boolean {
  const [prefersReducedMotion, setPrefersReducedMotion] = React.useState(false);

  React.useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);

    const handleChange = (event: MediaQueryListEvent) => {
      setPrefersReducedMotion(event.matches);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => {
      mediaQuery.removeEventListener('change', handleChange);
    };
  }, []);

  return prefersReducedMotion;
}

export default AdvancedOptionsPanel;
