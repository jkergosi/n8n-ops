import { createContext, useContext, useEffect, useMemo, useState, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import {
  useFeatureHintsStore,
  FEATURE_HINTS,
  type FeatureHint,
} from '@/store/use-feature-hints-store';

interface FeatureHintContextValue {
  // Current state
  currentHint: FeatureHint | null;
  availableHints: FeatureHint[];
  isOnboarding: boolean;

  // Actions
  showHint: (hintId: string) => void;
  hideHint: () => void;
  dismissCurrentHint: () => void;
  skipOnboarding: () => void;
  restartOnboarding: () => void;

  // Hint utilities
  getHintById: (id: string) => FeatureHint | undefined;
  getHintsForRoute: (route: string) => FeatureHint[];
  getHintsForCategory: (category: FeatureHint['category']) => FeatureHint[];

  // Feature adoption
  trackFeature: (featureId: string) => void;
  getUnusedFeatures: () => string[];
  suggestNextFeature: () => FeatureHint | null;
}

const FeatureHintContext = createContext<FeatureHintContextValue | null>(null);

interface FeatureHintProviderProps {
  children: React.ReactNode;
  /** Delay in ms before showing the first hint for new users */
  initialDelay?: number;
  /** Whether to automatically show hints to new users */
  autoShowForNewUsers?: boolean;
}

/**
 * FeatureHintProvider - Context provider for smart onboarding
 *
 * Wraps your app and provides contextual hint management.
 * Automatically tracks route changes and suggests relevant hints.
 */
export function FeatureHintProvider({
  children,
  initialDelay = 2000,
  autoShowForNewUsers = true,
}: FeatureHintProviderProps) {
  const location = useLocation();
  const [hasInitialized, setHasInitialized] = useState(false);

  const {
    isNewUser,
    activeHintId,
    dismissedHints,
    onboardingComplete,
    setActiveHint,
    dismissHint,
    markHintViewed,
    trackFeatureUsage,
    getUnusedFeatures,
    incrementInteraction,
    markOnboardingComplete,
    resetHints,
    shouldShowHint,
    getNextHint,
  } = useFeatureHintsStore();

  // Get the current active hint
  const currentHint = useMemo(() => {
    if (!activeHintId) return null;
    return FEATURE_HINTS.find((h) => h.id === activeHintId) || null;
  }, [activeHintId]);

  // Get available hints for the current route
  const availableHints = useMemo(() => {
    return FEATURE_HINTS.filter((hint) =>
      shouldShowHint(hint, location.pathname)
    );
  }, [location.pathname, shouldShowHint]);

  // Initialize for new users
  useEffect(() => {
    if (hasInitialized || !autoShowForNewUsers || !isNewUser || onboardingComplete) {
      return;
    }

    const timer = setTimeout(() => {
      const firstHint = getNextHint(FEATURE_HINTS, location.pathname);
      if (firstHint) {
        setActiveHint(firstHint.id);
      }
      setHasInitialized(true);
    }, initialDelay);

    return () => clearTimeout(timer);
  }, [
    hasInitialized,
    autoShowForNewUsers,
    isNewUser,
    onboardingComplete,
    location.pathname,
    getNextHint,
    setActiveHint,
    initialDelay,
  ]);

  // Track page navigation
  useEffect(() => {
    incrementInteraction();
  }, [location.pathname, incrementInteraction]);

  // Show a specific hint
  const showHint = useCallback((hintId: string) => {
    const hint = FEATURE_HINTS.find((h) => h.id === hintId);
    if (hint && !dismissedHints.includes(hintId)) {
      setActiveHint(hintId);
      markHintViewed(hintId);
    }
  }, [dismissedHints, setActiveHint, markHintViewed]);

  // Hide the current hint without dismissing
  const hideHint = useCallback(() => {
    setActiveHint(null);
  }, [setActiveHint]);

  // Dismiss the current hint permanently
  const dismissCurrentHint = useCallback(() => {
    if (activeHintId) {
      dismissHint(activeHintId);
    }
  }, [activeHintId, dismissHint]);

  // Skip the entire onboarding
  const skipOnboarding = useCallback(() => {
    markOnboardingComplete();
    setActiveHint(null);
  }, [markOnboardingComplete, setActiveHint]);

  // Restart onboarding (for settings/help)
  const restartOnboarding = useCallback(() => {
    resetHints();
    const firstHint = getNextHint(FEATURE_HINTS, location.pathname);
    if (firstHint) {
      setActiveHint(firstHint.id);
    }
  }, [resetHints, getNextHint, location.pathname, setActiveHint]);

  // Get a hint by ID
  const getHintById = useCallback((id: string) => {
    return FEATURE_HINTS.find((h) => h.id === id);
  }, []);

  // Get hints for a specific route
  const getHintsForRoute = useCallback((route: string) => {
    return FEATURE_HINTS.filter((hint) =>
      !hint.showOnRoutes || hint.showOnRoutes.length === 0 ||
      hint.showOnRoutes.some((r) => route === r || route.startsWith(r + '/'))
    );
  }, []);

  // Get hints by category
  const getHintsForCategory = useCallback((category: FeatureHint['category']) => {
    return FEATURE_HINTS.filter((h) => h.category === category);
  }, []);

  // Track feature usage
  const trackFeature = useCallback((featureId: string) => {
    trackFeatureUsage(featureId);
  }, [trackFeatureUsage]);

  // Suggest the next feature to explore
  const suggestNextFeature = useCallback((): FeatureHint | null => {
    const unused = getUnusedFeatures();
    if (unused.length === 0) return null;

    // Find a hint for an unused feature
    const hint = FEATURE_HINTS.find(
      (h) => h.category === 'feature' && unused.includes(h.id) && !dismissedHints.includes(h.id)
    );

    return hint || null;
  }, [getUnusedFeatures, dismissedHints]);

  const contextValue = useMemo<FeatureHintContextValue>(() => ({
    currentHint,
    availableHints,
    isOnboarding: isNewUser && !onboardingComplete,

    showHint,
    hideHint,
    dismissCurrentHint,
    skipOnboarding,
    restartOnboarding,

    getHintById,
    getHintsForRoute,
    getHintsForCategory,

    trackFeature,
    getUnusedFeatures,
    suggestNextFeature,
  }), [
    currentHint,
    availableHints,
    isNewUser,
    onboardingComplete,
    showHint,
    hideHint,
    dismissCurrentHint,
    skipOnboarding,
    restartOnboarding,
    getHintById,
    getHintsForRoute,
    getHintsForCategory,
    trackFeature,
    getUnusedFeatures,
    suggestNextFeature,
  ]);

  return (
    <FeatureHintContext.Provider value={contextValue}>
      {children}
    </FeatureHintContext.Provider>
  );
}

/**
 * Hook to access the feature hint context
 */
export function useFeatureHints() {
  const context = useContext(FeatureHintContext);
  if (!context) {
    throw new Error('useFeatureHints must be used within a FeatureHintProvider');
  }
  return context;
}

export default FeatureHintProvider;
