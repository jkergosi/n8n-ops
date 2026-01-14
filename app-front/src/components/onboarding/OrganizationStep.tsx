import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Building2, Loader2 } from 'lucide-react';
import type { OnboardingFormData } from '@/pages/OnboardingPage';

interface OrganizationStepProps {
  data: OnboardingFormData;
  onNext: (data: Partial<OnboardingFormData>) => void;
  isLoading: boolean;
}

export function OrganizationStep({ data, onNext, isLoading }: OrganizationStepProps) {
  const [organizationName, setOrganizationName] = useState(data.organizationName || '');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!organizationName.trim()) {
      return;
    }
    onNext({
      organizationName: organizationName.trim(),
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Building2 className="h-5 w-5" />
          <span className="text-sm font-medium">Workspace Details</span>
        </div>

        <div className="space-y-2">
          <Label htmlFor="organizationName">
            Workspace Name <span className="text-destructive">*</span>
          </Label>
          <Input
            id="organizationName"
            type="text"
            placeholder="My Workspace"
            value={organizationName}
            onChange={(e) => setOrganizationName(e.target.value)}
            disabled={isLoading}
            required
            autoFocus
          />
          <p className="text-xs text-muted-foreground">
            This workspace contains your environments, workflows, and deployments.
          </p>
          <p className="text-xs text-muted-foreground/70">
            You can rename this later in Admin Settings.
          </p>
        </div>
      </div>

      <div className="flex justify-end">
        <Button type="submit" disabled={isLoading || !organizationName.trim()}>
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Setting up...
            </>
          ) : (
            'Continue'
          )}
        </Button>
      </div>
    </form>
  );
}

