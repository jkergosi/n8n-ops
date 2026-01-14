import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * Feature hint definition for contextual onboarding
 */
export interface FeatureHint {
  id: string;
  title: string;
  description: string;
  shortcut?: string;
  category: 'navigation' | 'feature' | 'shortcut' | 'tip';
  targetSelector?: string;  // CSS selector for the target element
  position?: 'top' | 'bottom' | 'left' | 'right';
  priority?: number;  // Higher priority hints show first
  showOnRoutes?: string[];  // Only show on specific routes
  minInteractions?: number;  // Minimum interactions before showing (for context)
}

/**
 * Feature adoption tracking
 */
export interface FeatureAdoption {
  featureId: string;
  firstUsedAt: string;
  usageCount: number;
  lastUsedAt: string;
}

/**
 * Onboarding state interface
 */
interface FeatureHintsState {
  // Hint visibility state
  dismissedHints: string[];
  viewedHints: string[];
  activeHintId: string | null;

  // Feature adoption tracking
  featureAdoption: Record<string, FeatureAdoption>;

  // User interaction tracking
  interactionCount: number;
  sessionStartedAt: string | null;
  isNewUser: boolean;
  onboardingComplete: boolean;

  // Settings
  hintsEnabled: boolean;
  showKeyboardShortcuts: boolean;

  // Actions
  dismissHint: (hintId: string) => void;
  markHintViewed: (hintId: string) => void;
  setActiveHint: (hintId: string | null) => void;
  resetHints: () => void;

  // Feature adoption actions
  trackFeatureUsage: (featureId: string) => void;
  getUnusedFeatures: () => string[];

  // Interaction tracking
  incrementInteraction: () => void;
  markOnboardingComplete: () => void;
  setNewUser: (isNew: boolean) => void;

  // Settings actions
  setHintsEnabled: (enabled: boolean) => void;
  setShowKeyboardShortcuts: (show: boolean) => void;

  // Utility
  shouldShowHint: (hint: FeatureHint, currentRoute: string) => boolean;
  getNextHint: (availableHints: FeatureHint[], currentRoute: string) => FeatureHint | null;
}

/**
 * Predefined feature hints for the application
 */
export const FEATURE_HINTS: FeatureHint[] = [
  // Navigation hints
  {
    id: 'nav-search',
    title: 'Quick Search',
    description: 'Press ⌘K (or Ctrl+K) to quickly search and navigate to any page.',
    shortcut: '⌘K',
    category: 'shortcut',
    targetSelector: '[data-hint="search"]',
    position: 'bottom',
    priority: 10,
    showOnRoutes: ['/'],
  },
  {
    id: 'nav-sidebar-toggle',
    title: 'Collapse Sidebar',
    description: 'Click here to collapse or expand the sidebar for more screen space.',
    category: 'navigation',
    targetSelector: '[data-hint="sidebar-toggle"]',
    position: 'right',
    priority: 5,
  },

  // Feature hints
  {
    id: 'feature-environments',
    title: 'Manage Environments',
    description: 'Connect and manage your n8n environments. Add dev, staging, and production instances to track workflows across your infrastructure.',
    category: 'feature',
    targetSelector: '[data-hint="environments"]',
    position: 'right',
    priority: 8,
    showOnRoutes: ['/', '/environments'],
  },
  {
    id: 'feature-workflows',
    title: 'Workflow Overview',
    description: 'View all your canonical workflows and their status across environments. Track sync status and identify drift.',
    category: 'feature',
    targetSelector: '[data-hint="workflows"]',
    position: 'right',
    priority: 7,
    showOnRoutes: ['/', '/workflows'],
  },
  {
    id: 'feature-deployments',
    title: 'Deployments',
    description: 'Promote workflows between environments with full audit trail and rollback capabilities.',
    category: 'feature',
    targetSelector: '[data-hint="deployments"]',
    position: 'right',
    priority: 6,
    showOnRoutes: ['/deployments'],
  },
  {
    id: 'feature-snapshots',
    title: 'Snapshots',
    description: 'Create point-in-time backups of your environments. Restore to any previous state if needed.',
    category: 'feature',
    targetSelector: '[data-hint="snapshots"]',
    position: 'right',
    priority: 5,
    showOnRoutes: ['/snapshots'],
  },

  // Tip hints (shown after some usage)
  {
    id: 'tip-theme-toggle',
    title: 'Dark Mode',
    description: 'Toggle between light and dark themes in the user menu for comfortable viewing.',
    category: 'tip',
    targetSelector: '[data-hint="user-menu"]',
    position: 'bottom',
    priority: 2,
    minInteractions: 5,
  },
  {
    id: 'tip-notifications',
    title: 'Stay Updated',
    description: 'Check notifications for deployment status, drift alerts, and team updates.',
    category: 'tip',
    targetSelector: '[data-hint="notifications"]',
    position: 'bottom',
    priority: 2,
    minInteractions: 10,
  },

  // Contextual hints for specific pages
  {
    id: 'context-env-class',
    title: 'Environment Classes',
    description: 'Environments are classified as dev, staging, or production. This affects workflow policies and deployment restrictions.',
    category: 'tip',
    position: 'top',
    priority: 4,
    showOnRoutes: ['/environments'],
    minInteractions: 3,
  },
  {
    id: 'context-drift-detection',
    title: 'Drift Detection',
    description: 'We automatically detect when workflows change outside of the promotion pipeline. This helps maintain consistency.',
    category: 'tip',
    position: 'top',
    priority: 4,
    showOnRoutes: ['/observability', '/workflows'],
    minInteractions: 8,
  },
];

export const useFeatureHintsStore = create<FeatureHintsState>()(
  persist(
    (set, get) => ({
      // Initial state
      dismissedHints: [],
      viewedHints: [],
      activeHintId: null,
      featureAdoption: {},
      interactionCount: 0,
      sessionStartedAt: null,
      isNewUser: true,
      onboardingComplete: false,
      hintsEnabled: true,
      showKeyboardShortcuts: true,

      // Dismiss a hint permanently
      dismissHint: (hintId: string) =>
        set((state) => ({
          dismissedHints: state.dismissedHints.includes(hintId)
            ? state.dismissedHints
            : [...state.dismissedHints, hintId],
          activeHintId: state.activeHintId === hintId ? null : state.activeHintId,
        })),

      // Mark a hint as viewed (but not dismissed)
      markHintViewed: (hintId: string) =>
        set((state) => ({
          viewedHints: state.viewedHints.includes(hintId)
            ? state.viewedHints
            : [...state.viewedHints, hintId],
        })),

      // Set the currently active hint
      setActiveHint: (hintId: string | null) =>
        set({ activeHintId: hintId }),

      // Reset all hints (for testing or re-onboarding)
      resetHints: () =>
        set({
          dismissedHints: [],
          viewedHints: [],
          activeHintId: null,
          interactionCount: 0,
          isNewUser: true,
          onboardingComplete: false,
        }),

      // Track feature usage for adoption metrics
      trackFeatureUsage: (featureId: string) =>
        set((state) => {
          const now = new Date().toISOString();
          const existing = state.featureAdoption[featureId];

          return {
            featureAdoption: {
              ...state.featureAdoption,
              [featureId]: {
                featureId,
                firstUsedAt: existing?.firstUsedAt || now,
                usageCount: (existing?.usageCount || 0) + 1,
                lastUsedAt: now,
              },
            },
          };
        }),

      // Get list of features that haven't been used
      getUnusedFeatures: () => {
        const state = get();
        const usedFeatures = Object.keys(state.featureAdoption);
        const allFeatures = FEATURE_HINTS
          .filter((h) => h.category === 'feature')
          .map((h) => h.id);

        return allFeatures.filter((f) => !usedFeatures.includes(f));
      },

      // Increment interaction counter
      incrementInteraction: () =>
        set((state) => ({
          interactionCount: state.interactionCount + 1,
          sessionStartedAt: state.sessionStartedAt || new Date().toISOString(),
        })),

      // Mark onboarding as complete
      markOnboardingComplete: () =>
        set({ onboardingComplete: true, isNewUser: false }),

      // Set new user status
      setNewUser: (isNew: boolean) =>
        set({ isNewUser: isNew }),

      // Toggle hints enabled
      setHintsEnabled: (enabled: boolean) =>
        set({ hintsEnabled: enabled }),

      // Toggle keyboard shortcuts display
      setShowKeyboardShortcuts: (show: boolean) =>
        set({ showKeyboardShortcuts: show }),

      // Check if a hint should be shown
      shouldShowHint: (hint: FeatureHint, currentRoute: string): boolean => {
        const state = get();

        // Don't show if hints are disabled
        if (!state.hintsEnabled) return false;

        // Don't show if already dismissed
        if (state.dismissedHints.includes(hint.id)) return false;

        // Check route restrictions
        if (hint.showOnRoutes && hint.showOnRoutes.length > 0) {
          const routeMatches = hint.showOnRoutes.some(
            (route) => currentRoute === route || currentRoute.startsWith(route + '/')
          );
          if (!routeMatches) return false;
        }

        // Check minimum interactions
        if (hint.minInteractions && state.interactionCount < hint.minInteractions) {
          return false;
        }

        return true;
      },

      // Get the next hint to show based on priority and context
      getNextHint: (availableHints: FeatureHint[], currentRoute: string): FeatureHint | null => {
        const state = get();

        // Filter to hints that should be shown
        const showableHints = availableHints.filter((hint) =>
          state.shouldShowHint(hint, currentRoute)
        );

        if (showableHints.length === 0) return null;

        // Prioritize: not viewed > by priority
        const notViewed = showableHints.filter(
          (h) => !state.viewedHints.includes(h.id)
        );

        const hintsToConsider = notViewed.length > 0 ? notViewed : showableHints;

        // Sort by priority (higher first)
        const sorted = [...hintsToConsider].sort(
          (a, b) => (b.priority || 0) - (a.priority || 0)
        );

        return sorted[0] || null;
      },
    }),
    {
      name: 'feature-hints-store',
      partialize: (state) => ({
        dismissedHints: state.dismissedHints,
        viewedHints: state.viewedHints,
        featureAdoption: state.featureAdoption,
        interactionCount: state.interactionCount,
        isNewUser: state.isNewUser,
        onboardingComplete: state.onboardingComplete,
        hintsEnabled: state.hintsEnabled,
        showKeyboardShortcuts: state.showKeyboardShortcuts,
      }),
    }
  )
);
