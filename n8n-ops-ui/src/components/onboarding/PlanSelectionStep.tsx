import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Loader2, Zap, Sparkles, Crown, CheckCircle2, ArrowLeft, ArrowRight } from 'lucide-react';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import type { OnboardingFormData } from '@/pages/OnboardingPage';

interface PlanSelectionStepProps {
  data: OnboardingFormData;
  onNext: (data: Partial<OnboardingFormData>) => void;
  onBack: () => void;
  isLoading: boolean;
}

export function PlanSelectionStep({ data, onNext, onBack, isLoading }: PlanSelectionStepProps) {
  const [selectedPlan, setSelectedPlan] = useState(data.selectedPlan || 'free');
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>(data.billingCycle || 'monthly');

  const { data: plans, isLoading: loadingPlans } = useQuery({
    queryKey: ['subscription-plans'],
    queryFn: () => apiClient.getSubscriptionPlans(),
  });

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const handleNext = () => {
    if (!selectedPlan) {
      toast.error('Please select a plan');
      return;
    }
    onNext({ selectedPlan, billingCycle });
  };

  if (loadingPlans) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const sortedPlans = plans?.data?.sort((a: any, b: any) => {
    const order = ['free', 'pro', 'enterprise'];
    return order.indexOf(a.name) - order.indexOf(b.name);
  }) || [];

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h3 className="text-xl font-semibold">Choose Your Plan</h3>
        <p className="text-sm text-muted-foreground">
          Select the plan that best fits your needs. You can change this later.
        </p>
      </div>

      {/* Billing Cycle Toggle */}
      {sortedPlans.some((p: any) => p.name !== 'free') && (
        <div className="flex items-center justify-center gap-4">
          <span className={`text-sm ${billingCycle === 'monthly' ? 'font-medium' : 'text-muted-foreground'}`}>
            Monthly
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setBillingCycle(billingCycle === 'monthly' ? 'yearly' : 'monthly')}
            className="w-12"
          >
            <div className={`w-5 h-5 rounded-full bg-primary transition-transform ${billingCycle === 'yearly' ? 'translate-x-2' : '-translate-x-2'}`} />
          </Button>
          <span className={`text-sm ${billingCycle === 'yearly' ? 'font-medium' : 'text-muted-foreground'}`}>
            Yearly <span className="text-xs text-green-600">(Save up to 20%)</span>
          </span>
        </div>
      )}

      {/* Plans Grid */}
      <div className="grid gap-4 md:grid-cols-3">
        {sortedPlans.map((plan: any) => {
          const price = billingCycle === 'monthly' 
            ? parseFloat(plan.price_monthly || '0')
            : parseFloat(plan.price_yearly || '0') / 12;
          const isSelected = selectedPlan === plan.name;
          const isPopular = plan.name === 'pro';

          return (
            <Card
              key={plan.id}
              className={`relative cursor-pointer transition-all ${
                isSelected ? 'border-primary border-2 shadow-lg' : 'hover:border-primary/50'
              } ${isPopular ? 'shadow-md' : ''}`}
              onClick={() => setSelectedPlan(plan.name)}
            >
              {isPopular && (
                <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                  <Badge className="bg-primary text-primary-foreground gap-1">
                    <Sparkles className="h-3 w-3" />
                    Most Popular
                  </Badge>
                </div>
              )}
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {plan.name === 'enterprise' ? (
                      <Crown className="h-5 w-5 text-amber-500" />
                    ) : plan.name === 'pro' ? (
                      <Sparkles className="h-5 w-5 text-primary" />
                    ) : (
                      <Zap className="h-5 w-5 text-muted-foreground" />
                    )}
                    {plan.display_name || plan.name.charAt(0).toUpperCase() + plan.name.slice(1)}
                  </div>
                  {isSelected && (
                    <div className="h-5 w-5 rounded-full bg-primary flex items-center justify-center">
                      <CheckCircle2 className="h-3 w-3 text-primary-foreground" />
                    </div>
                  )}
                </CardTitle>
                <CardDescription>{plan.description || `${plan.name} plan`}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-bold">
                      {plan.name === 'free' ? 'Free' : formatCurrency(price)}
                    </span>
                    {plan.name !== 'free' && (
                      <span className="text-muted-foreground">/month</span>
                    )}
                  </div>
                  {billingCycle === 'yearly' && plan.name !== 'free' && plan.price_yearly && (
                    <p className="text-sm text-muted-foreground mt-1">
                      Billed annually ({formatCurrency(parseFloat(plan.price_yearly))}/year)
                    </p>
                  )}
                </div>

                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {plan.features && typeof plan.features === 'object' && (
                    <>
                      {plan.features.max_environments && (
                        <div className="flex items-center gap-2 text-sm">
                          <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0" />
                          <span>
                            {plan.features.max_environments === 'unlimited' 
                              ? 'Unlimited Environments' 
                              : `${plan.features.max_environments} Environment${plan.features.max_environments > 1 ? 's' : ''}`}
                          </span>
                        </div>
                      )}
                      {plan.features.max_team_members && (
                        <div className="flex items-center gap-2 text-sm">
                          <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0" />
                          <span>
                            {plan.features.max_team_members === 'unlimited' 
                              ? 'Unlimited Team Members' 
                              : `Up to ${plan.features.max_team_members} Team Members`}
                          </span>
                        </div>
                      )}
                      {plan.features.workflow_promotion && (
                        <div className="flex items-center gap-2 text-sm">
                          <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0" />
                          <span>Workflow Promotion</span>
                        </div>
                      )}
                      {plan.features.observability && (
                        <div className="flex items-center gap-2 text-sm">
                          <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0" />
                          <span>Observability & Monitoring</span>
                        </div>
                      )}
                      {plan.features.alerting && (
                        <div className="flex items-center gap-2 text-sm">
                          <CheckCircle2 className="h-4 w-4 text-green-500 flex-shrink-0" />
                          <span>Alerting & Notifications</span>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack} disabled={isLoading}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <Button onClick={handleNext} disabled={isLoading || !selectedPlan}>
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Processing...
            </>
          ) : (
            <>
              Continue
              <ArrowRight className="ml-2 h-4 w-4" />
            </>
          )}
        </Button>
      </div>
    </div>
  );
}

