import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as PopoverPrimitive from '@radix-ui/react-popover';
import { X, Lightbulb, Keyboard, Star, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import type { FeatureHint as FeatureHintType } from '@/store/use-feature-hints-store';
import { useFeatureHintsStore } from '@/store/use-feature-hints-store';

interface FeatureHintProps {
  hint: FeatureHintType;
  children: React.ReactNode;
  forceShow?: boolean;
  onDismiss?: () => void;
  onAction?: () => void;
  actionLabel?: string;
}

const categoryIcons = {
  navigation: ArrowRight,
  feature: Star,
  shortcut: Keyboard,
  tip: Lightbulb,
};

const categoryColors = {
  navigation: 'bg-blue-500',
  feature: 'bg-purple-500',
  shortcut: 'bg-amber-500',
  tip: 'bg-emerald-500',
};

/**
 * FeatureHint - A contextual tooltip component for smart onboarding
 *
 * Wraps a target element and shows a dismissible popover with helpful information.
 * Integrates with the feature hints store for persistence and tracking.
 */
export function FeatureHint({
  hint,
  children,
  forceShow = false,
  onDismiss,
  onAction,
  actionLabel,
}: FeatureHintProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [hasBeenShown, setHasBeenShown] = useState(false);
  const triggerRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const {
    dismissedHints,
    viewedHints,
    activeHintId,
    hintsEnabled,
    dismissHint,
    markHintViewed,
    setActiveHint,
    incrementInteraction,
  } = useFeatureHintsStore();

  const isDismissed = dismissedHints.includes(hint.id);
  const isViewed = viewedHints.includes(hint.id);
  const isActive = activeHintId === hint.id;

  // Determine if this hint should be visible
  const shouldShow = forceShow || (hintsEnabled && !isDismissed && (isActive || (!hasBeenShown && !isViewed)));

  // Show hint after a delay for new users
  useEffect(() => {
    if (!shouldShow || isDismissed || hasBeenShown) return;

    // Delay showing the hint to avoid overwhelming users
    timeoutRef.current = setTimeout(() => {
      if (!isDismissed) {
        setIsOpen(true);
        setHasBeenShown(true);
        markHintViewed(hint.id);
      }
    }, 1500); // 1.5 second delay

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [shouldShow, isDismissed, hasBeenShown, hint.id, markHintViewed]);

  // Handle active hint changes
  useEffect(() => {
    if (isActive && !isDismissed) {
      setIsOpen(true);
      markHintViewed(hint.id);
    } else if (!isActive && isOpen && !forceShow) {
      setIsOpen(false);
    }
  }, [isActive, isDismissed, hint.id, markHintViewed, isOpen, forceShow]);

  const handleDismiss = useCallback(() => {
    setIsOpen(false);
    dismissHint(hint.id);
    onDismiss?.();
    incrementInteraction();
  }, [dismissHint, hint.id, onDismiss, incrementInteraction]);

  const handleAction = useCallback(() => {
    setIsOpen(false);
    setActiveHint(null);
    onAction?.();
    incrementInteraction();
  }, [setActiveHint, onAction, incrementInteraction]);

  const handleOpenChange = useCallback((open: boolean) => {
    if (!open) {
      setIsOpen(false);
      if (activeHintId === hint.id) {
        setActiveHint(null);
      }
    } else {
      setIsOpen(true);
      markHintViewed(hint.id);
    }
  }, [activeHintId, hint.id, markHintViewed, setActiveHint]);

  const Icon = categoryIcons[hint.category];

  // If hints are disabled or this hint is dismissed, just render children
  if (!hintsEnabled || isDismissed) {
    return <>{children}</>;
  }

  return (
    <PopoverPrimitive.Root open={isOpen} onOpenChange={handleOpenChange}>
      <PopoverPrimitive.Anchor asChild>
        <div ref={triggerRef} className="inline-block">
          {children}
        </div>
      </PopoverPrimitive.Anchor>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          side={hint.position || 'bottom'}
          sideOffset={8}
          align="start"
          className={cn(
            'z-[100] w-80 rounded-lg border bg-popover text-popover-foreground shadow-lg outline-none',
            'data-[state=open]:animate-in data-[state=closed]:animate-out',
            'data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
            'data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95',
            'data-[side=bottom]:slide-in-from-top-2',
            'data-[side=left]:slide-in-from-right-2',
            'data-[side=right]:slide-in-from-left-2',
            'data-[side=top]:slide-in-from-bottom-2'
          )}
          data-testid="feature-hint-popover"
        >
          {/* Header with category indicator */}
          <div className="flex items-start gap-3 p-4 pb-2">
            <div className={cn(
              'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
              categoryColors[hint.category]
            )}>
              <Icon className="h-4 w-4 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2">
                <h4 className="font-semibold text-sm leading-tight">
                  {hint.title}
                </h4>
                <button
                  onClick={handleDismiss}
                  className="shrink-0 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                  aria-label="Dismiss hint"
                  data-testid="feature-hint-dismiss"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
              {hint.shortcut && (
                <kbd className="mt-1 inline-flex items-center gap-1 rounded border bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                  {hint.shortcut}
                </kbd>
              )}
            </div>
          </div>

          {/* Content */}
          <div className="px-4 pb-3">
            <p className="text-sm text-muted-foreground leading-relaxed">
              {hint.description}
            </p>
          </div>

          {/* Footer with actions */}
          <div className="flex items-center justify-between border-t bg-muted/50 px-4 py-2 rounded-b-lg">
            <button
              onClick={handleDismiss}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              data-testid="feature-hint-got-it"
            >
              Got it
            </button>
            {onAction && actionLabel && (
              <Button
                size="sm"
                variant="default"
                onClick={handleAction}
                className="h-7 text-xs"
              >
                {actionLabel}
              </Button>
            )}
          </div>

          {/* Arrow */}
          <PopoverPrimitive.Arrow className="fill-popover" />
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}

/**
 * FeatureHintTrigger - A simple wrapper that adds hint functionality to any element
 *
 * Use this when you want to add a hint to an existing element without wrapping it.
 */
interface FeatureHintTriggerProps {
  hintId: string;
  children: React.ReactNode;
  className?: string;
}

export function FeatureHintTrigger({
  hintId,
  children,
  className,
}: FeatureHintTriggerProps) {
  return (
    <div data-hint={hintId} className={className}>
      {children}
    </div>
  );
}

export default FeatureHint;
