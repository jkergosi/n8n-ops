import { useCallback, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import {
  useFeatureHintsStore,
  FEATURE_HINTS,
  type FeatureHint,
} from '@/store/use-feature-hints-store';

interface UseFeatureHintOptions {
  /** Auto-show this hint when component mounts */
  autoShow?: boolean;
  /** Delay in ms before auto-showing */
  autoShowDelay?: number;
  /** Only show once per session */
  showOncePerSession?: boolean;
}

interface UseFeatureHintReturn {
  /** The hint object */
  hint: FeatureHint | undefined;
  /** Whether the hint is currently active/visible */
  isActive: boolean;
  /** Whether the hint has been dismissed */
  isDismissed: boolean;
  /** Whether the hint has been viewed */
  isViewed: boolean;
  /** Whether hints are enabled globally */
  hintsEnabled: boolean;
  /** Show this hint */
  show: () => void;
  /** Hide this hint (without dismissing) */
  hide: () => void;
  /** Dismiss this hint permanently */
  dismiss: () => void;
  /** Track that the user used this feature */
  trackUsage: () => void;
}

/**
 * useFeatureHint - Hook for working with a specific feature hint
 *
 * Use this hook in components where you want to show a contextual hint.
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { hint, isActive, show, dismiss } = useFeatureHint('feature-workflows');
 *
 *   return (
 *     <FeatureHint hint={hint!} forceShow={isActive}>
 *       <Button onClick={() => { trackUsage(); navigate('/workflows'); }}>
 *         Workflows
 *       </Button>
 *     </FeatureHint>
 *   );
 * }
 * ```
 */
export function useFeatureHint(
  hintId: string,
  options: UseFeatureHintOptions = {}
): UseFeatureHintReturn {
  const { autoShow = false, autoShowDelay = 1000, showOncePerSession = true } = options;

  const location = useLocation();

  const {
    activeHintId,
    dismissedHints,
    viewedHints,
    hintsEnabled,
    setActiveHint,
    dismissHint,
    markHintViewed,
    trackFeatureUsage,
    shouldShowHint,
  } = useFeatureHintsStore();

  const hint = FEATURE_HINTS.find((h) => h.id === hintId);
  const isActive = activeHintId === hintId;
  const isDismissed = dismissedHints.includes(hintId);
  const isViewed = viewedHints.includes(hintId);

  // Check if hint should show based on route and conditions
  const canShow = hint ? shouldShowHint(hint, location.pathname) : false;

  // Auto-show hint on mount if configured
  useEffect(() => {
    if (!autoShow || !hint || !canShow || isDismissed) return;
    if (showOncePerSession && isViewed) return;

    const timer = setTimeout(() => {
      setActiveHint(hintId);
      markHintViewed(hintId);
    }, autoShowDelay);

    return () => clearTimeout(timer);
  }, [
    autoShow,
    hint,
    canShow,
    isDismissed,
    isViewed,
    showOncePerSession,
    hintId,
    setActiveHint,
    markHintViewed,
    autoShowDelay,
  ]);

  const show = useCallback(() => {
    if (!isDismissed && canShow) {
      setActiveHint(hintId);
      markHintViewed(hintId);
    }
  }, [isDismissed, canShow, hintId, setActiveHint, markHintViewed]);

  const hide = useCallback(() => {
    if (isActive) {
      setActiveHint(null);
    }
  }, [isActive, setActiveHint]);

  const dismiss = useCallback(() => {
    dismissHint(hintId);
  }, [dismissHint, hintId]);

  const trackUsage = useCallback(() => {
    trackFeatureUsage(hintId);
  }, [trackFeatureUsage, hintId]);

  return {
    hint,
    isActive,
    isDismissed,
    isViewed,
    hintsEnabled,
    show,
    hide,
    dismiss,
    trackUsage,
  };
}

/**
 * useContextualHints - Hook for getting all relevant hints for the current context
 *
 * Use this for components that need to show multiple hints or check hint availability.
 */
export function useContextualHints() {
  const location = useLocation();

  const {
    activeHintId,
    dismissedHints,
    viewedHints,
    hintsEnabled,
    interactionCount,
    isNewUser,
    onboardingComplete,
    setActiveHint,
    getNextHint,
    markOnboardingComplete,
  } = useFeatureHintsStore();

  // Get hints relevant to current route
  const routeHints = FEATURE_HINTS.filter((hint) => {
    if (hint.showOnRoutes && hint.showOnRoutes.length > 0) {
      return hint.showOnRoutes.some(
        (route) =>
          location.pathname === route ||
          location.pathname.startsWith(route + '/')
      );
    }
    return true;
  });

  // Get hints that can be shown (not dismissed, meeting conditions)
  const availableHints = routeHints.filter((hint) => {
    if (dismissedHints.includes(hint.id)) return false;
    if (hint.minInteractions && interactionCount < hint.minInteractions) return false;
    return true;
  });

  // Get unviewed hints
  const unviewedHints = availableHints.filter(
    (hint) => !viewedHints.includes(hint.id)
  );

  // Get the current active hint
  const currentHint = activeHintId
    ? FEATURE_HINTS.find((h) => h.id === activeHintId)
    : null;

  // Show the next available hint
  const showNextHint = useCallback(() => {
    const nextHint = getNextHint(FEATURE_HINTS, location.pathname);
    if (nextHint) {
      setActiveHint(nextHint.id);
    }
  }, [getNextHint, location.pathname, setActiveHint]);

  // Complete the onboarding
  const completeOnboarding = useCallback(() => {
    markOnboardingComplete();
    setActiveHint(null);
  }, [markOnboardingComplete, setActiveHint]);

  return {
    routeHints,
    availableHints,
    unviewedHints,
    currentHint,
    isOnboarding: isNewUser && !onboardingComplete,
    hintsEnabled,
    showNextHint,
    completeOnboarding,
  };
}

/**
 * useShortcutHints - Hook specifically for keyboard shortcut hints
 *
 * Returns keyboard shortcut hints that should be shown.
 */
export function useShortcutHints() {
  const { showKeyboardShortcuts, dismissedHints } = useFeatureHintsStore();

  const shortcutHints = FEATURE_HINTS.filter(
    (hint) =>
      hint.category === 'shortcut' &&
      hint.shortcut &&
      !dismissedHints.includes(hint.id)
  );

  return {
    shortcutHints,
    showShortcuts: showKeyboardShortcuts,
  };
}

export default useFeatureHint;
