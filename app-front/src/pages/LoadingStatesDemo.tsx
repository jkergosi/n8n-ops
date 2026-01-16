/**
 * Loading States Demo Page
 * Demonstrates all the new loading state variants for testing and documentation.
 */
import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { LoadingState, LoadingSpinner, MultiStepLoading, type LoadingStep } from '@/components/ui/loading-state';
import { Skeleton, SkeletonText, SkeletonTableRows, SkeletonCard, SkeletonList } from '@/components/ui/skeleton';
import { CancellableOperation, type OperationStatus } from '@/components/ui/cancellable-operation';
import { SmartEmptyState } from '@/components/SmartEmptyState';
import { Play, RotateCcw } from 'lucide-react';

export function LoadingStatesDemo() {
  // State for interactive demos
  const [operationStatus, setOperationStatus] = useState<OperationStatus>('idle');
  const [operationProgress, setOperationProgress] = useState(0);
  const [startTime, setStartTime] = useState<Date | undefined>();
  const [processedCount, setProcessedCount] = useState(0);
  const [isBackground, setIsBackground] = useState(false);

  const [multiStepSteps, setMultiStepSteps] = useState<LoadingStep[]>([
    { id: '1', label: 'Connecting to server', status: 'pending' },
    { id: '2', label: 'Fetching workflow data', status: 'pending' },
    { id: '3', label: 'Processing dependencies', status: 'pending' },
    { id: '4', label: 'Validating configuration', status: 'pending' },
    { id: '5', label: 'Finalizing', status: 'pending' },
  ]);

  // Simulate long-running operation
  useEffect(() => {
    if (operationStatus !== 'running') return;

    const interval = setInterval(() => {
      setOperationProgress((prev) => {
        const next = prev + Math.random() * 5;
        if (next >= 100) {
          setOperationStatus('completed');
          return 100;
        }
        setProcessedCount(Math.floor((next / 100) * 47));
        return next;
      });
    }, 500);

    return () => clearInterval(interval);
  }, [operationStatus]);

  // Simulate multi-step loading
  const [multiStepActive, setMultiStepActive] = useState(false);
  useEffect(() => {
    if (!multiStepActive) return;

    let stepIndex = 0;
    const interval = setInterval(() => {
      setMultiStepSteps((prev) => {
        const newSteps = [...prev];
        if (stepIndex > 0) {
          newSteps[stepIndex - 1].status = 'completed';
        }
        if (stepIndex < newSteps.length) {
          newSteps[stepIndex].status = 'loading';
          stepIndex++;
        } else {
          setMultiStepActive(false);
          clearInterval(interval);
        }
        return newSteps;
      });
    }, 1500);

    return () => clearInterval(interval);
  }, [multiStepActive]);

  const startOperation = () => {
    setOperationStatus('running');
    setOperationProgress(0);
    setProcessedCount(0);
    setStartTime(new Date());
    setIsBackground(false);
  };

  const resetOperation = () => {
    setOperationStatus('idle');
    setOperationProgress(0);
    setProcessedCount(0);
    setStartTime(undefined);
    setIsBackground(false);
  };

  const startMultiStep = () => {
    setMultiStepActive(true);
    setMultiStepSteps([
      { id: '1', label: 'Connecting to server', status: 'pending' },
      { id: '2', label: 'Fetching workflow data', status: 'pending' },
      { id: '3', label: 'Processing dependencies', status: 'pending' },
      { id: '4', label: 'Validating configuration', status: 'pending' },
      { id: '5', label: 'Finalizing', status: 'pending' },
    ]);
  };

  return (
    <div className="space-y-8 p-6">
      <div>
        <h1 className="text-2xl font-bold">Loading States Demo</h1>
        <p className="text-muted-foreground">
          Demonstrating informative loading states with progress, ETA, and skeleton screens
        </p>
      </div>

      <Tabs defaultValue="basic" className="space-y-6">
        <TabsList>
          <TabsTrigger value="basic">Basic Loading</TabsTrigger>
          <TabsTrigger value="skeletons">Skeletons</TabsTrigger>
          <TabsTrigger value="progress">Progress</TabsTrigger>
          <TabsTrigger value="cancellable">Cancellable Operations</TabsTrigger>
          <TabsTrigger value="smart">SmartEmptyState</TabsTrigger>
        </TabsList>

        {/* Basic Loading States */}
        <TabsContent value="basic" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>LoadingState Component</CardTitle>
              <CardDescription>Enhanced loading indicator with resource names and counts</CardDescription>
            </CardHeader>
            <CardContent className="space-y-8">
              <div className="grid md:grid-cols-3 gap-6">
                <div className="border rounded-lg p-4">
                  <h4 className="text-sm font-medium mb-4">Default</h4>
                  <LoadingState />
                </div>
                <div className="border rounded-lg p-4">
                  <h4 className="text-sm font-medium mb-4">With Resource</h4>
                  <LoadingState resource="workflows" />
                </div>
                <div className="border rounded-lg p-4">
                  <h4 className="text-sm font-medium mb-4">With Count</h4>
                  <LoadingState resource="environments" count={12} />
                </div>
              </div>

              <div className="grid md:grid-cols-3 gap-6">
                <div className="border rounded-lg p-4">
                  <h4 className="text-sm font-medium mb-4">Small</h4>
                  <LoadingState resource="items" size="sm" />
                </div>
                <div className="border rounded-lg p-4">
                  <h4 className="text-sm font-medium mb-4">Medium (Default)</h4>
                  <LoadingState resource="items" size="md" />
                </div>
                <div className="border rounded-lg p-4">
                  <h4 className="text-sm font-medium mb-4">Large</h4>
                  <LoadingState resource="items" size="lg" />
                </div>
              </div>

              <div className="border rounded-lg p-4">
                <h4 className="text-sm font-medium mb-4">Inline Variants</h4>
                <div className="space-y-4">
                  <LoadingState resource="data" inline />
                  <LoadingSpinner size="sm" label="Processing..." />
                  <LoadingSpinner size="md" label="Refreshing changes..." />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Multi-Step Loading</CardTitle>
              <CardDescription>Shows progress through multiple steps</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="max-w-md mx-auto">
                <MultiStepLoading
                  title="Refreshing Environment"
                  steps={multiStepSteps}
                />
                <Button
                  className="mt-4"
                  onClick={startMultiStep}
                  disabled={multiStepActive}
                >
                  <Play className="mr-2 h-4 w-4" />
                  Start Demo
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Skeleton Screens */}
        <TabsContent value="skeletons" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Skeleton Components</CardTitle>
              <CardDescription>Placeholder loading states for predictable layouts</CardDescription>
            </CardHeader>
            <CardContent className="space-y-8">
              <div>
                <h4 className="text-sm font-medium mb-4">Basic Skeletons</h4>
                <div className="flex gap-4 items-center">
                  <Skeleton className="h-12 w-12" circle />
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-[200px]" />
                    <Skeleton className="h-4 w-[150px]" />
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-4">Skeleton Text</h4>
                <SkeletonText lines={4} varied />
              </div>

              <div>
                <h4 className="text-sm font-medium mb-4">Skeleton Table Rows</h4>
                <SkeletonTableRows rows={4} columns={5} />
              </div>

              <div>
                <h4 className="text-sm font-medium mb-4">Skeleton Cards</h4>
                <div className="grid md:grid-cols-3 gap-4">
                  <SkeletonCard showHeader showAvatar contentLines={2} />
                  <SkeletonCard showHeader contentLines={3} />
                  <SkeletonCard showHeader contentLines={2} />
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-4">Skeleton List</h4>
                <SkeletonList items={4} showIcons />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Progress States */}
        <TabsContent value="progress" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Progress Indicators</CardTitle>
              <CardDescription>Loading states with progress percentage and ETA</CardDescription>
            </CardHeader>
            <CardContent className="space-y-8">
              <div className="grid md:grid-cols-2 gap-6">
                <div className="border rounded-lg p-4">
                  <h4 className="text-sm font-medium mb-4">25% Progress</h4>
                  <LoadingState
                    resource="workflows"
                    progress={25}
                    indeterminate={false}
                    estimatedTimeRemaining={45}
                  />
                </div>
                <div className="border rounded-lg p-4">
                  <h4 className="text-sm font-medium mb-4">75% Progress</h4>
                  <LoadingState
                    resource="credentials"
                    progress={75}
                    indeterminate={false}
                    estimatedTimeRemaining={12}
                  />
                </div>
              </div>

              <div className="border rounded-lg p-4">
                <h4 className="text-sm font-medium mb-4">With Steps</h4>
                <LoadingState
                  resource="deployment"
                  progress={50}
                  indeterminate={false}
                  currentStep="Validating configuration"
                  currentStepNumber={2}
                  totalSteps={4}
                  estimatedTimeRemaining={30}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Cancellable Operations */}
        <TabsContent value="cancellable" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Cancellable Operations</CardTitle>
              <CardDescription>Long-running operations with cancel and background options</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex gap-2">
                <Button onClick={startOperation} disabled={operationStatus === 'running'}>
                  <Play className="mr-2 h-4 w-4" />
                  Start Operation
                </Button>
                <Button variant="outline" onClick={resetOperation}>
                  <RotateCcw className="mr-2 h-4 w-4" />
                  Reset
                </Button>
              </div>

              <CancellableOperation
                title="Refreshing 47 Workflows"
                description="Synchronizing workflows from production environment"
                status={operationStatus}
                progress={operationProgress}
                currentAction="Processing workflow definitions..."
                currentItem={operationStatus === 'running' ? `Workflow ${processedCount + 1} of 47` : undefined}
                estimatedTimeRemaining={operationStatus === 'running' ? Math.round((100 - operationProgress) / 5) : undefined}
                processedCount={processedCount}
                totalCount={47}
                startTime={startTime}
                canCancel={true}
                canRunInBackground={true}
                isBackground={isBackground}
                onCancel={() => setOperationStatus('cancelled')}
                onMoveToBackground={() => setIsBackground(true)}
                onBringToForeground={() => setIsBackground(false)}
                successMessage="All 47 workflows synchronized successfully"
              />

              <div className="grid md:grid-cols-2 gap-4">
                <CancellableOperation
                  title="Completed Operation"
                  status="completed"
                  progress={100}
                  processedCount={47}
                  totalCount={47}
                  successMessage="All items processed successfully"
                />
                <CancellableOperation
                  title="Failed Operation"
                  status="failed"
                  progress={35}
                  processedCount={16}
                  totalCount={47}
                  errorMessage="Connection timeout after 30 seconds"
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* SmartEmptyState Variants */}
        <TabsContent value="smart" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>SmartEmptyState Loading Variants</CardTitle>
              <CardDescription>Enhanced SmartEmptyState with multiple loading display options</CardDescription>
            </CardHeader>
            <CardContent className="space-y-8">
              <div>
                <h4 className="text-sm font-medium mb-4">Default (Spinner)</h4>
                <div className="border rounded-lg p-4">
                  <SmartEmptyState
                    isLoading={true}
                    loadingResource="workflows"
                    loadingVariant="spinner"
                  />
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-4">Skeleton Table</h4>
                <div className="border rounded-lg p-4">
                  <SmartEmptyState
                    isLoading={true}
                    loadingResource="environments"
                    loadingVariant="skeleton-table"
                    skeletonCount={4}
                  />
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-4">Skeleton Cards</h4>
                <div className="border rounded-lg p-4">
                  <SmartEmptyState
                    isLoading={true}
                    loadingResource="credentials"
                    loadingVariant="skeleton-cards"
                    skeletonCount={3}
                  />
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-4">Skeleton List</h4>
                <div className="border rounded-lg p-4">
                  <SmartEmptyState
                    isLoading={true}
                    loadingResource="deployments"
                    loadingVariant="skeleton-list"
                    skeletonCount={4}
                  />
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-4">Progress</h4>
                <div className="border rounded-lg p-4">
                  <SmartEmptyState
                    isLoading={true}
                    loadingResource="snapshots"
                    loadingVariant="progress"
                    loadingProgress={65}
                    loadingEta={15}
                    loadingStep="Processing snapshot data"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default LoadingStatesDemo;
