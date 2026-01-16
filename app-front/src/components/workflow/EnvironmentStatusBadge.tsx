import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { CheckCircle2, AlertTriangle, Clock, HelpCircle } from 'lucide-react';
import type { WorkflowEnvironmentStatus } from '@/types';

/**
 * Badge variant type for WorkflowEnvironmentStatus
 */
type StatusBadgeVariant = 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning';

/**
 * Status badge configuration for each WorkflowEnvironmentStatus.
 * Maps backend-computed status to display label, variant, tooltip, and icon.
 */
const STATUS_CONFIG: Record<
  WorkflowEnvironmentStatus,
  {
    label: string;
    variant: StatusBadgeVariant;
    tooltip: string;
    icon: typeof CheckCircle2;
  }
> = {
  linked: {
    label: 'Linked',
    variant: 'success',
    tooltip: 'Canonical workflow is mapped to the environment and up to date.',
    icon: CheckCircle2,
  },
  unmapped: {
    label: 'Unmapped',
    variant: 'outline',
    tooltip: 'Workflow exists in the environment but has no canonical mapping.',
    icon: HelpCircle,
  },
  drift: {
    label: 'Drift',
    variant: 'destructive',
    tooltip: 'Canonical mapping exists, but the environment version differs from canonical.',
    icon: AlertTriangle,
  },
  out_of_date: {
    label: 'Out of Date',
    variant: 'warning',
    tooltip: 'Canonical version is newer than the version deployed to the environment.',
    icon: Clock,
  },
};

export interface EnvironmentStatusBadgeProps {
  /** Backend-computed status for this workflow in this environment */
  status: WorkflowEnvironmentStatus;
  /** Whether to show the tooltip on hover */
  showTooltip?: boolean;
  /** Whether to show the icon alongside the label */
  showIcon?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Pure presentation component for displaying workflow environment status.
 * The status is computed by the backend - this component only renders it.
 */
export function EnvironmentStatusBadge({
  status,
  showTooltip = true,
  showIcon = true,
  className,
}: EnvironmentStatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;

  const badge = (
    <Badge variant={config.variant} className={className}>
      {showIcon && <Icon className="h-3 w-3 mr-1" />}
      {config.label}
    </Badge>
  );

  if (!showTooltip) {
    return badge;
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          {badge}
        </TooltipTrigger>
        <TooltipContent>
          <p>{config.tooltip}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
