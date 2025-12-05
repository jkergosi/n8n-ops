import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { api } from '@/lib/api';
import { CreditCard, Zap, CheckCircle2, Download, Calendar, DollarSign } from 'lucide-react';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';

export function BillingPage() {
  const queryClient = useQueryClient();
  const [upgradeDialogOpen, setUpgradeDialogOpen] = useState(false);
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<any>(null);
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'yearly'>('monthly');

  const { data: subscription, isLoading: loadingSubscription } = useQuery({
    queryKey: ['subscription'],
    queryFn: () => api.getSubscription(),
  });

  const { data: plans, isLoading: loadingPlans } = useQuery({
    queryKey: ['subscription-plans'],
    queryFn: () => api.getSubscriptionPlans(),
  });

  const { data: paymentHistory } = useQuery({
    queryKey: ['payment-history'],
    queryFn: () => api.getPaymentHistory(5),
  });

  const checkoutMutation = useMutation({
    mutationFn: (data: { price_id: string; billing_cycle: string }) =>
      api.createCheckoutSession({
        ...data,
        success_url: `${window.location.origin}/billing?success=true`,
        cancel_url: `${window.location.origin}/billing?canceled=true`,
      }),
    onSuccess: (result) => {
      // Redirect to Stripe checkout
      window.location.href = result.data.url;
    },
    onError: () => {
      toast.error('Failed to start checkout process');
    },
  });

  const portalMutation = useMutation({
    mutationFn: () => api.createPortalSession(`${window.location.origin}/billing`),
    onSuccess: (result) => {
      window.location.href = result.data.url;
    },
    onError: () => {
      toast.error('Failed to open customer portal');
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => api.cancelSubscription(true),
    onSuccess: () => {
      toast.success('Subscription will be canceled at the end of the billing period');
      queryClient.invalidateQueries({ queryKey: ['subscription'] });
      setCancelDialogOpen(false);
    },
    onError: () => {
      toast.error('Failed to cancel subscription');
    },
  });

  const reactivateMutation = useMutation({
    mutationFn: () => api.reactivateSubscription(),
    onSuccess: () => {
      toast.success('Subscription reactivated successfully');
      queryClient.invalidateQueries({ queryKey: ['subscription'] });
    },
    onError: () => {
      toast.error('Failed to reactivate subscription');
    },
  });

  const currentPlan = subscription?.data?.plan;
  const isPro = currentPlan?.name === 'pro';
  const isEnterprise = currentPlan?.name === 'enterprise';
  const isFree = currentPlan?.name === 'free';

  const handleUpgrade = (plan: any) => {
    setSelectedPlan(plan);
    setUpgradeDialogOpen(true);
  };

  const confirmUpgrade = () => {
    if (!selectedPlan) return;

    const priceId = billingCycle === 'monthly'
      ? selectedPlan.stripe_price_id_monthly
      : selectedPlan.stripe_price_id_yearly;

    if (!priceId) {
      toast.error('Plan pricing not configured');
      return;
    }

    checkoutMutation.mutate({
      price_id: priceId,
      billing_cycle: billingCycle,
    });
  };

  const handleManageSubscription = () => {
    portalMutation.mutate();
  };

  const handleCancelSubscription = () => {
    setCancelDialogOpen(true);
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  const getFeaturesList = (features: any) => {
    if (!features) return [];

    return [
      {
        label: features.environments === 'unlimited' ? 'Unlimited Environments' : `${features.environments} Environment${features.environments > 1 ? 's' : ''}`,
        enabled: true
      },
      {
        label: features.team_members === 'unlimited' ? 'Unlimited Team Members' : `Up to ${features.team_members} Team Members`,
        enabled: true
      },
      {
        label: features.workflows === 'unlimited' ? 'Unlimited Workflows' : `Up to ${features.workflows} Workflows`,
        enabled: true
      },
      {
        label: 'GitHub Sync',
        enabled: features.github_sync
      },
      {
        label: 'Workflow Deployments',
        enabled: features.deployments
      },
      {
        label: 'Scheduled Backups',
        enabled: features.scheduled_backups
      },
      {
        label: 'Priority Support',
        enabled: features.priority_support
      },
      {
        label: 'SSO Integration',
        enabled: features.sso || false
      },
    ];
  };

  if (loadingSubscription || loadingPlans) {
    return (
      <div className="flex items-center justify-center h-64">
        <p>Loading billing information...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Billing & Subscription</h1>
        <p className="text-muted-foreground">Manage your subscription and billing</p>
      </div>

      {/* Current Subscription */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5" />
              Current Plan
            </CardTitle>
            <CardDescription>Your subscription details</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-2xl font-bold">{currentPlan?.display_name} Plan</p>
                <p className="text-sm text-muted-foreground">
                  Status:{' '}
                  <Badge variant={subscription?.data?.status === 'active' ? 'success' : 'outline'}>
                    {subscription?.data?.status}
                  </Badge>
                </p>
              </div>
              {isFree && <Zap className="h-8 w-8 text-yellow-500" />}
            </div>

            {subscription?.data?.current_period_end && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Calendar className="h-4 w-4" />
                {subscription.data.cancel_at_period_end ? (
                  <span>Cancels on {new Date(subscription.data.current_period_end).toLocaleDateString()}</span>
                ) : (
                  <span>Renews on {new Date(subscription.data.current_period_end).toLocaleDateString()}</span>
                )}
              </div>
            )}

            <div className="pt-4 space-y-2">
              {isFree ? (
                <Button className="w-full" onClick={() => {
                  const proPlan = plans?.data?.find((p: any) => p.name === 'pro');
                  if (proPlan) handleUpgrade(proPlan);
                }}>
                  <Zap className="h-4 w-4 mr-2" />
                  Upgrade to Pro
                </Button>
              ) : (
                <>
                  <Button variant="outline" className="w-full" onClick={handleManageSubscription}>
                    Manage Subscription
                  </Button>
                  {subscription?.data?.cancel_at_period_end ? (
                    <Button
                      variant="default"
                      className="w-full"
                      onClick={() => reactivateMutation.mutate()}
                      disabled={reactivateMutation.isPending}
                    >
                      Reactivate Subscription
                    </Button>
                  ) : (
                    <Button
                      variant="ghost"
                      className="w-full text-red-500 hover:text-red-600"
                      onClick={handleCancelSubscription}
                    >
                      Cancel Subscription
                    </Button>
                  )}
                </>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Current Features</CardTitle>
            <CardDescription>What's included in your plan</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {getFeaturesList(currentPlan?.features).map((feature, index) => (
                <div key={index} className="flex items-center gap-2">
                  <CheckCircle2
                    className={`h-4 w-4 ${feature.enabled ? 'text-green-500' : 'text-gray-300'}`}
                  />
                  <span className={`text-sm ${!feature.enabled && 'text-muted-foreground'}`}>
                    {feature.label}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Available Plans */}
      <div>
        <h2 className="text-2xl font-bold mb-4">Available Plans</h2>
        <div className="grid gap-6 md:grid-cols-3">
          {plans?.data?.map((plan: any) => (
            <Card key={plan.id} className={currentPlan?.id === plan.id ? 'border-primary' : ''}>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  {plan.display_name}
                  {currentPlan?.id === plan.id && <Badge>Current</Badge>}
                </CardTitle>
                <CardDescription>{plan.description}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <div className="flex items-baseline gap-1">
                    <span className="text-3xl font-bold">{formatCurrency(parseFloat(plan.price_monthly))}</span>
                    <span className="text-muted-foreground">/month</span>
                  </div>
                  {plan.price_yearly && parseFloat(plan.price_yearly) > 0 && (
                    <p className="text-sm text-muted-foreground mt-1">
                      or {formatCurrency(parseFloat(plan.price_yearly))}/year (save {Math.round((1 - (parseFloat(plan.price_yearly) / (parseFloat(plan.price_monthly) * 12))) * 100)}%)
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  {getFeaturesList(plan.features).filter(f => f.enabled).map((feature, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                      <span className="text-sm">{feature.label}</span>
                    </div>
                  ))}
                </div>

                {currentPlan?.id !== plan.id && plan.name !== 'free' && (
                  <Button
                    className="w-full"
                    variant={plan.name === 'pro' ? 'default' : 'outline'}
                    onClick={() => handleUpgrade(plan)}
                  >
                    {plan.name === 'pro' ? 'Upgrade to Pro' : 'Contact Sales'}
                  </Button>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Payment History */}
      {paymentHistory?.data && paymentHistory.data.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              Recent Payments
            </CardTitle>
            <CardDescription>Your payment history</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {paymentHistory.data.map((payment: any) => (
                <div key={payment.id} className="flex items-center justify-between py-2 border-b last:border-0">
                  <div>
                    <p className="font-medium">{payment.description || 'Subscription Payment'}</p>
                    <p className="text-sm text-muted-foreground">
                      {new Date(payment.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium">{formatCurrency(parseFloat(payment.amount))}</p>
                    <Badge variant={payment.status === 'succeeded' ? 'success' : 'destructive'}>
                      {payment.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Upgrade Dialog */}
      <Dialog open={upgradeDialogOpen} onOpenChange={setUpgradeDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Upgrade to {selectedPlan?.display_name}</DialogTitle>
            <DialogDescription>
              Choose your billing cycle and proceed to checkout
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Billing Cycle</Label>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  variant={billingCycle === 'monthly' ? 'default' : 'outline'}
                  onClick={() => setBillingCycle('monthly')}
                  className="w-full"
                >
                  <div className="text-center">
                    <div>Monthly</div>
                    <div className="text-xs">{formatCurrency(parseFloat(selectedPlan?.price_monthly || 0))}/mo</div>
                  </div>
                </Button>
                {selectedPlan?.price_yearly && parseFloat(selectedPlan.price_yearly) > 0 && (
                  <Button
                    variant={billingCycle === 'yearly' ? 'default' : 'outline'}
                    onClick={() => setBillingCycle('yearly')}
                    className="w-full"
                  >
                    <div className="text-center">
                      <div>Yearly</div>
                      <div className="text-xs">{formatCurrency(parseFloat(selectedPlan.price_yearly) / 12)}/mo</div>
                    </div>
                  </Button>
                )}
              </div>
            </div>

            <div className="bg-muted p-4 rounded-md">
              <p className="text-sm">
                You will be charged{' '}
                <span className="font-bold">
                  {formatCurrency(
                    billingCycle === 'monthly'
                      ? parseFloat(selectedPlan?.price_monthly || 0)
                      : parseFloat(selectedPlan?.price_yearly || 0)
                  )}
                </span>{' '}
                {billingCycle === 'monthly' ? 'per month' : 'per year'}
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setUpgradeDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={confirmUpgrade} disabled={checkoutMutation.isPending}>
              {checkoutMutation.isPending ? 'Processing...' : 'Proceed to Checkout'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Cancel Confirmation Dialog */}
      <Dialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Cancel Subscription</DialogTitle>
            <DialogDescription>
              Are you sure you want to cancel your subscription? You will retain access until the end of your billing period.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCancelDialogOpen(false)}>
              Keep Subscription
            </Button>
            <Button
              variant="destructive"
              onClick={() => cancelMutation.mutate()}
              disabled={cancelMutation.isPending}
            >
              {cancelMutation.isPending ? 'Canceling...' : 'Yes, Cancel'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
