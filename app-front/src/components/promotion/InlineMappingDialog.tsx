import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { CredentialPicker } from '@/components/credentials/CredentialPicker';
import { apiClient } from '@/lib/api-client';
import { toast } from 'sonner';
import { Key, ArrowRight, Loader2, AlertTriangle } from 'lucide-react';
import type { CredentialIssue, N8NCredentialRef } from '@/types/credentials';

interface InlineMappingDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  issue: CredentialIssue | null;
  targetEnvironmentId: string;
  targetEnvironmentName: string;
  onMappingCreated: () => void;
}

export function InlineMappingDialog({
  open,
  onOpenChange,
  issue,
  targetEnvironmentId,
  targetEnvironmentName,
  onMappingCreated,
}: InlineMappingDialogProps) {
  const queryClient = useQueryClient();
  const [selectedCredentialId, setSelectedCredentialId] = useState('');
  const [selectedCredential, setSelectedCredential] = useState<N8NCredentialRef | null>(null);
  const [logicalName, setLogicalName] = useState('');
  const [needsLogicalCredential, setNeedsLogicalCredential] = useState(false);

  useEffect(() => {
    if (issue) {
      setLogicalName(issue.logical_credential_key);
      setNeedsLogicalCredential(issue.issue_type === 'no_logical_credential');
      setSelectedCredentialId('');
      setSelectedCredential(null);
    }
  }, [issue]);

  const credentialType = issue?.logical_credential_key.split(':')[0] || '';

  const createLogicalMutation = useMutation({
    mutationFn: (data: { name: string; required_type: string }) =>
      apiClient.createLogicalCredential({
        name: data.name,
        required_type: data.required_type,
        description: `Created during deployment for ${issue?.workflow_name}`,
        tenant_id: '00000000-0000-0000-0000-000000000000',
      }),
    onSuccess: (data) => {
      toast.success('Logical credential created');
      queryClient.invalidateQueries({ queryKey: ['logical-credentials'] });
      return data.data.id;
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create logical credential');
    },
  });

  const createMappingMutation = useMutation({
    mutationFn: (data: {
      logical_credential_id: string;
      environment_id: string;
      physical_credential_id: string;
      physical_name: string;
      physical_type: string;
    }) => apiClient.createCredentialMapping(data),
    onSuccess: () => {
      toast.success('Credential mapping created');
      queryClient.invalidateQueries({ queryKey: ['credential-mappings'] });
      queryClient.invalidateQueries({ queryKey: ['credential-matrix'] });
      onMappingCreated();
      onOpenChange(false);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to create mapping');
    },
  });

  const handleSubmit = async () => {
    if (!selectedCredentialId || !selectedCredential) {
      toast.error('Please select a credential');
      return;
    }

    let logicalCredentialId: string | null = null;

    if (needsLogicalCredential) {
      try {
        const result = await createLogicalMutation.mutateAsync({
          name: logicalName,
          required_type: credentialType,
        });
        logicalCredentialId = result.data.id;
      } catch {
        return;
      }
    } else {
      const logicalCreds = await apiClient.getLogicalCredentials();
      const existing = logicalCreds.data?.find(
        (lc: any) => lc.name === logicalName
      );
      if (existing) {
        logicalCredentialId = existing.id;
      } else {
        toast.error('Logical credential not found. Creating one...');
        try {
          const result = await createLogicalMutation.mutateAsync({
            name: logicalName,
            required_type: credentialType,
          });
          logicalCredentialId = result.data.id;
        } catch {
          return;
        }
      }
    }

    if (!logicalCredentialId) {
      toast.error('Failed to resolve logical credential');
      return;
    }

    createMappingMutation.mutate({
      logical_credential_id: logicalCredentialId,
      environment_id: targetEnvironmentId,
      physical_credential_id: selectedCredentialId,
      physical_name: selectedCredential.name,
      physical_type: selectedCredential.type,
    });
  };

  const handleCredentialSelect = (id: string, cred: N8NCredentialRef | null) => {
    setSelectedCredentialId(id);
    setSelectedCredential(cred);
  };

  const isLoading = createLogicalMutation.isPending || createMappingMutation.isPending;

  if (!issue) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Key className="h-5 w-5" />
            Create Credential Mapping
          </DialogTitle>
          <DialogDescription>
            Map the credential used by "{issue.workflow_name}" to a credential in {targetEnvironmentName}.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Source Info */}
          <div className="p-3 bg-muted rounded-lg">
            <div className="text-sm font-medium mb-2">Source Credential Reference</div>
            <div className="flex items-center gap-2">
              <code className="text-sm bg-background px-2 py-1 rounded">
                {issue.logical_credential_key}
              </code>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">{targetEnvironmentName}</span>
            </div>
          </div>

          {/* Logical Credential Name */}
          {needsLogicalCredential && (
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                No logical credential exists for this reference. One will be created automatically.
              </AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Label>Logical Credential Name</Label>
            <Input
              value={logicalName}
              onChange={(e) => setLogicalName(e.target.value)}
              disabled={!needsLogicalCredential}
              placeholder="e.g., slackApi:notifications"
            />
            <p className="text-xs text-muted-foreground">
              This is the identifier used to map credentials across environments.
            </p>
          </div>

          {/* Target Credential Picker */}
          <div className="space-y-2">
            <Label>Target Credential in {targetEnvironmentName} *</Label>
            <CredentialPicker
              environmentId={targetEnvironmentId}
              filterType={credentialType}
              value={selectedCredentialId}
              onChange={handleCredentialSelect}
              placeholder={`Select ${credentialType || 'credential'}...`}
            />
            <p className="text-xs text-muted-foreground">
              Select the credential from N8N that should be used in {targetEnvironmentName}.
            </p>
          </div>

          {/* Selected Credential Preview */}
          {selectedCredential && (
            <div className="p-3 border rounded-lg bg-green-50/50 border-green-200">
              <div className="text-sm font-medium text-green-800 mb-1">Selected Credential</div>
              <div className="flex items-center gap-2">
                <Key className="h-4 w-4 text-green-600" />
                <span className="font-medium">{selectedCredential.name}</span>
                <span className="text-xs text-muted-foreground">({selectedCredential.type})</span>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!selectedCredentialId || isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Creating...
              </>
            ) : (
              'Create Mapping'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
