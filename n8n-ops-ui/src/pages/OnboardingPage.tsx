import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Server, GitBranch, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';

export function OnboardingPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    devN8nUrl: '',
    devApiKey: '',
    githubUrl: '',
    githubToken: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Validate current step
    if (step === 1) {
      if (!formData.devN8nUrl || !formData.devApiKey) {
        toast.error('Please fill in all development environment fields');
        return;
      }
      setStep(2);
    } else {
      if (!formData.githubUrl || !formData.githubToken) {
        toast.error('Please fill in all GitHub credentials');
        return;
      }

      // Save to localStorage (in production, this would call an API)
      localStorage.setItem('onboarding_complete', 'true');
      localStorage.setItem('dev_n8n_url', formData.devN8nUrl);

      toast.success('Setup completed successfully!');
      navigate('/');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <CardTitle className="text-2xl">Welcome to N8N Ops</CardTitle>
          <CardDescription>
            Let's get your workspace set up. This will only take a minute.
          </CardDescription>

          {/* Progress indicator */}
          <div className="flex items-center gap-2 mt-4">
            <div className={`flex items-center gap-2 ${step >= 1 ? 'text-primary' : 'text-muted-foreground'}`}>
              {step > 1 ? <CheckCircle className="h-5 w-5" /> : <div className="h-5 w-5 rounded-full border-2 border-current flex items-center justify-center text-xs">1</div>}
              <span className="text-sm font-medium">Dev Environment</span>
            </div>
            <div className="flex-1 h-0.5 bg-border" />
            <div className={`flex items-center gap-2 ${step >= 2 ? 'text-primary' : 'text-muted-foreground'}`}>
              <div className="h-5 w-5 rounded-full border-2 border-current flex items-center justify-center text-xs">2</div>
              <span className="text-sm font-medium">GitHub</span>
            </div>
          </div>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {step === 1 && (
              <div className="space-y-4">
                <div className="flex items-center gap-2 mb-4">
                  <Server className="h-5 w-5 text-primary" />
                  <h3 className="text-lg font-semibold">Development Environment</h3>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="devN8nUrl">Development N8N URL *</Label>
                  <Input
                    id="devN8nUrl"
                    type="url"
                    placeholder="https://dev.n8n.example.com"
                    value={formData.devN8nUrl}
                    onChange={(e) => setFormData({ ...formData, devN8nUrl: e.target.value })}
                    required
                  />
                  <p className="text-xs text-muted-foreground">
                    The URL of your development n8n instance
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="devApiKey">Development API Key *</Label>
                  <Input
                    id="devApiKey"
                    type="password"
                    placeholder="n8n_api_xxxxxxxxxxxxx"
                    value={formData.devApiKey}
                    onChange={(e) => setFormData({ ...formData, devApiKey: e.target.value })}
                    required
                  />
                  <p className="text-xs text-muted-foreground">
                    API key from your n8n instance settings
                  </p>
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-4">
                  <p className="text-sm text-blue-900">
                    <strong>Tip:</strong> You can find your API key in your n8n instance under Settings → API
                  </p>
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="space-y-4">
                <div className="flex items-center gap-2 mb-4">
                  <GitBranch className="h-5 w-5 text-primary" />
                  <h3 className="text-lg font-semibold">GitHub Configuration</h3>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="githubUrl">GitHub Repository URL *</Label>
                  <Input
                    id="githubUrl"
                    type="url"
                    placeholder="https://github.com/your-org/your-repo"
                    value={formData.githubUrl}
                    onChange={(e) => setFormData({ ...formData, githubUrl: e.target.value })}
                    required
                  />
                  <p className="text-xs text-muted-foreground">
                    Repository where your workflows will be versioned
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="githubToken">Personal Access Token *</Label>
                  <Input
                    id="githubToken"
                    type="password"
                    placeholder="ghp_xxxxxxxxxxxxx"
                    value={formData.githubToken}
                    onChange={(e) => setFormData({ ...formData, githubToken: e.target.value })}
                    required
                  />
                  <p className="text-xs text-muted-foreground">
                    GitHub token with repo access permissions
                  </p>
                </div>

                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-4">
                  <p className="text-sm text-blue-900">
                    <strong>Tip:</strong> Create a token at github.com/settings/tokens with 'repo' scope
                  </p>
                </div>
              </div>
            )}

            <div className="flex justify-between pt-4">
              {step > 1 && (
                <Button type="button" variant="outline" onClick={() => setStep(step - 1)}>
                  Back
                </Button>
              )}
              <Button type="submit" className={step === 1 ? 'ml-auto' : ''}>
                {step === 1 ? 'Continue' : 'Complete Setup'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
