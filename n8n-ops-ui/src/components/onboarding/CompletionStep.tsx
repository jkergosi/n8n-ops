import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Loader2, CheckCircle2, Building2, CreditCard, Users, Sparkles } from 'lucide-react';
import type { OnboardingFormData } from '@/pages/OnboardingPage';

interface CompletionStepProps {
  data: OnboardingFormData;
  onComplete: () => void;
  isLoading: boolean;
}

export function CompletionStep({ data, onComplete, isLoading }: CompletionStepProps) {
  return (
    <div className="space-y-6">
      <div className="flex flex-col items-center justify-center space-y-4">
        <div className="h-20 w-20 rounded-full bg-primary/10 flex items-center justify-center">
          <CheckCircle2 className="h-10 w-10 text-primary" />
        </div>
        <div className="text-center space-y-2">
          <h3 className="text-2xl font-semibold">Welcome to WorkflowOps!</h3>
          <p className="text-muted-foreground">
            Your workspace has been set up successfully.
          </p>
        </div>
      </div>

      <Card>
        <CardContent className="pt-6">
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                <Building2 className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1">
                <p className="font-medium">Organization</p>
                <p className="text-sm text-muted-foreground">{data.organizationName}</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                <Sparkles className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1">
                <p className="font-medium">Plan</p>
                <p className="text-sm text-muted-foreground capitalize">
                  {data.selectedPlan} Plan
                  {data.selectedPlan !== 'free' && ` (${data.billingCycle})`}
                </p>
              </div>
            </div>

            {data.selectedPlan !== 'free' && (
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <CreditCard className="h-5 w-5 text-primary" />
                </div>
                <div className="flex-1">
                  <p className="font-medium">Payment</p>
                  <p className="text-sm text-muted-foreground">Payment method configured</p>
                </div>
              </div>
            )}

            {data.teamInvites && data.teamInvites.length > 0 && (
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <Users className="h-5 w-5 text-primary" />
                </div>
                <div className="flex-1">
                  <p className="font-medium">Team Invitations</p>
                  <p className="text-sm text-muted-foreground">
                    {data.teamInvites.length} invitation{data.teamInvites.length > 1 ? 's' : ''} sent
                  </p>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <div className="rounded-lg bg-muted/50 p-4 space-y-2">
        <p className="text-sm font-medium">What's Next?</p>
        <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
          <li>Add your first N8N environment</li>
          <li>Import or create workflows</li>
          <li>Set up your deployment pipeline</li>
          {data.teamInvites && data.teamInvites.length > 0 && (
            <li>Team members will receive invitation emails</li>
          )}
        </ul>
      </div>

      <div className="flex justify-center">
        <Button onClick={onComplete} disabled={isLoading} size="lg" className="min-w-[200px]">
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Completing...
            </>
          ) : (
            <>
              Get Started
              <Sparkles className="ml-2 h-4 w-4" />
            </>
          )}
        </Button>
      </div>
    </div>
  );
}

