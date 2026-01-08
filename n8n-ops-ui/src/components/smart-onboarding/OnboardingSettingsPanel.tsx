import { RefreshCw, Lightbulb, Keyboard, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useFeatureHintsStore, FEATURE_HINTS } from '@/store/use-feature-hints-store';
import { cn } from '@/lib/utils';

interface OnboardingSettingsPanelProps {
  className?: string;
}

/**
 * OnboardingSettingsPanel - UI for managing onboarding preferences
 *
 * Shows in user settings/preferences to let users control hint behavior.
 */
export function OnboardingSettingsPanel({ className }: OnboardingSettingsPanelProps) {
  const {
    hintsEnabled,
    showKeyboardShortcuts,
    dismissedHints,
    viewedHints,
    featureAdoption,
    onboardingComplete,
    setHintsEnabled,
    setShowKeyboardShortcuts,
    resetHints,
    markOnboardingComplete,
  } = useFeatureHintsStore();

  const totalHints = FEATURE_HINTS.length;
  const viewedCount = viewedHints.length;
  const dismissedCount = dismissedHints.length;
  const adoptedFeatures = Object.keys(featureAdoption).length;
  const totalFeatures = FEATURE_HINTS.filter((h) => h.category === 'feature').length;

  const handleResetHints = () => {
    if (window.confirm('This will reset all onboarding hints. Continue?')) {
      resetHints();
    }
  };

  const handleSkipOnboarding = () => {
    markOnboardingComplete();
  };

  return (
    <Card className={cn('w-full', className)}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Lightbulb className="h-5 w-5" />
          Smart Onboarding
        </CardTitle>
        <CardDescription>
          Control how contextual tips and hints are displayed
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Quick Stats */}
        <div className="grid grid-cols-3 gap-4 p-4 bg-muted/50 rounded-lg">
          <div className="text-center">
            <div className="text-2xl font-bold">{viewedCount}/{totalHints}</div>
            <div className="text-xs text-muted-foreground">Tips Viewed</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold">{adoptedFeatures}/{totalFeatures}</div>
            <div className="text-xs text-muted-foreground">Features Used</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold">{dismissedCount}</div>
            <div className="text-xs text-muted-foreground">Dismissed</div>
          </div>
        </div>

        {/* Settings Toggles */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="flex items-center gap-2">
                <Info className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">Feature Hints</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Show contextual tips when encountering new features
              </p>
            </div>
            <Switch
              checked={hintsEnabled}
              onCheckedChange={setHintsEnabled}
              aria-label="Toggle feature hints"
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="flex items-center gap-2">
                <Keyboard className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">Keyboard Shortcuts</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Show keyboard shortcut hints in tooltips
              </p>
            </div>
            <Switch
              checked={showKeyboardShortcuts}
              onCheckedChange={setShowKeyboardShortcuts}
              aria-label="Toggle keyboard shortcut hints"
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-2 pt-4 border-t">
          {!onboardingComplete && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleSkipOnboarding}
              className="w-full"
            >
              Skip Remaining Hints
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleResetHints}
            className="w-full"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Reset All Hints
          </Button>
        </div>

        {/* Status */}
        {onboardingComplete && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground bg-muted/50 rounded-lg p-3">
            <Lightbulb className="h-4 w-4" />
            <span>
              Onboarding complete! You can reset hints anytime to see them again.
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default OnboardingSettingsPanel;
