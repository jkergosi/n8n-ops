import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Loader2, ArrowLeft, ArrowRight, UserPlus, X, Mail } from 'lucide-react';
import type { OnboardingFormData } from '@/pages/OnboardingPage';

interface TeamInvitationStepProps {
  data: OnboardingFormData;
  onNext: (data: Partial<OnboardingFormData>) => void;
  onBack: () => void;
  onSkip: () => void;
  isLoading: boolean;
}

interface TeamInvite {
  email: string;
  role: string;
}

export function TeamInvitationStep({ data, onNext, onBack, onSkip, isLoading }: TeamInvitationStepProps) {
  const [invites, setInvites] = useState<TeamInvite[]>(data.teamInvites || []);
  const [currentEmail, setCurrentEmail] = useState('');
  const [currentRole, setCurrentRole] = useState('developer');
  const [emailError, setEmailError] = useState<string | null>(null);

  const addInvite = () => {
    setEmailError(null);
    
    if (!currentEmail.trim()) {
      setEmailError('Email address is required');
      return;
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(currentEmail.trim())) {
      setEmailError('Please enter a valid email address');
      return;
    }

    // Check if email already added
    if (invites.some(inv => inv.email.toLowerCase() === currentEmail.trim().toLowerCase())) {
      setEmailError('This email has already been added');
      return;
    }

    setInvites([...invites, { email: currentEmail.trim(), role: currentRole }]);
    setCurrentEmail('');
    setCurrentRole('developer');
    setEmailError(null);
  };

  const removeInvite = (index: number) => {
    setInvites(invites.filter((_, i) => i !== index));
  };

  const handleNext = () => {
    onNext({ teamInvites: invites });
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addInvite();
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h3 className="text-xl font-semibold">Invite Team Members</h3>
        <p className="text-sm text-muted-foreground">
          Add team members to your workspace. You can skip this step and add members later.
        </p>
      </div>

      <div className="space-y-4">
        <div className="flex gap-2">
          <div className="flex-1 space-y-2">
            <Label htmlFor="teamEmail">Email Address</Label>
            <Input
              id="teamEmail"
              type="email"
              placeholder="colleague@example.com"
              value={currentEmail}
              onChange={(e) => {
                setCurrentEmail(e.target.value);
                setEmailError(null);
              }}
              onKeyPress={handleKeyPress}
              disabled={isLoading}
              className={emailError ? 'border-destructive' : ''}
            />
            {emailError && (
              <p className="text-sm text-destructive">{emailError}</p>
            )}
          </div>
          <div className="w-40 space-y-2">
            <Label htmlFor="teamRole">Role</Label>
            <Select value={currentRole} onValueChange={setCurrentRole} disabled={isLoading}>
              <SelectTrigger id="teamRole">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="developer">Developer</SelectItem>
                <SelectItem value="viewer">Viewer</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-end">
            <Button
              type="button"
              onClick={addInvite}
              disabled={isLoading || !currentEmail.trim()}
              className="mb-0"
            >
              <UserPlus className="h-4 w-4 mr-2" />
              Add
            </Button>
          </div>
        </div>

        {invites.length > 0 && (
          <div className="space-y-2">
            <Label>Team Members to Invite ({invites.length})</Label>
            <div className="space-y-2 max-h-64 overflow-y-auto border rounded-lg p-4">
              {invites.map((invite, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-2 bg-muted/50 rounded-md"
                >
                  <div className="flex items-center gap-2 flex-1">
                    <Mail className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium">{invite.email}</span>
                    <Badge variant="secondary" className="ml-2 capitalize">
                      {invite.role}
                    </Badge>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeInvite(index)}
                    disabled={isLoading}
                    className="h-8 w-8 p-0"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}

        {invites.length === 0 && (
          <div className="rounded-lg border-2 border-dashed p-8 text-center">
            <UserPlus className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-sm text-muted-foreground">
              No team members added yet. Add members above or skip to continue.
            </p>
          </div>
        )}
      </div>

      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack} disabled={isLoading}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={onSkip} disabled={isLoading}>
            Skip for Now
          </Button>
          <Button onClick={handleNext} disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Sending Invites...
              </>
            ) : (
              <>
                {invites.length > 0 ? `Continue with ${invites.length} Invite${invites.length > 1 ? 's' : ''}` : 'Continue'}
                <ArrowRight className="ml-2 h-4 w-4" />
              </>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}

