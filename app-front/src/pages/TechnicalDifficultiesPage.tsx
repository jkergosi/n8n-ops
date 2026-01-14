/**
 * Technical Difficulties Page
 * Shown when the backend is unavailable to prevent redirect to login page.
 */
import { useAuth } from '@/lib/auth';
import { useHealthCheck } from '@/lib/use-health-check';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { AlertTriangle, RefreshCw, Loader2, ServerOff, CheckCircle } from 'lucide-react';

export function TechnicalDifficultiesPage() {
  const { retryConnection, isLoading } = useAuth();
  const { status, healthStatus, checkHealth, isChecking } = useHealthCheck();

  const handleRetry = async () => {
    // First check health to see if backend is back
    await checkHealth();
    // Then try to reconnect auth
    await retryConnection();
  };

  const isRetrying = isLoading || isChecking;

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-6">
      <Card className="max-w-lg w-full">
        <CardHeader className="text-center">
          <div className="mx-auto w-16 h-16 rounded-full bg-yellow-100 dark:bg-yellow-900/30 flex items-center justify-center mb-4">
            <ServerOff className="h-8 w-8 text-yellow-600 dark:text-yellow-400" />
          </div>
          <CardTitle className="text-2xl">We are Experiencing Technical Difficulties</CardTitle>
          <CardDescription className="text-base mt-2">
            Our services are temporarily unavailable. We apologize for any inconvenience.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Status message */}
          <div className="p-4 rounded-lg bg-muted text-center">
            <p className="text-sm text-muted-foreground">
              {status === 'unhealthy' ? (
                <>
                  <AlertTriangle className="h-4 w-4 inline mr-1 text-yellow-500" />
                  Unable to connect to the server
                </>
              ) : status === 'degraded' ? (
                <>
                  <AlertTriangle className="h-4 w-4 inline mr-1 text-orange-500" />
                  Some services are degraded
                </>
              ) : (
                <>
                  <CheckCircle className="h-4 w-4 inline mr-1 text-green-500" />
                  Services appear to be back online
                </>
              )}
            </p>
          </div>

          {/* Service status details (visible when health check has data) */}
          {healthStatus && healthStatus.services && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-muted-foreground">Service Status:</p>
              <div className="grid gap-2">
                {Object.entries(healthStatus.services).map(([service, data]) => {
                  const svcData = data as { status?: string; error?: string } | undefined;
                  return (
                    <div
                      key={service}
                      className="flex items-center justify-between p-2 rounded bg-muted/50"
                    >
                      <span className="text-sm capitalize">{service}</span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded ${
                          svcData?.status === 'healthy'
                            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                            : svcData?.status === 'degraded'
                            ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400'
                            : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                        }`}
                      >
                        {svcData?.status || 'unknown'}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Suggestions */}
          <div className="text-sm text-muted-foreground space-y-2">
            <p className="font-medium">What you can try:</p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              <li>Wait a moment and click "Try Again"</li>
              <li>Check your internet connection</li>
              <li>If the issue persists, please try again later</li>
            </ul>
          </div>

          {/* Action button */}
          <div className="flex justify-center pt-2">
            <Button
              onClick={handleRetry}
              disabled={isRetrying}
              size="lg"
              className="min-w-[140px]"
            >
              {isRetrying ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Connecting...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Try Again
                </>
              )}
            </Button>
          </div>

          {/* Additional help text */}
          <p className="text-xs text-center text-muted-foreground pt-4">
            If you continue to experience issues, please contact support.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
