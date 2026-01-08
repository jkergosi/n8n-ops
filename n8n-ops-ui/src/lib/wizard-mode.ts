/**
 * Wizard Mode Utilities
 *
 * Per-user, per-device localStorage utilities for wizard mode detection and persistence.
 *
 * Keys:
 * - wizard_env_setup_seen: "true" after user completes setup or dismisses wizard
 * - wizard_mode_enabled: "true" or "false" for explicit user preference
 *
 * Behavior:
 * - First-time users (no localStorage key) default to wizard mode
 * - Returning users see full form by default
 * - User can manually toggle wizard mode on/off
 */

const STORAGE_KEYS = {
  ENV_SETUP_SEEN: 'wizard_env_setup_seen',
  MODE_ENABLED: 'wizard_mode_enabled',
} as const;

/**
 * Check if wizard mode should be enabled for the Environment Setup page.
 *
 * Logic:
 * 1. If user has explicit preference (wizard_mode_enabled), use that
 * 2. If user has seen setup before (wizard_env_setup_seen), default to false
 * 3. Otherwise (first-time user), default to true (wizard mode)
 */
export function isWizardModeEnabled(): boolean {
  try {
    // Check for explicit user preference first
    const explicitPreference = localStorage.getItem(STORAGE_KEYS.MODE_ENABLED);
    if (explicitPreference !== null) {
      return explicitPreference === 'true';
    }

    // Check if user has seen the setup before
    const hasSeenSetup = localStorage.getItem(STORAGE_KEYS.ENV_SETUP_SEEN);
    if (hasSeenSetup === 'true') {
      // Returning user - default to full form
      return false;
    }

    // First-time user - default to wizard mode
    return true;
  } catch {
    // localStorage might be unavailable (e.g., private browsing)
    return true;
  }
}

/**
 * Mark that the user has completed or seen the environment setup.
 * This ensures returning users see the full form by default.
 */
export function setWizardModeSeen(): void {
  try {
    localStorage.setItem(STORAGE_KEYS.ENV_SETUP_SEEN, 'true');
  } catch {
    // Silently fail if localStorage is unavailable
  }
}

/**
 * Toggle wizard mode preference.
 * Sets an explicit preference that overrides the default behavior.
 *
 * @param enabled - Whether wizard mode should be enabled
 */
export function setWizardModeEnabled(enabled: boolean): void {
  try {
    localStorage.setItem(STORAGE_KEYS.MODE_ENABLED, enabled.toString());
  } catch {
    // Silently fail if localStorage is unavailable
  }
}

/**
 * Toggle wizard mode between enabled and disabled.
 * Returns the new state.
 */
export function toggleWizardMode(): boolean {
  const currentState = isWizardModeEnabled();
  const newState = !currentState;
  setWizardModeEnabled(newState);
  return newState;
}

/**
 * Clear all wizard mode preferences.
 * Useful for testing or resetting user state.
 */
export function clearWizardModePreferences(): void {
  try {
    localStorage.removeItem(STORAGE_KEYS.ENV_SETUP_SEEN);
    localStorage.removeItem(STORAGE_KEYS.MODE_ENABLED);
  } catch {
    // Silently fail if localStorage is unavailable
  }
}

/**
 * Get the storage keys for testing purposes.
 */
export const WIZARD_STORAGE_KEYS = STORAGE_KEYS;
