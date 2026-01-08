// Smart Onboarding System
// Provides contextual, just-in-time guidance for users

export { FeatureHint, FeatureHintTrigger } from './FeatureHint';
export { FeatureHintProvider, useFeatureHints } from './FeatureHintProvider';
export { OnboardingSettingsPanel } from './OnboardingSettingsPanel';

// Re-export types and store
export {
  useFeatureHintsStore,
  FEATURE_HINTS,
  type FeatureHint as FeatureHintType,
  type FeatureAdoption,
} from '@/store/use-feature-hints-store';

// Re-export hooks
export {
  useFeatureHint,
  useContextualHints,
  useShortcutHints,
} from '@/hooks/useFeatureHint';
