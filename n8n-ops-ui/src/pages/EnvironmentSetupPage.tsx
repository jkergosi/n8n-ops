// @ts-nocheck
// TODO: Fix TypeScript errors in this file
import { useState, useEffect } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Loader2, Server, GitBranch, CheckCircle, XCircle, ArrowLeft, CheckCircle2, AlertCircle, ArrowRight, Wand2 } from 'lucide-react';
import { toast } from 'sonner';
import { apiClient } from '@/lib/api-client';
import { useAuth } from '@/lib/auth';
import { useEnvironmentTypes } from '@/hooks/useEnvironmentTypes';
import { AdvancedOptionsPanel } from '@/components/ui/AdvancedOptionsPanel';
import {
  isWizardModeEnabled,
  setWizardModeSeen,
  setWizardModeEnabled,
} from '@/lib/wizard-mode';
import type { EnvironmentType } from '@/types';

// Wizard step definitions
type WizardStep = 'n8n' | 'github';

export function EnvironmentSetupPage() {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const isFirstEnvironment = searchParams.get('first') === 'true';
  const isEditMode = !!id;

  const { refreshUser } = useAuth();
  const { environmentTypes } = useEnvironmentTypes();

  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingEnv, setIsLoadingEnv] = useState(isEditMode);
  const [testingN8n, setTestingN8n] = useState(false);
  const [testingGit, setTestingGit] = useState(false);
  const [n8nTestResult, setN8nTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [gitTestResult, setGitTestResult] = useState<{ success: boolean; message: string } | null>(null);

  // Wizard mode state
  const [wizardMode, setWizardMode] = useState(() => isWizardModeEnabled());
  const [wizardStep, setWizardStep] = useState<WizardStep>('n8n');

  // Get the default type from environment types (first active one)
  const defaultType = environmentTypes[0]?.key || 'dev';

  const [formData, setFormData] = useState({
    name: '',
    type: '' as EnvironmentType,
    n8nUrl: '',
    n8nApiKey: '',
    gitRepoUrl: '',
    gitBranch: '',
    gitPat: '',
  });

  // Set default type when environment types are loaded (only for new environments)
  useEffect(() => {
    if (!isEditMode && !formData.type && defaultType) {
      setFormData((prev) => ({ ...prev, type: defaultType }));
    }
  }, [defaultType, isEditMode, formData.type]);

  useEffect(() => {
    document.title = isEditMode ? 'Edit Environment - WorkflowOps' : 'New Environment - WorkflowOps';
    return () => {
      document.title = 'WorkflowOps';
    };
  }, [isEditMode]);

  // Load existing environment data if editing
  useEffect(() => {
    if (isEditMode && id) {
      loadEnvironment(id);
    }
  }, [id, isEditMode]);

  const loadEnvironment = async (envId: string) => {
    try {
      setIsLoadingEnv(true);
      const response = await apiClient.getEnvironment(envId);
      const env = response.data;
      setFormData({
        name: env.name || '',
        type: env.type || defaultType,
        n8nUrl: env.baseUrl || '',
        n8nApiKey: env.apiKey || '',
        gitRepoUrl: env.gitRepoUrl || '',
        gitBranch: env.gitBranch || 'main',
        gitPat: env.gitPat || '',
      });
    } catch (error) {
      console.error('Failed to load environment:', error);
      toast.error('Failed to load environment');
      navigate('/environments');
    } finally {
      setIsLoadingEnv(false);
    }
  };

  const testN8nConnection = async () => {
    if (!formData.n8nUrl || !formData.n8nApiKey) {
      toast.error('Please enter N8N URL and API key first', {
        icon: <AlertCircle className="h-5 w-5" />,
      });
      return;
    }

    setTestingN8n(true);
    setN8nTestResult(null);
    try {
      const response = await apiClient.testEnvironmentConnection(formData.n8nUrl, formData.n8nApiKey);
      setN8nTestResult(response.data);
      if (response.data.success) {
        toast.success('N8N connection successful!', {
          icon: <CheckCircle2 className="h-5 w-5" />,
        });
      } else {
        toast.error(response.data.message || 'Connection failed', {
          icon: <AlertCircle className="h-5 w-5" />,
        });
      }
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Connection test failed';
      setN8nTestResult({ success: false, message });
      toast.error(message, {
        icon: <AlertCircle className="h-5 w-5" />,
      });
    } finally {
      setTestingN8n(false);
    }
  };

  const testGitConnection = async () => {
    if (!formData.gitRepoUrl) {
      toast.error('Please enter GitHub repository URL first');
      return;
    }

    setTestingGit(true);
    setGitTestResult(null);
    try {
      const response = await apiClient.testGitConnection({
        gitRepoUrl: formData.gitRepoUrl,
        gitBranch: formData.gitBranch,
        gitPat: formData.gitPat,
      });
      setGitTestResult(response.data);
      if (response.data.success) {
        toast.success('GitHub connection successful!');
      } else {
        toast.error(response.data.message || 'Connection failed');
      }
    } catch (error: any) {
      const message = error.response?.data?.detail || 'Connection test failed';
      setGitTestResult({ success: false, message });
      toast.error(message);
    } finally {
      setTestingGit(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name || !formData.n8nUrl || !formData.n8nApiKey) {
      toast.error('Please fill in all required fields');
      return;
    }

    setIsLoading(true);
    try {
      if (isEditMode && id) {
        // Update existing environment
        await apiClient.updateEnvironment(id, {
          name: formData.name,
          base_url: formData.n8nUrl,
          api_key: formData.n8nApiKey,
          git_repo_url: formData.gitRepoUrl || undefined,
          git_branch: formData.gitBranch || undefined,
          git_pat: formData.gitPat || undefined,
        });
        toast.success('Environment updated successfully!');
        navigate('/environments');
      } else {
        // Create new environment
        const response = await apiClient.createEnvironment({
          name: formData.name,
          type: formData.type,
          base_url: formData.n8nUrl,
          api_key: formData.n8nApiKey,
          git_repo_url: formData.gitRepoUrl || undefined,
          git_branch: formData.gitBranch || undefined,
          git_pat: formData.gitPat || undefined,
        });

        // Mark wizard as seen for future visits
        setWizardModeSeen();

        // Start syncing in background
        const environmentId = response.data.id;
        toast.success('Environment created! Starting synchronization...');

        // Refresh user to update hasEnvironment flag
        await refreshUser();

        // Navigate to dashboard first, then trigger sync
        navigate('/');

        // Trigger sync in background (don't await)
        apiClient.syncEnvironment(environmentId)
          .then((syncResult) => {
            if (syncResult.data.success) {
              toast.success(`Sync complete: ${syncResult.data.results.workflows.synced} workflows synced`);
            } else {
              toast.warning('Sync completed with some issues');
            }
          })
          .catch((error) => {
            console.error('Sync failed:', error);
            toast.error('Environment sync failed. You can retry from the Environments page.');
          });
      }
    } catch (error: any) {
      console.error('Failed to save environment:', error);
      const message = error.response?.data?.detail || 'Failed to save environment';
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  // Toggle wizard mode
  const handleToggleWizardMode = () => {
    const newMode = !wizardMode;
    setWizardMode(newMode);
    setWizardModeEnabled(newMode);
    // Reset to first step when entering wizard mode
    if (newMode) {
      setWizardStep('n8n');
    }
  };

  // Navigate to next wizard step
  const handleNextStep = () => {
    if (wizardStep === 'n8n') {
      // Validate N8N fields before proceeding
      if (!formData.name || !formData.n8nUrl || !formData.n8nApiKey) {
        toast.error('Please fill in all required fields');
        return;
      }
      setWizardStep('github');
    }
  };

  // Navigate to previous wizard step
  const handlePrevStep = () => {
    if (wizardStep === 'github') {
      setWizardStep('n8n');
    }
  };

  // Check if N8N step is valid
  const isN8nStepValid = formData.name && formData.n8nUrl && formData.n8nApiKey;

  if (isLoadingEnv) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
          <p className="mt-4 text-muted-foreground">Loading environment...</p>
        </div>
      </div>
    );
  }

  // Render wizard mode toggle link
  const renderWizardModeToggle = () => (
    <button
      type="button"
      onClick={handleToggleWizardMode}
      className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded"
    >
      <Wand2 className="h-3.5 w-3.5" />
      {wizardMode ? 'Switch to full form' : 'Switch to guided setup'}
    </button>
  );

  // Render Basic Info section
  const renderBasicInfoSection = () => (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold flex items-center gap-2">
        <Server className="h-5 w-5 text-primary" />
        Basic Information
      </h3>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="name">Environment Name *</Label>
          <Input
            id="name"
            placeholder="Development"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            disabled={isLoading}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="type">Type *</Label>
          <Select
            value={formData.type}
            onValueChange={(value: EnvironmentType) => setFormData({ ...formData, type: value })}
            disabled={isLoading}
          >
            <SelectTrigger id="type">
              <SelectValue placeholder="Select type" />
            </SelectTrigger>
            <SelectContent>
              {environmentTypes.map((t) => (
                <SelectItem key={t.id} value={t.key}>
                  {t.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  );

  // Render N8N Instance section
  const renderN8nSection = () => (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold flex items-center gap-2">
        <Server className="h-5 w-5 text-primary" />
        N8N Instance
      </h3>

      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="n8nUrl">N8N URL *</Label>
          <Input
            id="n8nUrl"
            type="url"
            placeholder="https://your-n8n.example.com"
            value={formData.n8nUrl}
            onChange={(e) => {
              setFormData({ ...formData, n8nUrl: e.target.value });
              setN8nTestResult(null);
            }}
            disabled={isLoading}
          />
          <p className="text-xs text-muted-foreground">
            The URL of your N8N instance
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="n8nApiKey">API Key *</Label>
          <Input
            id="n8nApiKey"
            type="password"
            placeholder="n8n_api_xxxxxxxxxxxxx"
            value={formData.n8nApiKey}
            onChange={(e) => {
              setFormData({ ...formData, n8nApiKey: e.target.value });
              setN8nTestResult(null);
            }}
            disabled={isLoading}
          />
          <p className="text-xs text-muted-foreground">
            Generate an API key in your N8N instance under Settings &rarr; API
          </p>
        </div>

        <div className="flex items-center gap-4">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={testN8nConnection}
            disabled={testingN8n || isLoading}
          >
            {testingN8n ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Testing...
              </>
            ) : (
              'Test Connection'
            )}
          </Button>

          {n8nTestResult && (
            <div className={`flex items-center gap-2 text-sm ${n8nTestResult.success ? 'text-green-600' : 'text-red-600'}`}>
              {n8nTestResult.success ? (
                <CheckCircle className="h-4 w-4" />
              ) : (
                <XCircle className="h-4 w-4" />
              )}
              {n8nTestResult.message}
            </div>
          )}
        </div>
      </div>
    </div>
  );

  // Render GitHub section content (used in both modes)
  const renderGitHubContent = () => (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="gitRepoUrl">Repository URL</Label>
        <Input
          id="gitRepoUrl"
          type="url"
          placeholder="https://github.com/your-org/your-repo"
          value={formData.gitRepoUrl}
          onChange={(e) => {
            setFormData({ ...formData, gitRepoUrl: e.target.value });
            setGitTestResult(null);
          }}
          disabled={isLoading}
        />
        <p className="text-xs text-muted-foreground">
          Repository for workflow versioning and backup
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="gitBranch">Branch</Label>
          <Input
            id="gitBranch"
            placeholder="main"
            value={formData.gitBranch}
            onChange={(e) => setFormData({ ...formData, gitBranch: e.target.value })}
            disabled={isLoading}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="gitPat">Personal Access Token</Label>
          <Input
            id="gitPat"
            type="password"
            placeholder="ghp_xxxxxxxxxxxxx"
            value={formData.gitPat}
            onChange={(e) => {
              setFormData({ ...formData, gitPat: e.target.value });
              setGitTestResult(null);
            }}
            disabled={isLoading}
          />
        </div>
      </div>

      {formData.gitRepoUrl && (
        <div className="flex items-center gap-4">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={testGitConnection}
            disabled={testingGit || isLoading}
          >
            {testingGit ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Testing...
              </>
            ) : (
              'Test Connection'
            )}
          </Button>

          {gitTestResult && (
            <div className={`flex items-center gap-2 text-sm ${gitTestResult.success ? 'text-green-600' : 'text-red-600'}`}>
              {gitTestResult.success ? (
                <CheckCircle className="h-4 w-4" />
              ) : (
                <XCircle className="h-4 w-4" />
              )}
              {gitTestResult.message}
            </div>
          )}
        </div>
      )}
    </div>
  );

  // Render GitHub section (full form mode with AdvancedOptionsPanel)
  const renderGitHubSection = () => (
    <AdvancedOptionsPanel
      title="GitHub Integration"
      description="Optional: Set up version control for your workflows"
      defaultExpanded={!!formData.gitRepoUrl}
    >
      {renderGitHubContent()}
    </AdvancedOptionsPanel>
  );

  // Render GitHub section (wizard mode - without panel wrapper)
  const renderGitHubSectionWizard = () => (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold flex items-center gap-2">
        <GitBranch className="h-5 w-5 text-primary" />
        GitHub Integration
        <span className="text-xs font-normal text-muted-foreground">(Optional)</span>
      </h3>
      {renderGitHubContent()}
    </div>
  );

  // Render wizard step indicator
  const renderWizardStepIndicator = () => (
    <div className="flex items-center justify-center gap-2 mb-6">
      <div
        className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium ${
          wizardStep === 'n8n'
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted text-muted-foreground'
        }`}
      >
        1
      </div>
      <div className="w-8 h-0.5 bg-muted" />
      <div
        className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-medium ${
          wizardStep === 'github'
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted text-muted-foreground'
        }`}
      >
        2
      </div>
    </div>
  );

  // Render wizard mode content
  const renderWizardContent = () => (
    <>
      {renderWizardStepIndicator()}

      {wizardStep === 'n8n' && (
        <div className="space-y-8">
          {renderBasicInfoSection()}
          {renderN8nSection()}

          {/* Info Box */}
          {isFirstEnvironment && (
            <div className="rounded-lg bg-muted/50 p-4">
              <h4 className="text-sm font-medium mb-2">What happens next?</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>Your environment will be created</li>
                <li>Workflows will be automatically synced from your N8N instance</li>
                <li>You can view and manage your workflows from the dashboard</li>
              </ul>
            </div>
          )}

          {/* Wizard Actions - Step 1 */}
          <div className="flex justify-between gap-4">
            <div>
              {renderWizardModeToggle()}
            </div>
            <div className="flex gap-4">
              {!isFirstEnvironment && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate(-1)}
                  disabled={isLoading}
                >
                  Cancel
                </Button>
              )}
              <Button
                type="button"
                onClick={handleNextStep}
                disabled={!isN8nStepValid || isLoading}
              >
                Next: GitHub Setup
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </div>
        </div>
      )}

      {wizardStep === 'github' && (
        <div className="space-y-8">
          {renderGitHubSectionWizard()}

          <div className="rounded-lg bg-muted/50 p-4">
            <h4 className="text-sm font-medium mb-2">GitHub Integration (Optional)</h4>
            <p className="text-sm text-muted-foreground">
              Connect to GitHub to enable workflow versioning and backup. You can skip this step and set it up later.
            </p>
          </div>

          {/* Wizard Actions - Step 2 */}
          <div className="flex justify-between gap-4">
            <Button
              type="button"
              variant="outline"
              onClick={handlePrevStep}
              disabled={isLoading}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>
            <div className="flex gap-4">
              <Button type="submit" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {isEditMode ? 'Saving...' : 'Creating...'}
                  </>
                ) : (
                  isEditMode ? 'Save Changes' : 'Create Environment'
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );

  // Render full form mode content
  const renderFullFormContent = () => (
    <div className="space-y-8">
      {renderBasicInfoSection()}
      {renderN8nSection()}
      {renderGitHubSection()}

      {/* Info Box */}
      {isFirstEnvironment && (
        <div className="rounded-lg bg-muted/50 p-4">
          <h4 className="text-sm font-medium mb-2">What happens next?</h4>
          <ul className="text-sm text-muted-foreground space-y-1">
            <li>Your environment will be created</li>
            <li>Workflows will be automatically synced from your N8N instance</li>
            <li>You can view and manage your workflows from the dashboard</li>
          </ul>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-between gap-4">
        <div>
          {renderWizardModeToggle()}
        </div>
        <div className="flex gap-4">
          {!isFirstEnvironment && (
            <Button
              type="button"
              variant="outline"
              onClick={() => navigate(-1)}
              disabled={isLoading}
            >
              Cancel
            </Button>
          )}
          <Button type="submit" disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {isEditMode ? 'Saving...' : 'Creating...'}
              </>
            ) : (
              isEditMode ? 'Save Changes' : 'Create Environment'
            )}
          </Button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="container max-w-3xl py-8">
      {!isFirstEnvironment && (
        <Button variant="ghost" onClick={() => navigate(-1)} className="mb-6">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">
            {isEditMode ? 'Edit Environment' : isFirstEnvironment ? 'Set Up Your First Environment' : 'Add Environment'}
          </CardTitle>
          <CardDescription>
            {isFirstEnvironment
              ? 'Connect your N8N instance and optionally set up GitHub for workflow versioning.'
              : isEditMode
                ? 'Update your environment configuration.'
                : 'Add a new N8N environment to your workspace.'}
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit}>
            {wizardMode && !isEditMode ? renderWizardContent() : renderFullFormContent()}
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
