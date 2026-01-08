/**
 * Informative Empty State Component
 *
 * Provides rich, contextual empty states that:
 * - Explain why content is missing
 * - Offer immediate actionable steps
 * - Include illustrations to communicate purpose
 * - Provide tutorial links or video walkthroughs
 * - Guide users to populate the area with prominent CTAs
 */
import * as React from "react"
import { cn } from "@/lib/utils"
import { Button } from "./button"
import { Card, CardContent } from "./card"
import { EmptyStateIllustration, type IllustrationType } from "./empty-state-illustration"
import { ExternalLink, Play, BookOpen, ArrowRight } from "lucide-react"
import type { LucideIcon } from "lucide-react"

interface HelpLink {
  /** Link text */
  label: string
  /** URL to navigate to */
  href: string
  /** Whether this is an external link (opens in new tab) */
  external?: boolean
  /** Icon to show before the label */
  icon?: LucideIcon
}

interface QuickAction {
  /** Button label */
  label: string
  /** Click handler */
  onClick: () => void
  /** Button variant */
  variant?: 'default' | 'secondary' | 'outline' | 'ghost'
  /** Icon to show in the button */
  icon?: LucideIcon
}

interface InformativeEmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  /** The main title explaining what's empty */
  title: string
  /** Detailed description explaining why it's empty and what the user can do */
  description: string
  /** Secondary text with additional context or tips */
  secondaryText?: string
  /** Illustration type to display */
  illustration?: IllustrationType
  /** Custom icon component (used if no illustration provided) */
  icon?: LucideIcon
  /** Primary call-to-action button */
  primaryAction?: QuickAction
  /** Secondary call-to-action button */
  secondaryAction?: QuickAction
  /** List of quick action buttons */
  quickActions?: QuickAction[]
  /** Help/tutorial links */
  helpLinks?: HelpLink[]
  /** Video tutorial link */
  videoTutorial?: {
    title: string
    url: string
    duration?: string
  }
  /** Feature bullets explaining what the user can do */
  featureBullets?: string[]
  /** Size variant */
  size?: 'sm' | 'md' | 'lg'
  /** Whether to show in a card wrapper */
  showCard?: boolean
  /** Custom content to render below the description */
  children?: React.ReactNode
}

const sizeClasses = {
  sm: {
    container: 'py-8 px-4',
    illustration: 'sm' as const,
    title: 'text-base font-medium',
    description: 'text-sm',
    spacing: 'space-y-3',
  },
  md: {
    container: 'py-12 px-6',
    illustration: 'md' as const,
    title: 'text-lg font-semibold',
    description: 'text-sm',
    spacing: 'space-y-4',
  },
  lg: {
    container: 'py-16 px-8',
    illustration: 'lg' as const,
    title: 'text-xl font-semibold',
    description: 'text-base',
    spacing: 'space-y-5',
  },
}

const InformativeEmptyState = React.forwardRef<HTMLDivElement, InformativeEmptyStateProps>(
  ({
    title,
    description,
    secondaryText,
    illustration,
    icon: Icon,
    primaryAction,
    secondaryAction,
    quickActions,
    helpLinks,
    videoTutorial,
    featureBullets,
    size = 'md',
    showCard = false,
    className,
    children,
    ...props
  }, ref) => {
    const sizes = sizeClasses[size]

    const content = (
      <div
        ref={ref}
        className={cn(
          "flex flex-col items-center justify-center text-center",
          sizes.container,
          sizes.spacing,
          className
        )}
        {...props}
      >
        {/* Illustration or Icon */}
        {illustration ? (
          <EmptyStateIllustration
            type={illustration}
            size={sizes.illustration}
            className="mb-2 opacity-90"
          />
        ) : Icon ? (
          <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-2">
            <Icon className="h-8 w-8 text-muted-foreground" />
          </div>
        ) : null}

        {/* Title */}
        <h3 className={cn(sizes.title, "text-foreground")}>{title}</h3>

        {/* Description */}
        <p className={cn(sizes.description, "text-muted-foreground max-w-md")}>
          {description}
        </p>

        {/* Secondary Text */}
        {secondaryText && (
          <p className="text-xs text-muted-foreground/80 max-w-sm italic">
            {secondaryText}
          </p>
        )}

        {/* Feature Bullets */}
        {featureBullets && featureBullets.length > 0 && (
          <ul className="mt-2 space-y-1.5 text-left max-w-sm">
            {featureBullets.map((bullet, index) => (
              <li key={index} className="flex items-start gap-2 text-sm text-muted-foreground">
                <ArrowRight className="h-4 w-4 mt-0.5 text-primary shrink-0" />
                <span>{bullet}</span>
              </li>
            ))}
          </ul>
        )}

        {/* Custom Children */}
        {children}

        {/* Primary & Secondary Actions */}
        {(primaryAction || secondaryAction) && (
          <div className="flex flex-wrap items-center justify-center gap-3 mt-2">
            {primaryAction && (
              <Button
                onClick={primaryAction.onClick}
                variant={primaryAction.variant || 'default'}
                className="gap-2"
              >
                {primaryAction.icon && <primaryAction.icon className="h-4 w-4" />}
                {primaryAction.label}
              </Button>
            )}
            {secondaryAction && (
              <Button
                onClick={secondaryAction.onClick}
                variant={secondaryAction.variant || 'outline'}
                className="gap-2"
              >
                {secondaryAction.icon && <secondaryAction.icon className="h-4 w-4" />}
                {secondaryAction.label}
              </Button>
            )}
          </div>
        )}

        {/* Quick Actions */}
        {quickActions && quickActions.length > 0 && (
          <div className="flex flex-wrap items-center justify-center gap-2 mt-2">
            {quickActions.map((action, index) => (
              <Button
                key={index}
                onClick={action.onClick}
                variant={action.variant || 'outline'}
                size="sm"
                className="gap-1.5"
              >
                {action.icon && <action.icon className="h-3.5 w-3.5" />}
                {action.label}
              </Button>
            ))}
          </div>
        )}

        {/* Video Tutorial */}
        {videoTutorial && (
          <a
            href={videoTutorial.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group flex items-center gap-3 mt-4 p-3 rounded-lg border bg-muted/50 hover:bg-muted transition-colors max-w-sm w-full"
          >
            <div className="flex items-center justify-center w-10 h-10 rounded-full bg-primary/10 text-primary group-hover:bg-primary/20 transition-colors">
              <Play className="h-5 w-5 ml-0.5" />
            </div>
            <div className="text-left">
              <p className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                {videoTutorial.title}
              </p>
              {videoTutorial.duration && (
                <p className="text-xs text-muted-foreground">
                  {videoTutorial.duration}
                </p>
              )}
            </div>
            <ExternalLink className="h-4 w-4 ml-auto text-muted-foreground group-hover:text-primary transition-colors" />
          </a>
        )}

        {/* Help Links */}
        {helpLinks && helpLinks.length > 0 && (
          <div className="flex flex-wrap items-center justify-center gap-4 mt-4 text-sm">
            {helpLinks.map((link, index) => {
              const LinkIcon = link.icon || (link.external ? ExternalLink : BookOpen)
              return (
                <a
                  key={index}
                  href={link.href}
                  target={link.external ? '_blank' : undefined}
                  rel={link.external ? 'noopener noreferrer' : undefined}
                  className="flex items-center gap-1.5 text-primary hover:underline"
                >
                  <LinkIcon className="h-3.5 w-3.5" />
                  {link.label}
                </a>
              )
            })}
          </div>
        )}
      </div>
    )

    if (showCard) {
      return (
        <Card className="border-dashed">
          <CardContent className="p-0">
            {content}
          </CardContent>
        </Card>
      )
    }

    return content
  }
)
InformativeEmptyState.displayName = "InformativeEmptyState"

export { InformativeEmptyState, type InformativeEmptyStateProps, type HelpLink, type QuickAction }
