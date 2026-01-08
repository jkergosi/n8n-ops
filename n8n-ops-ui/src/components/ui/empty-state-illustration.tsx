/**
 * Empty State Illustration Component
 * Provides contextual SVG illustrations for empty states
 * Each illustration communicates the purpose of the empty area
 */
import * as React from "react"
import { cn } from "@/lib/utils"

export type IllustrationType =
  | 'empty-folder'
  | 'empty-inbox'
  | 'no-data'
  | 'no-environments'
  | 'no-workflows'
  | 'no-deployments'
  | 'no-pipelines'
  | 'no-incidents'
  | 'no-credentials'
  | 'no-activity'
  | 'no-search-results'
  | 'getting-started'
  | 'connection-error'
  | 'success'

interface EmptyStateIllustrationProps extends React.SVGProps<SVGSVGElement> {
  type: IllustrationType
  size?: 'sm' | 'md' | 'lg' | 'xl'
}

const sizeClasses = {
  sm: 'w-16 h-16',
  md: 'w-24 h-24',
  lg: 'w-32 h-32',
  xl: 'w-48 h-48',
}

// Empty Folder Illustration
const EmptyFolderIllustration = (props: React.SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
    <path d="M10 25C10 22.2386 12.2386 20 15 20H40L50 30H105C107.761 30 110 32.2386 110 35V85C110 87.7614 107.761 90 105 90H15C12.2386 90 10 87.7614 10 85V25Z" className="fill-muted stroke-muted-foreground/30" strokeWidth="2"/>
    <path d="M10 35V25C10 22.2386 12.2386 20 15 20H40L50 30H105C107.761 30 110 32.2386 110 35V35H10Z" className="fill-muted-foreground/10"/>
    <circle cx="60" cy="60" r="12" className="stroke-muted-foreground/40" strokeWidth="2" strokeDasharray="4 4"/>
    <path d="M55 60L65 60M60 55V65" className="stroke-muted-foreground/40" strokeWidth="2" strokeLinecap="round"/>
  </svg>
)

// No Environments Illustration
const NoEnvironmentsIllustration = (props: React.SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
    {/* Server rack outline */}
    <rect x="20" y="15" width="80" height="70" rx="4" className="fill-muted stroke-muted-foreground/30" strokeWidth="2"/>
    {/* Server slots */}
    <rect x="28" y="25" width="64" height="14" rx="2" className="fill-background stroke-muted-foreground/20" strokeWidth="1.5" strokeDasharray="4 2"/>
    <rect x="28" y="45" width="64" height="14" rx="2" className="fill-background stroke-muted-foreground/20" strokeWidth="1.5" strokeDasharray="4 2"/>
    <rect x="28" y="65" width="64" height="14" rx="2" className="fill-background stroke-muted-foreground/20" strokeWidth="1.5" strokeDasharray="4 2"/>
    {/* Plus icon */}
    <circle cx="60" cy="50" r="16" className="fill-primary/10 stroke-primary/50" strokeWidth="2"/>
    <path d="M52 50H68M60 42V58" className="stroke-primary" strokeWidth="2" strokeLinecap="round"/>
  </svg>
)

// No Workflows Illustration
const NoWorkflowsIllustration = (props: React.SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
    {/* Flow nodes */}
    <rect x="10" y="35" width="25" height="25" rx="4" className="fill-muted stroke-muted-foreground/30" strokeWidth="2" strokeDasharray="4 2"/>
    <rect x="47" y="35" width="25" height="25" rx="4" className="fill-muted stroke-muted-foreground/30" strokeWidth="2" strokeDasharray="4 2"/>
    <rect x="85" y="35" width="25" height="25" rx="4" className="fill-muted stroke-muted-foreground/30" strokeWidth="2" strokeDasharray="4 2"/>
    {/* Connecting lines */}
    <path d="M35 47.5H47M72 47.5H85" className="stroke-muted-foreground/30" strokeWidth="2" strokeDasharray="4 2"/>
    {/* Sparkle/New indicator */}
    <circle cx="60" cy="75" r="10" className="fill-primary/10"/>
    <path d="M60 68V82M53 75H67" className="stroke-primary" strokeWidth="2" strokeLinecap="round"/>
  </svg>
)

// No Deployments Illustration
const NoDeploymentsIllustration = (props: React.SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
    {/* Rocket */}
    <path d="M60 20C60 20 45 35 45 55C45 75 60 85 60 85C60 85 75 75 75 55C75 35 60 20 60 20Z" className="fill-muted stroke-muted-foreground/40" strokeWidth="2"/>
    <circle cx="60" cy="50" r="8" className="fill-primary/20 stroke-primary/60" strokeWidth="2"/>
    {/* Fins */}
    <path d="M45 70L35 80L45 75Z" className="fill-muted-foreground/30"/>
    <path d="M75 70L85 80L75 75Z" className="fill-muted-foreground/30"/>
    {/* Launch pad */}
    <rect x="40" y="88" width="40" height="4" rx="2" className="fill-muted-foreground/20"/>
    {/* Stars */}
    <circle cx="25" cy="25" r="2" className="fill-primary/40"/>
    <circle cx="95" cy="30" r="1.5" className="fill-primary/30"/>
    <circle cx="90" cy="15" r="2" className="fill-primary/40"/>
  </svg>
)

// No Pipelines Illustration
const NoPipelinesIllustration = (props: React.SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
    {/* Pipeline stages */}
    <rect x="10" y="40" width="20" height="20" rx="10" className="fill-muted stroke-muted-foreground/30" strokeWidth="2"/>
    <rect x="50" y="40" width="20" height="20" rx="10" className="fill-muted stroke-muted-foreground/30" strokeWidth="2"/>
    <rect x="90" y="40" width="20" height="20" rx="10" className="fill-muted stroke-muted-foreground/30" strokeWidth="2"/>
    {/* Arrows */}
    <path d="M32 50H48M72 50H88" className="stroke-muted-foreground/30" strokeWidth="2" strokeDasharray="4 2"/>
    <path d="M42 50L46 46M42 50L46 54" className="stroke-muted-foreground/30" strokeWidth="2" strokeLinecap="round"/>
    <path d="M82 50L86 46M82 50L86 54" className="stroke-muted-foreground/30" strokeWidth="2" strokeLinecap="round"/>
    {/* Git branch icon */}
    <circle cx="60" cy="75" r="12" className="fill-primary/10"/>
    <path d="M55 72V78M65 72V76C65 77.1 64.1 78 63 78H57" className="stroke-primary" strokeWidth="2" strokeLinecap="round"/>
    <circle cx="55" cy="70" r="2" className="fill-primary"/>
    <circle cx="65" cy="70" r="2" className="fill-primary"/>
    <circle cx="55" cy="80" r="2" className="fill-primary"/>
  </svg>
)

// No Incidents Illustration (Happy state!)
const NoIncidentsIllustration = (props: React.SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
    {/* Shield with checkmark */}
    <path d="M60 10L100 25V50C100 75 60 95 60 95C60 95 20 75 20 50V25L60 10Z" className="fill-green-500/10 stroke-green-500/50" strokeWidth="2"/>
    <path d="M45 50L55 60L75 40" className="stroke-green-500" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
    {/* Sparkles */}
    <circle cx="15" cy="30" r="2" className="fill-green-500/40"/>
    <circle cx="105" cy="35" r="2" className="fill-green-500/40"/>
    <circle cx="100" cy="20" r="1.5" className="fill-green-500/30"/>
  </svg>
)

// No Credentials Illustration
const NoCredentialsIllustration = (props: React.SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
    {/* Key */}
    <circle cx="40" cy="40" r="20" className="fill-muted stroke-muted-foreground/30" strokeWidth="2"/>
    <circle cx="40" cy="40" r="8" className="fill-background stroke-muted-foreground/40" strokeWidth="2"/>
    <path d="M55 55L85 85" className="stroke-muted-foreground/40" strokeWidth="4" strokeLinecap="round"/>
    <path d="M75 75L80 70M80 80L85 75" className="stroke-muted-foreground/40" strokeWidth="4" strokeLinecap="round"/>
    {/* Lock indicator */}
    <circle cx="40" cy="40" r="3" className="fill-primary/40"/>
  </svg>
)

// No Activity Illustration
const NoActivityIllustration = (props: React.SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
    {/* Clock */}
    <circle cx="60" cy="50" r="35" className="fill-muted stroke-muted-foreground/30" strokeWidth="2"/>
    <circle cx="60" cy="50" r="28" className="fill-background"/>
    <path d="M60 30V50L75 60" className="stroke-muted-foreground/40" strokeWidth="3" strokeLinecap="round"/>
    {/* ZZZ sleep */}
    <text x="85" y="25" className="fill-muted-foreground/40" fontSize="12" fontWeight="bold">z</text>
    <text x="90" y="18" className="fill-muted-foreground/30" fontSize="10" fontWeight="bold">z</text>
    <text x="95" y="12" className="fill-muted-foreground/20" fontSize="8" fontWeight="bold">z</text>
  </svg>
)

// No Search Results Illustration
const NoSearchResultsIllustration = (props: React.SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
    {/* Magnifying glass */}
    <circle cx="50" cy="45" r="25" className="fill-muted stroke-muted-foreground/30" strokeWidth="2"/>
    <circle cx="50" cy="45" r="18" className="fill-background"/>
    <path d="M68 63L90 85" className="stroke-muted-foreground/40" strokeWidth="4" strokeLinecap="round"/>
    {/* Question mark */}
    <text x="42" y="52" className="fill-muted-foreground/40" fontSize="24" fontWeight="bold">?</text>
  </svg>
)

// Getting Started Illustration
const GettingStartedIllustration = (props: React.SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
    {/* Flag */}
    <path d="M30 85V15" className="stroke-muted-foreground/40" strokeWidth="3" strokeLinecap="round"/>
    <path d="M30 15L80 25L30 40V15Z" className="fill-primary/20 stroke-primary/60" strokeWidth="2"/>
    {/* Steps */}
    <circle cx="60" cy="60" r="6" className="fill-primary/30"/>
    <circle cx="75" cy="70" r="6" className="fill-primary/20"/>
    <circle cx="90" cy="80" r="6" className="fill-primary/10"/>
    {/* Sparkle */}
    <path d="M95 20L97 25L102 27L97 29L95 34L93 29L88 27L93 25L95 20Z" className="fill-primary/40"/>
  </svg>
)

// Connection Error Illustration
const ConnectionErrorIllustration = (props: React.SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
    {/* Cloud with X */}
    <path d="M25 60C20 60 15 55 15 50C15 45 20 40 25 40C25 30 35 20 50 20C65 20 75 30 75 40C80 40 90 45 90 55C90 65 80 70 70 70H30C25 70 25 65 25 60Z" className="fill-muted stroke-muted-foreground/30" strokeWidth="2"/>
    {/* X mark */}
    <path d="M45 40L65 60M65 40L45 60" className="stroke-destructive/60" strokeWidth="3" strokeLinecap="round"/>
    {/* Broken connection line */}
    <path d="M50 80L50 90M60 80L60 90" className="stroke-muted-foreground/30" strokeWidth="2" strokeLinecap="round" strokeDasharray="2 4"/>
  </svg>
)

// Success Illustration
const SuccessIllustration = (props: React.SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
    <circle cx="60" cy="50" r="35" className="fill-green-500/10 stroke-green-500/50" strokeWidth="2"/>
    <path d="M40 50L55 65L80 35" className="stroke-green-500" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"/>
    {/* Celebration sparkles */}
    <circle cx="25" cy="25" r="3" className="fill-green-500/40"/>
    <circle cx="95" cy="30" r="2" className="fill-green-500/30"/>
    <circle cx="90" cy="75" r="2.5" className="fill-green-500/35"/>
    <circle cx="30" cy="70" r="2" className="fill-green-500/30"/>
    <path d="M15 50L18 55L23 57L18 59L15 64L12 59L7 57L12 55L15 50Z" className="fill-green-500/30"/>
  </svg>
)

// Empty Inbox Illustration
const EmptyInboxIllustration = (props: React.SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
    {/* Inbox tray */}
    <path d="M15 50L25 25H95L105 50V80C105 82.7614 102.761 85 100 85H20C17.2386 85 15 82.7614 15 80V50Z" className="fill-muted stroke-muted-foreground/30" strokeWidth="2"/>
    <path d="M15 50H40L45 60H75L80 50H105" className="stroke-muted-foreground/30" strokeWidth="2"/>
    {/* Dashed inbox symbol */}
    <rect x="45" y="35" width="30" height="20" rx="2" className="stroke-muted-foreground/30" strokeWidth="2" strokeDasharray="4 2" fill="none"/>
    <path d="M52 42L60 48L68 42" className="stroke-muted-foreground/30" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)

// No Data Illustration
const NoDataIllustration = (props: React.SVGProps<SVGSVGElement>) => (
  <svg viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg" {...props}>
    {/* Database cylinders */}
    <ellipse cx="60" cy="25" rx="35" ry="10" className="fill-muted stroke-muted-foreground/30" strokeWidth="2"/>
    <path d="M25 25V75C25 80.5228 40.6701 85 60 85C79.3299 85 95 80.5228 95 75V25" className="fill-muted stroke-muted-foreground/30" strokeWidth="2"/>
    <ellipse cx="60" cy="75" rx="35" ry="10" className="stroke-muted-foreground/30" strokeWidth="2" fill="none"/>
    {/* Empty indicator */}
    <circle cx="60" cy="50" r="12" className="stroke-muted-foreground/40" strokeWidth="2" strokeDasharray="4 4"/>
    <path d="M55 50H65M60 45V55" className="stroke-muted-foreground/40" strokeWidth="2" strokeLinecap="round"/>
  </svg>
)

// Map illustration type to component
const illustrations: Record<IllustrationType, React.ComponentType<React.SVGProps<SVGSVGElement>>> = {
  'empty-folder': EmptyFolderIllustration,
  'empty-inbox': EmptyInboxIllustration,
  'no-data': NoDataIllustration,
  'no-environments': NoEnvironmentsIllustration,
  'no-workflows': NoWorkflowsIllustration,
  'no-deployments': NoDeploymentsIllustration,
  'no-pipelines': NoPipelinesIllustration,
  'no-incidents': NoIncidentsIllustration,
  'no-credentials': NoCredentialsIllustration,
  'no-activity': NoActivityIllustration,
  'no-search-results': NoSearchResultsIllustration,
  'getting-started': GettingStartedIllustration,
  'connection-error': ConnectionErrorIllustration,
  'success': SuccessIllustration,
}

const EmptyStateIllustration = React.forwardRef<SVGSVGElement, EmptyStateIllustrationProps>(
  ({ type, size = 'lg', className, ...props }, ref) => {
    const Illustration = illustrations[type] || NoDataIllustration

    return (
      <Illustration
        ref={ref}
        className={cn(sizeClasses[size], "mx-auto", className)}
        {...props}
      />
    )
  }
)
EmptyStateIllustration.displayName = "EmptyStateIllustration"

export { EmptyStateIllustration }
