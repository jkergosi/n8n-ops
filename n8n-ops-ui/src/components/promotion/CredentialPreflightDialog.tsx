import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { AlertTriangle, CheckCircle2, XCircle, ArrowRight } from 'lucide-react';
import type { CredentialPreflightResult, CredentialIssue as _CredentialIssue, ResolvedMapping as _ResolvedMapping } from '@/types/credentials';

interface CredentialPreflightDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  preflightResult: CredentialPreflightResult | null;
  onProceed: () => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export function CredentialPreflightDialog({
  open,
  onOpenChange,
  preflightResult,
  onProceed,
  onCancel,
  isLoading = false,
}: CredentialPreflightDialogProps) {
  if (!preflightResult) return null;

  const hasBlockingIssues = preflightResult.blocking_issues.length > 0;
  const hasWarnings = preflightResult.warnings.length > 0;
  const hasResolved = preflightResult.resolved_mappings.length > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {hasBlockingIssues ? (
              <>
                <XCircle className="h-5 w-5 text-destructive" />
                Credential Preflight Failed
              </>
            ) : hasWarnings ? (
              <>
                <AlertTriangle className="h-5 w-5 text-yellow-500" />
                Credential Preflight Warnings
              </>
            ) : (
              <>
                <CheckCircle2 className="h-5 w-5 text-green-500" />
                Credential Preflight Passed
              </>
            )}
          </DialogTitle>
          <DialogDescription>
            {hasBlockingIssues
              ? 'Some credential mappings are missing or invalid. Fix these before proceeding.'
              : hasWarnings
              ? 'Some credentials have warnings. Review before proceeding.'
              : 'All credential mappings are valid for this promotion.'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Blocking Issues */}
          {hasBlockingIssues && (
            <Alert variant="destructive">
              <XCircle className="h-4 w-4" />
              <AlertTitle>Blocking Issues ({preflightResult.blocking_issues.length})</AlertTitle>
              <AlertDescription>
                <ul className="mt-2 space-y-1 text-sm">
                  {preflightResult.blocking_issues.map((issue, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="font-medium">{issue.workflow_name}:</span>
                      <span>{issue.message}</span>
                    </li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          )}

          {/* Warnings */}
          {hasWarnings && (
            <Alert className="border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20">
              <AlertTriangle className="h-4 w-4 text-yellow-600" />
              <AlertTitle className="text-yellow-800 dark:text-yellow-200">
                Warnings ({preflightResult.warnings.length})
              </AlertTitle>
              <AlertDescription className="text-yellow-700 dark:text-yellow-300">
                <ul className="mt-2 space-y-1 text-sm">
                  {preflightResult.warnings.map((warning, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="font-medium">{warning.workflow_name}:</span>
                      <span>{warning.message}</span>
                    </li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          )}

          {/* Resolved Mappings */}
          {hasResolved && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base text-green-600 dark:text-green-400">
                  <CheckCircle2 className="h-4 w-4" />
                  Resolved Mappings ({preflightResult.resolved_mappings.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Logical Credential</TableHead>
                      <TableHead></TableHead>
                      <TableHead>Target Credential</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {preflightResult.resolved_mappings.map((mapping, idx) => (
                      <TableRow key={idx}>
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="font-medium">{mapping.logical_key}</span>
                            <span className="text-xs text-muted-foreground">
                              Source: {mapping.source_physical_name}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <ArrowRight className="h-4 w-4 text-muted-foreground" />
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-col">
                            <span className="font-medium">{mapping.target_physical_name}</span>
                            <span className="text-xs text-muted-foreground">
                              ID: {mapping.target_physical_id || 'N/A'}
                            </span>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}

          {/* No credentials */}
          {!hasBlockingIssues && !hasWarnings && !hasResolved && (
            <Alert>
              <CheckCircle2 className="h-4 w-4" />
              <AlertTitle>No Credentials Required</AlertTitle>
              <AlertDescription>
                The selected workflows do not use any credentials that require mapping.
              </AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            onClick={onProceed}
            disabled={hasBlockingIssues || isLoading}
            variant={hasBlockingIssues ? 'destructive' : 'default'}
          >
            {hasBlockingIssues
              ? 'Cannot Proceed - Fix Issues'
              : isLoading
              ? 'Processing...'
              : 'Proceed with Promotion'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
