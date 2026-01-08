# Progressive Disclosure & Wizard Mode Specification (v3 - MVP)

## Overview

This specification defines the implementation of progressive disclosure patterns for N8N Ops UI to reduce cognitive load for new users while maintaining power-user access to all features.

**MVP Scope**: Environment Setup page only.

---

## Problem Statement

The Environment Setup page presents all configuration options at once, which can overwhelm first-time users. Users need a guided experience that surfaces essential fields first while providing access to advanced options when needed.

---

## Solution

### Primary MVP Feature: AdvancedOptionsPanel

A collapsible panel component that groups optional/advanced fields behind an expandable section. This is the **primary deliverable** for MVP.

**Usage Pattern:**
- Essential fields (Name, Type, N8N URL, API Key) are always visible
- GitHub integration fields are grouped in an `AdvancedOptionsPanel`
- Panel is collapsed by default for new users, expanded for returning users

### Secondary Feature: Wizard Mode (MVP-scoped)

A simplified, step-by-step interface for first-time users on the Environment Setup page.

**Wizard Mode Detection & Persistence (MVP):**
- Detection is **per-user, per-device** using `localStorage`
- Keys:
  - `wizard_env_setup_seen` - `"true"` after user completes setup or dismisses wizard
  - `wizard_mode_enabled` - `"true"` or `"false"` for user preference
- Behavior:
  - First-time users (no localStorage key) default to wizard mode
  - Returning users see full form by default
  - User can manually toggle wizard mode on/off via a link/button

**Note:** Server-side detection, tenant-wide settings, and analytics-based detection are **not in scope for MVP**.

### Post-MVP Features

The following are explicitly **Post-MVP** and should not be implemented in this phase:

- Global `WizardModeProvider` context
- Pipeline `StageCard` refactoring
- Multi-page wizard flows
- Server-side wizard mode persistence
- Analytics-based user experience detection

---

## Components

### 1. AdvancedOptionsPanel (MVP)

A reusable collapsible panel for grouping advanced options.

**Props:**
```typescript
interface AdvancedOptionsPanelProps {
  title: string;
  description?: string;
  defaultExpanded?: boolean;
  children: React.ReactNode;
}
```

**Behavior:**
- Renders a button with chevron icon that toggles panel visibility
- Smooth expand/collapse animation (150-200ms)
- Maintains expand/collapse state in component (not persisted)
- Button uses `aria-expanded` attribute for accessibility

### 2. Wizard Mode Toggle (MVP)

A simple toggle component inline on the Environment Setup page.

**Behavior:**
- Displays "Switch to guided setup" / "Switch to full form" link
- Reads/writes to `localStorage` key `wizard_mode_enabled`
- Triggers page re-render to show appropriate view

### 3. ConditionalField (Optional)

**Decision:** Conditional field logic should be implemented **inline at the page level** for MVP. A reusable `ConditionalField` component is optional and should only be created if the pattern is reused in 3+ places.

---

## Accessibility Considerations

The following accessibility requirements **must** be met:

1. **ARIA Attributes:**
   - Collapsible sections use `<button>` elements with `aria-expanded="true|false"`
   - Panel content uses `aria-hidden` when collapsed

2. **Keyboard Navigation:**
   - All interactive elements are focusable via Tab key
   - Enter/Space toggles collapsible panels
   - Escape does not close panels (standard behavior)

3. **Focus Management:**
   - On wizard step transitions, focus moves to the first interactive element in the new step
   - Focus is not trapped within panels

4. **Animation Behavior:**
   - No layout shifts during expand/collapse animations
   - Use `transform` and `opacity` for animations, not `height` where possible
   - Respect `prefers-reduced-motion` media query

---

## CSS / Animation Guidance

1. **Preferred Approach:**
   - Use Tailwind utility classes for animations where possible
   - Use component-scoped styles (CSS modules or styled-components) for custom animations

2. **Global Styles:**
   - Avoid modifying `index.css` unless defining a shared animation token
   - If a shared token is needed, add it as a CSS custom property in `:root`

3. **Animation Requirements:**
   - Use simple, non-blocking transitions (150-200ms)
   - Prefer `transition-all` with Tailwind or explicit `transition` properties
   - Example: `transition-all duration-200 ease-in-out`

---

## Implementation Tasks

### MVP Tasks

```tasks
1. [MVP] Create AdvancedOptionsPanel component
   - File: src/components/ui/AdvancedOptionsPanel.tsx
   - Implement collapsible panel with proper ARIA attributes
   - Add smooth expand/collapse animation using Tailwind
   - Include chevron icon rotation on toggle

2. [MVP] Implement wizard mode localStorage utilities
   - File: src/lib/wizard-mode.ts
   - Functions: isWizardModeEnabled(), setWizardModeSeen(), toggleWizardMode()
   - Keys: wizard_env_setup_seen, wizard_mode_enabled

3. [MVP] Refactor EnvironmentSetupPage with AdvancedOptionsPanel
   - File: src/pages/EnvironmentSetupPage.tsx
   - Wrap GitHub integration fields in AdvancedOptionsPanel
   - Add wizard mode toggle link
   - Implement wizard view (2-step: N8N connection, then GitHub)

4. [MVP] Add wizard mode toggle UI to EnvironmentSetupPage
   - Display "Switch to guided setup" / "Switch to full form" link
   - Persist preference to localStorage

5. [MVP] Write Playwright e2e test for AdvancedOptionsPanel
   - File: tests/e2e/advanced-options-panel.spec.ts
   - Test expand/collapse behavior
   - Test keyboard accessibility
   - Test ARIA attributes

6. [MVP] Write Playwright e2e test for wizard mode
   - File: tests/e2e/environment-setup-wizard.spec.ts
   - Test first-time user flow (wizard mode)
   - Test returning user flow (full form)
   - Test mode toggle functionality
```

### Post-MVP Tasks

```tasks
7. [Post-MVP] Create global WizardModeProvider context
   - Only implement if wizard mode extends to multiple pages

8. [Post-MVP] Refactor Pipeline StageCard with progressive disclosure
   - Apply AdvancedOptionsPanel pattern to pipeline configuration

9. [Post-MVP] Create reusable ConditionalField component
   - Only if pattern is used in 3+ places

10. [Post-MVP] Add server-side wizard mode persistence
    - Sync localStorage preference with user profile
```

---

## Files to Modify

### MVP Files

| File | Action | Description |
|------|--------|-------------|
| `src/components/ui/AdvancedOptionsPanel.tsx` | Create | New collapsible panel component |
| `src/lib/wizard-mode.ts` | Create | localStorage utilities for wizard mode |
| `src/pages/EnvironmentSetupPage.tsx` | Modify | Apply AdvancedOptionsPanel, add wizard mode |
| `tests/e2e/advanced-options-panel.spec.ts` | Create | E2E tests for panel component |
| `tests/e2e/environment-setup-wizard.spec.ts` | Create | E2E tests for wizard mode |

### Post-MVP Files (Do Not Modify Yet)

| File | Action | Description |
|------|--------|-------------|
| `src/contexts/WizardModeContext.tsx` | Create | Global wizard mode context |
| `src/pages/PipelinesPage.tsx` | Modify | Apply progressive disclosure to StageCard |
| `src/components/ui/ConditionalField.tsx` | Create | Reusable conditional field wrapper |

---

## Acceptance Criteria

### MVP Criteria

1. **AdvancedOptionsPanel:**
   - [ ] Panel collapses and expands with smooth animation
   - [ ] Chevron icon rotates on toggle
   - [ ] `aria-expanded` attribute updates correctly
   - [ ] Keyboard navigation works (Enter/Space to toggle)
   - [ ] No layout shift during animation

2. **Wizard Mode:**
   - [ ] First-time users see wizard mode by default
   - [ ] Returning users see full form by default
   - [ ] Toggle link switches between modes
   - [ ] Preference persists in localStorage
   - [ ] Wizard mode detection is per-device only (no server calls)

3. **Environment Setup Page:**
   - [ ] GitHub fields are wrapped in AdvancedOptionsPanel
   - [ ] Panel is collapsed by default for first-time users
   - [ ] All existing functionality works unchanged
   - [ ] Form validation works in both modes

4. **Accessibility:**
   - [ ] All interactive elements are keyboard accessible
   - [ ] ARIA attributes are correctly implemented
   - [ ] Focus management works on step transitions
   - [ ] Animations respect `prefers-reduced-motion`

---

## Verification & Testing

### Test Files

Tests should be **kept in the repository** and not deleted after verification.

| Test File | Purpose | Run Mode |
|-----------|---------|----------|
| `tests/e2e/advanced-options-panel.spec.ts` | Panel expand/collapse, ARIA, keyboard | Manual/Local |
| `tests/e2e/environment-setup-wizard.spec.ts` | Wizard mode toggle, localStorage | Manual/Local |

**Note:** If CI does not run Playwright tests, mark these as "Manual / local verification" in test reports.

### Test Behaviors to Validate

**AdvancedOptionsPanel Tests:**
1. Panel is collapsed by default when `defaultExpanded` is false/undefined
2. Clicking the toggle button expands/collapses the panel
3. `aria-expanded` attribute changes on toggle
4. Panel content is hidden when collapsed (`aria-hidden="true"`)
5. Enter and Space keys toggle the panel
6. Tab navigates to the toggle button

**Wizard Mode Tests:**
1. First visit (no localStorage) shows wizard mode
2. After completing setup, `wizard_env_setup_seen` is set
3. Subsequent visits show full form
4. Toggle link changes mode and updates localStorage
5. Mode persists across page refreshes

### Manual Verification Checklist

- [ ] Create new environment as first-time user (clear localStorage)
- [ ] Verify wizard mode appears with step-by-step flow
- [ ] Complete setup and verify full form appears on return
- [ ] Toggle between wizard and full form modes
- [ ] Test keyboard navigation through all interactive elements
- [ ] Verify no console errors during expand/collapse animations
- [ ] Test with screen reader (VoiceOver/NVDA) for ARIA correctness

---

## Design Notes

### Visual Design

- Use existing shadcn/ui patterns for consistency
- Chevron icon from Lucide (`ChevronDown`, `ChevronRight`)
- Panel border matches Card component style
- Toggle link uses `text-primary` with underline on hover

### Animation Specifications

```css
/* Tailwind approach */
.panel-content {
  @apply transition-all duration-200 ease-in-out;
}

/* Collapsed state */
.panel-content[data-state="closed"] {
  @apply opacity-0 max-h-0 overflow-hidden;
}

/* Expanded state */
.panel-content[data-state="open"] {
  @apply opacity-100 max-h-[1000px];
}
```

---

## Out of Scope

The following are explicitly **not** part of this specification:

- Server-side wizard mode detection or persistence
- Tenant-wide wizard settings
- Analytics-based user experience detection
- Pipeline page changes (Post-MVP)
- Multi-page wizard flows
- A/B testing of wizard vs full form
- User onboarding tours or tooltips

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| v1 | 2026-01-07 | Initial specification |
| v2 | 2026-01-08 | Added component details |
| v3 | 2026-01-08 | MVP scope tightening per user feedback: localStorage persistence, accessibility requirements, CSS guidance, testing corrections, task labeling |
