import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Building2, Loader2 } from 'lucide-react';
import type { OnboardingFormData } from '@/pages/OnboardingPage';

interface OrganizationStepProps {
  data: OnboardingFormData;
  onNext: (data: Partial<OnboardingFormData>) => void;
  isLoading: boolean;
}

export function OrganizationStep({ data, onNext, isLoading }: OrganizationStepProps) {
  const [organizationName, setOrganizationName] = useState(data.organizationName || '');
  const [industry, setIndustry] = useState(data.industry || '');
  const [companySize, setCompanySize] = useState(data.companySize || '');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!organizationName.trim()) {
      return;
    }
    onNext({
      organizationName: organizationName.trim(),
      industry: industry || undefined,
      companySize: companySize || undefined,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Building2 className="h-5 w-5" />
          <span className="text-sm font-medium">Organization Details</span>
        </div>

        <div className="space-y-2">
          <Label htmlFor="organizationName">
            Organization Name <span className="text-destructive">*</span>
          </Label>
          <Input
            id="organizationName"
            type="text"
            placeholder="My Organization"
            value={organizationName}
            onChange={(e) => setOrganizationName(e.target.value)}
            disabled={isLoading}
            required
            autoFocus
          />
          <p className="text-xs text-muted-foreground">
            This will be the name of your workspace.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="industry">Industry (Optional)</Label>
            <Select value={industry} onValueChange={setIndustry} disabled={isLoading}>
              <SelectTrigger id="industry">
                <SelectValue placeholder="Select industry" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="technology">Technology</SelectItem>
                <SelectItem value="finance">Finance</SelectItem>
                <SelectItem value="healthcare">Healthcare</SelectItem>
                <SelectItem value="retail">Retail</SelectItem>
                <SelectItem value="manufacturing">Manufacturing</SelectItem>
                <SelectItem value="education">Education</SelectItem>
                <SelectItem value="other">Other</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="companySize">Company Size (Optional)</Label>
            <Select value={companySize} onValueChange={setCompanySize} disabled={isLoading}>
              <SelectTrigger id="companySize">
                <SelectValue placeholder="Select size" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1-10">1-10 employees</SelectItem>
                <SelectItem value="11-50">11-50 employees</SelectItem>
                <SelectItem value="51-200">51-200 employees</SelectItem>
                <SelectItem value="201-1000">201-1000 employees</SelectItem>
                <SelectItem value="1000+">1000+ employees</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <Button type="submit" disabled={isLoading || !organizationName.trim()}>
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Setting up...
            </>
          ) : (
            'Continue'
          )}
        </Button>
      </div>
    </form>
  );
}

